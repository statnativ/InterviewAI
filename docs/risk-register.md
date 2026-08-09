# Risk Register

Maintained per the format defined in [.claude/product-architect.md](../.claude/product-architect.md).
Owners are not invented — `Unassigned` is used wherever no owner is actually known; this is
currently a solo project, so most risks are owned by Amit Tiwari by default.

---

### R-001
- **Category**: Security / Authorization
- **Description**: No authentication or authorization exists anywhere in the app. Every
  endpoint is open; `jobs.posted_by` has no real "current user" to point to.
- **Evidence**: Confirmed in `app/routers/*.py` — no auth dependency on any route.
  `app/models/user.py` exists but nothing creates or authenticates a `User`.
- **Likelihood**: High (certain, given current state)
- **Impact**: High (blocks any multi-user or real-data usage; PRD §5.5/§6 requires RBAC)
- **Severity**: High
- **Owner**: Amit Tiwari
- **Mitigation**: Sequenced as M6 (JWT auth, tenant isolation, RBAC) — not started.
- **Contingency**: None currently; app must not be exposed beyond localhost until M6.
- **Trigger**: Any plan to deploy beyond local dev, or to onboard a second user.
- **Status**: Open
- **Related ADR or product decision**: none yet

---

### R-002
- **Category**: Scalability / Reliability
- **Description**: AI calls (résumé parsing, and now M3's question generation) run inline on
  the request thread with no background job runner at all — not even `BackgroundTasks`, which
  has never been introduced anywhere in the codebase (confirmed: no celery/redis/rq/arq in
  `requirements.txt`). M3 added a third synchronous LLM call site (`POST /interviews`) without
  addressing this, reinforcing rather than resolving the risk.
- **Evidence**: Confirmed in `app/routers/candidates.py` (`upload_resume` awaits `parse_resume`
  directly) and `app/routers/interviews.py` (`create_interview` awaits `generate_questions`
  directly, added 2026-08-10).
- **Likelihood**: High (already true today; worsens as more AI calls are added)
- **Impact**: Medium (request latency/timeouts, not data loss)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: ADR-007 (2026-08-10) examined this for M4 specifically and found the
  roadmap's original "BackgroundTasks → Celery+Redis" framing doesn't fit M4's live-conversation
  shape — recommends a synchronous/WebSocket execution model for M4 instead, and defers
  Celery+Redis to M5 (report generation), which is genuinely a decoupled batch workload. This
  risk (inline calls on the request path) remains open for the *current* endpoints
  (résumé parsing, M3 question generation) regardless — ADR-007 doesn't address those.
- **Contingency**: None currently.
- **Trigger**: Observed request timeouts, or M2/M4 implementation start.
- **Status**: Open
- **Related ADR or product decision**: ADR-007

---

### R-003
- **Category**: Vendor dependence / Availability
- **Description**: Every AI capability (LLM, STT, TTS) depends entirely on OpenRouter with no
  fallback gateway or provider.
- **Evidence**: `app/services/llm_client.py`, `stt_client.py`, `tts_client.py` all call only
  `settings.openrouter_base_url`.
- **Likelihood**: Low-Medium (unmeasured — no incident yet, no SLA reviewed)
- **Impact**: High (an OpenRouter outage takes down every AI feature simultaneously)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: None for this risk specifically. IA-009 (2026-08-10) built a model-level
  fallback for the interview LLM (`deepseek/deepseek-v4-pro` on primary failure) — that's real,
  but it's still routed through OpenRouter, so it does nothing for an OpenRouter-wide outage.
  This risk (the gateway itself, not one model behind it) remains genuinely unaddressed.
- **Contingency**: Manual model-slug swap via `.env` if OpenRouter itself is down (does not
  help — OpenRouter is the single point of failure, not a specific model).
- **Trigger**: An observed OpenRouter outage or sustained degraded service.
- **Status**: Open
- **Related ADR or product decision**: ADR-002

---

### R-004
- **Category**: Availability / Cost
- **Description**: The default interview LLM (`nvidia/nemotron-3-ultra-550b-a55b:free`) is a
  free tier with undocumented rate limits — **now observed under real, if light, load** (IA-002,
  2026-08-10), not just theorized from public listings.
- **Evidence**: Model choice in `app/config.py`. During IA-002's latency measurement (4 real runs
  of `scripts/test_interview_pipeline.py` across two sessions): one run's TTS call
  (`hexgrad/kokoro-82m` — corrected: this is a **paid**, cheap model per `AI Architecture.md`
  ($0.62/M chars), not free-tier; its timeout reads as transient service trouble, not
  rate-limiting) hit the full 60s timeout with no response; another run's LLM call returned a
  200 with no usable `choices` field; a fourth run's LLM call succeeded but took 24.63s for a
  single leg — well above the 2.4–5.5s range the first clean run showed. None of these
  reproduced consistently — this reads as real variance, not a consistent failure, but it is now
  directly observed, not a guess.
