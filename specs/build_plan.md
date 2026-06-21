# Build Plan — `coilmem` MVP (solo, 1–3 days)

Spec: `specs/mvp_spec.md`. Goal: a runnable hosted shared-memory API + a two-agent demo
that proves cross-agent context transfer. Stop at the first version that works.

Ordering rule: build the retrieval core + its self-check **first** (highest risk, the
whole differentiator). API and demo wrap around a proven core.

---

## Day 1 — Core: store + retrieval + self-check

The riskiest, most valuable piece. Nothing else matters if scoped retrieval is wrong.

1. **Project skeleton** — `coilmem/` with `store.py`, `embed.py`, `app.py`, `demo.py`,
   `requirements.txt` (`fastapi uvicorn httpx numpy`). ~15 min.
2. **`embed.py`** — `embed(text) -> list[float]` calling OpenAI `text-embedding-3-small`
   via `httpx`. Read `OPENAI_API_KEY` from env. One function, pluggable.
3. **`store.py`** — SQLite layer:
   - `init_db(path)` — create `memories` table (schema in spec) + index on `workspace`.
   - `add(workspace, agent_id, scope, text, metadata=None)` — embed, pack float32 BLOB, insert, return id.
   - `search(workspace, agent_id, query, k=5)` — apply the **retrieval rule** (spec): filter
     `workspace` + (`shared` OR own `private`), cosine-rank, return top-k.
   - `delete(id)`, `list(workspace, agent_id)`.
4. **Self-check `demo()` in `store.py` (`python -m coilmem.store`):** the ONE runnable
   check the logic leaves behind —
   ```
   A writes shared "DB is Postgres on port 5433"
   C writes private "my secret scratchpad note"
   B searches "what database are we using"
   assert top result is A's shared memory
   assert C's private memory NOT in results   # the invariant that must not break
   ```
   This guards the entire wedge. Do not move on until green.

**End of Day 1:** scoped retrieval works and is proven. ~half a day; buffer is fine.

## Day 2 — API + auth + run

Wrap the proven core in HTTP. Thin layer, low risk.

5. **`app.py`** — FastAPI over `store.py`: `POST /memory`, `GET /memory/search`,
   `GET /memory`, `DELETE /memory/{id}`. Pydantic request models.
6. **Auth** — one dependency checking `X-API-Key` against `COILMEM_KEY` env. Reject 401 otherwise. No user table.
7. **Manual smoke test** — `uvicorn coilmem.app:app`, then `curl` each endpoint; confirm
   the same scope invariant holds over HTTP (B's search excludes C's private).
8. **`README.md`** — 5-line quickstart: set 2 env vars, run, `curl` example. The README is the product's front door.

**End of Day 2:** shippable API. If time runs out here, this is a legitimate stopping point — the demo can be Day 2.5.

## Day 3 — Two-agent demo + ship (buffer day)

The artifact that does the selling.

9. **`demo.py`** — two tiny "agents" (plain functions, no framework needed) sharing one
   workspace via the live API:
   - `researcher` agent writes 2–3 findings to `shared`.
   - `writer` agent searches `shared`, retrieves the findings, prints a short synthesis —
     visibly using context it never computed itself.
   - Print a before/after token note (with vs without shared recall) to make the value legible.
   Keep it copy-pasteable; it doubles as the Reddit/Discord post.
10. **Polish + publish** — push repo, post demo to r/AI_Agents + LangGraph/CrewAI Discords.
    Collect the ≥3-of-5 "this is a real pain" signal (spec success criteria).

**End of Day 3:** public demo + first validation signal.

---

## Cut lines (if behind)

- Drop `GET /memory` (list) and `DELETE` — `search` + `POST` alone prove the wedge.
- Drop API auth for the demo (run locally) — add before any public endpoint.
- Optional `numpy` → pure-Python cosine if dependency setup eats time.

## Explicit non-goals (don't let these creep in)

Dashboard/UI, graph memory, summarization, fact extraction, TTL/eviction, SDK,
multi-tenant key management, a real vector index. All are post-validation, and most
are *other* products. Build them only if the wedge proves out first.

## Definition of done (MVP)

- `python -m coilmem.store` self-check passes (scope invariant holds).
- API serves all in-scope endpoints; auth rejects bad keys.
- `demo.py` shows agent B using agent A's shared memory, with C's private memory invisible.
- README quickstart works from a clean clone.
