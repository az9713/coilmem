"""Instrumented live run that persists evidence of shared-memory use.

Wraps coilmem.store.search to log every recall (caller, topic, and each hit's
author+scope+score+text). Dumps the full memory store and a human-readable report
so the role of `shared` memory in researcher -> critic -> writer is auditable.

Run from the repo root:  python tools/evidence_run.py
Writes artifacts to ./evidence/ (needs provider keys in .env).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for coilmem/agents imports

from coilmem.config import load_env  # noqa: E402

load_env()
os.environ.setdefault("EMBED_PROVIDER", "openai")  # default the harness to openai embeddings (no torch)

import coilmem.store as store          # noqa: E402
from agents import team as T           # noqa: E402
from agents.demo import TOPICS         # noqa: E402
from agents.llm import CostMeter       # noqa: E402

WS = "learning-ai"
OUT = Path(__file__).resolve().parent.parent / "evidence"
OUT.mkdir(exist_ok=True)

# --- instrument: log every recall the agents make -------------------------------
_orig_search = store.search
recall_log = []


def logged_search(conn, workspace, agent_id, query, k=5, embed_fn=None):
    hits = _orig_search(conn, workspace, agent_id, query, k=k, embed_fn=embed_fn)
    recall_log.append({
        "turn": TOPICS.index(query) + 1 if query in TOPICS else None,
        "caller": agent_id,
        "topic": query,
        "recalled": [
            {"author": h["agent_id"], "scope": h["scope"],
             "score": round(h.get("score", 0.0), 4), "text": h["text"]}
            for h in hits
        ],
    })
    return hits


store.search = logged_search

# --- run the real team ----------------------------------------------------------
conn = store.connect(":memory:")
seats = T.live_seats()
cost = CostMeter()
out = T.run_team(conn, WS, TOPICS, seats, mode="memory", k=5, embed_fn=None, cost=cost)

# --- 1) full memory dump (every shared + private memory written) ----------------
rows = conn.execute(
    "SELECT agent_id, scope, text, metadata, created FROM memories ORDER BY created"
).fetchall()
memories = [dict(r) for r in rows]
(OUT / "memories.json").write_text(json.dumps(memories, indent=2), encoding="utf-8")

# --- 2) recall log: the evidence of shared-memory use ---------------------------
(OUT / "recall_log.json").write_text(json.dumps(recall_log, indent=2), encoding="utf-8")

# --- 3) full (untruncated) role outputs per turn --------------------------------
(OUT / "sections.json").write_text(json.dumps(out["sections"], indent=2), encoding="utf-8")

# --- 4) human-readable report ---------------------------------------------------
L = [
    "# Shared-memory evidence — researcher -> critic -> writer (LIVE)\n",
    f"Workspace: `{WS}` | mode: memory | k=5 | embeddings: openai",
    f"Models: researcher=gpt-4o-mini, critic=claude-haiku-4-5, writer=gpt-4o",
    f"Cost: {cost.total_calls()} LLM calls, {cost.total_tokens()} tokens\n",
    "Each agent calls store.search BEFORE acting. `CROSS-SHARED` = a memory authored by a",
    "*different* agent, in `shared` scope — i.e. context this agent did not produce itself.",
    "A non-zero CROSS-SHARED count is shared memory doing its job. `foreign PRIVATE` must",
    "always be 0 (the scope rule forbids seeing another agent's private memory).\n",
]
for ev in recall_log:
    cross = [h for h in ev["recalled"] if h["scope"] == "shared" and h["author"] != ev["caller"]]
    own = [h for h in ev["recalled"] if h["author"] == ev["caller"]]
    foreign_priv = [h for h in ev["recalled"] if h["scope"] == "private" and h["author"] != ev["caller"]]
    L.append(f"\n## Turn {ev['turn']} — `{ev['caller']}` recalls before acting")
    L.append(f"_topic: {ev['topic']}_")
    L.append(f"**cross-agent SHARED: {len(cross)} | own: {len(own)} | foreign PRIVATE leaked: {len(foreign_priv)}**")
    if not ev["recalled"]:
        L.append("  (store empty — nothing to recall yet)")
    for h in ev["recalled"]:
        is_cross = h["scope"] == "shared" and h["author"] != ev["caller"]
        tag = "CROSS-SHARED" if is_cross else h["scope"].upper()
        L.append(f"  - [{h['author']}/{tag} score={h['score']}] {h['text'][:160].strip()}")
(OUT / "report.md").write_text("\n".join(L), encoding="utf-8")

# --- console summary ------------------------------------------------------------
total_cross = sum(
    1 for ev in recall_log for h in ev["recalled"]
    if h["scope"] == "shared" and h["author"] != ev["caller"]
)
total_leak = sum(
    1 for ev in recall_log for h in ev["recalled"]
    if h["scope"] == "private" and h["author"] != ev["caller"]
)
print(f"recalls logged:           {len(recall_log)}")
print(f"memories stored:          {len(memories)}")
print(f"cross-agent SHARED hits:  {total_cross}  (shared memory in use)")
print(f"foreign PRIVATE leaks:    {total_leak}  (must be 0)")
print(f"cost:                     {cost.total_calls()} calls, {cost.total_tokens()} tokens")
print(f"artifacts written to:     {OUT}")