- **Likelihood**: Medium (upgraded from Unknown — multiple anomalies observed across a handful of
  short runs; too small a sample to quantify a real rate, but no longer purely theoretical)
- **Impact**: Medium (would require an on-the-fly swap to a paid model mid-interview; for a live
  candidate, either failure mode — a 60s hang or a crash — is a genuinely bad experience, not
  just an inconvenience)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: Both observed hard-failure modes are now handled. The malformed-response case:
  `llm_client.py`'s `chat_completion` validates the response shape before indexing and raises a
  clean `LLMError` instead of an unhandled `KeyError` (fixed 2026-08-10, directly triggered by
  reproducing this during IA-002). The timeout/network-failure case: IA-009 (2026-08-10, priority
  bumped from Low to High given this is now observed, not hypothetical) added
  `interview_llm_model`'s automatic fallback to `interview_llm_fallback_model`
  (`deepseek/deepseek-v4-pro`) on any hard failure, plus a same-model retry-with-backoff for
  STT/TTS (no second model on record for either, so a swap isn't the honest option there). **Not
  mitigated**: the 24.63s-successful-but-slow case — the fallback only triggers on failure, not
  on a slow-but-technically-fine response; a performance guarantee would need racing against a
  shorter timeout, a bigger design not built here.
- **Contingency**: Manual swap to `z-ai/glm-5.2` via config if `deepseek/deepseek-v4-pro` (the
  new automatic fallback) is also degraded.
- **Trigger**: Already triggered — both hard-failure modes observed and now mitigated;
  slow-but-successful responses remain unmitigated and would need a future trigger of their own
  (e.g., a candidate complaint about a long wait) before that's worth building.
- **Status**: Open — both observed hard-failure modes mitigated (IA-009); the "successful but
  slow" case is a known, stated gap, not a hidden one
- **Related ADR or product decision**: ADR-002, ADR-007

---

### R-005
- **Category**: Correctness / Product quality
- **Description**: Reasoning-capable LLMs can leak internal "thinking" into user-facing output
  instead of a separate channel. Already observed once (Nemotron 3 Ultra) and fixed for that
  specific call path, but the failure mode could recur with a different reasoning model or an
  LLM call that doesn't yet set `reasoning.exclude`.
- **Evidence**: Confirmed and fixed in `app/services/llm_client.py` (`exclude_reasoning` param)
  and `interview_pipeline.py`'s use of it, this session.
- **Likelihood**: Medium (recurs if a new reasoning-model call site forgets the flag)
- **Impact**: Medium (a candidate could hear/read the AI's internal reasoning verbatim)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: `exclude_reasoning=True` used on interview-brain calls. Not enforced
  structurally — a future call site could still forget it.
- **Contingency**: None beyond code review; no automated test catches this.
- **Trigger**: Adding a new LLM call site using a reasoning-capable model.
- **Status**: Partially mitigated
- **Related ADR or product decision**: ADR-002

---

### R-006
- **Category**: Compliance / Privacy
- **Description**: The PRD (§6) requires encryption at rest/in transit, PII protection, and
  GDPR/CCPA-ready data handling and deletion. None of this exists — resumes and candidate PII
  are stored in plain local files and an unencrypted local Postgres instance.
- **Evidence**: `app/storage/local.py` writes plaintext files to `data/resumes/`; no encryption
  configuration anywhere in `docker-compose.yml` or `app/db.py`.
- **Likelihood**: High (certain, given current state)
- **Impact**: High (real PII, real compliance exposure the moment real candidate data is used)
- **Severity**: High
- **Owner**: Amit Tiwari
- **Mitigation**: None yet. Not explicitly sequenced into a milestone — currently implicit in
  M6 (auth/tenancy) but compliance/encryption isn't called out on its own.
- **Contingency**: Do not use real candidate PII until this is addressed.
- **Trigger**: Any use of real (non-test) candidate data.
- **Status**: Open
- **Related ADR or product decision**: none yet

---

### R-007
- **Category**: Data quality / Performance
- **Description**: `resumes.embedding` and `skills.embedding` (pgvector) are unpopulated —
  nothing generates embeddings yet. The `ivfflat` indexes on both columns were built against an
  empty table, and pgvector's own guidance is that ivfflat index quality depends on being built
  with representative data present.
- **Evidence**: Confirmed via `\di` — indexes exist; confirmed via code review — nothing in
  `app/services/` calls an embedding model.
- **Likelihood**: High (certain once embeddings are eventually populated in bulk)
- **Impact**: Low-Medium (degraded similarity search quality, not data loss — rebuildable)
- **Severity**: Low
- **Owner**: Amit Tiwari
- **Mitigation**: None yet — flagged in ADR-003.
- **Contingency**: Rebuild the ivfflat indexes (`REINDEX`) once real embeddings exist.
- **Trigger**: First bulk population of embeddings.
- **Status**: Open
- **Related ADR or product decision**: ADR-003

---

### R-008
- **Category**: Cost / Observability
- **Description**: The project is explicitly cost-sensitive (PD-002), but no cost tracking is
  actually instrumented. `ai_processing_logs` exists in the schema specifically for this
  purpose but nothing writes to it.
- **Evidence**: `app/models/ai_processing_log.py` has no corresponding write path in any
  service (`llm_client.py`, `stt_client.py`, `tts_client.py`, `resume_parser.py`).
- **Likelihood**: High (certain, given current state)
- **Impact**: Medium (cost claims in ADRs/PDs are estimates from published pricing, not
  measured actuals)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: None yet.
- **Contingency**: Manual cost estimation from OpenRouter's dashboard in the interim.
- **Trigger**: Before any milestone that meaningfully increases AI call volume (M2, M4).
- **Status**: Open
- **Related ADR or product decision**: PD-002

---

### R-009
- **Category**: Operational readiness
- **Description**: Everything is local-only — no CI, no deployed environment, no monitoring,
  no alerting. A machine restart, disk issue, or lost `.env` file currently has no recovery
  plan beyond re-running setup from `CLAUDE.md`.
- **Evidence**: No `.github/workflows/` or equivalent exists; `docker-compose.yml` targets
  `localhost` only.
- **Likelihood**: High (certain, given current state — this is expected at this project stage)
- **Impact**: Low currently (no production users), rising sharply once anything is deployed
- **Severity**: Low (for now — explicitly deferred, not neglected; see M6b)
- **Owner**: Amit Tiwari
- **Mitigation**: Deployment explicitly sequenced as M6b (Cloud Run + Neon + GCS), not started.
- **Contingency**: None needed while local-only.
- **Trigger**: Start of M6b.
- **Status**: Open (accepted for current phase)
- **Related ADR or product decision**: PD-002

---

### R-010
- **Category**: Cost / Performance
- **Description**: `interview_pipeline.py`'s conversation history is an unbounded in-memory
  Python list passed to the LLM in full on every turn. A long interview grows the context
  window (and therefore per-turn cost and latency) without limit. It is also process-local —
  lost on restart, unreachable from any other uvicorn worker.
- **Evidence**: Confirmed in `app/services/interview_pipeline.py` — `run_turn` appends to
  `history` with no truncation, summarization, or size check.
- **Likelihood**: Medium (depends on typical interview length, which is currently unmeasured)
- **Impact**: Medium (rising per-turn cost/latency over a long interview)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: Partially designed. ADR-007 (2026-08-10) requires externalizing session state
  to Postgres for M4 — this resolves the *process-locality* half (lost on restart, unreachable
  from other workers) as a byproduct of doing persistence at all. It does **not** by itself
  bound what gets sent to the LLM each turn — that still needs IA-004's truncation/sliding-window
  logic, which remains a separate, unimplemented piece of work regardless of storage backend.
  Not yet implemented either way — M4 hasn't started.
- **Contingency**: None currently.
- **Trigger**: M4 (wiring the cascade into real, longer interviews) surfacing measurably
  degraded latency or cost on later turns.
- **Status**: Open — partial mitigation designed, nothing built
- **Related ADR or product decision**: ADR-004, ADR-007

---

### R-011
- **Category**: Data model / Architecture
- **Description**: `Interview` (`app/models/interview.py`) is simultaneously a reusable
  template shared across every applicant to a job (`shared: bool`, no candidate tie) and, as of
  M3, a one-off artifact personalized for exactly one candidate (`candidate_id` set). Both
  states live in the same table with no constraint distinguishing them. `shared = true` and
  `candidate_id IS NOT NULL` is a reachable, undefined state today — nothing stops a recruiter
  from sharing a candidate-personalized interview with every other applicant, surfacing one
  person's résumé-derived questions to everyone else.
- **Evidence**: Confirmed in `app/models/interview.py` and `app/routers/interviews.py` — no
  CHECK constraint or application-level guard exists for this combination, unlike the analogous
  two-mode `User` entity, which does have `ck_users_platform_admin_no_tenant`.
- **Likelihood**: Medium (requires a recruiter to both personalize an interview and then toggle
  sharing on it — a plausible UI path, not an edge case)
- **Impact**: Medium (a candidate could see interview questions written with visible reference
  to a different candidate's employer/skills — a real, visible mistake, not silent data
  corruption)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: None implemented. Options: a DB `CHECK` constraint preventing
  `shared AND candidate_id IS NOT NULL` simultaneously (cheapest); or a product decision that
  this combination is intentionally allowed (unlikely, given personalization's entire point is
  specificity to one person).
- **Contingency**: None currently — found during the 2026-08-10 architecture review, not yet
  triggered in practice.
- **Trigger**: A recruiter shares a personalized interview, or a test/audit surfaces the
  combination.
- **Status**: Open
- **Related ADR or product decision**: none yet — M3 shipped the schema change without one.

---

### R-012
- **Category**: Operational readiness / Process
- **Description**: The repository has exactly one git commit ("Initial commit: full ATS
  vertical slice," 2026-08-09) despite three major features having shipped since (M6 Phase 1/2,
  the master admin auth module, M3) — all of it sitting uncommitted in the working tree (77
  modified/untracked files as of the 2026-08-10 architecture review). Every ADR in this
  directory has a "Rollback or exit strategy" section that implicitly assumes revertible git
  history exists; it does not, for anything shipped after the initial commit.
- **Evidence**: Confirmed via `git log --oneline` (1 commit) and `git status --short` (77 files)
  on 2026-08-10.
- **Likelihood**: High (already true today)
- **Impact**: Medium (no incremental rollback granularity if a regression is found in any
  shipped-but-uncommitted work; no code-review trail)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: IA-013's checkpoint commit landed and pushed to `origin/main` on 2026-08-10
  (commit `ef827e3`, 87 files) — real rollback granularity now exists from this point forward.
  The historical gap (M6 Phase 1/2, the admin module, and M3 all landed as one undifferentiated
  commit rather than one per feature) is not retroactively fixable without a history rewrite,
  which is not worth the disruption for a solo POC repo — accepted as-is. What matters is the
  discipline going forward: one commit per feature, not accumulated indefinitely.
- **Contingency**: A regression in anything from before 2026-08-10 still requires manually
  reverting specific file edits. Anything after this commit has real `git revert` available.
- **Trigger**: Already triggered — resolved for future work as of this review's mitigation.
- **Status**: Mitigated (going forward) — historical gap accepted, not retroactively fixed
- **Related ADR or product decision**: none — a process gap, not a technical one.
