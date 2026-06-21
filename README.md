# coilmem

Shared memory for **multi-agent** systems. A memory store + HTTP service whose scoping model
is built for *teams of agents*: a workspace-level **`shared`** scope any agent can read, plus
per-agent **`private`** scope. An agent's search returns its own private memories plus the
workspace's shared ones — and never another agent's private memories.

Independent codebase (no council, no shared package). Design context:
[`council-coilmem-decision.md`](council-coilmem-decision.md). Product spec:
[`specs/mvp_spec.md`](specs/mvp_spec.md).

## Two surfaces

1. **The memory library + HTTP API** (`coilmem/`) — SQLite store, pluggable embeddings
   (`local` MiniLM default / `openai` / `gemini`), FastAPI service.
2. **A researcher → critic → writer team** (`agents/`) on LangGraph that shares one coilmem
   workspace over many turns — the validation that the shared+private wedge earns its keep.

```
researcher ─→ critic ─→ writer        (one turn = one topic; repeated over a session)
   │            │          │
   └── writes shared findings / critiques / sections; private scratch stays isolated
   └── reads team context: memory mode = recall(top-k shared + own private)
                           naive mode  = full transcript (grows O(turns))
```

## Setup

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows; or .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

Offline (no API key — stub LLMs + real local embeddings):
```bash
python -m pytest               # full suite
python -m coilmem.store        # store scope self-check
python -m agents.demo          # team session: cross-agent shared recall + private isolation
python -m agents.eval          # memory vs naive token measurement + quality-parity guardrail
```

Live agents (real models; needs provider keys in .env):
```bash
python -m agents.demo live
```

Roles are an ordered list in `agents/config.py` — add agents by extending `ROLES`/`ROLE_MODELS`.

## What the eval proves (honestly)

- **Memory vs naive**: recall feeds bounded (~O(k)) input context per agent; naive
  context-stuffing grows O(turns). The eval prints the % fewer input tokens over a session.
- **Quality parity**: in memory mode the writer's retrieved context still contains the
  researcher's finding and the critic's critique (and excludes others' private notes) — so the
  saving is real, not the result of dropping needed context.

## Files

Library: `coilmem/{store,embed,app,config,demo}.py`. Team: `agents/{team,config,demo,eval,llm}.py`.
Tests: `tests/{test_store,test_api,test_agents}.py`.

## Notes / caveats

- One `EMBED_PROVIDER` per DB (dims differ across providers; the store rejects mixed dims).
- Anthropic has no embeddings API → use `local` (or openai/gemini) for `EMBED_PROVIDER`.
- `agents/team.py` runs roles sequentially (correctness first; parallelize with asyncio later).
