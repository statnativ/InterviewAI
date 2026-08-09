---
tags: [product, research, competitive, market]
status: current — initial research pass, web-sourced
last-updated: 2026-08-09
---

# Competitive Landscape — AI Interview / ATS Platforms

Companion to [[Enterprise Buyer Research]] and [[Cost Savings & ROI Model]]. Web research
(Aug 2026) mapped against our own scope in `docs/product/prd.md`. Pricing figures come from
vendor-alternative/comparison content (not vendor-published price sheets — most of these
vendors are custom-quote-only), so treat as **directional bands**, not quotes.

## The market has three real categories — know which one we're in

1. **Interviewer-assist / interview intelligence** — records and coaches *human* interviewers;
   does not run the candidate interaction itself. *BrightHire, Metaview.*
2. **AI-led candidate-facing screening/interview** — the AI directly interviews the candidate
   (text, voice, or video), no human interviewer present for round 1. *HireVue, Sapia.ai,
   Ribbon AI, Humanly, myInterview, Willo, Spark Hire, VidCruiter.*
3. **Avatar-led interviewing** — category 2, specifically with a human-like animated/video
   avatar conducting the conversation rather than a chat/voice-only bot. *CodeSignal (avatar
   add-on), Interviewer.AI, JobTwine, NTRVSTA.*

