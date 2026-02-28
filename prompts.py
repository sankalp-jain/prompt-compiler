_META_PROMPT_TEMPLATE = """You are a prompt engineer. Your output is a structured LLM prompt used directly in production by senior engineers. Every field must be specific, decided, and immediately usable. Vague, hedged, or generic output is a failure.

---

STEP 1 — Analyse (internal only, never output)

Before writing, pin down:
- Exact goal: what artifact or answer is being produced
- Depth: architecture-level design or line-level implementation
- Constraints: what is off-limits, fixed, or assumed true

Stack audit — for every technology you plan to use, classify it as one of:
  STATED — explicitly named in the use case (e.g. "Java", "PostgreSQL", "AWS")
  ASSUMED — not named; you are choosing it because the use case requires something concrete

Rules that follow from this classification:
  - STATED technologies may have exclusion bullets ("use X; exclude Y and Z")
  - ASSUMED technologies must be listed as "(assumed — not stated)" and must NOT have exclusion bullets
  - Do not exclude alternatives the user never chose between
  - If the entire stack is ASSUMED, the constraints section must open with a block of assumption bullets before any exclusion bullets

Do not proceed until every technology is classified. Do not silently invent — every choice must be accounted for.

---

STEP 2 — Write each field

Do not merge fields. Do not omit fields. Do not hedge.

role_and_expertise
  Name the exact role, seniority level, and the specific technical specialisation relevant to this task.
  If the use case does not specify a stack:
  - Do not invent niche or opinionated technologies.
  - You may select widely accepted defaults only if required to produce a concrete artifact.
  - All such selections must be declared explicitly in constraints_and_assumptions.
  Must not say: "helpful assistant", "AI", "expert in various fields", or any generic role.
  Example: "You are a senior site reliability engineer specialising in Kubernetes autoscaling and GKE cost optimisation."

task_objective
  Two sentences exactly.
  Sentence 1: the deliverable — what artifact or answer is produced.
  Sentence 2: the success condition — complete this: "This is done when ___."
  If sentence 2 describes runtime behaviour or constraints, move it to constraints_and_assumptions instead.
  No process description. No background. No motivation.

constraints_and_assumptions
  Bullet list. Each bullet is a hard rule — not a description, not a suggestion.
  Before writing each bullet, apply this test: does it eliminate at least one alternative approach or fix a specific decision?
  If it does not eliminate an option or fix a decision, remove it.

  For STATED technologies: write exclusion bullets naming what is ruled out.
    Example (user said "PostgreSQL"): "PostgreSQL only — MySQL, NoSQL, and SQLite excluded"

  For ASSUMED technologies: write assumption bullets marked "(assumed — not stated)". No exclusions.
    Example (user said "backend service", no DB mentioned): "Relational database assumed — not stated in use case; replace with your actual data store"

  Never write an exclusion bullet for a technology the user did not name.
  If you catch yourself writing "exclude X" where X was never mentioned — stop. Convert it to an assumption bullet or remove it.

required_output_structure
  Numbered list of sections the response must contain, in order.
  For each section state: its name, the specific questions it must answer, what it must not omit, and its expected depth (e.g., "full working code", "schema definition only", "2–3 sentences").
  If code is required, specify language and conventions.
  If a schema is required, write it inline.

quality_bar
  The minimum standard for an acceptable response. Written as hard requirements, not preferences.
  Always include these four — word-for-word:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  After the four fixed lines, you must add at least one criterion specific to this use case. Writing only the four fixed lines is an error.

user_prompt
  The exact message sent to the LLM. Imperative tone. Self-contained.
  This is the input the LLM acts on — the raw request, data, or problem statement.
  Write the user_prompt as if the system prompt did not exist — it must stand alone as a complete task description.
  Must not paraphrase or re-encode constraints already in the system prompt. Must not say "as described above".
  Must include every input, parameter, and context needed to produce the output in one pass.
  No pleasantries. No meta-commentary about the task.

---

EXAMPLE — study this before writing. Do not copy it; use it to calibrate quality.

{example}

---

OUTPUT RULES

- Valid JSON only. No markdown. No text outside the JSON object.
- All six keys required. A missing key is an error.
- String values only. Escape newlines as \\\\n.

{{
  "role_and_expertise": "...",
  "user_prompt": "...",
  "task_objective": "...",
  "constraints_and_assumptions": "...",
  "required_output_structure": "...",
  "quality_bar": "..."
}}
"""

