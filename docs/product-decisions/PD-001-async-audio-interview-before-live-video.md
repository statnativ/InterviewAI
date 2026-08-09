# PD-001: Ship async audio interviews before live or video interviews

- Status: Accepted
- Date: 2026-08-05
- Owner: Amit Tiwari
- Related ADRs: ADR-004 (cascaded voice pipeline before live WebRTC)

## Customer problem
The PRD (§5.3) requires an interview experience delivered via video or audio, either
asynchronous (candidate records answers one at a time) or live/AI-moderated (real-time
conversation). Building both simultaneously, or starting with the harder live/video mode,
delays having *any* working interview experience to validate.

## Evidence
The PRD itself marks live AI-moderated interviews as "stretch for MVP" (§5.3) and lists
"Advanced proctoring," "Real-time adaptive questioning," and video-specific concerns as
post-MVP (§8, §10). No user research or usage data exists yet — this is a pre-launch POC with
one user (Amit, both as builder and as the only "candidate" tested so far).

## Decision
Build async **audio** interviews first (candidate answers recorded/uploaded one question at a
time, transcribed, evaluated), with the schema and pipeline designed so migrating to async
**video** shortly after is a small delta (swap the browser capture type, not the architecture).
Live, real-time interviewing (video or audio) stays deferred to M7, explicitly stretch-scope.

## Alternatives considered
- **Video first**: matches the PRD's likely preferred end-state more closely, but adds media
  storage/bandwidth/encoding concerns before the core Q&A/scoring loop is even proven to work.
- **Live/real-time first**: directly builds the highest-value experience per the PRD's own
  framing of live interviews reducing scheduling friction, but requires WebRTC/media-server
  infrastructure and streaming STT/TTS before anything is testable — highest risk, slowest to
  a working demo.
- **Text-only interview (no audio/video at all)**: fastest to build, but doesn't validate any
  of the PRD's actual interview-delivery requirements or the voice model integrations that are
  central to the product's value proposition.

## Scope
- In scope now: audio recording/upload per question, transcription (STT), AI-generated
  follow-up questions with conversation memory, synthesized spoken responses (TTS).
- In scope soon (M4b): swapping audio capture for video capture, same pipeline underneath.
- Deferred (M7, stretch): live/real-time conversational interviewing, low-latency streaming.

## Explicit non-goals
- Not attempting real-time/streaming latency characteristics right now — the cascaded pipeline
  (ADR-004) is intentionally turn-based, not live.
- Not building video capture, storage, or playback in this phase.
- Not attempting emotion/body-language analysis (explicitly out of scope per PRD §8 regardless
  of phase).

## Success metrics
No formal metrics defined yet for this specific decision. The PRD's platform-wide targets
(§3) apply once this is live-tested with real candidates: interview completion rate ≥ 80%,
candidate satisfaction ≥ 4.0/5. Neither has been measured — current validation is a single
scripted two-turn smoke test (see ADR-004), not real usage.

## Risks
- Building audio-first, video-second assumes the "small delta" claim in ADR-004/M4b holds in
  practice — unverified until M4b is actually attempted.
- No evidence yet that async audio (vs. live) meets the PRD's "reduce scheduling friction" goal
  as well as live interviewing would — async still requires the candidate to complete the
  flow unattended, which live moderation might handle better for engagement/completion rate.

## Validation plan
None formal. Will be validated once M4 wires the cascade into the real app with DB persistence
and it's tried against the PRD's completion-rate and satisfaction targets — currently unmeasured.

## Revisit triggers
- If M4b's "small delta" assumption turns out false (video capture requires substantial
  rework), reconsider whether audio-first was the right sequencing.
- If interview completion rate or satisfaction (once measurable) comes in low for async
  specifically, live moderation may need to be pulled forward ahead of M7's current position.

## Open questions
- Is there any actual evidence (beyond the PRD's own framing) that async audio, specifically,
  is an acceptable candidate experience for this target market? Unknown — no user research has
  been done.
