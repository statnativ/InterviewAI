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
- **Description**: AI calls (LLM, resume parsing, and eventually STT/TTS) run inline on the
  request thread with no background job runner. Slower calls will degrade or time out requests
  as more AI work is added (M2 scoring, M4 voice cascade).
- **Evidence**: Confirmed in `app/routers/candidates.py` — `upload_resume` awaits
  `parse_resume` directly in the request path.
- **Likelihood**: High (already true today; worsens as more AI calls are added)
- **Impact**: Medium (request latency/timeouts, not data loss)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: Sequenced as M2 (BackgroundTasks + polling) and M4 (Celery+Redis once
  BackgroundTasks isn't enough) — not started.
- **Contingency**: None currently.
- **Trigger**: Observed request timeouts, or M2/M4 implementation start.
- **Status**: Open
- **Related ADR or product decision**: none yet

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
- **Mitigation**: None implemented. Paid fallback LLM models (DeepSeek V4 Pro, GLM-5.2) were
  identified but no automatic failover exists.
- **Contingency**: Manual model-slug swap via `.env` if OpenRouter itself is down (does not
  help — OpenRouter is the single point of failure, not a specific model).
- **Trigger**: An observed OpenRouter outage or sustained degraded service.
- **Status**: Open
- **Related ADR or product decision**: ADR-002

---

### R-004
- **Category**: Availability / Cost
- **Description**: The default interview LLM (`nvidia/nemotron-3-ultra-550b-a55b:free`) is a
  free tier with undocumented rate limits observed from public listings, not confirmed via load
  testing.
- **Evidence**: Model choice in `app/config.py`; rate-limit behavior not tested under load.
- **Likelihood**: Unknown (not tested)
- **Impact**: Medium (would require an on-the-fly swap to a paid model mid-interview)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: None implemented yet.
- **Contingency**: Manual swap to `deepseek/deepseek-v4-pro` or `z-ai/glm-5.2` via config.
- **Trigger**: Observed 429s/throttling from OpenRouter on the free-tier model.
- **Status**: Open
- **Related ADR or product decision**: ADR-002

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
  window (and therefore per-turn cost and latency) without limit.
- **Evidence**: Confirmed in `app/services/interview_pipeline.py` — `run_turn` appends to
  `history` with no truncation, summarization, or size check.
- **Likelihood**: Medium (depends on typical interview length, which is currently unmeasured)
- **Impact**: Medium (rising per-turn cost/latency over a long interview)
- **Severity**: Medium
- **Owner**: Amit Tiwari
- **Mitigation**: None implemented.
- **Contingency**: None currently.
- **Trigger**: M4 (wiring the cascade into real, longer interviews) surfacing measurably
  degraded latency or cost on later turns.
- **Status**: Open
- **Related ADR or product decision**: ADR-004
