"""Minimal .env loader. ponytail: ~12 lines instead of a python-dotenv dep.

Reads KEY=VALUE lines from ./.env (or the project-root .env as a fallback) and
sets them with os.environ.setdefault — so real environment variables and test
monkeypatches always take precedence over the file.
"""
import os
from pathlib import Path


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.is_file():
        alt = Path(__file__).resolve().parent.parent / ".env"
        if not alt.is_file():
            return
        p = alt
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
