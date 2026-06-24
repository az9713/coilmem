# coilmem Codex Security Scan Progress Report

Date: 2026-06-23 America/Los_Angeles  
Repository: `az9713/coilmem`  
Local checkout: `(redacted local checkout path)`  
Target revision: `82071655bc0f3252fd3299083851f60483f3162d` (`8207165`)  
Scan ID: `ca887c2d-33fd-4956-be94-f48e6ec6c1d4`  
Mode: Codex Security `standard` repository-wide scan  
Scope: whole repository (`.`)

## Current Status

The scan is not complete yet. It is in the finding-discovery phase.

The setup, preflight, threat-model phase, repository worklist generation, and a substantial part of discovery have run. Validation, attack-path analysis, final canonical JSON generation, report finalization, and `complete_codex_security_scan` remain to be done.

## Setup And Preflight Completed

1. Cloned `https://github.com/az9713/coilmem.git` into the local workspace.
2. Opened a Codex Security workspace for the cloned checkout.
3. User started the scan in the Codex Security workspace.
4. Loaded the authoritative scan context:
   - Scan directory: `(redacted local scan directory)`
   - Scope: `.`
   - Target path: local cloned repo
5. Ran the Codex Security config preflight.
   - Result: `ready`
   - Delegation available: yes
   - Goal tools available: yes
   - Multi-agent runtime: native v1 from tool surface
   - Usable worker slots: documented default 6
   - Goals enabled: yes
6. Created a scan goal requiring full worklist/candidate/report closure before completion.

## Threat Model Completed

The repository-level threat model was written and copied into the scan context.

Artifacts written:

- Repository-scoped threat model: `<scan-context>\threat_model.md`
- Per-scan threat model copy: `<scan-context>\artifacts\01_context\threat_model.md`

Threat model summary:

- Primary product surface is a Python/FastAPI memory service backed by SQLite.
- Core security invariant is multi-agent memory isolation: shared workspace memories plus each agent's own private memories, never another agent's private memories.
- Key boundaries reviewed:
  - HTTP clients to FastAPI API.
  - API service to SQLite store.
  - API/store to external embedding providers.
  - `.env` and environment variable loading.
  - Agent orchestration and prompt/memory flows.
  - Developer evidence tools and generated evidence files.
- Main risk classes identified:
  - Cross-agent or cross-workspace private memory exposure.
  - Shared API-key authorization weaknesses.
  - Memory poisoning and prompt-context integrity.
  - Sensitive evidence artifact leakage.
  - Outbound embedding/provider privacy surprises.
  - Unbounded resource usage in embedding/search paths.

## Discovery Worklist Generated

The deterministic repository-wide source-like inventory was generated using Codex Security's `generate_rank_input.py`.

Artifacts generated:

- `artifacts\02_discovery\rank_input.jsonl`
- `artifacts\02_discovery\deep_review_input.jsonl`

The worklist contains 18 rows. Because the repository is small, the scan used a 100% deep-review set instead of ranking away files.

Files in the deep-review worklist:

- `agents/__init__.py`
- `agents/config.py`
- `agents/demo.py`
- `agents/eval.py`
- `agents/llm.py`
- `agents/team.py`
- `coilmem/__init__.py`
- `coilmem/app.py`
- `coilmem/config.py`
- `coilmem/demo.py`
- `coilmem/embed.py`
- `coilmem/store.py`
- `evidence/memories.json`
- `evidence/recall_log.json`
- `evidence/sections.json`
- `tools/evidence_run.py`
- `tools/generate_memories_md.py`
- `tools/generate_trace.py`

The Codex Security progress UI was updated to discovery with 18 worklist rows.

## Subagent File Review Run So Far

Six file-review workers were dispatched, each with explicit ownership of three files.

Completed workers:

1. Worker `019ef7c6-f6f4-7b53-b9b4-e456e1c3f276`
   - Reviewed:
     - `agents/__init__.py`
     - `agents/config.py`
     - `agents/demo.py`
   - Found one plausible low/medium privacy/configuration candidate:
     - `CAND-agents-config-01`: silent live-model provider fallback can send prompts/team context to an unintended provider when a preferred provider key is missing but another provider key is present.

2. Worker `019ef7c8-96cd-7863-a88c-d8bc9bf3874c`
   - Reviewed:
     - `evidence/memories.json`
     - `evidence/recall_log.json`
     - `evidence/sections.json`
   - Found no reportable candidates in the checked synthetic evidence files.
   - Confirmed `recall_log.json` showed `foreign_private_recalled = 0`.

