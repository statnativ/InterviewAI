# ADR-004: Build a cascaded, turn-based STT→LLM→TTS pipeline before live/real-time WebRTC

- Status: Accepted
- Date: 2026-08-05
- Owners: Amit Tiwari
- Related product decision: PD-001 (async audio interview before live/video)
- Supersedes: none
- Superseded by: none

## Context
The PRD's interview experience (§5.3) describes two modes: asynchronous (candidate records
answers one at a time) and live AI-moderated (real-time conversation), the latter explicitly
marked stretch-scope for MVP. The original milestone roadmap deferred any voice capability to
M4 (async) and M7 (live, stretch). Amit asked to pull voice work forward, specifically as a
cascaded pipeline (separate STT, LLM, and TTS steps) rather than jumping straight to a
real-time/live implementation.

## Decision drivers
- The PRD itself treats live/real-time as the hard, expensive, stretch part — not something to
  build first.
- A cascaded, turn-based design (record → transcribe → respond → synthesize, one turn at a
  time) is testable without any WebRTC/media-server infrastructure, using ordinary HTTP calls
  and file I/O.
- Needed to validate whether the three chosen models (Nemotron 3 Ultra, Qwen3 ASR Flash,
  Kokoro 82M) actually work together and hold conversational context before investing in
  real-time infrastructure.

## Considered options

### Option 1: Cascaded, turn-based pipeline (STT → LLM → TTS), no live audio streaming
Candidate's answer arrives as a complete audio file per turn; each stage runs sequentially;
conversation history is a plain list of chat messages passed to the LLM each turn.

### Option 2: Jump straight to live, real-time WebRTC with streaming STT/TTS
Matches the PRD's "live AI-moderated" stretch goal directly, but requires a media server
(LiveKit/Agora/self-hosted), streaming-capable STT/TTS, and latency-budget engineering before
any of it could be tested at all.

### Option 3: Skip voice entirely until M4/M7 as originally sequenced
Lowest risk, but the PRD's core interview experience is voice-based — deferring all voice
validation risked discovering integration problems (model behavior, request formats, reasoning
leakage) much later, with more already built on top.

## Decision
Option 1 — cascaded, turn-based pipeline, built as a standalone script before any app/DB
integration.

## Rationale
This validates the riskiest, least-known part of the system (do these three specific models
actually work together, hold context, and avoid failure modes like reasoning leakage) at the
lowest possible infrastructure cost — no WebRTC, no media server, no DB writes, just three HTTP
calls per turn. It directly informs whether Option 2 (live) is even worth attempting later, and
with which models.

## Consequences

### Positive
- Confirmed empirically, same session: STT transcription accuracy was close to ground truth,
  multi-turn conversation memory worked (the LLM referenced information from turn 1 while
  responding in turn 2), and TTS output was audible/usable — validated by generating and
  listening to real audio files, not just inspecting text output.
- Found and fixed a real integration bug (reasoning leaking into spoken text) *before* any
  candidate-facing code existed, at near-zero cost to fix.
- No infrastructure investment (media server, streaming protocols) made before knowing the
  models were viable.

### Negative
- Does not currently exercise anything resembling real-time latency — each turn is a full
  request/response round trip with no streaming, so total interview latency at conversational
  pace is unmeasured and likely far too slow for a live experience.
- Standalone script only (`scripts/test_interview_pipeline.py`) — no persistence, no HTTP
  endpoint, no candidate-facing UI. Not usable by an actual candidate yet; that's M4.

### Risks
- Turn-based cascade latency (STT + LLM + TTS, sequentially, per turn) has not been measured
  end-to-end. If it's too slow even for *asynchronous* use (PRD requires question generation
  latency < 10s), that's a problem before M4 is even reached.
- Conversation history is currently an in-memory Python list with no size/cost bound — a long
  interview would grow the LLM context (and therefore cost/latency) unboundedly. No truncation
  or summarization strategy exists yet.

## Validation plan
Manual: ran the two-turn scripted demo, read the transcripts and LLM responses for coherence,
and listened to the generated audio. No automated test, no latency measurement, no evaluation
against the PRD's quantitative targets (§3, §6) yet.

## Migration and rollout
N/A yet — nothing is wired into the running app. Rollout happens at M4 (DB persistence + a real
endpoint) and M4b (video).

## Rollback or exit strategy
The three service clients (`stt_client.py`, `llm_client.py`, `tts_client.py`) and the
orchestrator (`interview_pipeline.py`) are isolated from the rest of the app — deleting or
replacing the cascade approach entirely would not affect `jobs`/`candidates`/`resumes`
functionality.

## Revisit triggers
- Before M4 (wiring into the app): measure actual per-turn latency end-to-end against the
  PRD's targets.
- Before attempting M7 (live/real-time): this cascade's measured latency is the baseline that
  determines whether streaming STT/TTS is actually required, or whether a "fast enough"
  cascade could serve as a cheaper live-ish experience.

## Unresolved questions
- What is the actual end-to-end latency per turn? Not measured yet.
- At what conversation length does unbounded history become a real cost/latency problem, and
  what's the mitigation (truncation, summarization, sliding window)? Undecided.
- No PD exists yet formally justifying "async audio first" as a product sequencing choice
  (referenced above as PD-001 but not yet written) — should be logged.
