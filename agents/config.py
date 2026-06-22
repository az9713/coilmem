"""Team composition. Roles are an ordered list — add agents by extending ROLES + ROLE_MODELS."""
import os

ROLES = ["researcher", "critic", "writer"]

ROLE_MODELS = {
    "researcher": "openai:gpt-4o-mini",
    "critic": "anthropic:claude-haiku-4-5-20251001",
    "writer": "openai:gpt-4o",
}

ROLE_INSTR = {
    "researcher": "Research the topic and state 2-3 concrete findings.",
    "critic": "Critique the findings so far: name gaps, risks, or contradictions.",
    "writer": "Write a concise section using the team's findings and critiques.",
}

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_genai": "GEMINI_API_KEY",
}


def _has_key(model_str: str) -> bool:
    return bool(os.environ.get(PROVIDER_ENV.get(model_str.split(":", 1)[0], "")))


def resolve_model(preferred: str) -> str:
    """Use `preferred` if its key is set, else any provider whose key is present."""
    if _has_key(preferred):
        return preferred
    for m in ROLE_MODELS.values():
        if _has_key(m):
            return m
    return preferred  # let it fail clearly if truly no keys