3. Worker `019ef7c8-f6e0-7491-a96f-814defe7cbeb`
   - Reviewed:
     - `tools/evidence_run.py`
     - `tools/generate_memories_md.py`
     - `tools/generate_trace.py`
   - Found several plausible evidence-disclosure candidates:
     - `CAND-tools-evidence-run-01`: `tools/evidence_run.py` writes unredacted full memory rows and recall text to tracked evidence artifacts.
     - `CAND-tools-evidence-run-02`: `tools/evidence_run.py` defaults `EMBED_PROVIDER` to OpenAI when unset, which can send real memory/query text to an external embedding provider during live evidence runs.
     - `CAND-tools-generate-memories-md-01`: `tools/generate_memories_md.py` writes and prints full private memory text from `evidence/memories.json`.
     - `CAND-tools-generate-trace-01`: `tools/generate_trace.py` writes unredacted shared/model text excerpts into `trace.md`.

Workers still not returned when this status report was requested:

- `019ef7c7-55e7-7212-ab3b-316d39a36c53`
  - Assigned: `agents/eval.py`, `agents/llm.py`, `agents/team.py`
- `019ef7c7-be3f-7951-a683-f3f44bc29f43`
  - Assigned: `coilmem/__init__.py`, `coilmem/app.py`, `coilmem/config.py`
- `019ef7c8-259f-73e0-9b11-7c016e109ab5`
  - Assigned: `coilmem/demo.py`, `coilmem/embed.py`, `coilmem/store.py`

Because those workers timed out, parent-side review was started for their areas to avoid blocking indefinitely.

## Parent-Side Discovery And Validation Evidence Collected

The parent scan inspected key runtime surfaces directly:

- `coilmem/app.py`
- `coilmem/store.py`
- `coilmem/embed.py`
- `coilmem/config.py`
- `coilmem/demo.py`
- `agents/team.py`
- `agents/eval.py`
- `agents/llm.py`
- `tests/test_api.py`
- `tests/test_store.py`
- `tests/test_agents.py`
- `.env.example`
- `.gitignore`
- tracked `evidence/*`

Important confirmed behavior:

1. SQL queries in `coilmem/store.py` use bound parameters.
2. Store-level `search()` enforces the documented predicate:
   - same workspace
   - shared memories, or private memories for the supplied `agent_id`
3. Store-level tests cover workspace isolation and foreign-private exclusion.
4. API-level authentication is a single shared `X-API-Key`.
5. The API accepts caller-supplied `workspace` and `agent_id`.
6. The API delete route deletes by `mem_id` only, with no workspace or agent ownership check.
7. Evidence artifacts under `evidence/` are tracked by git.
8. `.gitignore` does not exclude generated evidence outputs.

## Strongest Candidate Found So Far

The strongest candidate is an HTTP API authorization-boundary issue.

### Candidate: Shared API Key Allows Agent Impersonation And Private Memory Access

Affected locations:

- `coilmem/app.py:25-28`: `require_key()` authenticates only a single shared `COILMEM_KEY`.
- `coilmem/app.py:49-52`: `/memory/search` trusts caller-supplied `workspace` and `agent_id`.
- `coilmem/app.py:55-58`: `/memory` list trusts caller-supplied `workspace` and `agent_id`.
- `coilmem/store.py:91-106`: `search()` correctly filters private rows for the supplied `agent_id`, but the API does not bind that id to the authenticated caller.
- `coilmem/store.py:109-114`: `list_memories()` returns rows for the supplied `agent_id`.

Observed reproduction during scan:

- A private memory was written for agent `C`.
- A client with the shared API key requested `/memory?workspace=w1&agent_id=C`.
- The API returned C's private memory.
- The same caller could search as `agent_id=C` and retrieve C's private memory.

This means the store predicate is internally correct, but the HTTP boundary does not authenticate an agent identity. In any deployment where different agents/clients are mutually untrusted but share the service key, private scope can be bypassed by choosing another `agent_id`.

Likely severity:

- High if `COILMEM_KEY` is shared among multiple mutually untrusted agents/clients or tenants.
- Medium if the service is intentionally single-operator/single-trust-domain and `agent_id` is only a caller-supplied label.

This candidate still needs formal validation and attack-path ledger receipts before it can appear in the official final report.

## Other Plausible Candidates Needing Validation

