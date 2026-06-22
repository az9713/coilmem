# coilmem — Development Journey & Context

Context for future work on this repo. Read alongside `README.md` (how to run) and
`specs/mvp_spec.md` (the product wedge). This file captures the "why and how we got here."

---

## 1. Origin

coilmem started as an MVP for **shared memory in multi-agent systems**. The distinctive
wedge — confirmed by surveying the field (Mem0, Zep, Letta, Cognee are all *single-agent /
conversational* memory) — is a **workspace-level `shared` scope plus per-agent `private`
scope**: an agent's search returns its own private memories **plus** the workspace's shared
ones, and **never** another agent's private memories. That scope rule is the product.

It was briefly entangled with an "LLM Council" experiment. We concluded the council is the
wrong vehicle to prove coilmem (a council is low-frequency and uses only the non-novel
`shared` half — i.e. plain RAG). So the projects were split; this repo is coilmem standalone,
**plus a multi-agent team that actually exercises the wedge.**

## 2. What this is — two surfaces

1. **Memory library + HTTP service** (`coilmem/`).
2. **A researcher → critic → writer team** (`agents/`) on LangGraph that shares one coilmem
   workspace over many turns — the validation that shared+private earns its keep, with an
   honest memory-vs-naive measurement.

```
researcher ─→ critic ─→ writer        (one turn = one topic; repeated over a session)
   each agent: read team context, act, write output to `shared` + scratch to `private`
   context = memory mode: recall(top-k of shared + own private)
             naive mode : full transcript (grows O(turns))
```

## 3. Architecture

| File | Role |
|---|---|
| `coilmem/store.py` | SQLite store; **the scope rule** in `search()` (shared + own private, never others' private). `add()` has a **dim guard** (one embedder per DB). Stdlib only. `python -m coilmem.store` runs a self-check. |
| `coilmem/embed.py` | pluggable embeddings: `local` all-MiniLM-L6-v2 (384-dim, keyless default), `openai` (1536), `gemini` (768). Heavy imports lazy. |
| `coilmem/app.py` | FastAPI service (`POST/GET/DELETE /memory`, `/memory/search`, `X-API-Key`). |
| `coilmem/config.py` | `load_env()` (reads `./.env`, setdefault so real env wins). |
| `agents/team.py` | LangGraph team, node per role; `run_team(conn, workspace, topics, seats, mode, k, embed_fn, cost)`; `live_seats()`. Two modes: `memory` (recall) vs `naive` (full transcript). |
| `agents/config.py` | `ROLES` (ordered list — extend to add agents), `ROLE_MODELS`, `ROLE_INSTR`, key-aware `resolve_model`. |
| `agents/llm.py` | `make_chat`, `call()` (usage_metadata + tiktoken fallback, list-content coercion), `CostMeter`, `StubChat`. |
| `agents/demo.py` | a team session; shows cross-agent shared recall + private isolation. |
| `agents/eval.py` | `measure()` (memory vs naive input tokens) + `check_quality_parity()` (needed context retained, others' private isolated) + `stub_seats()`. |
| `tests/` | `test_store.py` (scope rule, dim guard, `fake_embed`), `test_api.py` (HTTP scope + auth), `test_agents.py` (cross-agent transfer, isolation, measurement). |

## 4. Key decisions & rationale (don't silently undo these)

- **The scope rule is the product.** `search()` returns `shared` + the caller's own `private`.
  This single SQL predicate is the differentiator; keep it intact and tested.
- **Dim guard:** one `EMBED_PROVIDER` per DB. Cosine over `zip()` silently truncates mismatched
  dims, so `add()` rejects a different dim. Don't remove without a real multi-vector design.
- **Pluggable embedder, local default.** Keyless `local` so everything runs offline; openai/
  gemini for production. (Anthropic has **no** embeddings API → use local/openai/gemini.)
- **Agents recall with their real `agent_id`** (not a generic reader) — that's what enforces
  private isolation *and* lets an agent see its own private. Cross-agent sharing happens only
  via `shared`.
- **Two measurement modes** (`memory` vs `naive`) so savings are demonstrated, not asserted.
- **Quality-parity guardrail is mandatory.** A token saving is only honest if the needed
  context survives retrieval. `check_quality_parity` asserts the writer's recalled context
  still contains the researcher's FINDING and critic's CRITIQUE, and excludes **other** roles'
  private notes. (History: an earlier version checked the bare string `"private scratch"`,
  which wrongly tripped on the writer's *own* allowed private notes — fixed to check by author
  role. If you touch this, keep it author/agent-id based, not a substring.)
- **Dependency injection** — seats + `embed_fn` are passed in; tests use `StubChat` +
  `fake_embed` and run offline.

## 5. Honest caveats (carry into any feature work)

- **The 73.5% input-token reduction is vs the naive full-replay baseline — a ceiling.**
  Real systems often window or summarize history, against which coilmem's edge is smaller.
  Always state the baseline when quoting the number.
- **Live agents are unverified end-to-end.** All tests/demos run offline (stubs + fake/local
  embeddings). Real LLM runs need provider keys; `make_chat`/`live_seats` are
  construction-verified only.
- **Agents run sequentially** within a turn (researcher→critic→writer). Fine for correctness;
  parallelize independent steps later if latency matters.
- **In-process store for the team.** The agents use `coilmem.store` directly (not the HTTP
  service). The FastAPI app is the separate deployment surface.

## 6. Verification status

- `python -m pytest` → **18 passed**, offline, no keys.
- `python -m coilmem.store` → scope self-check passes.
- `python -m agents.demo` → cross-agent shared recall works; private isolated.
- `python -m agents.eval` → memory feeds ~73.5% fewer input tokens than naive over 12 turns,
  and the parity guardrail passes.

## 7. How to extend (common changes)

- **Add an agent role:** append to `ROLES` and add `ROLE_MODELS`/`ROLE_INSTR` entries in
  `agents/config.py`. The graph wires roles in list order automatically (`team.py`).
- **Change the workflow shape** (e.g. critic loops back to researcher): edit the edges in
  `_build_graph` in `team.py`.
- **Swap embeddings:** set `EMBED_PROVIDER` (local/openai/gemini) in `.env`, or pass `embed_fn`.
  Remember: one provider per DB (dim guard).
- **Real LLMs:** `agents/team.live_seats()` builds key-aware chats from `ROLE_MODELS`.
- **Stronger baseline for the eval:** add a "windowed" or "summarized" mode alongside
  `naive`/`memory` in `team._grounding` to report a more conservative saving.
- **Persist/scale the store:** `coilmem/store.py` is SQLite + brute-force cosine (fine to a
  few thousand memories/workspace). Swap to sqlite-vec/pgvector behind the same `add`/`search`
  API when needed.
- **HTTP surface:** extend `coilmem/app.py`; keep `X-API-Key` auth.

## 8. Known limitations / TODO

- Brute-force cosine (O(n) per search) — fine at MVP scale; index later.
- Sequential agents; no parallelism yet.
- Eval baseline is naive full-replay only (add windowed baseline for realism).
- No multi-tenant key management on the HTTP service (single static `COILMEM_KEY`).

## 9. Pointers

- `specs/mvp_spec.md`, `specs/build_plan.md` — the product wedge and original build plan.
- Tests encode the intended behavior — change them deliberately, they are the spec.
