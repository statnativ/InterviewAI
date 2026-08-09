---
tags: [product, research, market, enterprise, compliance]
status: current — initial research pass, web-sourced
last-updated: 2026-08-09
---

# Enterprise Buyer Research — AI Interview / ATS Platforms

Companion to [[Cost Savings & ROI Model]] and [[Competitive Landscape]]. This note answers:
who buys these platforms, what they actually evaluate on, and what's non-negotiable —
grounded in web research (Aug 2026), read against our own [[Project Overview]] and
`docs/product/prd.md`. Source credibility varies (see note at the end); treat vendor-blog
statistics as directional, not verified.

## Who's buying

Matches the PRD's persona table almost exactly, which is a useful sanity check — the market
research doesn't contradict the assumed buyer:

| Persona | What they're actually optimizing for | Where they show up in the sales cycle |
|---|---|---|
| Recruiter / TA Lead | Throughput without burning out; wants screening off their plate | Day-to-day user, first demo attendee |
| Hiring Manager | Trusts the score enough to skip a redundant human screen | Objection-raiser: "will this actually find good people?" |
| HR Ops / Admin (compliance, security) | Doesn't want the company sued or breached | Late-stage gatekeeper — can kill a deal procurement already liked |
| Candidate | Not a buyer, but their backlash *becomes* the buyer's problem | Referenced constantly in vendor pitches ("candidate experience") |

## Top buying criteria (what actually gets evaluated)

1. **Compliance posture, not features, is the first gate for enterprise deals.** SOC 2 Type
   II, GDPR readiness, configurable data retention, and (per one Q1 2026 DLA Piper benchmark
   cited in vendor content) EU AI Act conformity statements are treated as table stakes by a
   reported 71% of buyers — even for companies that don't hire in the EU, apparently used as a
   proxy for "this vendor takes AI governance seriously" rather than strict jurisdictional need.
2. **Scoring explainability.** Buyers want to see *why* a candidate got a score, not just the
   number — this maps directly to our rubric/scorecard/strengths-gaps model
   (`app/services/screening.py`), which is already evidence-based rather than a black-box
   number. That's a real point in our favor once compliance basics exist alongside it.
3. **ATS integration depth**, specifically Greenhouse (Harvest API, RecOps favorite), Lever
   (GraphQL, developer-friendly), and Workday (the default when recruiting must sync into a
   broader HCM). This is explicitly **out of scope for our MVP** per `prd.md` §8 — worth
   flagging as a real gap the moment we target actual enterprise pilots, not just a "later"
   line item.
4. **Whether the tool assists interviewers or replaces the interview.** The market has split
   into two camps — BrightHire/Metaview record and coach human interviewers; HireVue/Sapia/our
   product actually run the candidate-facing interaction. Buyers seem to be evaluating these as
   different categories, not head-to-head — worth being explicit in our own positioning about
   which camp we're in (see [[Competitive Landscape]]).
5. **Whether the AI summary/score is good enough to trust without heavy editing.** Repeated
   theme: recruiter-tuned models reportedly outperform general-purpose ones on this. We already
   use a JD-specific deterministic rubric rather than a generic prompt, which is directionally
   right — but see the resume-personalization gap below.

## Compliance: the part that can kill a deal, not just annoy legal

- **NYC Local Law 144** (in force since 2023): any "Automated Employment Decision Tool" used
  to substantially assist or replace a hiring decision needs (a) an independent bias audit
  within the past year, (b) a public summary of that audit, (c) ≥10 business days' candidate
  notice before use. Penalties are $500–$1,500 *per violation, per day, per un-notified
  candidate* — this compounds fast at any real hiring volume. Our resume-scoring and
  AI-interview-scoring paths both clearly qualify as AEDTs under this definition.
