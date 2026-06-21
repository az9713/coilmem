# MVP Spec — Shared Memory for Multi-Agent Systems

**Working name:** `coilmem` (placeholder)
**Date:** 2026-06-20
**Picked from:** top-3 validation (see `reports/idea_brainstorm.md`, `data/idea_candidates.json`)

## Why this one (validation summary)

All three top ideas were validated via Bright Data MCP (`search_engine` + `scrape_as_markdown`):

- **#1 Agent observability** — oversaturated. 15+ tools scraped (Langfuse, LangSmith, Arize, Phoenix, Braintrust, Weave, Laminar, Confident AI, AgentOps). Table stakes (traces, evals, dashboards) too large for a 3-day solo MVP. Rejected.
- **#3 Vertical agent builder** — oversaturated. 12–14 platforms (Langflow, Lindy, Relevance, Vellum, Voiceflow, Stack AI, Pickaxe). Needs breadth. Rejected.
- **#2 Shared memory layer** — *picked.* The market is crowded (Mem0 ~47–55k★, Zep, Letta, Cognee, LangChain/LlamaIndex Memory), **but every shipped framework is built for single-agent / conversational memory.** None target shared memory across *multiple collaborating agents* — the exact gap. That slice is thin and buildable solo in 1–3 days.

**Honest caveat:** this is a contested space. The MVP's job is to validate the *multi-agent shared-context* wedge with real users — not to out-feature Mem0. If the wedge doesn't resonate, kill it; don't expand into general memory.

## The wedge (one sentence)

When several agents collaborate on one task, each starts cold — there is no shared store, so they burn tokens re-establishing context. `coilmem` is a tiny hosted memory service whose scoping model is built for *teams of agents*, not one chatbot.

The one thing incumbents don't do: a **`shared` scope at the workspace level** that any agent in the workspace can read, alongside per-agent **`private`** scope. That's the whole differentiator.

## Scope — in

- `POST /memory` — write a memory `{workspace, agent_id, scope: private|shared, text, metadata?}`. Server embeds `text` and stores it.
- `GET /memory/search?workspace=&agent_id=&query=&k=` — semantic search. Returns the agent's own `private` memories **plus** the workspace's `shared` memories, ranked by cosine similarity. Never returns another agent's `private` memories.
- `GET /memory?workspace=&agent_id=` — list (debug/inspection).
- `DELETE /memory/{id}` — delete one.
- API-key header auth (single static key from env). Multi-tenant key management is out.

## Scope — out (ponytail: say no early)

- No UI/dashboard (that's idea #1; don't drift into it).
- No graph memory, no auto-summarization, no fact extraction, no memory "evolution" (that's Mem0/Zep/Cognee territory — not the wedge).
- No real vector index. Brute-force cosine over SQLite is fine at MVP scale.
- No SDK. `curl`/`requests` is the MVP interface; an SDK is a day-4 nicety if anyone asks.
- No streaming, no websockets, no eviction/TTL policy beyond a hard row cap.

## Data model (one table)

```
memories(
  id        TEXT PRIMARY KEY,   -- uuid4 (passed in / generated client-side; no Date/random server constraints)
  workspace TEXT NOT NULL,
  agent_id  TEXT NOT NULL,
  scope     TEXT NOT NULL CHECK(scope IN ('private','shared')),
  text      TEXT NOT NULL,
  embedding BLOB NOT NULL,      -- float32 array, packed
  metadata  TEXT,               -- JSON string, nullable
  created   TEXT NOT NULL       -- ISO timestamp, server-stamped
)
```

Index on `workspace` (search filters by it first, then scans).

## Retrieval rule (the core logic — this is what gets a test)

For a search by `(workspace, agent_id, query)`:
1. Candidate set = rows where `workspace = ?` AND (`scope='shared'` OR (`scope='private'` AND `agent_id = ?`)).
2. Cosine-similarity each candidate's embedding against the query embedding.
3. Return top `k`.

**Invariant under test:** agent B searching workspace W must get W's shared memories and B's private ones, but **never** agent C's private memories. (See `build_plan.md` Day 1 self-check.)

## Stack (ladder applied)

- **Python 3.11 + FastAPI + uvicorn** — already the lingua franca for agent tooling; buyers integrate in minutes.
- **SQLite (stdlib `sqlite3`)** — zero infra. `embedding` stored as packed float32 BLOB.
- **Embeddings: one API** — OpenAI `text-embedding-3-small` (cheap, 1536-dim) via `httpx`. Pluggable behind one function so it can be swapped.
- Cosine: `numpy` (or pure-Python if avoiding the dep). `numpy` is worth it.

That's 3 deps: `fastapi`, `uvicorn`, `httpx` (+`numpy`). No vector DB, no ORM, no auth lib.

```
# ponytail: brute-force cosine over a full workspace scan — O(n) per query.
# Fine to a few thousand memories/workspace. Swap to sqlite-vec or pgvector when a
# real workspace crosses ~10k rows and search latency shows up.
```

## Success criteria (what "validated" means)

- **Technical:** the two-agent demo passes — agent A writes a finding to `shared`, agent B retrieves it by meaning; agent C's `private` note stays invisible to B.
- **Market (post-build, 1 week):** show 5 people building multi-agent systems (LangGraph/CrewAI/Autogen users on r/AI_Agents, Discord). Target: ≥3 say "yes, cross-agent context is a real pain I'd wire this into." Below that → wedge is weak, stop.

## Distribution (free, no sales)

Post the two-agent demo + repo to r/AI_Agents and the LangGraph/CrewAI Discords. The demo *is* the pitch.
