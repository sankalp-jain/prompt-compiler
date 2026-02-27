import os
import json
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from prompts import META_PROMPT, REFINE_PROMPT, REVIEWER_PROMPT, REQUIRED_KEYS, build_system_prompt

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
    use_case: str
    model: str = "gpt-4o-mini"


class GenerateResponse(BaseModel):
    system_prompt: str
    user_prompt: str
    reviewer_prompt: str


class RefineRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    feedback: str
    model: str = "gpt-4o-mini"


def is_valid_use_case(text: str) -> bool:
    words = text.split()
    if len(text.strip()) < 8 or len(words) < 2:
        return False
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters:
        return False
    vowel_ratio = sum(1 for c in letters if c in "aeiou") / len(letters)
    return vowel_ratio >= 0.15


@app.get("/models")
def get_models():
    return MODELS


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    if not is_valid_use_case(req.use_case):
        raise HTTPException(status_code=422, detail="Input does not look like a valid use case. Please describe what you want to build or solve.")

    if req.model not in ALLOWED_MODEL_IDS:
        raise HTTPException(status_code=422, detail=f"Invalid model '{req.model}'. Allowed: {', '.join(sorted(ALLOWED_MODEL_IDS))}")

    # o-series reasoning models use max_completion_tokens instead of max_tokens
    token_kwarg = "max_completion_tokens" if req.model.startswith("o") else "max_tokens"

    response = client.chat.completions.create(
        model=req.model,
        **{token_kwarg: 8192},
        messages=[
            {"role": "system", "content": META_PROMPT},
            {"role": "user", "content": f"Use case: {req.use_case}"},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wrapped its output
    if "```" in raw:
        raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw
        raw = raw.lstrip("json").strip()

    # Skip any preamble before the JSON object
    start = raw.find("{")
    if start > 0:
        raw = raw[start:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {raw}")

    if not all(k in data for k in REQUIRED_KEYS):
        raise HTTPException(status_code=502, detail=f"LLM response missing required keys: {data}")

    return GenerateResponse(
        system_prompt=build_system_prompt(data),
        user_prompt=data["user_prompt"],
        reviewer_prompt=REVIEWER_PROMPT,
    )


@app.post("/refine", response_model=GenerateResponse)
def refine(req: RefineRequest) -> GenerateResponse:
    if not req.feedback.strip():
        raise HTTPException(status_code=422, detail="Feedback cannot be empty.")

    if req.model not in ALLOWED_MODEL_IDS:
        raise HTTPException(status_code=422, detail=f"Invalid model '{req.model}'.")

    token_kwarg = "max_completion_tokens" if req.model.startswith("o") else "max_tokens"

    user_content = (
        f"Existing system prompt:\n{req.system_prompt}\n\n"
        f"Existing user prompt:\n{req.user_prompt}\n\n"
        f"Feedback:\n{req.feedback}"
    )

    response = client.chat.completions.create(
        model=req.model,
        **{token_kwarg: 8192},
        messages=[
            {"role": "system", "content": REFINE_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw = response.choices[0].message.content.strip()

    if "```" in raw:
        raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw
        raw = raw.lstrip("json").strip()

    start = raw.find("{")
    if start > 0:
        raw = raw[start:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {raw}")

    if not all(k in data for k in REQUIRED_KEYS):
        raise HTTPException(status_code=502, detail=f"LLM response missing required keys: {data}")

    return GenerateResponse(
        system_prompt=build_system_prompt(data),
        user_prompt=data["user_prompt"],
        reviewer_prompt=REVIEWER_PROMPT,
    )
