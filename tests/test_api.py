"""End-to-end HTTP tests: routing + auth + the scope invariant over the API.

Offline — the real embedder is monkeypatched to a deterministic one, and a
fresh in-memory store is injected, so no network / no OPENAI_API_KEY needed.
Run: python -m pytest
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_store import fake_embed

KEY = "test-key"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COILMEM_KEY", KEY)
    monkeypatch.setenv("COILMEM_DB", ":memory:")
    monkeypatch.setenv("OPENAI_API_KEY", "unused")
    # import after env is set so module-level connection uses :memory:
    import coilmem.app as appmod
    import coilmem.store as store
    from fastapi.testclient import TestClient

    fresh = store.connect(":memory:")
    monkeypatch.setattr(appmod, "_conn", fresh)
    monkeypatch.setattr(store, "_default_embed", fake_embed)  # used by add/search defaults
    return TestClient(appmod.app)


H = {"X-API-Key": KEY}


def _write(client, agent, scope, text):
    r = client.post("/memory", headers=H,
                    json={"workspace": "w1", "agent_id": agent, "scope": scope, "text": text})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_requires_api_key(client):
    r = client.post("/memory", json={"workspace": "w1", "agent_id": "A", "scope": "shared", "text": "x"})
    assert r.status_code == 401


def test_shared_visible_private_hidden_over_http(client):
    _write(client, "A", "shared", "the database is Postgres on port 5433")
    _write(client, "C", "private", "secret scratchpad note about cats")
    r = client.get("/memory/search", headers=H,
                   params={"workspace": "w1", "agent_id": "B", "query": "what database are we using"})
    assert r.status_code == 200
    texts = [m["text"] for m in r.json()["results"]]
    assert "the database is Postgres on port 5433" in texts
    assert "secret scratchpad note about cats" not in texts


def test_bad_scope_returns_400(client):
    r = client.post("/memory", headers=H,
                    json={"workspace": "w1", "agent_id": "A", "scope": "public", "text": "x"})
    assert r.status_code == 400


def test_delete_over_http(client):
    mem_id = _write(client, "A", "shared", "temp fact")
    assert client.delete(f"/memory/{mem_id}", headers=H).status_code == 200
    assert client.delete(f"/memory/{mem_id}", headers=H).status_code == 404


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