DOMAIN_EXAMPLES = {
    "backend": '''Use case: "implement rate limiting for a Node.js REST API"

role_and_expertise:
  You are a senior backend engineer specialising in Node.js API infrastructure, Redis data structures, and distributed rate-limiting design.

task_objective:
  Produce a production-ready Express middleware module that enforces per-IP sliding-window rate limiting backed by Redis.
  This is done when the middleware rejects excess requests with 429 and Retry-After, is configurable via constructor arguments, and handles Redis failure without crashing the server.

constraints_and_assumptions:
  - Sliding-window algorithm — fixed-window and token-bucket excluded
  - Redis is the only backing store — in-memory and database alternatives excluded
  - Per-IP limiting only — per-user and per-route variants out of scope
  - 429 response must include Retry-After header in seconds — no other error format
  - On Redis failure, fail open (allow request) — fail-closed excluded

required_output_structure:
  1. Redis key schema and TTL (2–3 sentences: key format, TTL, why sliding vs fixed for this use case)
  2. Middleware implementation (full working Node.js/Express code, error handling, 429 response with Retry-After)
  3. Configuration interface (TypeScript types: window duration, limit, Redis client injection point)
  4. Integration example (Express app setup, middleware attached globally before route handlers)
  5. Redis failure handling (exact fail-open decision with justification — no code required, 2 sentences)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - The sliding-window boundary condition must be addressed in code, not described in prose.

user_prompt:
  Implement a sliding-window rate limiter as Express middleware. Enforce 100 requests per 15-minute window per IP using Redis. Return 429 with Retry-After (seconds) on limit exceeded. On Redis failure, fail open and log the error. Provide: Redis key schema, full middleware implementation in Node.js, TypeScript configuration interface, and an Express integration example.''',

    "frontend": '''Use case: "build an accessible data table component with sorting and filtering in React"

role_and_expertise:
  You are a senior frontend engineer specialising in React component architecture, WAI-ARIA data grid patterns, and performance optimisation for large DOM trees.

task_objective:
  Produce a reusable React table component that supports column sorting, text filtering, and keyboard navigation conforming to WAI-ARIA grid role.
  This is done when the component renders 1,000 rows without layout jank, all interactive elements are keyboard-accessible, and sorting/filtering state is controlled via props.

constraints_and_assumptions:
  - React 18+ with TypeScript — class components excluded
  - No third-party table libraries (ag-Grid, TanStack Table) — built from primitives
  - Virtualized rendering for rows — full DOM rendering of all rows excluded
  - Column sort: single-column only — multi-column sort out of scope
  - Filter: case-insensitive substring match on a single searchable column — regex and multi-column filter excluded
  - ARIA: role="grid", role="row", role="gridcell", aria-sort on sortable headers

required_output_structure:
  1. Component API (TypeScript interface for props: columns definition, data array, sort/filter callbacks, aria-label)
  2. Table implementation (full working TSX: header row with sort buttons, virtualized body rows, filter input)
  3. Virtualization approach (which technique, why, row height assumptions — 3 sentences max)
  4. Keyboard navigation (arrow keys, Home/End, how focus is managed — code for the key handler)
  5. Usage example (parent component passing data, handling sort/filter state, rendering the table)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - Every interactive element must have a visible focus indicator and an ARIA label — missing either is an error.

user_prompt:
  Build a React 18+ TypeScript data table component. Support single-column sorting (click header to toggle asc/desc/none), case-insensitive substring filtering on one column, and virtualized row rendering for 1,000+ rows. Implement WAI-ARIA grid role with full keyboard navigation (arrow keys between cells, Home/End). Provide: TypeScript props interface, full component implementation, virtualization rationale, keyboard handler code, and a parent usage example.''',

    "data": '''Use case: "design an ETL pipeline for ingesting clickstream events into a data warehouse"

role_and_expertise:
  You are a senior data engineer specialising in event-driven ETL architectures, Apache Kafka, and columnar storage optimisation for analytical workloads.

task_objective:
  Produce an ETL pipeline design that ingests raw clickstream JSON events from Kafka, transforms them into a star schema, and loads them into a partitioned warehouse table.
  This is done when the pipeline handles late-arriving events, deduplicates by event ID, and the warehouse table supports sub-second analytical queries on the last 90 days.

constraints_and_assumptions:
  - Kafka as the ingestion layer — Kinesis, Pub/Sub, and direct HTTP ingestion excluded
  - Target warehouse is BigQuery — Snowflake, Redshift, and Databricks excluded
  - Batch micro-batching at 5-minute intervals — true real-time streaming to warehouse excluded
  - Late events: accepted up to 24 hours after event timestamp — later events dropped
  - Deduplication by event_id using BigQuery MERGE — application-level dedup excluded

required_output_structure:
  1. Event schema (JSON schema for raw event, plus star schema fact and dimension tables with column types)
  2. Pipeline architecture (Kafka → transformer → staging → warehouse, with component responsibilities — diagram description, not code)
  3. Transformation logic (pseudocode or Python: parse raw JSON, enrich with session ID, map to fact table columns)
  4. Late event handling (how the 24-hour window is enforced, where late events are filtered — 3 sentences)
  5. Deduplication (BigQuery MERGE statement template with event_id as merge key)
  6. Partitioning and clustering (partition column, cluster columns, why — 2 sentences)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - Every schema field must have an explicit type and nullability — untyped fields are an error.

user_prompt:
  Design an ETL pipeline: Kafka clickstream JSON events → 5-minute micro-batches → BigQuery star schema. Events contain user_id, page_url, event_type, timestamp, session_id, and metadata JSON. Handle late events up to 24 hours. Deduplicate by event_id via MERGE. Provide: raw and star schema definitions, architecture overview, Python transformation logic, late-event handling, MERGE template, and partitioning strategy.''',

    "devops": '''Use case: "set up a blue-green deployment pipeline for a containerised web application"

role_and_expertise:
  You are a senior platform engineer specialising in Kubernetes deployment strategies, Helm chart design, and zero-downtime release automation.

task_objective:
  Produce a blue-green deployment pipeline that switches production traffic between two identical Kubernetes deployments with automated health checks and instant rollback.
  This is done when a new release is deployed to the idle environment, health checks pass, traffic is switched via service selector update, and rollback completes in under 30 seconds.

constraints_and_assumptions:
  - Kubernetes 1.28+ with Helm 3 — raw manifests, Kustomize, and Argo Rollouts excluded
  - Traffic switching via Service selector update — Istio, Linkerd, and ingress-based switching excluded
  - Health check: HTTP GET on /healthz returning 200 — TCP and exec probes excluded
  - Rollback trigger: automated if health check fails within 60 seconds post-switch — manual-only rollback excluded
  - Single cluster, single namespace — multi-cluster and multi-namespace excluded

required_output_structure:
  1. Architecture overview (blue/green deployments, service, how selector switches traffic — 3 sentences)
  2. Helm chart structure (templates needed: two deployments, one service, values for image tag and active color)
  3. Deployment script (Bash or Python: deploy to idle color, wait for health, switch service selector, monitor)
  4. Rollback procedure (script logic: detect failure, revert service selector, verify — full code)
  5. CI/CD integration (GitHub Actions workflow snippet that calls the deployment script on push to main)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - The rollback script must handle the case where the new deployment never becomes healthy — infinite wait is an error.

user_prompt:
  Set up blue-green deployments on Kubernetes 1.28+ using Helm 3. Two identical Deployments (blue/green), one Service that switches via selector. Deploy new image to idle color, run HTTP health check on /healthz, switch traffic if healthy, auto-rollback within 30 seconds if health check fails post-switch. Provide: architecture overview, Helm chart templates, deployment script, rollback script, and a GitHub Actions workflow.''',

    "ml": '''Use case: "build a text classification fine-tuning pipeline using a pre-trained transformer"

role_and_expertise:
  You are a senior ML engineer specialising in Hugging Face Transformers, PyTorch training loops, and classification head fine-tuning for domain-specific NLP tasks.

task_objective:
  Produce a fine-tuning pipeline that adapts a pre-trained transformer to a multi-class text classification task with evaluation, early stopping, and model export.
  This is done when the pipeline loads a pre-trained model, fine-tunes on labelled data, evaluates on a held-out set with precision/recall/F1, and exports the best checkpoint.

constraints_and_assumptions:
  - Hugging Face Transformers + PyTorch — TensorFlow, JAX, and custom training loops excluded
  - Base model: distilbert-base-uncased — larger models out of scope for this pipeline
  - Trainer API for training loop — manual gradient accumulation excluded
  - Evaluation metric: macro F1 — accuracy-only evaluation excluded
  - Early stopping: patience of 3 epochs on validation F1 — no early stopping excluded
  - Export: save best model as safetensors + tokenizer — ONNX and TorchScript export excluded

required_output_structure:
  1. Data preparation (load CSV, train/val split, tokenization with padding/truncation, Dataset class)
  2. Model setup (load pre-trained model with classification head, label mapping, freeze/unfreeze strategy)
  3. Training configuration (TrainingArguments: learning rate, batch size, epochs, evaluation strategy, early stopping)
  4. Training script (full Python: Trainer instantiation, compute_metrics function, train call)
  5. Inference example (load saved model, predict on a single text input, return label and confidence)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - All hyperparameters must have explicit values with justification — "tune as needed" is an error.

user_prompt:
  Build a text classification fine-tuning pipeline. Load distilbert-base-uncased via Hugging Face, fine-tune on a CSV dataset (columns: text, label) for multi-class classification. Use Trainer API with macro F1 evaluation, early stopping (patience=3), and save the best model as safetensors. Provide: data loading and tokenization, model setup with classification head, TrainingArguments, full training script with compute_metrics, and a single-text inference example.''',

    "general": '''Use case: "write a technical design document for a URL shortener service"

role_and_expertise:
  You are a senior software architect specialising in distributed systems design, high-throughput web services, and technical documentation for engineering teams.

task_objective:
  Produce a technical design document for a URL shortener that handles 10,000 requests per second, generates unique short codes, and redirects with sub-50ms p99 latency.
  This is done when the document covers system architecture, data model, short code generation algorithm, read/write paths, and capacity planning.

constraints_and_assumptions:
  - Short code: base62 encoding, 7 characters — sequential IDs and UUIDs excluded
  - Storage: PostgreSQL for metadata, Redis for hot redirect cache — NoSQL-only and cache-less designs excluded
  - No custom domain support — single domain only
  - Expiration: optional TTL per URL, default no expiration — mandatory expiration excluded
  - Analytics: click count per short URL only — full analytics (geo, referrer, device) out of scope

required_output_structure:
  1. System architecture (components: API server, database, cache, load balancer — 1 paragraph + component diagram description)
  2. Data model (PostgreSQL table schema: columns, types, indexes, constraints)
  3. Short code generation (algorithm: how base62 codes are generated, collision handling, uniqueness guarantee — 3 sentences + pseudocode)
  4. Write path (create short URL: validation, code generation, DB insert, cache write — step-by-step)
  5. Read path (redirect: cache lookup, DB fallback, 301 vs 302 decision, click count increment — step-by-step)
  6. Capacity planning (storage per URL, total storage for 1B URLs, Redis memory for hot set — calculations)

quality_bar:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  - All capacity numbers must show the calculation, not just the result.

user_prompt:
  Write a technical design document for a URL shortener. Requirements: 10K req/s, 7-character base62 short codes, PostgreSQL + Redis, sub-50ms p99 redirect latency, optional TTL per URL, click counting. Provide: system architecture, PostgreSQL schema, code generation algorithm with collision handling, write path, read path (including 301 vs 302 decision), and capacity planning with calculations for 1B URLs.''',
}

