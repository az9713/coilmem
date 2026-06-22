"""Team demo: researcher -> critic -> writer over a shared coilmem workspace.

Shows the writer building on the researcher's findings AND the critic's flags via the
`shared` scope, while each agent's `private` scratch stays isolated. Offline (default):
stub LLMs + real local embeddings. Live: `python -m agents.demo live` (needs provider keys).
"""
import sys

from coilmem import store
from coilmem.config import load_env

from . import team as T
from .eval import stub_seats
from .llm import CostMeter

TOPICS = [
    "the core math and ML foundations a beginner should learn first",
    "hands-on projects to build those foundations into real skills",
    "how to stay current as the AI field keeps changing",
]


def main(live=False):
    load_env()
    conn = store.connect(":memory:")
    WS = "learning-ai"
    seats = T.live_seats() if live else stub_seats()
    cost = CostMeter()
    out = T.run_team(conn, WS, TOPICS, seats, mode="memory", k=5,
                     embed_fn=None, cost=cost)

    print(f"=== Team session ({'LIVE' if live else 'OFFLINE stub LLMs + local embeddings'}) ===\n")
    for s in out["sections"]:
        print(f"--- Turn {s['turn']}: {s['topic']}")
        for role in T.ROLES:
            print(f"  [{role}] {s['outputs'][role][:100]}")
        print()

    # Author-based check: reproduce the writer's recall and inspect who authored each hit
    # (memory mode grounding is store.search with the writer's own agent_id over the topic).
    hits = store.search(conn, WS, "writer", TOPICS[-1], k=5, embed_fn=None)
    shared_authors = {h["agent_id"] for h in hits if h["scope"] == "shared"}
    leaked = [h for h in hits if h["scope"] == "private" and h["agent_id"] != "writer"]
    foreign_private_exists = conn.execute(
        "SELECT 1 FROM memories WHERE workspace=? AND scope='private' AND agent_id!='writer' LIMIT 1",
        (WS,)).fetchone() is not None
    print("=== cross-agent shared context + private isolation (author-based) ===")
    print(f"  writer recalled researcher's SHARED note:  {'researcher' in shared_authors}")
    print(f"  writer recalled critic's SHARED note:      {'critic' in shared_authors}")
    print(f"  other agents' private notes exist in DB:   {foreign_private_exists}")
    print(f"  ...yet NONE leaked into writer's recall:   {not leaked}")
    print(f"\n=== cost: {cost.total_calls()} calls, {cost.total_tokens()} tokens ===")


if __name__ == "__main__":
    main(live=(len(sys.argv) > 1 and sys.argv[1] == "live"))
