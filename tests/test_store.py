"""Tests for coilmem.store. Stdlib + a deterministic offline embedder — no
network, no third-party deps beyond pytest. Run: python -m pytest

Also runnable without pytest: python tests/test_store.py
"""
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coilmem import store


def fake_embed(text: str):
    """Deterministic bag-of-words embedding (stable across processes via md5).
    Token overlap -> higher cosine, so ranking is meaningful in tests."""
    dim = 256
    vec = [0.0] * dim
    for tok in text.lower().split():
        tok = "".join(c for c in tok if c.isalnum())
        if not tok:
            continue
        idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim
        vec[idx] += 1.0
    return vec


def add(conn, ws, agent, scope, text):
    return store.add(conn, ws, agent, scope, text, embed_fn=fake_embed)


def search(conn, ws, agent, query, k=5):
    return store.search(conn, ws, agent, query, k=k, embed_fn=fake_embed)


@pytest.fixture
def conn():
    return store.connect(":memory:")


def test_scope_invariant_shared_visible_private_hidden(conn):
    add(conn, "w1", "A", "shared", "the database is Postgres on port 5433")
    add(conn, "w1", "C", "private", "my secret scratchpad note about cats")
    results = search(conn, "w1", "B", "what database are we using")
    texts = [r["text"] for r in results]
    assert results
    assert "the database is Postgres on port 5433" in texts
    assert "my secret scratchpad note about cats" not in texts  # C's private must not leak


def test_agent_sees_own_private(conn):
    add(conn, "w1", "B", "private", "B remembers the api key rotation schedule")
    results = search(conn, "w1", "B", "api key rotation schedule")
    assert any("rotation schedule" in r["text"] for r in results)


def test_other_agents_private_never_returned(conn):
    add(conn, "w1", "A", "private", "A private deployment runbook steps")
    results = search(conn, "w1", "B", "deployment runbook steps")
    assert all(r["text"] != "A private deployment runbook steps" for r in results)


def test_ranking_more_relevant_first(conn):
    add(conn, "w1", "A", "shared", "kubernetes cluster autoscaling configuration details")
    add(conn, "w1", "A", "shared", "office coffee machine maintenance schedule")
    results = search(conn, "w1", "B", "kubernetes cluster autoscaling configuration")
    assert results[0]["text"] == "kubernetes cluster autoscaling configuration details"


def test_workspace_isolation(conn):
    add(conn, "w1", "A", "shared", "workspace one secret topic alpha")
    results = search(conn, "w2", "B", "workspace one secret topic alpha")
    assert results == []  # different workspace sees nothing


def test_delete(conn):
    mem_id = add(conn, "w1", "A", "shared", "temporary fact to be deleted")
    assert store.delete(conn, mem_id) is True
    assert store.delete(conn, mem_id) is False  # already gone
    results = search(conn, "w1", "B", "temporary fact to be deleted")
    assert all(r["id"] != mem_id for r in results)


def test_invalid_scope_rejected(conn):
    with pytest.raises(ValueError):
        add(conn, "w1", "A", "public", "wrong scope value")


def test_list_only_own_memories(conn):
    add(conn, "w1", "A", "shared", "A first")
    add(conn, "w1", "A", "private", "A second")
    add(conn, "w1", "B", "shared", "B thing")
    rows = store.list_memories(conn, "w1", "A")
    assert {r["text"] for r in rows} == {"A first", "A second"}


def test_metadata_roundtrip(conn):
    store.add(conn, "w1", "A", "shared", "fact with meta", metadata={"src": "doc1"}, embed_fn=fake_embed)
    results = search(conn, "w1", "B", "fact with meta")
    assert results[0]["metadata"] == {"src": "doc1"}


def test_dim_guard_rejects_mismatched_embedder(conn):
    add(conn, "w1", "A", "shared", "first fact at dim 256")  # fake_embed -> 256-dim
    other_dim = lambda text: [0.0] * 128  # noqa: E731 - different dim on purpose
    with pytest.raises(ValueError, match="one EMBED_PROVIDER per DB"):
        store.add(conn, "w1", "A", "shared", "second fact", embed_fn=other_dim)


def test_local_embed_returns_384_dim():
    pytest.importorskip("sentence_transformers")  # skip if not installed (heavy/torch)
    import os

    os.environ["EMBED_PROVIDER"] = "local"
    from coilmem import embed as embed_mod

    vec = embed_mod.embed("hello world")
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
