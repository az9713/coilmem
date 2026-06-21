"""SQLite-backed shared memory store with multi-agent scoping.

The retrieval rule (the whole differentiator) lives in `search`:
an agent sees its own `private` memories plus the workspace's `shared` ones,
and never another agent's `private` memories.

Stdlib only — no third-party deps — so tests run offline. Embeddings are
injected via `embed_fn` (defaults to the real OpenAI embedder).
"""
import json
import math
import sqlite3
import struct
import uuid
from datetime import datetime, timezone

from .embed import embed as _default_embed

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id        TEXT PRIMARY KEY,
    workspace TEXT NOT NULL,
    agent_id  TEXT NOT NULL,
    scope     TEXT NOT NULL CHECK(scope IN ('private','shared')),
    text      TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata  TEXT,
    created   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_workspace ON memories(workspace);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _pack(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes):
    return struct.unpack(f"{len(blob) // 4}f", blob)


def _cosine(a, b) -> float:
    # ponytail: pure-Python cosine, O(dim). Keeps the store dependency-free.
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def add(conn, workspace, agent_id, scope, text, metadata=None, embed_fn=None):
    embed_fn = embed_fn or _default_embed  # resolve global at call time (monkeypatch-friendly)
    if scope not in ("private", "shared"):
        raise ValueError("scope must be 'private' or 'shared'")
    mem_id = str(uuid.uuid4())
    emb = embed_fn(text)
    # dim guard: cosine over zip() silently truncates mismatched dims, so a DB must
    # use one embedder. Reject writes whose dim differs from existing rows.
    existing = conn.execute("SELECT length(embedding) AS n FROM memories LIMIT 1").fetchone()
    if existing is not None and existing["n"] != len(emb) * 4:
        raise ValueError(
            f"embedding dim {len(emb)} != existing {existing['n'] // 4}; "
            "one EMBED_PROVIDER per DB"
        )
    conn.execute(
        "INSERT INTO memories (id, workspace, agent_id, scope, text, embedding, metadata, created)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            mem_id,
            workspace,
            agent_id,
            scope,
            text,
            _pack(emb),
            json.dumps(metadata) if metadata is not None else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return mem_id


def search(conn, workspace, agent_id, query, k=5, embed_fn=None):
    """Top-k by cosine over the agent's visible candidate set:
    workspace's shared memories + this agent's own private memories."""
    embed_fn = embed_fn or _default_embed  # resolve global at call time (monkeypatch-friendly)
    q = embed_fn(query)
    rows = conn.execute(
        "SELECT * FROM memories WHERE workspace = ?"
        " AND (scope = 'shared' OR (scope = 'private' AND agent_id = ?))",
        (workspace, agent_id),
    ).fetchall()
    scored = []
    for r in rows:
        score = _cosine(q, _unpack(r["embedding"]))
        scored.append((score, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [_to_dict(r, score) for score, r in scored[:k]]


def list_memories(conn, workspace, agent_id):
    rows = conn.execute(
        "SELECT * FROM memories WHERE workspace = ? AND agent_id = ? ORDER BY created",
        (workspace, agent_id),
    ).fetchall()
    return [_to_dict(r) for r in rows]


def delete(conn, mem_id) -> bool:
    cur = conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
    conn.commit()
    return cur.rowcount > 0


def _to_dict(row, score=None):
    d = {
        "id": row["id"],
        "workspace": row["workspace"],
        "agent_id": row["agent_id"],
        "scope": row["scope"],
        "text": row["text"],
        "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
        "created": row["created"],
    }
    if score is not None:
        d["score"] = score
    return d


def _toy_embed(text: str):
    """Deterministic, offline bag-of-words embedding for the self-check.
    Token overlap -> higher cosine. Not for production; tests/demo only."""
    dim = 64
    vec = [0.0] * dim
    for tok in text.lower().split():
        tok = "".join(c for c in tok if c.isalnum())
        if tok:
            vec[hash(tok) % dim] += 1.0
    return vec


def demo():
    """Self-check: scope invariant must hold. Run: python -m coilmem.store"""
    conn = connect(":memory:")
    add(conn, "w1", "A", "shared", "the database is Postgres on port 5433", embed_fn=_toy_embed)
    add(conn, "w1", "C", "private", "my secret scratchpad note about cats", embed_fn=_toy_embed)

    results = search(conn, "w1", "B", "what database are we using", embed_fn=_toy_embed)
    texts = [r["text"] for r in results]

    assert results, "expected at least one result"
    assert results[0]["agent_id"] == "A", "top result should be A's shared memory"
    assert all(r["scope"] != "private" or r["agent_id"] == "B" for r in results), (
        "agent B must never see another agent's private memory"
    )
    assert "my secret scratchpad note about cats" not in texts, "C's private leaked to B"
    print("OK: scope invariant holds. results=", texts)


if __name__ == "__main__":
    demo()
