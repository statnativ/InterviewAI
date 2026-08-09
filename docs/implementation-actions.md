# Implementation Actions

Maintained per the format defined in [.claude/product-architect.md](../.claude/product-architect.md).
Detailed milestone descriptions live in [architecture/overview.md](architecture/overview.md)'s
roadmap table — this list is the actionable, trackable version, split into required work and
optional improvements, plus near-term gaps surfaced by the risk register.

## Required

| ID | Action | Reason | Owner | Priority | Dependencies | Acceptance criteria | Related decision | Status |
|---|---|---|---|---|---|---|---|---|
| IA-001 | Wire `ai_processing_logs` writes into `llm_client.py`, `stt_client.py`, `tts_client.py`, `resume_parser.py` | Cost-sensitive POC has zero actual cost tracking today (R-008) | Amit Tiwari | High | None | Every AI call writes a row with model, token/duration counts, and cost | PD-002, R-008 | Not started |
| IA-002 | Measure end-to-end latency of one full cascade turn (STT+LLM+TTS) | ADR-004 left this as an explicit unresolved question; blocks knowing if async is even fast enough per PRD §6 | Amit Tiwari | High | None | A recorded, repeatable latency number for a single turn, compared against PRD's <10s question-gen target | ADR-004 | Not started |
| IA-003 | Move resume scoring (and eventually parsing) off the request path (M2: BackgroundTasks + polling) | Inline AI calls in the request path will degrade/timeout as more AI work is added (R-002) | Amit Tiwari | High | None | `POST` returns immediately with a pending status; a polling `GET` returns the result once ready | R-002 | Not started |
| IA-004 | Add a conversation-history bound (truncation, summarization, or sliding window) to `interview_pipeline.py` | History currently grows unboundedly, risking rising cost/latency on long interviews (R-010) | Amit Tiwari | Medium | IA-002 (need a latency baseline first) | A defined max history size/strategy, with a test showing a long interview doesn't grow context unboundedly | ADR-004, R-010 | Not started |
| IA-005 | M3: AI question generation (8–12 Qs, edit/reorder/regenerate) | Core PRD feature (§5.2), not yet built | Amit Tiwari | Medium | M2 | Recruiter can generate, edit, reorder, and regenerate individual questions via the API | PRD §5.2 | Not started |
| IA-006 | M4: wire the voice cascade into the real app with DB persistence | Currently only a standalone script (`scripts/test_interview_pipeline.py`); not usable by an actual candidate | Amit Tiwari | Medium | IA-002, IA-004 | A real endpoint persists each interview turn (transcript, AI response, audio refs) to Postgres | ADR-004 | Not started |
| IA-007 | M6: auth, tenant isolation, RBAC | No authentication exists anywhere; blocks any real multi-user or deployed usage (R-001) | Amit Tiwari | High (before any deployment) | None | Every endpoint requires auth; `jobs.posted_by` resolves to a real authenticated user; roles enforced | R-001, PRD §5.5/§6 | Not started |
| IA-008 | Address PII/compliance gap: encryption at rest/in transit, data deletion path | PRD §6 requires this; currently plaintext local storage (R-006) | Amit Tiwari | High (before real candidate data) | IA-007 | Resume files and PII encrypted at rest; a deletion endpoint/process exists | R-006, PRD §6 | Not started |

## Optional / improvements

| ID | Action | Reason | Owner | Priority | Dependencies | Acceptance criteria | Related decision | Status |
|---|---|---|---|---|---|---|---|---|
| IA-009 | Add automatic LLM fallback (DeepSeek V4 Pro / GLM-5.2) if the free-tier interview model is rate-limited | No fallback exists today (R-003, R-004) | Amit Tiwari | Low | IA-001 (to observe actual rate-limit behavior first) | A 429/throttle response from the primary model triggers an automatic retry on a paid fallback | ADR-002, R-003, R-004 | Not started |
| IA-010 | Rebuild `ivfflat` indexes on `resumes.embedding`/`skills.embedding` after real embeddings are populated | Indexes were built empty; pgvector guidance says index quality depends on representative data at build time (R-007) | Amit Tiwari | Low | Whichever milestone first populates embeddings in bulk | `REINDEX` run and documented after first bulk embedding population | ADR-003, R-007 | Not started |
| IA-011 | M6b: deploy to Cloud Run + Neon + GCS | Currently local-only, no CI/monitoring (R-009) | Amit Tiwari | Low (deferred by design) | M6 (auth) should land first | App reachable outside localhost with cost within the stated free/cheap-tier target | PD-002, R-009 | Not started |

## Done (for traceability)

| ID | Action | Reason | Owner | Priority | Dependencies | Acceptance criteria | Related decision | Status |
|---|---|---|---|---|---|---|---|---|
| IA-000a | Adopt full 9-table ATS schema with pgvector | Avoid a second schema migration once M2/M3/M5 need it | Amit Tiwari | High | None | All 9 tables, both extensions, and every specified index exist and verified via `\dt`/`\dx`/`\di` | ADR-003 | Done |
| IA-000b | Build and validate the STT→LLM→TTS cascade as a standalone script | De-risk the voice pipeline before any app/DB integration | Amit Tiwari | High | None | Two-turn scripted demo runs end-to-end with coherent multi-turn output, verified by listening to generated audio | ADR-004 | Done |
| IA-000c | Log PD-001 and PD-002 | Formalize product decisions that were previously only stated in conversation | Amit Tiwari | Medium | None | PD files exist under `docs/product-decisions/` following the required template | PD-001, PD-002 | Done |
