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
    "real-time sync design for the voice-notes app",
    "storage and database choice",
    "the top risk to de-risk first",
]


def main(live=False):
    load_env()
    conn = store.connect(":memory:")
    seats = T.live_seats() if live else stub_seats()
    cost = CostMeter()
    out = T.run_team(conn, "voice-notes-app", TOPICS, seats, mode="memory", k=5,
                     embed_fn=None, cost=cost)

    print(f"=== Team session ({'LIVE' if live else 'OFFLINE stub LLMs + local embeddings'}) ===\n")
    for s in out["sections"]:
        print(f"--- Turn {s['turn']}: {s['topic']}")
        for role in T.ROLES:
            print(f"  [{role}] {s['outputs'][role][:100]}")
        print()

    writer_ctx = out["last_ctx"].get("writer", "")
    print("=== cross-agent shared context + private isolation ===")
    print(f"  writer saw researcher's shared FINDING:  {'FINDING' in writer_ctx}")
    print(f"  writer saw critic's shared CRITIQUE:     {'CRITIQUE' in writer_ctx}")
    print(f"  writer did NOT see any private scratch:  {'private scratch' not in writer_ctx}")
    print(f"\n=== cost: {cost.total_calls()} calls, {cost.total_tokens()} tokens ===")


if __name__ == "__main__":
    main(live=(len(sys.argv) > 1 and sys.argv[1] == "live"))
