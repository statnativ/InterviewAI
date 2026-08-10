# ADR-008: Candidate session authentication and interview-audio storage (M4)

- Status: Accepted
- Date: 2026-08-10
- Owners: Amit Tiwari
- Related product decision: none yet
- Supersedes: none
- Superseded by: none

## Context

ADR-007 settled M4's execution model (a synchronous endpoint persisting each interview turn to
Postgres) but was scoped entirely to *transport* — it never asked who is calling the new
endpoint. A pre-implementation `/architect-review` against that plan (2026-08-10) found the gap
directly: `app/deps.py`/`app/services/authz.py` define exactly three roles (`admin`,
`recruiter`, `hiring_manager`), all resolved via the recruiter-side `X-Tenant-Id`/`X-User-Email`
dev headers. **No candidate identity or auth mechanism exists anywhere in this codebase.** A
follow-up frontend exploration confirmed the gap is real, not theoretical:
`frontend/src/pages/session/OnboardingConsent.tsx` collects zero name/email fields, and every
existing `frontend/src/lib/api.ts` call — including on candidate-facing pages — sends the
*recruiter's* identity headers.

ADR-007 also left interview-audio storage as an explicitly unresolved, non-deferrable
dependency: R-006 (PII/retention gap, already open for résumés) applies at least as much to
interview audio, arguably more, since voice is more sensitive than a résumé file. ADR-007's own
words: "a real decision... is required before M4 ships, not an open question to carry forward."

Both decisions were made together because they're the same shape of tradeoff: this is a
cost-sensitive POC (PD-002) with an established precedent — R-001 already accepts "no real auth
exists" for the entire recruiter side pre-M6, and ship-then-track is how every risk in this
codebase gets handled once the alternative is blocking a milestone that has real learning value
(the STT→LLM→TTS cascade itself, which is what M4 actually teaches).

## Decision drivers
- PD-002 (cost-sensitive POC scope) — no appetite to build a token-issuance system or
  encryption-at-rest inside a milestone that's about wiring a voice cascade, not auth or crypto.
- R-001's existing precedent: the recruiter side has operated with header-only "identity" since
  M1, tracked as an open, accepted risk rather than a blocker — the candidate side inheriting
  the same posture is consistent, not a new lowering of the bar.
- ADR-007 already established `interview_sessions.id` as a random, server-minted UUID for
  idempotency purposes (the `(session_id, turn_index)` key) — reusing it as a credential adds no
  new primitive to the system.
- `app/storage/local.py`'s existing pattern (plaintext local disk for résumés) is the only
  storage precedent in this codebase; introducing a second, different pattern (encrypted) for
  audio specifically, without a broader PII/encryption pass covering résumés too, would be
  inconsistent rather than actually safer in practice.

## Considered options

### Candidate auth

#### Option 1: `interview_sessions.id` as bearer credential (no login)
The session UUID itself, returned once at creation and held by the client, is what every
subsequent turn request presents. No separate token, no expiry logic, no login form.

#### Option 2: Short-lived signed invite token
Issued when a recruiter sends the interview invite (PRD §7 step 3), tied to a specific
candidate+interview, expiring after some window.

#### Option 3: Ship with zero access control, track as a stated gap
No credential at all — any request naming a valid `session_id` (or even an inferred one, if IDs
were sequential) succeeds.

### Audio storage

#### Option 1: Raw, unencrypted local disk (same pattern as résumés)
`app/storage/local.py`'s existing `save_upload` pattern, extended with a sibling function for
interview audio.

#### Option 2: Transcript-only, never persist raw audio
STT output (text) is what's stored on `interview_turns`; candidate audio bytes are used
transiently for the STT call and discarded.

#### Option 3: Encrypted at rest
Same local-disk storage, encrypted (e.g. Fernet or a KMS-backed key) before write.

## Decision

**Candidate auth: Option 1 — `interview_sessions.id` as the bearer credential.** Session
creation is itself keyed on the interview's own id (already an unguessable UUID, already the
frontend's URL param since M3), so there's no unauthenticated bootstrap step to design around —
the first request in the chain is already gated by an unguessable identifier, and the second
(the session id) inherits the same property.