### Unscoped Delete By Memory ID

Affected locations:

- `coilmem/app.py:61-67`
- `coilmem/store.py:117-120`

Observed reproduction during scan:

- A private memory was created.
- A request with only the shared API key called `DELETE /memory/{mem_id}`.
- The row was deleted, with no workspace or agent ownership check.

Impact:

- Any client with the shared key and a known or leaked memory id can delete any memory row, including another agent's private row or another workspace's row.

Severity depends on whether memory ids are guessable or exposed to the caller through other list/search/impersonation paths.

### Tracked Evidence Artifacts Can Expose Memory Contents

Affected files:

- `tools/evidence_run.py`
- `tools/generate_memories_md.py`
- `tools/generate_trace.py`
- tracked `evidence/*`
- `.gitignore`

Current assessment:

- This is real if operators run the evidence tools on sensitive or production-like memory data and then commit, publish, or share generated artifacts/logs.
- The currently tracked sample evidence appears synthetic and did not contain secrets in the worker review.
- This may be reported as a lower-severity finding or grouped as a hardening recommendation, depending on final validation.

### External Provider Privacy Surprises

Affected files:

- `tools/evidence_run.py`
- `coilmem/embed.py`
- `agents/config.py`
- `agents/team.py`
- `agents/llm.py`

Current assessment:

- `tools/evidence_run.py` defaults `EMBED_PROVIDER` to OpenAI when unset.
- `coilmem/embed.py` sends embedding input text to OpenAI or Gemini when configured.
- `agents/config.py` can silently fall back to a different live chat provider if the preferred provider key is absent.
- These issues are mostly operator-controlled privacy/configuration risks, not remote attacker paths.
- They need validation and severity calibration before final reporting.

## Coverage Completed So Far

Completed or parent-reviewed areas include:

- FastAPI API boundary and auth model.
- Store predicates for search/list/delete.
- Embedding provider dispatch and external calls.
- Environment loading behavior.
- Agent team prompt/memory flow.
- Agent eval and demo paths.
- Evidence JSON files.
- Evidence generation/rendering scripts.
- Git tracking and ignore behavior for evidence artifacts.

Coverage still needs to be formally written into:

- `artifacts\02_discovery\work_ledger.jsonl`
- `artifacts\02_discovery\raw_candidates.jsonl`
- `artifacts\03_coverage\repository_coverage_ledger.md`
- per-candidate ledgers under `artifacts\05_findings\<candidate_id>\candidate_ledger.jsonl`

## What Remains To Be Done

1. Finish or close the three timed-out file-review workers.
   - If they return, reconcile their receipts.
   - If they do not return, replace them with parent-authored full-file receipts for their assigned files.

2. Write the discovery artifacts:
   - `work_ledger.jsonl` with completion receipts for all 18 worklist rows.
   - `raw_candidates.jsonl` with normalized candidate objects.
   - `finding_discovery_report.md`.
   - `repository_coverage_ledger.md` with rows for high-impact families, including rows closed as suppressed, not applicable, or reportable.

3. Create per-candidate directories and candidate ledgers.
   - Each candidate needs discovery, validation, and attack-path receipts or an explicit deferred reason.

4. Run formal validation phase.
   - Validate the API impersonation/private-memory access candidate.
   - Validate unscoped delete.
   - Decide whether evidence-artifact disclosure is reportable or should be a lower-severity hardening finding.
   - Decide whether provider fallback/default embedding behavior is reportable or a configuration warning.

5. Run formal attack-path analysis.
   - Assign final severity and confidence.
   - Record realistic preconditions.
   - Separate high-impact API boundary issues from operator-only tooling/privacy issues.

6. Generate canonical final JSON contract.
   - The Codex Security workflow requires final report semantics in canonical JSON, not a hand-authored final report.

7. Run finalization.
   - Use the plugin finalizer to generate the official `report.md`.
   - Validate/seal the report contract.

8. Complete the Codex Security scan.
   - Call `complete_codex_security_scan` only after artifacts, ledgers, candidate receipts, final report, and coverage closure are all complete.

## Bottom Line

The scan has already found at least one likely reportable issue in the HTTP API authorization model: the single shared API key does not bind to an agent identity, so callers can choose another `agent_id` and retrieve that agent's private memories. A related delete-by-id issue may also be reportable.

The scan is not final. The remaining work is primarily artifact reconciliation, formal validation, attack-path severity analysis, and official Codex Security finalization.