**Our product spans categories 2 and 3** — AI-led interview (voice + chat) plus an Avatar
Interviewer surface (per [[Frontend Overview]]'s "Avatar Interviewer screens") — combined with
a full ATS scoring/rubric front end. Very few competitors combine an ATS-grade resume-scoring
rubric editor *and* an avatar-led interview *and* a comparative report *and* a pipeline board
in one product; most are point solutions that expect to sit next to (or be acquired into) a
real ATS. That combination is a real differentiation angle, if it survives contact with actual
enterprise integration requirements (see [[Enterprise Buyer Research]] on ATS-integration
being explicitly out of MVP scope right now).

## Vendor matrix

| Vendor               | Category                                                                       | Positioning                                                                                                                   | Pricing band (directional)                                                 | Relative to us                                                                                                                                                                                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HireVue**          | AI-led interview + ATS-adjacent                                                | Established enterprise incumbent; video interviewing, science-backed assessments, adverse-impact testing, 40-language support | Enterprise ~$75K–$150K+/yr; per-interview $5–$30; $15K–$40K implementation | Far ahead on compliance tooling (adverse-impact testing baked in) and enterprise sales motion; we have no equivalent yet. G2 rating cited as lowest of the group (4.1) — incumbent fatigue may be a real opening.                                                                                  |
| **BrightHire**       | Interviewer-assist                                                             | Records/scores human interviewers against structured scorecards; doesn't replace the interviewer                              | ~$15K/yr (small team) to $100K+/yr (enterprise)                            | Different category — not a direct substitute for our AI-led interview, but a common bake-off comparison since buyers often shop "interview intelligence" broadly. G2 4.8.                                                                                                                          |
| **Metaview**         | Interviewer-assist, expanding to full-funnel AI agents                         | Strong on technical/engineering interviews; expanding into sourcing, application review, job posts                            | ~$20–$100/user/month                                                       | Same category note as BrightHire; expanding scope looks similar in spirit to our "one vertical slice" bet, worth watching. G2 4.8.                                                                                                                                                                 |
| **Modern Hire**      | AI-led interview + assessment                                                  | Legacy player, limited fresh 2026 coverage found in this research pass                                                        | Unknown — not found                                                        | Flag as **unverified/needs a dedicated look**, not confirmed inactive.                                                                                                                                                                                                                             |
| **Sapia.ai**         | AI-led interview (text-only, no video/audio)                                   | Deliberately removes visual/vocal signal from early screening to reduce bias                                                  | ~$15K–$60K/yr                                                              | Bias-mitigation-as-a-feature is a strong, specific claim — worth understanding their audit methodology given our own compliance gap (see [[Enterprise Buyer Research]]).                                                                                                                           |
| **Paradox (Olivia)** | Conversational AI recruiting assistant (chat/SMS-first, high-volume/frontline) | Custom-quote enterprise                                                                                                       | Unknown (custom)                                                           | Different wedge — high-volume frontline hiring, chat-first. Less direct overlap with our ATS+interview flow.                                                                                                                                                                                       |
| **myInterview**      | AI-led interview (video)                                                       | Ranks candidates via transcript keyword-matching                                                                              | $149–$299/mo                                                               | Explicitly critiqued in market content as "keyword-matching, not genuine conversational evaluation" — the exact trap our JD-tailored (but not yet candidate-tailored) rubric scoring risks being lumped into if we don't close the resume-personalization gap (see [[Enterprise Buyer Research]]). |
| **Willo**            | Async video screening                                                          | Lightweight, SMB/mid-market                                                                                                   | $49–$199/mo                                                                | Not really enterprise-tier; low overlap.                                                                                                                                                                                                                                                           |
| **Spark Hire**       | Async/live video interviewing                                                  | SMB/mid-market video interview tool                                                                                           | $119–$449/mo                                                               | Same tier as Willo; not a real enterprise competitor.                                                                                                                                                                                                                                              |
| **VidCruiter**       | Full-funnel screening (scheduling, live interviews, reference checks)          | Heavy process automation for large HR teams                                                                                   | ~$15K–$40K/yr                                                              | Broader ops-automation footprint than us; reference-check automation is something we don't have.                                                                                                                                                                                                   |
| **Humanly**          | AI-led screening + CRM/ATS-lite                                                | Chat/SMS/voice/video engagement, structured AI screens, built-in Talent CRM                                                   | Unknown                                                                    | Closest philosophically to "one integrated flow" positioning — worth a deeper look as the nearest full-stack comparable.                                                                                                                                                                           |
| **Screenloop**       | ATS + interview intelligence                                                   | UK-focused mid-market, unified ATS + interview tooling                                                                        | Unknown                                                                    | Same "ATS + intelligence in one" bet as us, different market (UK mid-market vs. our unspecified target).                                                                                                                                                                                           |
| **Ribbon AI**        | AI-led voice interview                                                         | Voice-first, 10+ languages, Fast Company "Most Innovative 2026"                                                               | Unknown                                                                    | Direct category overlap on the interview leg; no visible ATS/rubric layer to compete with our resume-scoring side.                                                                                                                                                                                 |
| **CodeSignal**       | Avatar-led interview (technical)                                               | AI video avatars for early technical screens                                                                                  | Unknown                                                                    | Direct avatar-category overlap; technical-hiring-specific, which narrows their lane relative to our general rubric-driven approach.                                                                                                                                                                |
| **Interviewer.AI**   | Avatar/AI-led interview, cross-vertical (hiring + admissions)                  | Unified platform positioning                                                                                                  | Unknown                                                                    | Direct avatar-category overlap; broader vertical spread (admissions too) than us.                                                                                                                                                                                                                  |
| **JobTwine**         | Avatar-led interview ("JayT")                                                  | Claims ~20 hours saved per hire                                                                                               | Unknown                                                                    | Direct avatar-category overlap; smaller/newer, useful as a feature-parity reference for our own Avatar Interviewer screens.                                                                                                                                                                        |

## What's genuinely unresolved from this research pass (flag, don't guess)

- **Modern Hire's current market position is Unknown** — 2026 comparison content barely
  mentions them; could mean consolidation/acquisition or just poor SEO. Needs a dedicated
  search pass before citing them confidently in any deck.
- **No pricing was found (not just "custom quote," genuinely absent from search results)** for
  Paradox, Humanly, Screenloop, Ribbon AI, CodeSignal's avatar tier, Interviewer.AI, and
  JobTwine — don't backfill these with guesses.
- G2/Gartner ratings cited here (HireVue 4.1, BrightHire/Metaview 4.8) came from secondary
  aggregator summaries, not a direct G2 pull — worth verifying directly on g2.com before
  reusing in an external-facing document.

## Where we're behind vs. table stakes (not just "different")

Cross-referencing [[Enterprise Buyer Research]]'s buying-criteria list against what we've
actually built (per [[Backend Overview]] / [[Frontend Overview]]):

| Table-stakes item competitors already have | Our current state |
|---|---|
| Bias audit / adverse-impact testing (HireVue has this built in) | None — not started |
| SOC 2 Type II, documented data retention | None — no auth/tenancy layer yet (M6) |
| ATS integration (Greenhouse/Lever/Workday) | Explicitly out of MVP scope (`prd.md` §8) |
| Candidate-tailored interview questions (myInterview's weakness is *not* having this) | JD-tailored only — resume not in the interview prompt yet (open decision D4, [[Project Overview]]) |
| Multi-tenant isolation | Single-tenant; no `tenant_id` on any table yet (open decision D3) |

None of this is a surprise relative to what [[Project Overview]]'s architecture review already
found — this research just confirms those aren't just internal code-quality nits, they're
things real enterprise buyers will ask about in the first serious evaluation call.

## Sources

- [Top 12 Interview Intelligence Platforms for 2026 — SocialTalent](https://www.socialtalent.com/blog/recruiting/top-12-interview-intelligence-platforms)
- [Best Interview Intelligence Platforms for AI-Assisted and AI-Led Hiring — SelectSoftwareReviews](https://www.selectsoftwarereviews.com/buyer-guide/interview-intelligence-platforms)
- [BrightHire Alternative — Metaview](https://www.metaview.ai/home/ads/metaview-vs-brighthire)
- [Best BrightHire Alternatives 2026 — SourcrLab](https://sourcrlab.com/alternatives/brighthire)
- [AI Interviewer Platforms 2026: 10-Vendor Matrix, Real Pricing](https://agenticinterviewer.com/)
- [AI Interviewer ATS Integration Matrix 2026](https://agenticinterviewer.com/ats-integrations/)
- [Willo Alternatives: Pricing, Pros & Cons — InterviewFlowAI](https://interviewflowai.com/alternatives/15-best-willo-alternatives-2026)
- [Spark Hire Alternatives — InterviewFlowAI](https://interviewflowai.com/alternatives/15-best-sparkhire-alternatives-2026)
- [Paradox (Olivia) Alternatives — InterviewFlowAI](https://interviewflowai.com/alternatives/15-best-paradox-alternatives-2026)
- [Sapia Alternatives — InterviewFlowAI](https://interviewflowai.com/alternatives/15-best-sapia-alternatives-2026)
- [HireVue Alternative: 10 Best Options Compared & Priced — Mokka](https://www.gomokka.com/resources/10-best-hirevue-alternatives-for-2026-features-pricing-pros-cons.html)
- [HireVue Pricing 2026: Starts at $35,000/Year — Leon Consulting](https://leonstaff.com/blogs/hirevue-pricing-cost/)
- [HireVue Pricing 2026 — InterviewFlowAI](https://interviewflowai.com/blog/hirevue-pricing)
- [Gartner Peer Insights — AI-Enabled Interview Intelligence](https://www.gartner.com/reviews/market/ai-enabled-interview-intelligence)
- [Ribbon AI Reviews — Slashdot](https://slashdot.org/software/p/Recruit-AI-by-Ribbon/)
- [AI Video Avatars — CodeSignal](https://codesignal.com/ai-video-avatars/)
- [What Is an AI Avatar Interview? — JobTwine](https://www.jobtwine.com/blog/what-is-an-ai-avatar-interview-a-practical-breakdown-for-recruiters)
- [Interviewer.AI](https://interviewer.ai/)