- **EU AI Act** classifies HR/hiring AI as "high-risk," with post-market monitoring
  obligations that an annual audit cycle (LL 144's model) doesn't actually satisfy on its own.
- **Candidates are asking for exactly this**, not just regulators: in one cited survey, 38%
  of candidates want confirmation a human reviews the AI's evaluation before a decision, and
  29% want proof the tool was bias-audited. 70% said they were never told upfront AI would
  evaluate them — a disclosure failure mode we should design against from day one rather than
  bolt on later.
- **Direct implication for our roadmap**: the PRD already lists "human oversight remains
  available on all AI scores" as an assumption (§9) — good. What's missing is anything
  resembling audit logging of *who reviewed/overrode what, when* (flagged generally as
  compliance debt in [[Project Overview]] → architecture review), and there's no
  candidate-facing disclosure/consent screen yet. M6 (auth/tenancy) is the natural place this
  compliance work should land, not an afterthought bolted on right before a real enterprise
  pilot.

## Pain points the market keeps citing (validates our core wedge)

- Recruiters reportedly spend ~23 hours screening resumes per hire (mix of vendor-blog
  benchmarks — treat as directional); at real applicant volumes this is the single biggest
  lever, and it's exactly the ATS-scoring flow we've already built end-to-end.
  See [[Cost Savings & ROI Model]] for the numbers.
- **Tool fragmentation** — enterprise teams reportedly stitch together separate tools for
  outreach, video collection, assessment, and compliance instead of one flow. Our product's
  actual advantage, if it holds up past MVP, is that resume scoring → AI interview → structured
  report → pipeline board is *one* vertical slice already, not five vendors glued together.
  Worth stating explicitly in future positioning rather than assuming it's obvious.
- **Alignment, not volume, is often the real problem** — hiring managers and recruiters
  frequently disagree on what "qualified" means. Our rubric editor (recruiter-adjustable
  scoring criteria per job) is a direct answer to this, *if* hiring managers can also see and
  weigh in on the rubric — currently the rubric flow is recruiter-only per the frontend
  (`JobDetail`/rubric editor); whether hiring managers get visibility is worth a product
  decision, not an assumption.

## A gap this research surfaces in our own PRD promise

The PRD's stated differentiator is AI questions "tailored to the role **and candidate**"
(§5.2). Market research shows this is a real, actively marketed differentiator among
resume-personalization tools — but [[Project Overview]] already documents (architecture
review finding #3) that our interview prompt currently only injects the JD, not resume data.
This isn't a new problem this research found — it's the same D4 decision already logged as
open — but the market confirms it's not a nice-to-have: it's the exact category buyers use to
distinguish "real personalization" from "keyword matching," and myInterview is explicitly
called out in research as suffering from the keyword-matching-only reputation. Worth weighting
D4 accordingly.

## Source credibility note

Search-engine results for 2026 "recruiting statistics" are dominated by vendor content
marketing (Pin, TuraHire, OphyAI, TheHireHub, Zivaro, and similar) — numbers like "340% ROI"
or "23 hours per hire" come from these and should be treated as directional/marketing framing,
not verified research, unless corroborated by a primary source (SHRM, DOL, Gallup, an
identified named study). Where a claim below rests only on vendor-blog aggregation, it's
flagged inline. See [[Cost Savings & ROI Model]] for the same discipline applied to dollar
figures.

## Sources

- [Top 12 Interview Intelligence Platforms for 2026](https://www.socialtalent.com/blog/recruiting/top-12-interview-intelligence-platforms)
- [Best Interview Intelligence Platforms for Enterprise 2026](https://bestrecruitingtools.com/blog/best-interview-intelligence-software-enterprise-2026)
- [NYC Local Law 144 Compliance Guide 2026 — Warden AI](https://www.warden-ai.com/resources/hr-tech-compliance-nyc-local-law-144)
- [Automated Employment Decision Tools (AEDT) Under NYC LL 144 — Warden AI](https://www.warden-ai.com/resources/automated-employment-decision-tools)
- [AI Hiring Compliance 2026: NYC Law 144 + EU AI Act — TheHireHub](https://www.thehirehub.ai/blog/ai-hiring-compliance-in-2026-the-recruiter-s-guide-to-nyc-local-law-144-and-the-eu-ai-act)
- [How AI Regulations Are Transforming Hiring Practices](https://talentcollective.substack.com/p/how-emerging-ai-regulations-are-transforming)
- [Recruiting complaints 2026: what 20,973 r/recruitinghell posts reveal — Truffle](https://www.hiretruffle.com/reports/recruiting-complaints-2026)
- [Enterprise Recruiting Software Trends in 2026](https://blog.hiringthing.com/enterprise-recruiting-software-trends-in-2026)
- [63% of Job Seekers Have Faced an AI Interview — PR Newswire](https://www.prnewswire.com/news-releases/63-of-job-seekers-have-faced-an-ai-interview-most-havent-had-a-good-one-yet-302760120.html)
- [Skin-Deep Bias: How Avatar Appearances Shape Perceptions of AI Hiring (arXiv)](https://arxiv.org/pdf/2604.06187)
- [Eliminating Biases in Hiring: Structured Interviewing and AI Solutions — SHRM](https://www.shrm.org/labs/resources/eliminating-biases-in-hiring--structured-interviewing-and-ai-solutions)
- [Greenhouse vs Workday — 2026 ATS Comparison](https://www.mokahr.io/articles/en/compare/greenhouse-vs-workday)
- [15 ATS APIs to Integrate With in 2026](https://unified.to/blog/15_ats_apis_to_integrate_with_in_2026_greenhouse_lever_workable)
