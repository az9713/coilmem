# Project: coilmem

Shared memory for **multi-agent** systems (workspace `shared` scope + per-agent `private`
scope), plus a **researcher → critic → writer** team on LangGraph that exercises it.
Independent codebase — no council, no shared package.

## Orientation (read these before non-trivial changes)
- `DEVELOPMENT.md` — architecture, decisions + rationale, extension guide, known limits.
- `DEVELOPMENT_JOURNEY.md` — how this came to be (the full cross-project history).
- `specs/mvp_spec.md`, `specs/build_plan.md` — the product wedge and original build plan.
- `council-coilmem-decision.md` — why coilmem is its own repo (the council was the wrong vehicle).
- `README.md` — setup + run.

## Invariants — do not break without explicit intent
- **The scope rule is the product.** `store.search()` returns `shared` + the caller's own
  `private`, and **never** another agent's `private`. Keep it intact and tested.
- **Dim guard:** one `EMBED_PROVIDER` per DB. `add()` rejects mismatched embedding dims
  (cosine over `zip()` would silently truncate). Don't remove without a multi-vector design.
- **Agents recall with their real `agent_id`** — that enforces private isolation while letting
  an agent see its own private. Cross-agent sharing happens only via `shared`.
- **Quality-parity guardrail is author/role-based, not a substring.** `check_quality_parity`
  must verify needed context is retained AND that no *other* role's private appears (the
  writer's own private is allowed). A prior bug used a bare `"private scratch"` string and
  tripped on the writer's own notes — keep it role-based.

## Workflow
- Run offline tests before and after changes: `python -m pytest` (no API keys; StubChat + fake
  embeddings) and `python -m coilmem.store` (scope self-check). Tests are the spec.
- Live agent runs need provider keys in `.env`; construction-verified only so far.
- The eval's token saving is measured vs the **naive full-replay baseline (a ceiling)** — state
  the baseline when quoting the number; windowing/summarizing would narrow it.
- Embeddings: `local` (keyless default) / `openai` / `gemini`. Anthropic has no embeddings API.
