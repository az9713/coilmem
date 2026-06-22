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
        val = val.strip()
        if val[:1] not in ("'", '"'):  # strip inline "# comment" from unquoted values only
            val = val.split(" #", 1)[0].split("\t#", 1)[0].strip()
        os.environ.setdefault(key.strip(), val.strip('"').strip("'"))


def _selfcheck():
    """Run: python -m coilmem.config — verifies inline-comment stripping."""
    import tempfile

    f = Path(tempfile.mkdtemp()) / ".env"
    f.write_text('CM_A=openai   # local | openai | gemini\nCM_B="va#lue"\nCM_C=pa#ss\n',
                 encoding="utf-8")
    load_env(str(f))
    assert os.environ["CM_A"] == "openai", repr(os.environ["CM_A"])        # inline comment stripped
    assert os.environ["CM_B"] == "va#lue", repr(os.environ["CM_B"])        # quoted '#' preserved
    assert os.environ["CM_C"] == "pa#ss", repr(os.environ["CM_C"])         # unspaced '#' preserved
    print("OK: load_env strips inline comments and preserves '#' inside values")


if __name__ == "__main__":
    _selfcheck()
