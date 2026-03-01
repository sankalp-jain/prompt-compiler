from pathlib import Path


def _load(name: str) -> str:
    return (Path(__file__).parent / "prompts" / name).read_text(encoding="utf-8")


_META_PROMPT_TEMPLATE = _load("meta_prompt_template.txt")

JUDGE_PROMPT = _load("judge.txt")
SUGGESTIONS_PROMPT = _load("suggestions.txt")
REFLEXION_PROMPT = _load("reflexion.txt")
REFINE_PROMPT = _load("refine.txt")
REVIEWER_PROMPT = _load("reviewer.txt")

_DOMAIN_EXAMPLES = {
    "backend":  _load("examples/backend.txt"),
    "frontend": _load("examples/frontend.txt"),
    "data":     _load("examples/data.txt"),
    "devops":   _load("examples/devops.txt"),
    "ml":       _load("examples/ml.txt"),
    "general":  _load("examples/general.txt"),
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
    example = _DOMAIN_EXAMPLES[domain]
    return _META_PROMPT_TEMPLATE.replace("{example}", example)


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
