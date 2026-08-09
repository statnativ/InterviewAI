---
tags: [product, research, finance, roi, enterprise]
status: current — initial research pass, web-sourced
last-updated: 2026-08-09
---

# Cost Savings & ROI Model — AI Interview / ATS Platform

Companion to [[Enterprise Buyer Research]] and [[Competitive Landscape]]. This note builds an
illustrative ROI model for the product using the success metrics already committed to in
`docs/product/vision.md` (≥60% reduction in time-to-first-interview, ≥50% reduction in
recruiter screening hours) against market cost benchmarks (Aug 2026 web research). **Treat the
dollar outputs as illustrative, not a sales claim** — see the source-credibility tiering below.

## Source credibility tiers (read this before the numbers)

| Tier | Sources | How to use them |
|---|---|---|
| A — primary/institutional | SHRM benchmarking reports, U.S. Dept. of Labor, Gallup, CareerBuilder surveys | Safe to cite directly, with the report named |
| B — aggregator/secondary | Sites summarizing "SHRM says X" without a linkable primary report | Use, but note it's secondhand |
| C — vendor content marketing | Pin, TuraHire, OphyAI, TheHireHub, Zivaro, Outhire, FormaCV, and similar SEO blogs | Directional only — these exist to sell a product and often round numbers to make a compelling pitch. Never state as fact without the "reportedly" framing. |

Most of the specific ROI/percentage claims below (340% ROI, $2,400–$3,000 savings/hire, etc.)
are **Tier C**. The cost-per-hire and bad-hire baselines are **Tier A/B**. This split matters
if any of this is reused externally — don't launder Tier C numbers as if they were SHRM data.

## Baseline cost benchmarks (Tier A/B — safe to build on)

| Metric | Figure | Source tier |
|---|---|---|
| Average U.S. cost-per-hire (non-executive) | $4,700–$5,475 (SHRM figures vary by report year cited) | A |
| Average cost-per-hire, executive roles | ~$35,879 | A (SHRM, as cited) |
| Enterprise (1,000+ employees) cost-per-hire | ~$5,500 avg; range $2.8K–$7.2K at 5,000+ employees | B |
| Cost-per-hire composition | ~57% recruiter time/internal labor/sourcing spend; ~30% tech stack/assessments/verification; ~13% candidate experience/onboarding | B |
| Minimum cost of a bad hire | 30% of first-year salary (U.S. DOL) | A |
| Bad hire cost by seniority | ~30% of salary (entry) scaling to 200%+ (executive) | A/B |
| Average cost to replace an employee (SHRM, 2026 cited) | ~$56,500 | B (secondhand SHRM citation) |
| Recruiter hours spent screening resumes, per hire | ~23 hours (mix of phone screens + resume review) | C |
| Manual screen time | 300 resumes @ 2–3 min each ≈ 10–15 hours resume review alone, plus phone screens | C |
| Industry avg time-to-fill | 36–44 days (tech roles 42–55, hourly 25–35, executive 80–120) | C |

## What our own PRD already commits to

From `docs/product/vision.md`:
- ≥60% reduction in time-to-first-interview
- ≥50% reduction in recruiter hours spent on screening/first-round interviews
- Resume-to-score turnaround < 2 minutes
- Recruiter time saved per candidate ≥ 30 minutes (from `prd.md` §3)

These are **our own targets**, not yet measured against real usage (the ATS vertical slice is
functionally complete per [[Project Overview]], but there's no production traffic to validate
against). The model below treats them as the input assumption, not a proven result.

## Illustrative ROI model (assumption-driven — not a claim)

Using the Tier A/B baseline of ~23 hours of recruiter time per hire on
screening/first-round-interview work, and our own committed ≥50% reduction target:

| Input | Value |
|---|---|
| Recruiter fully-loaded hourly cost (assumption, not sourced — plug in real number before using externally) | $50/hr |
| Baseline screening hours per hire | 23 hrs |
| Our target reduction | ≥50% |
| Hours saved per hire | ≥11.5 hrs |
| **Illustrative labor savings per hire** | **≥$575** |
| At 500 hires/year (mid-size enterprise TA team) | **≥$287,500/year** in recruiter time alone |
| At 5,000 hires/year (large enterprise) | **≥$2.875M/year** in recruiter time alone |