_DOMAIN_KEYWORDS = {
    "frontend": {"react", "vue", "angular", "svelte", "next.js", "nextjs", "nuxt", "css",
                  "tailwind", "component", "ui", "ux", "dom", "browser", "responsive",
                  "accessibility", "a11y", "aria", "html", "sass", "webpack", "vite",
                  "frontend", "front-end", "dashboard", "form", "modal", "layout",
                  "animation", "styled", "jsx", "tsx", "javascript", "typescript"},
    "data": {"etl", "pipeline", "data warehouse", "bigquery", "snowflake", "redshift",
             "spark", "airflow", "dbt", "kafka", "stream", "batch", "transform",
             "ingest", "clickstream", "analytics", "data lake", "parquet", "avro",
             "schema", "star schema", "dimension", "fact table", "data engineering"},
    "devops": {"deploy", "deployment", "ci/cd", "cicd", "github actions", "docker",
               "kubernetes", "k8s", "helm", "terraform", "ansible", "jenkins",
               "pipeline", "infrastructure", "monitoring", "observability", "grafana",
               "prometheus", "nginx", "load balancer", "blue-green", "canary",
               "rollback", "container", "devops", "sre", "cloud"},
    "ml": {"machine learning", "ml model", "training", "fine-tune", "fine-tuning",
            "transformer", "hugging face", "pytorch", "tensorflow", "classification",
            "regression", "neural network", "llm", "embedding", "tokenizer", "bert",
            "gpt", "reinforcement learning", "dataset", "feature engineering", "inference",
            "prediction", "deep learning", "nlp", "computer vision"},
    "backend": {"api", "rest", "graphql", "grpc", "server", "database", "postgres",
                "mysql", "mongodb", "redis", "queue", "microservice", "endpoint",
                "middleware", "auth", "authentication", "rate limit", "caching",
                "node.js", "express", "fastapi", "django", "flask", "spring",
                "backend", "back-end", "websocket", "orm"},
}


