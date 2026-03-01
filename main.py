import json
import asyncio
import openai
from openai import OpenAI, AsyncOpenAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prompts import (
    REFLEXION_PROMPT, REFINE_PROMPT, REVIEWER_PROMPT, SUGGESTIONS_PROMPT,
    JUDGE_PROMPT, REQUIRED_KEYS, build_system_prompt, build_meta_prompt,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

MODELS = [
    {"id": "gpt-4o-mini",  "label": "GPT-4o mini  — fastest, cheapest"},
    {"id": "gpt-4o",       "label": "GPT-4o        — best value"},
    {"id": "gpt-4.1-nano", "label": "GPT-4.1 nano  — cheapest 4.1"},
    {"id": "gpt-4.1-mini", "label": "GPT-4.1 mini  — balanced 4.1"},
    {"id": "gpt-4.1",      "label": "GPT-4.1        — highest quality"},
    {"id": "o4-mini",      "label": "o4-mini        — reasoning"},
]
ALLOWED_MODEL_IDS = {m["id"] for m in MODELS}


class GenerateRequest(BaseModel):
    use_case: str = Field(..., max_length=2000)
    model: str = "gpt-4o-mini"
    api_key: str


class GenerateResponse(BaseModel):
    system_prompt: str
    user_prompt: str
    reviewer_prompt: str
    weaknesses: list[str] = []
    raw_fields: dict = {}


class RefineRequest(BaseModel):
    system_prompt: str = Field(..., max_length=10000)
    user_prompt: str = Field(..., max_length=5000)
    feedback: str = Field(..., max_length=2000)
    use_case: str = Field(default="", max_length=2000)
    raw_fields: dict = {}
    refinement_history: list[str] = []
    model: str = "gpt-4o-mini"
    api_key: str


class SuggestionsRequest(BaseModel):
    system_prompt: str = Field(..., max_length=10000)
    user_prompt: str = Field(..., max_length=5000)
    weaknesses: list[str] = []
    api_key: str


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


def validate_api_key(api_key: str) -> None:
    if not api_key or not api_key.strip().startswith("sk-"):
        raise HTTPException(status_code=422, detail="Invalid API key format. OpenAI keys start with 'sk-'.")


def is_valid_use_case(text: str) -> bool:
    words = text.split()
    if len(text.strip()) < 8 or len(words) < 2:
        return False
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters:
        return False
    vowel_ratio = sum(1 for c in letters if c in "aeiou") / len(letters)
    return vowel_ratio >= 0.15


_GENERIC_ROLE_TERMS = {"helpful assistant", "ai assistant", "expert in various", "language model", "chatbot", "ai model"}

_META_REFS = {"as described above", "following the system prompt", "as mentioned", "per the system prompt", "see above"}


def _ape_score(data: dict, use_case: str = "") -> int:
    """Heuristic scorer for APE candidate selection. Returns 0–8."""
    score = 0

    # -- Role specificity (0-2)
    role = data.get("role_and_expertise", "").lower()
    if not any(t in role for t in _GENERIC_ROLE_TERMS):
        score += 2

    # -- Task objective structure (0-1)
    if "this is done when" in data.get("task_objective", "").lower():
        score += 1

    # -- Constraint density (0-1)
    constraints = data.get("constraints_and_assumptions", "")
    if constraints.count("- ") >= 3 or constraints.count("\n") >= 2:
        score += 1

    # -- Quality bar completeness (0-1)
    qb = data.get("quality_bar", "")
    fixed = ["reader is a senior", "every decision must", "where trade-offs", "no filler sentences"]
    if all(f in qb.lower() for f in fixed) and len(qb) > 350:
        score += 1

    # -- User prompt: self-contained, no meta-references (0-1)
    up = data.get("user_prompt", "").lower()
    if not any(ref in up for ref in _META_REFS):
        score += 1

    # -- User prompt: sufficient substance (0-1)
    up_words = data.get("user_prompt", "").split()
    if len(up_words) >= 50:
        score += 1

    # -- User prompt: specificity — contains terms from the original use case (0-1)
    if use_case:
        uc_words = {w.lower().strip(".,;:!?") for w in use_case.split() if len(w) > 3}
        up_lower = data.get("user_prompt", "").lower()
        matches = sum(1 for w in uc_words if w in up_lower)
        if matches >= min(3, len(uc_words)):
            score += 1

    return score


def _ape_weaknesses(data: dict, use_case: str = "") -> list[str]:
    """Return human-readable weakness descriptions based on which scoring criteria scored 0."""
    weaknesses = []

    role = data.get("role_and_expertise", "").lower()
    if any(t in role for t in _GENERIC_ROLE_TERMS):
        weaknesses.append("Role is generic — should name a specific seniority level and technical specialisation")

    if "this is done when" not in data.get("task_objective", "").lower():
        weaknesses.append("Task objective missing 'This is done when' success condition")

    constraints = data.get("constraints_and_assumptions", "")
    if constraints.count("- ") < 3 and constraints.count("\n") < 2:
        weaknesses.append("Too few constraints — should have at least 3 hard rules that eliminate alternatives")

    qb = data.get("quality_bar", "")
    fixed = ["reader is a senior", "every decision must", "where trade-offs", "no filler sentences"]
    if not all(f in qb.lower() for f in fixed) or len(qb) <= 350:
        weaknesses.append("Quality bar is incomplete — missing fixed rules or use-case-specific criteria")

    up = data.get("user_prompt", "").lower()
    if any(ref in up for ref in _META_REFS):
        weaknesses.append("User prompt is not self-contained — references the system prompt instead of standing alone")

    up_words = data.get("user_prompt", "").split()
    if len(up_words) < 50:
        weaknesses.append("User prompt is too short to be self-contained — needs more specifics and context")

    if use_case:
        uc_words = {w.lower().strip(".,;:!?") for w in use_case.split() if len(w) > 3}
        up_lower = data.get("user_prompt", "").lower()
        matches = sum(1 for w in uc_words if w in up_lower)
        if matches < min(3, len(uc_words)):
            weaknesses.append("User prompt doesn't reference enough specifics from the original use case")

    return weaknesses


def _compute_token_budget(use_case: str) -> int:
    """Adapt max token budget based on use case complexity."""
    word_count = len(use_case.split())
    if word_count < 30:
        return 4096
    if word_count < 80:
        return 6144
    return 8192


async def _gen_candidate(client: AsyncOpenAI, model: str, token_kwarg: str,
                         use_case: str, meta_prompt: str, token_budget: int) -> str:
    response = await client.chat.completions.create(
        model=model,
        **{token_kwarg: token_budget},
        messages=[
            {"role": "system", "content": meta_prompt},
            {"role": "user", "content": f"Use case: {use_case}"},
        ],
    )
    return response.choices[0].message.content.strip()


async def _reflect(client: AsyncOpenAI, model: str, token_kwarg: str, data: dict, use_case: str) -> str:
    user_content = f"Use case: {use_case}\n\nGenerated prompt:\n{json.dumps(data, indent=2)}"
    extra = {} if model.startswith("o") else {"temperature": 0.3}
    response = await client.chat.completions.create(
        model=model,
        **{token_kwarg: 8192},
        **extra,
        messages=[
            {"role": "system", "content": REFLEXION_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content.strip()


def _parse_raw(raw: str) -> str:
    if "```" in raw:
        raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw
        raw = raw.lstrip("json").strip()
    start = raw.find("{")
    if start > 0:
        raw = raw[start:]
    return raw


async def _llm_judge(client: AsyncOpenAI, candidates: list[dict],
                     use_case: str) -> tuple[dict, list[str]]:
    """Score all candidates via LLM judge. Returns (best_candidate, weaknesses).
    Falls back to _ape_score heuristic if the judge call fails."""

    if len(candidates) == 1:
        return candidates[0], _ape_weaknesses(candidates[0], use_case)

    # Format candidates for the judge
    candidate_blocks = []
    for i, c in enumerate(candidates, 1):
        candidate_blocks.append(f"Candidate {i}:\n{json.dumps(c, indent=2)}")
    candidates_text = "\n\n---\n\n".join(candidate_blocks)

    user_content = f"Use case: {use_case}\n\n{candidates_text}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-nano",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw = _parse_raw(response.choices[0].message.content.strip())
        result = json.loads(raw)

        best_idx = result.get("best", 1) - 1  # Convert 1-indexed to 0-indexed
        if not (0 <= best_idx < len(candidates)):
            best_idx = 0

        weaknesses = result.get("weaknesses", [])
        if not isinstance(weaknesses, list):
            weaknesses = []

        return candidates[best_idx], weaknesses

    except Exception:
        # Fallback to heuristic scoring
        best_data = candidates[0]
        best_score = -1
        for c in candidates:
            score = _ape_score(c, use_case)
            if score > best_score:
                best_score = score
                best_data = c
        return best_data, _ape_weaknesses(best_data, use_case)


@app.get("/models")
def get_models():
    return MODELS


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    validate_api_key(req.api_key)

    if not is_valid_use_case(req.use_case):
        raise HTTPException(status_code=422, detail="Input does not look like a valid use case. Please describe what you want to build or solve.")

    if req.model not in ALLOWED_MODEL_IDS:
        raise HTTPException(status_code=422, detail=f"Invalid model '{req.model}'. Allowed: {', '.join(sorted(ALLOWED_MODEL_IDS))}")

    client = AsyncOpenAI(api_key=req.api_key)
    token_kwarg = "max_completion_tokens" if req.model.startswith("o") else "max_tokens"

    # Domain-aware meta-prompt
    meta_prompt = build_meta_prompt(req.use_case)

    # Complexity-aware token budget
    token_budget = _compute_token_budget(req.use_case)

    # Step 1 — Self-Consistency: generate 3 candidates in parallel
    raws = await asyncio.gather(
        _gen_candidate(client, req.model, token_kwarg, req.use_case, meta_prompt, token_budget),
        _gen_candidate(client, req.model, token_kwarg, req.use_case, meta_prompt, token_budget),
        _gen_candidate(client, req.model, token_kwarg, req.use_case, meta_prompt, token_budget),
        return_exceptions=True,
    )

    for r in raws:
        if isinstance(r, openai.AuthenticationError):
            raise HTTPException(status_code=401, detail="Invalid API key. Check your OpenAI key and try again.")
        if isinstance(r, Exception):
            pass

    # Step 2 — Parse all candidates
    parsed_candidates: list[dict] = []
    for raw in raws:
        if isinstance(raw, Exception):
            continue
        try:
            data = json.loads(_parse_raw(raw))
        except json.JSONDecodeError:
            continue
        if not all(k in data for k in REQUIRED_KEYS):
            continue
        parsed_candidates.append(data)

    if not parsed_candidates:
        raise HTTPException(status_code=502, detail="Failed to parse model response. Please try again.")

    # Step 3 — LLM-as-Judge: score all candidates in a single call, fallback to APE heuristic
    best_data, weaknesses = await _llm_judge(client, parsed_candidates, req.use_case)

    # Step 4 — Reflexion: critique and improve the best candidate (with heuristic scoring gate)
    best_score = _ape_score(best_data, req.use_case)
    try:
        reflected_raw = _parse_raw(await _reflect(client, req.model, token_kwarg, best_data, req.use_case))
        final_data = json.loads(reflected_raw)
        if not all(k in final_data for k in REQUIRED_KEYS):
            final_data = best_data
        else:
            # Scoring gate: only use reflected version if it scores >= the original
            reflected_score = _ape_score(final_data, req.use_case)
            if reflected_score < best_score:
                final_data = best_data
            else:
                # Re-check weaknesses for the improved version
                weaknesses = _ape_weaknesses(final_data, req.use_case)
    except Exception:
        final_data = best_data

    return GenerateResponse(
        system_prompt=build_system_prompt(final_data),
        user_prompt=final_data["user_prompt"],
        reviewer_prompt=REVIEWER_PROMPT,
        weaknesses=weaknesses,
        raw_fields=final_data,
    )


@app.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(req: SuggestionsRequest) -> SuggestionsResponse:
    validate_api_key(req.api_key)

    client = AsyncOpenAI(api_key=req.api_key)

    # Build user content with weaknesses if available
    user_content = f"System prompt:\n{req.system_prompt}\n\nUser prompt:\n{req.user_prompt}"
    if req.weaknesses:
        weakness_text = "\n".join(f"- {w}" for w in req.weaknesses)
        user_content += f"\n\nIdentified weaknesses:\n{weakness_text}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            messages=[
                {"role": "system", "content": SUGGESTIONS_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
    except openai.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key. Check your OpenAI key and try again.")

    raw = _parse_raw(response.choices[0].message.content.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Failed to parse suggestions.")

    items = data.get("suggestions", [])
    if len(items) < 3:
        raise HTTPException(status_code=502, detail="Could not generate suggestions.")

    return SuggestionsResponse(suggestions=items[:3])


@app.post("/refine", response_model=GenerateResponse)
async def refine(req: RefineRequest) -> GenerateResponse:
    validate_api_key(req.api_key)

    if not req.feedback.strip():
        raise HTTPException(status_code=422, detail="Feedback cannot be empty.")

    if req.model not in ALLOWED_MODEL_IDS:
        raise HTTPException(status_code=422, detail=f"Invalid model '{req.model}'.")

    client = AsyncOpenAI(api_key=req.api_key)
    token_kwarg = "max_completion_tokens" if req.model.startswith("o") else "max_tokens"

    # Apply feedback surgically on top of the existing raw JSON fields
    if req.raw_fields and all(k in req.raw_fields for k in REQUIRED_KEYS):
        existing = f"Existing prompt fields:\n{json.dumps(req.raw_fields, indent=2)}"
    else:
        existing = f"Existing system prompt:\n{req.system_prompt}\n\nExisting user prompt:\n{req.user_prompt}"

    user_content = f"{existing}\n\nFeedback:\n{req.feedback}"

    if req.refinement_history:
        history_text = "\n".join(f"{i+1}. {h}" for i, h in enumerate(req.refinement_history))
        user_content += f"\n\nPrevious refinements (preserve these changes):\n{history_text}"

    try:
        extra = {} if req.model.startswith("o") else {"temperature": 0.1}
        response = await client.chat.completions.create(
            model=req.model,
            **{token_kwarg: 8192},
            **extra,
            messages=[
                {"role": "system", "content": REFINE_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
    except openai.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key. Check your OpenAI key and try again.")

    raw = _parse_raw(response.choices[0].message.content.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Failed to parse model response. Please try again.")

    if not all(k in data for k in REQUIRED_KEYS):
        raise HTTPException(status_code=502, detail="Model response was incomplete. Please try again.")

    weaknesses = _ape_weaknesses(data)

    return GenerateResponse(
        system_prompt=build_system_prompt(data),
        user_prompt=data["user_prompt"],
        reviewer_prompt=REVIEWER_PROMPT,
        weaknesses=weaknesses,
        raw_fields=data,
    )
