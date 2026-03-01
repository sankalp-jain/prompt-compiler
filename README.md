# Prompt Compiler

Turn a plain-English use case into a structured, production-ready LLM prompt.

## What it does

You describe what you want to build or solve. The tool generates three outputs:

- **System Prompt** — five enforced sections: role & expertise, task objective, constraints & assumptions, required output structure, quality bar.
- **User Prompt** — self-contained, imperative, ready to paste into any LLM.
- **Reviewer Prompt** — a senior architect checklist to critique the model's response.

You can then refine the prompts iteratively using the in-app feedback loop.

## Pipeline flows

```
User action
│
├── /generate
│   ├── 1. Domain classifier (keyword) → pick few-shot example
│   ├── 2. Self-Consistency → 3 candidates generated in parallel
│   ├── 3. LLM-as-Judge (gpt-4.1-nano) → score all 3, pick best
│   │        └── fallback: APE heuristic scorer if judge call fails
│   ├── 4. Reflexion (temperature=0.3) → critique + rewrite best candidate
│   │        └── scoring gate: keep reflected version only if score ≥ original
│   └── 5. Weakness analysis → feeds /suggestions
│
└── /refine
    └── 1. REFINE_PROMPT (temperature=0.1) → surgical edit on raw JSON fields
             only fields targeted by feedback are changed; all others copied verbatim
             refinement history passed to prevent reverting earlier changes
```

**LLM call count per action:**

| Action | Calls |
|---|---|
| /generate | 5 (3 candidates + judge + reflexion) |
| /refine | 1 |
| /suggestions | 1 |

## Running locally

**Requirements:** Python 3.11+, an OpenAI API key.

```bash
# 1. Clone and install dependencies
git clone https://github.com/sankalp-jain/ai-prompt.git
cd ai-prompt
pip install fastapi uvicorn openai pydantic

# 2. Start the backend
uvicorn main:app --reload --port 8000

# 3. Serve the frontend (any static file server)
python3 -m http.server 8001

# 4. Open http://localhost:8001/index.html
```

Enter your OpenAI API key in the UI when prompted. Keys are stored in your browser session only and never saved on the server.

## Configuring the API URL (for deployment)

The frontend defaults to `http://localhost:8000`. To point it at a deployed backend, set `window.ENV_API_URL` before `app.js` loads:

```html
<script>window.ENV_API_URL = "https://your-backend.com";</script>
<script src="app.js"></script>
```

## Project structure

```
main.py            — FastAPI routes: /generate, /refine, /suggestions, /models
                   — LLM-as-judge scoring, APE heuristic fallback, reflexion gate
prompts.py         — Meta-prompt template, 6 domain-specific few-shot examples,
                     domain detection, REFLEXION_PROMPT, REFINE_PROMPT,
                     JUDGE_PROMPT, SUGGESTIONS_PROMPT, build_system_prompt()
index.html         — HTML structure + Tailwind CSS
app.js             — Frontend logic: generation, refinement, history, suggestions
test_pipeline.py   — End-to-end test suite (10 cases, all flows)
```

The meta-prompt in `prompts.py` is a template that adapts to the use case domain. `detect_domain()` classifies the use case (backend, frontend, data, DevOps, ML, general) via keyword matching, and `build_meta_prompt()` inserts a domain-specific few-shot example.

The meta-prompt instructs the LLM to:

1. Analyse the use case internally (goal, stack, constraints, depth) before writing.
2. Write six JSON fields — each with specific rules that prevent generic output:
   - `role_and_expertise` — must name an exact role and technology. Generic roles ("helpful assistant", "AI") are explicitly prohibited.
   - `task_objective` — exactly two sentences: deliverable and success condition.
   - `constraints_and_assumptions` — each bullet must eliminate at least one alternative approach. Descriptive bullets are rejected.
   - `required_output_structure` — each section must specify what questions it answers, what it must not omit, and expected depth.
   - `quality_bar` — four fixed rules (senior reader, explicit decisions, named trade-offs, no filler) plus at least one use-case-specific criterion.
   - `user_prompt` — self-contained, imperative, written as if the system prompt does not exist.

The six fields are assembled in `build_system_prompt()` in code — structure is enforced by schema, not model behaviour.

## Supported models