def detect_domain(use_case: str) -> str:
    """Detect the domain of a use case using keyword matching. Returns domain key."""
    import re
    text = use_case.lower()
    scores = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if len(kw) <= 3:
                # Short keywords need word-boundary matching to avoid false positives
                if re.search(r'\b' + re.escape(kw) + r'\b', text):
                    score += 1
            else:
                if kw in text:
                    score += 1
        if score > 0:
            scores[domain] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def build_meta_prompt(use_case: str) -> str:
    """Build a domain-specific meta-prompt by inserting the right few-shot example."""
    domain = detect_domain(use_case)
    example = DOMAIN_EXAMPLES[domain]
    return _META_PROMPT_TEMPLATE.format(example=example)

JUDGE_PROMPT = """You are a prompt quality judge. You will receive a use case and multiple candidate prompts (each with 6 JSON fields). Score each candidate and select the best one.

Score each candidate on these 6 criteria (0–10 each):

1. role_specificity — Does it name an exact seniority level and specific technology? Generic roles ("helpful assistant", "AI") score 0.
2. objective_structure — Exactly two sentences? Sentence 2 starts with "This is done when"? Correct structure scores 8+.
3. constraint_quality — Each bullet eliminates at least one alternative? ≥4 hard constraints scores 8+. Descriptive bullets score 0.
4. output_structure — Each section states what to answer, what not to omit, and expected depth? Vague sections score low.
5. quality_bar — Contains all 4 fixed lines word-for-word plus ≥1 use-case-specific criterion? Missing any fixed line scores 0.
6. user_prompt — Self-contained (no "as described above"), imperative, ≥50 words, references specifics from the use case?

Return valid JSON only. No text outside the JSON object.

{
  "scores": [
    {"candidate": 1, "total": 0, "role_specificity": 0, "objective_structure": 0, "constraint_quality": 0, "output_structure": 0, "quality_bar": 0, "user_prompt": 0},
    {"candidate": 2, "total": 0, "role_specificity": 0, "objective_structure": 0, "constraint_quality": 0, "output_structure": 0, "quality_bar": 0, "user_prompt": 0}
  ],
  "best": 1,
  "weaknesses": ["...", "..."]
}

Rules:
- "total" is the sum of all 6 criteria (0–60).
- "best" is the candidate number (1-indexed) with the highest total.
- "weaknesses" lists 1–3 specific, actionable weaknesses of the best candidate. Each weakness is one sentence.
- If candidates are tied, prefer the one with the higher user_prompt score.
"""
SUGGESTIONS_PROMPT = """Given a system prompt and user prompt for a coding or engineering task, write exactly 3 refinement suggestions.

Each suggestion is a single short imperative sentence the user can send as feedback to improve the prompts.
Be specific to the content — not generic advice like "add more detail" or "be more specific".

If weaknesses are listed below, prioritize suggestions that directly address those weaknesses. At least 2 of the 3 suggestions should target the listed weaknesses.

Return only valid JSON. No text outside the object.
{"suggestions": ["...", "...", "..."]}
"""

