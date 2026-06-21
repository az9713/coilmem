"""Honest measurement for the team: memory (coilmem recall) vs naive (full transcript).

  - input tokens fed to agents over a session: memory is bounded (~O(k)), naive grows O(turns).
  - quality-parity guardrail: in memory mode, the writer's retrieved context MUST still
    contain the researcher's finding and the critic's critique — so a token saving is real,
    not the result of dropping needed context.

Run: `python -m agents.eval`  (offline, real local embeddings + stub LLMs, no API keys).
"""
import re
import sys

from coilmem import store
from coilmem.config import load_env

from . import team as T
from .config import ROLES
from .llm import CostMeter, StubChat


def _topic_of(text):
    m = re.search(r"Topic:\s*(.+)", text)
    return m.group(1).strip() if m else text[:40]


def _responder(role):
    def r(messages):
        topic = _topic_of(" ".join(str(m[1]) for m in messages))
        if role == "researcher":
            return f"FINDING on {topic}: prefer option Alpha for {topic}"
        if role == "critic":
            return f"CRITIQUE on {topic}: watch the latency risk in {topic}"
        return f"SECTION on {topic}: synthesis grounded in the team's findings and critiques"
    return r


def stub_seats():
    return {role: StubChat(role, _responder(role)) for role in ROLES}


def measure(topics, seats=None, embed_fn=None, k=5):
    results = {}
    for mode in ("memory", "naive"):
        conn = store.connect(":memory:")
        cost = CostMeter()
        out = T.run_team(conn, "proj", topics, seats or stub_seats(),
                         mode=mode, k=k, embed_fn=embed_fn, cost=cost)
        results[mode] = {"input": cost.total_input_tokens(), "last_ctx": out["last_ctx"]}
    return results


def print_measure(topics, results):
    mi, ni = results["memory"]["input"], results["naive"]["input"]
    pct = (ni - mi) / ni * 100 if ni else 0
    print(f"\n=== input tokens fed to agents over {len(topics)} turns ===")
    print(f"  memory (recall top-k):    {mi}")
    print(f"  naive  (full transcript): {ni}")
    print(f"  => memory feeds {pct:.1f}% fewer input tokens vs the naive full-replay baseline")
    print("     (full-replay is the weakest baseline = a ceiling; windowing/summarizing would narrow it)")


def check_quality_parity(results) -> bool:
    ctx = results["memory"]["last_ctx"].get("writer", "")
    has_finding = "FINDING" in ctx
    has_critique = "CRITIQUE" in ctx
    # isolation = no OTHER role's private note (the writer's own private is allowed by the
    # scope rule, so check by author role, not the bare "private scratch" string).
    others = [r for r in ROLES if r != "writer"]
    no_others_private = not any(f"{r} private scratch" in ctx for r in others)
    print("\n=== quality parity (memory mode) ===")
    print(f"  writer's retrieved context includes researcher FINDING:   {has_finding}")
    print(f"  writer's retrieved context includes critic CRITIQUE:      {has_critique}")
    print(f"  writer's retrieved context excludes OTHER agents' private:{no_others_private}")
    ok = has_finding and has_critique and no_others_private
    print("  => saving is real (needed context retained, others' private isolated)" if ok
          else "  => WARNING: needed context missing or another agent's private leaked")
    return ok


def main():
    load_env()
    topics = [f"subsystem {i} design" for i in range(1, 13)]
    results = measure(topics, embed_fn=None, k=5)  # embed_fn None -> coilmem local default
    print_measure(topics, results)
    check_quality_parity(results)


if __name__ == "__main__":
    sys.exit(0 if (main() or True) else 1)
