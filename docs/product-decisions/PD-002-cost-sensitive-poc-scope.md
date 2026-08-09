# PD-002: Treat this as an explicit cost-sensitive proof of concept

- Status: Accepted
- Date: 2026-08-05
- Owner: Amit Tiwari
- Related ADRs: ADR-001 (local Postgres via Docker), ADR-002 (OpenRouter as unified AI gateway)

## Customer problem
There is no paying customer or enterprise deployment yet — the "customer" at this stage is
Amit himself, learning system design by building a real, working system without incurring
meaningful cloud spend before the product is validated.

## Evidence
Stated directly and repeatedly by Amit: this is a learning project, self-funded, with explicit
instructions to prefer free/cheap infrastructure (OpenRouter free-tier LLM, local Docker
Postgres instead of a managed cloud DB, deferred cloud deployment) and to flag anything that
would introduce a real recurring bill before adopting it.

## Decision
Prioritize $0-or-near-$0 infrastructure choices at every layer while still building toward the
PRD's real enterprise requirements (multi-tenancy, compliance, scale) as later, sequenced
milestones rather than immediate requirements:
- Local Docker Postgres, not a managed cloud database, during active development.
- OpenRouter's free-tier LLM (Nemotron 3 Ultra) as the default interview brain, paid models
  (DeepSeek V4 Pro, GLM-5.2) identified but held as fallback only.
- Cloud deployment (Cloud Run + Neon + GCS — both with generous free tiers and scale-to-zero
  pricing) deferred to milestone M6b, only once there's something worth demoing.

## Alternatives considered
- **Provision production-grade infrastructure now** (managed Postgres, paid LLM tier, deployed
  environment from day one): would de-risk the eventual production transition earlier, but
  contradicts the explicit cost constraint and isn't justified without a customer yet.
- **Self-host all AI models** (local Whisper, local LLM, local TTS) to avoid API costs
  entirely: rejected for STT specifically — OpenRouter's Qwen3 ASR Flash pricing (~$0.13/hour
  of audio) is cheaper in practice than the engineering cost of running/maintaining a local
  inference stack for a solo POC.

## Scope
- In scope: every infrastructure decision made so far has an explicit cost rationale (see the
  related ADRs).
- In scope: flagging real dollar costs before any paid tier or deployment step is taken.
- Out of scope for now: cost optimization beyond "use the free/cheap tier" — no rigorous cost
  modeling, load testing, or capacity planning has been done.

## Explicit non-goals
- Not optimizing for production scale (PRD §6 requires 500 concurrent interviews, 99.5%
  uptime) at this stage — those are real eventual requirements, not current ones.
- Not building enterprise features (SSO, multi-tenancy, compliance tooling — PRD §5.5, §6)
  until M6, since they have no cost-sensitivity implication one way or the other but are
  sequenced later regardless.

## Success metrics
No formal budget or cost ceiling has been set. "Success" so far has been informal: every
capability built has run within OpenRouter's free tier or single-digit-cents-per-call pricing,
and no cloud hosting cost has been incurred at all (everything is local).

## Risks
- No cost tracking is actually wired up (`ai_processing_logs` table exists but nothing writes
  to it yet — see ADR-002's unresolved questions) — "cost-sensitive" is currently a stated
  intent, not a measured/enforced constraint.
- Free-tier LLM reliability at scale is unknown and could force an earlier-than-planned move to
  a paid model, with unclear cost impact since no per-interview cost has been measured.

## Validation plan
None formal. Will need actual cost tracking (via `ai_processing_logs`) before this can be
validated against real numbers rather than published per-unit pricing estimates.

## Revisit triggers
- Any point where a paid tier or cloud service becomes necessary — must be flagged explicitly
  per the standing instruction, not adopted silently.
- If free-tier LLM rate limits force reliance on paid fallback models at meaningful volume.

## Open questions
- What is the actual dollar cost per interview once M4 wires the full cascade into real usage?
  Unknown — no instrumentation exists yet.