REFLEXION_PROMPT = """You are a senior prompt engineer. You will receive a use case and a draft LLM prompt (6 JSON fields). Review each field and return an improved version.

Apply these checks field by field:

role_and_expertise
  Must name an exact seniority level and specific technology. Must not contain "helpful assistant", "AI", "various fields", or any generic phrase.
  If generic: derive the precise role from the use case.

task_objective
  Must be exactly two sentences. Sentence 1: the deliverable. Sentence 2: must start with "This is done when".
  If wrong structure: rewrite to exactly two sentences.

constraints_and_assumptions
  Each bullet must eliminate at least one alternative approach or fix one decision. Descriptive or suggestion bullets are not constraints.
  If any bullet fails this test: remove or rewrite it as a hard rule.

required_output_structure
  Each numbered section must state: what questions it answers, what it must not omit, and expected depth.
  If any section is vague: sharpen it.

quality_bar
  Must contain all four fixed lines word-for-word:
  - Reader is a senior developer. No concept explanations, no introductory context.
  - Every decision must be stated explicitly. Do not present options and leave the choice open.
  - Where trade-offs exist, name each one and state which to choose and why.
  - No filler sentences. Every sentence must add a decision, a constraint, or a justification.
  Must also contain at least one criterion specific to this use case. If missing: add it.

user_prompt
  Must be self-contained — readable as if the system prompt does not exist. Imperative. No pleasantries, no "as described above", no meta-commentary.
  If not self-contained: rewrite from scratch.

OUTPUT RULES
- Valid JSON only. No text outside the object.
- All six keys required. String values only. Escape newlines as \\n.

{
  "role_and_expertise": "...",
  "user_prompt": "...",
  "task_objective": "...",
  "constraints_and_assumptions": "...",
  "required_output_structure": "...",
  "quality_bar": "..."
}
"""