| Model | Notes | Cost / generate | Cost / refine |
|---|---|---|---|
| gpt-4.1-nano | Cheapest | ~$0.001 | ~$0.0001 |
| gpt-4o-mini | Default | ~$0.002 | ~$0.0002 |
| gpt-4.1-mini | Recommended for daily use | ~$0.004 | ~$0.0004 |
| gpt-4.1 | Highest quality | ~$0.015–0.020 | ~$0.002 |
| gpt-4o | Strong alternative | ~$0.020–0.030 | ~$0.003 |
| o4-mini | Best for complex use cases (reasoning model) | ~$0.05+ | ~$0.005 |

Generate cost covers 5 LLM calls (3 candidates + judge + reflexion). The UI shows a cost warning when a higher-priced model is selected.

## Testing

`test_pipeline.py` is an end-to-end test suite that hits the live backend with real OpenAI calls. No mocks.

> **Note:** The test suite is currently commented out. Uncomment `test_pipeline.py` before running.

```bash
# Backend must be running on port 8000
export OPENAI_API_KEY=sk-...
python3 test_pipeline.py
```

**10 test cases across all flows:**

| TC | Flow | What it checks |
|---|---|---|
| TC1 | generate — backend | Domain detection, all 5 system prompt sections, raw_fields structure |
| TC2 | generate — frontend | Same structural checks for frontend domain |
| TC3 | generate — ml | Same structural checks for ML domain |
| TC4 | generate — devops | Same structural checks for DevOps domain |
| TC5 | generate — general | Same + captures weaknesses for TC10 |
| TC6 | refine | Adding a section — untargeted fields preserved (≥60% word overlap) |
| TC7 | refine | Changing role seniority — targeted field changed, others preserved |
| TC8 | refine | Tech swap (AWS → Azure equivalent) — only relevant fields change |
| TC9 | refine | Constraint removal — untargeted fields unchanged |
| TC10 | suggestions | 3 suggestions returned, each ≥5 words |

The suite exits with a per-flow pass rate summary.

## Prompt engineering techniques

| Technique | Where applied | What it does |
|---|---|---|
| **Few-shot prompting** | `/generate` — meta-prompt | Domain-specific example (backend, frontend, data, DevOps, ML, general) is injected into the meta-prompt to calibrate output quality before the model writes a single field |
| **Self-consistency** | `/generate` — step 2 | 3 candidates generated in parallel with the same prompt; variance across outputs exposes weak phrasings that a single call would lock in |
| **LLM-as-Judge** | `/generate` — step 3 | A separate gpt-4.1-nano call scores all 3 candidates on 6 structured criteria and selects the best; removes human bias from candidate selection |
| **APE (Automatic Prompt Engineer) heuristic** | `/generate` — judge fallback | Rule-based scorer (0–8) used when the judge call fails; scores role specificity, constraint density, quality bar completeness, and user prompt substance |
| **Reflexion** | `/generate` — step 4 | The best candidate is critiqued and rewritten by a second LLM call at temperature=0.3; a scoring gate discards the reflected version if it regresses |
| **Chain-of-thought (internal)** | Meta-prompt STEP 1 | Model is instructed to analyse goal, depth, and stack internally before writing any field; output of the analysis is never emitted |
| **Schema-enforced output** | All generation calls | All LLM outputs are constrained to a fixed 6-key JSON schema; structure is validated in code, not trusted from model behaviour |
| **Temperature control** | `/refine` | temperature=0.1 on refine calls enforces surgical edits — low temperature prevents the model from creatively rewriting fields it was not asked to change |
| **Prompt chaining with state** | `/refine` | Raw JSON fields from the previous generate/refine are passed back verbatim on every refine call, so the model edits a structured object rather than reconstructing from rendered markdown |
| **Refinement history** | `/refine` | All previous feedback instructions are appended to the refine prompt, preventing the model from reverting changes made in earlier iterations |
| **Weakness-aware suggestions** | `/suggestions` | Identified weaknesses from the APE scorer are passed to the suggestions prompt, biasing at least 2 of 3 suggestions toward the actual gaps in the current prompt |

## Known limitations

- Domain detection is keyword-based — ambiguous use cases may get a suboptimal few-shot example, though the model adapts regardless.
- No persistence — prompts are stored in browser session only.
- Frontend must be configured with the backend URL for non-local deployment.
