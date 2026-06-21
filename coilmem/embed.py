"""Pluggable embeddings. Dispatch on EMBED_PROVIDER (default 'local').

  local   sentence-transformers all-MiniLM-L6-v2 (384-dim) — keyless, runs offline
  openai  text-embedding-3-small (1536-dim)
  gemini  text-embedding-004 (768-dim)

Heavy imports (torch via sentence-transformers, httpx) are lazy so importing this
module — and therefore store.py — never pulls them. Tests inject their own embed_fn
and never call these.
"""
import os

_local_model = None  # cached SentenceTransformer instance


def embed(text: str) -> list[float]:
    provider = os.environ.get("EMBED_PROVIDER", "local").lower()
    if provider == "local":
        return _embed_local(text)
    if provider == "openai":
        return _embed_openai(text)
    if provider == "gemini":
        return _embed_gemini(text)
    raise ValueError(f"unknown EMBED_PROVIDER: {provider!r} (use local|openai|gemini)")


def _embed_local(text: str) -> list[float]:
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer  # lazy: pulls torch

        _local_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _local_model.encode(text).tolist()


def _embed_openai(text: str) -> list[float]:
    import httpx

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    resp = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def _embed_gemini(text: str) -> list[float]:
    import httpx

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    resp = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent",
        params={"key": key},
        json={"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]