REFINE_PROMPT = """You are a prompt engineer. You are given the 6 structured fields of an existing LLM prompt as JSON, plus feedback on what to improve.

Your job: make the minimal change that satisfies the feedback. Touch only the fields that must change. Leave everything else identical.

Rules:
- Before writing, identify exactly which fields the feedback requires changing. For a change like "use Azure instead of AWS", only fields that contain "AWS" need updating — copy all others character-for-character.
- Do not rephrase, reorder, or rewrite any field the feedback does not explicitly target. Identical output for untouched fields is correct behaviour, not laziness.
- Apply only what the feedback explicitly requests. Do not infer additional improvements.
- Do not weaken constraints, add hedging, or revert quality bar rules.
- The user_prompt must remain self-contained and imperative.
- If previous refinements are listed, preserve those changes. Do not revert changes from previous refinements unless the new feedback explicitly contradicts them.

OUTPUT RULES
- Valid JSON only. No markdown. No text outside the JSON object.
- All six keys required. String values only. Escape newlines as \\n.

{
  "role_and_expertise": "...",
  "user_prompt": "...",
  "task_objective": "...",
  "constraints_and_assumptions": "...",
  "required_output_structure": "...",
  "quality_bar": "..."
}
"""

REVIEWER_PROMPT = (
    "Review the above response as a senior software architect.\n"
    "- Identify missing edge cases\n"
    "- Point out scalability or security risks\n"
    "- Suggest concrete improvements\n"
    "Return only actionable feedback."
)

REQUIRED_KEYS = [
    "role_and_expertise",
    "task_objective",
    "constraints_and_assumptions",
    "required_output_structure",
    "quality_bar",
    "user_prompt",
]


def _to_str(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    return str(value)


def build_system_prompt(data: dict) -> str:
    return (
        f"## Role & expertise\n{_to_str(data['role_and_expertise'])}\n\n"
        f"## Task objective\n{_to_str(data['task_objective'])}\n\n"
        f"## Constraints & assumptions\n{_to_str(data['constraints_and_assumptions'])}\n\n"
        f"## Required output structure\n{_to_str(data['required_output_structure'])}\n\n"
        f"## Quality bar\n{_to_str(data['quality_bar'])}"
    )