**Audio storage: Option 1 — raw, unencrypted local disk, deliberately risk-accepted, not
solved.** This decision does not close R-006 for interview audio; it widens R-006's existing,
already-open scope to include a new data category and records that the widening was a conscious
choice, not an oversight ADR-007 flagged and this decision silently dropped.

## Rationale

Both decisions follow the same logic this codebase has already applied once, successfully, to
the recruiter side: ship the real feature the milestone is actually about, and make the
resulting gap a tracked, inspectable fact (risk-register entry, ADR) rather than either (a)
silently ignoring it or (b) inflating the milestone's scope to include a second, unrelated
project (real auth, or encryption-at-rest) that has no natural stopping point and would delay
the thing M4 exists to teach — the voice cascade itself.

Option 2 for auth (signed invite tokens) is the more defensible long-term answer, but it's
premature here: there is currently no invite-sending flow at all (PRD §7 step 3's "recruiter
sends interview link" is itself unbuilt — `ShareInterviewModal.tsx`'s link went nowhere until
this same session's fix), so a token system would have nothing real to attach to yet. Building
it now would be solving a problem one layer removed from where the actual gap is.

Option 3 for audio (transcript-only) was seriously considered — it's the cheapest way to make
R-006 genuinely not apply to this milestone rather than widening it. Rejected because the AI's
own synthesized responses are already being persisted as audio paths in the `interview_turns`
schema design (so the candidate can replay what they heard), and dropping *candidate* audio
specifically while keeping *AI* audio would be an inconsistent, half-measure that still leaves a
real design question (what about the AI's audio?) unresolved rather than actually simplifying
anything.

## Consequences

### Positive
- Zero new infrastructure, zero new dependencies — ships on the current stack, consistent with
  PD-002.
- `interview_sessions.id`'s dual purpose (idempotency key *and* credential) means no new
  identifier needed anywhere in the schema.
- The gap is now explicit and inspectable (this ADR, plus the risk-register update below) —
  discoverable by the next person or review, not silently reintroduced.

### Negative
- A leaked `interview_sessions.id` (e.g. via a referrer header, browser history sync, or a
  shared screen) grants full access to that one interview session — no revocation mechanism
  exists beyond the session naturally reaching `complete`/`abandoned`.
- Interview audio — now a second category alongside résumés — sits as plaintext on local disk
  with no encryption, no retention policy, no deletion path.

### Risks
- If real (non-synthetic) candidate data is ever used against this endpoint before Phase 3
  (real tenant-user SSO) or a dedicated PII-hardening pass lands, both gaps above become live
  legal/security exposure, not theoretical ones — same trigger condition R-006 already uses.

## Validation plan

None required to ship this decision — it is explicitly a scope/risk-acceptance choice, not a
technical claim needing measurement (unlike ADR-007's latency question, which had a real
threshold to validate against).

## Migration and rollout

No schema change from this ADR beyond what ADR-007 already specified (`interview_sessions.id`,
`interview_turns.candidate_audio_path`/`ai_audio_path`) — this ADR is a decision record for
choices already reflected in that schema, not a new migration.

## Rollback or exit strategy

Both are additive, low-blast-radius choices with clear future upgrade paths that don't require
touching the schema: candidate auth can be strengthened later (Option 2, once an invite flow
exists) by adding a token check *in front of* the existing session-id check, without changing
`interview_sessions`/`interview_turns` at all; audio storage can be encrypted later (Option 3)
by changing only what `save_interview_audio` writes, not the path-based column design.

## Revisit triggers
- Real candidate data used against this endpoint (see Risks above).
- PRD §7 step 3's invite-sending flow actually gets built — the natural point to revisit Option
  2 for candidate auth, since a token would finally have something real to attach to.
- A broader PII/encryption pass gets scheduled (R-006, IA-008) — should cover résumés and
  interview audio together, not interview audio alone, to avoid the inconsistency Option 3 for
  audio storage would have introduced now.

## Unresolved questions
- Whether a `interview_sessions` row should ever be revocable/expirable independent of reaching
  `complete`/`abandoned` (e.g. a time-based expiry) — not required by anything in scope today,
  worth a look once real usage patterns exist.
