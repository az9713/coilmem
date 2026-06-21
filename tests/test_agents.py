"""Tests for the researcher->critic->writer team (offline — fake embedder + StubChat).
Run: python -m pytest tests/test_agents.py
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import eval as cev
from agents import team as T
from agents.eval import stub_seats
from coilmem import store
from test_store import fake_embed


def test_cross_agent_shared_transfer_and_private_isolation():
    conn = store.connect(":memory:")
    out = T.run_team(conn, "p", ["alpha subsystem design"], stub_seats(),
                     mode="memory", k=5, embed_fn=fake_embed)
    wc = out["last_ctx"]["writer"]
    assert "FINDING" in wc and "CRITIQUE" in wc      # writer got researcher + critic SHARED
    assert "private scratch" not in wc               # no private leaked into writer's context
    # direct check: writer recall never returns another agent's private
    hits = store.search(conn, "p", "writer", "alpha subsystem design", k=20, embed_fn=fake_embed)
    assert all(("private scratch" not in h["text"]) or (h["agent_id"] == "writer") for h in hits)


def test_memory_cheaper_than_naive_over_session():
    topics = [f"subsystem {i} design" for i in range(1, 11)]
    res = cev.measure(topics, embed_fn=fake_embed, k=5)
    assert res["memory"]["input"] < res["naive"]["input"]  # bounded recall vs growing transcript


def test_quality_parity_holds():
    topics = [f"subsystem {i} design" for i in range(1, 6)]
    res = cev.measure(topics, embed_fn=fake_embed, k=5)
    assert cev.check_quality_parity(res) is True  # needed context retained + private isolated


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