This is a **conservative, single-lever model** — it only counts recruiter screening time
saved, using our own stated target, against a real (if Tier B) baseline. It deliberately
excludes:
- Faster time-to-fill reducing vacancy cost (real, but harder to source cleanly)
- Reduced cost-per-hire from fewer/no staffing-agency fees on volume roles
- Bad-hire avoidance from more consistent scoring (the DOL's 30%+-of-salary figure is real
  and large, but attributing *how much* of a bad-hire reduction is attributable to better
  screening vs. other factors requires actual outcome data we don't have yet)
- Any second-order employer-brand effect from a better/worse candidate experience (cuts both
  ways — see [[Enterprise Buyer Research]] on the 34% who report a *more negative* view after
  a bad AI interview)

**Why keep it this narrow:** the vault's own discipline ([[Project Overview]] governance
section) is to cite the actual support for a claim and mark anything unverified — a bigger,
more impressive-looking ROI number built by stacking five Tier-C vendor stats on top of each
other would not survive a real due-diligence conversation with an enterprise buyer, and this
document exists to be argued with, not to look good in a deck.

## What vendors are claiming (context, not something to repeat as our own)

For calibration only — these are the numbers competitors and market-research content put in
front of buyers, cited here so we know what expectation an enterprise prospect may walk in
with:

- "340% ROI within 18 months" (PwC figure, as cited by a vendor blog — primary PwC report not
  independently located)
- "280% ROI in year one for mid-market" (vendor's own 3,000-project dataset — self-reported)
- "33% reduction in cost-per-hire," "60–80% reduction in time-to-shortlist" (vendor content,
  Tier C)
- Enterprise dollar-savings claims of "$500K–$1.5M annually" and "break-even in 12–18 months"
  (vendor content, Tier C, no methodology disclosed)

If we ever build a customer-facing ROI calculator, the honest move is to let the *buyer* plug
in their own hourly cost and hire volume against our measured (not assumed) time-savings —
not to publish a fixed multiplier borrowed from a competitor's marketing page.

## What would make this model real instead of illustrative

1. Actual usage telemetry once the ATS slice has real users: measured screening time before/
   after, not an assumed 50%.
2. A real fully-loaded recruiter cost from an actual pilot customer, not a $50/hr placeholder.
3. Time-to-fill data pre/post adoption from a pilot, to unlock the vacancy-cost lever honestly.
4. If pursuing the bad-hire-avoidance angle, a hiring-outcome tracking mechanism (which doesn't
   exist in the schema yet — `applications` has no "performance after hire" field) — this is a
   product gap, not just a data gap, if this angle matters for a future sales motion.

## Sources

- [Cost-Per-Hire: Complete Breakdown and Benchmarks 2026 — Pin](https://www.pin.com/blog/cost-per-hire-benchmarks/)
- [Cost per hire benchmarks 2026 — Raffi](https://getraffi.ai/research/cost-per-hire-benchmarks-2026)
- [Cost Per Hire Calculator: SHRM Formula & Benchmarks — teamed.](https://www.teamed.global/insights/cost-per-hire-calculator-shrm-formula-and-benchmarks)
- [Recruiter Productivity Benchmarks 2026 — Outhire](https://outhire.ai/blog/recruiter-productivity-benchmarks-2026)
- [You're Spending 23 Hours Per Hire on Screening — Zivaro](https://www.zivaro.ai/blog/recruiter-time-per-hire)
- [Time-to-Hire Metrics: How AI Cuts Hiring Timelines by 70% — Pin](https://www.pin.com/blog/time-to-hire-metrics-ai/)
- [What Is the ROI of AI Interviews for Enterprise Hiring? — Tech Magazine](https://www.techmagazines.net/what-is-the-roi-of-ai-interviews-for-enterprise-hiring/)
- [ROI of AI Recruitment: Calculator + Guide (2026) — TheHireHub](https://www.thehirehub.ai/blog/ai-recruitment-roi-calculator-guide)
- [AI Interview Assistant ROI for Enterprise Recruitment — OphyAI](https://ophyai.com/blog/industry-insights/ai-interview-assistant-roi-enterprise-recruitment)
- [How Much Does a Bad Hire Really Cost Your Company in 2026?](https://www.frontlinesourcegroup.com/blog-what-a-bad-hire-really-costs-your-company-in-2026.html)
- [Cost of a Bad Hire: 2026 Statistics with DOL and SHRM Source Citations](https://inop.ai/the-true-cost-of-a-bad-hire-in-2026/)
- [Cost of Hiring Statistics 2026: SHRM Data & Total Cost Analysis](https://vamasters.com/cost-of-hiring-statistics-2026/)
