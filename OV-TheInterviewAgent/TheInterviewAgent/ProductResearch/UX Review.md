---
tags: [product, ux, design, frontend, review]
status: current — P0 + safe P1 fixed and re-verified live (2026-08-09); #4 and P2/P3 still open
last-updated: 2026-08-09
---

# UX Review — Recruiter & Candidate Experience

Companion to [[Frontend Overview]] (what's built) and [[Enterprise Must-Haves Checklist]]
(what enterprise procurement will ask for). This note is a UX critique of the running app —
what's actually on screen, not what the code intends. Method: ran the real stack (Postgres +
FastAPI + Vite dev server), clicked through both the recruiter (`OrgAppShell`) and candidate
(`CandidateShell`) sides at 1440×900, and verified every "bug" claim below two ways — live
repro **and** the source line that causes it — so this reads as findings, not impressions. Follows
the vault discipline: cite the actual file/line, don't guess.

## Fix status (2026-08-09)

Findings **#1, #2, #3, #5, #6, #7** below were fixed in the same session this review was
written and re-verified live (fresh direct-navigation repros, `pytest`, `npm run build`, and a
clean-tab console check all pass) — and again with an automated **Playwright** re-run
(`frontend/e2e/ux-audit.mjs`, screenshots in `frontend/e2e/screenshots/`): 10 real DOM
assertions PASS (the fixed findings) and 5 correctly FAIL (the still-open findings #4, #8, #9,
#10, #11 — asserted as gaps on purpose, so a FAIL there confirms they're honestly still open,
not a regression), plus 6 supplementary tour screenshots. Root-cause note for #1: five of the ten pages
(`JobDetail`/`PipelineBoard`/`RankedShortlist`/`CandidateDetail`/`ComparativeReport`) were
subscribing to the store's `getJob`/`getCandidatesForJob` **functions** rather than the
reactive `jobs`/`candidates` state, so Zustand never re-rendered them once `init()` populated
the store — fixed by selecting the raw arrays directly (mirroring the correct pattern already
used in `InterviewEditor.tsx`). **Finding #4 (real rubric weight editing) was deliberately left
out of scope** — it's a genuine feature, not a bug fix, and needs its own product decision. P2
and P3 findings are all still open. Each fixed section below is marked inline; nothing was
deleted so the original findings remain readable.

**Read this as a punch list, ranked by how much damage it does to trust and enterprise
credibility — not a redesign.** The visual design system itself (`src/index.css` tokens,
`Button`/`Card`/`Badge`/`ScorePill`) is genuinely good and shouldn't be touched. What needs
work is mostly *robustness and honesty* — screens that lie about their own state, or go blank
instead of failing gracefully.

## P0 — Breaks trust or loses work outright

### 1. Any direct navigation to a job/candidate/interview-scoped page renders a fully blank screen — ✅ Fixed 2026-08-09
**The single most damaging finding in this review.** Reload the browser, open a bookmark, or
paste a shared link to any `:jobId` / `:candidateId` / `:interviewId` route, and you get a
white page — no sidebar, no error, no spinner, nothing. Verified live with fresh UUIDs pulled
straight from `/api/jobs` in the same session (so it's not a stale-ID issue), and confirmed
by source — the pattern is identical across **ten pages**:

```
PipelineBoard.tsx:37        if (!job) return null;
ComparativeReport.tsx:24    if (!job) return null;
RankedShortlist.tsx:33      if (!job) return null;
CandidateDetail.tsx:34      if (!job || !candidate) return null;
JobDetail.tsx:29            if (!job) return null;
AvatarVideoInterview.tsx:56 if (!interview) return null;
ShareInterviewModal.tsx:21  if (!interview) return null;
InterviewEditor.tsx:28      if (!interview) return null;
VoiceInterviewSession.tsx:47 if (!interview) return null;
ChatInterviewSession.tsx:62  if (!interview) return null;
```

**Why this matters more than a normal 404:** `CandidateDetail` ships a real, working "Copy
link" button (`navigator.clipboard.writeText`, per [[Frontend Overview]]) — a feature whose
entire purpose is to be pasted somewhere and opened fresh. Today, opening that link in a new
tab (or the same tab after a refresh) produces a blank page. Same for every interview link a
recruiter might paste into Slack. This isn't a rare edge case — refresh-while-on-a-detail-page
is one of the most common things a real user does.

**Fix shape, not a prescription:** these components need a three-state render (loading /
not-found / found) instead of a single `if (!x) return null`. The store already has `ready` on
`AppState` ([[Frontend Overview]]) — these pages just aren't reading it before bailing out.

**Fixed:** all ten pages now render a loading state (`ready` false) or a not-found state with a
back-link (`ready` true, record missing) via a shared `RecordState.tsx` component, instead of
`return null`. Re-verified live: a fresh UUID pulled from `/api/jobs` renders the Pipeline Board
correctly on a hard direct navigation; a random UUID shows "This job doesn't exist or may have
been removed." with a working back-link, instead of blank. **A second bug was found and fixed
while implementing this**: naively rewriting the five broken selectors to
`useAppStore((s) => s.candidates.filter(...).sort(...))` returns a new array reference every
render, which Zustand's `useSyncExternalStore` treats as "changed" every time → infinite
re-render loop (`Maximum update depth exceeded`). Fixed by selecting the raw `candidates` array
once and deriving the filtered/sorted list with `useMemo` in the component body instead of
inside the store selector.

### 2. The candidate-facing interview mode shown doesn't match the mode delivered — ✅ Fixed 2026-08-09
Sophia's candidate dashboard lists "Product Designer — Portfolio Walkthrough · **Voice**."
Clicking **Start** on that exact card lands on the **Avatar** disclosure screen ("You'll be
interviewed by an AI... uses an AI-generated avatar interviewer") and then the avatar video
session. A candidate who read "Voice" and prepared for a phone-style call gets a video avatar
instead. This is a real trust problem on its own, and it's a compliance problem too — the AI
disclosure content itself (a genuinely well-written screen, see "What's working" below)
describes the wrong modality if this is a labeling bug rather than the intended mode.

**Fixed:** `LandingCandidate.tsx`'s Start button now branches on `interview.mode` (Avatar →
`/avatar/:id/disclosure`, Chat/Voice → `/session/:id/consent`), mirroring the branch already
used correctly in `OnboardingDeviceCheck.tsx`. Re-verified live: the Voice-mode "Product
Designer" card now lands on the consent screen, not the avatar disclosure screen.

### 3. An archived interview is still offered to the candidate as startable — ✅ Fixed 2026-08-09
`InterviewsList` (recruiter side) shows "Staff SRE — Incident Leadership" with an **Archived**
badge. The same interview appears on the candidate's dashboard under "Upcoming interviews"
with an active **Start →** button. Archiving something on the recruiter side should mean a
candidate can no longer start it — right now the two sides of the same record disagree.

**Fixed:** the "Upcoming interviews" list now filters to `status === "Active"` before slicing,
mirroring the status check already used one line above it for the practice-session picker.
Re-verified live: the Archived "Staff SRE" interview no longer appears on the candidate
dashboard.

## P1 — Undermines specific product claims

### 4. The rubric editor doesn't edit anything
`JobDetail`'s "Evaluation Criteria" panel renders each weight (`25%`, `20%`, ...) inside a
white, bordered box — visually identical to every real input field elsewhere in the design
system. It is not one: `read_page` on the live screen shows zero interactive elements there,
only `Regenerate rubric` (full re-generation) and `Save as new version` (snapshots whatever
exists, doesn't let you change it first). There is no way, anywhere in the UI, to adjust a
single criterion's weight, add one, remove one, or edit its description.

This lands directly on a claim in [[Enterprise Buyer Research]]: *"hiring managers and
recruiters frequently disagree on what 'qualified' means... our rubric editor is a direct
answer to this, if hiring managers can also see and weigh in."* Right now nobody can weigh in —
the rubric is view-only wearing an edit-mode costume. Either build real inline editing, or
restyle these as plainly read-only (remove the input-like border/background) so the UI stops
promising something it can't do.

### 5. Every rubric criterion has the same boilerplate description — ✅ Fixed 2026-08-09
"Team Leadership," "Technical Mentorship," "Agile Delivery," and every other must-have
criterion on the Engineering Manager rubric all render the identical sentence: *"Required must
have competency for this role."* Nice-to-haves all get *"Required nice to have competency for
this role."* This is presumably a placeholder that never got replaced with the LLM's actual
per-criterion rationale — but as shipped, it visibly contradicts the product's core pitch
("AI-generated rubrics," "structured, evidence-backed candidate scoring" — both stated on the
login page itself). A recruiter who reads two criteria back to back will notice immediately.

**Fixed, staying deterministic (no LLM call added):** `generate_rubric` in
`app/services/screening.py` now builds each description from a cleaned-up excerpt of the JD
text actually surrounding the matched skill (`_context_snippet`), falling back to the old
generic sentence only when no useful surrounding text exists. No test asserted on the exact
string, so `pytest` stayed green. Re-verified live: regenerating a job's rubric now shows each
criterion quoting a different piece of the JD instead of the identical sentence repeated four times.

### 6. Decorative SSO buttons on both login screens — ✅ Neutralized 2026-08-09
Both `LoginOrg` and `LoginCandidate` show working-looking **Google** / **Microsoft** (org side)
and **Google** / **LinkedIn** (candidate side) buttons. Per [[Enterprise Must-Haves
Checklist]] §1, we have **no auth layer at all** — these buttons do nothing. This is the literal
first screen an enterprise evaluator sees, and it currently oversells identity readiness before
they've clicked anything else. A concurrent M6 planning effort ([[Identity & Access
Overview]]) is already scoping real OIDC SSO — until that ships, these buttons should either be
removed or visibly marked "coming soon," not rendered as functional.

**Neutralized, not built:** both login screens' SSO buttons are now `disabled` with a
"coming soon" caption/tooltip, so they read as visibly non-functional instead of silently
dead. Real SSO stays scoped to [[Identity & Access Overview]] (M6) — not built here.

### 7. Interactive-looking elements that aren't real interactive elements — ✅ Fixed 2026-08-09
Two separate instances of the same underlying problem:
- `CandidatesList` table rows are wrapped in an unlabeled `<button>` (confirmed via
  `read_page` — the accessible tree reports `button [ref]` with no name). A screen-reader user
  tabbing through the table hears "button" 228 times with no way to tell which candidate it opens.
- `InterviewsList` cards use a plain `onClick` on a non-interactive element
  (`InterviewsList.tsx:45`, `navigate(...)` fires on click) rather than a real `<button>` or
  `<Link>` — confirmed by `read_page` returning **zero** accessible elements for three visible,
  clickable cards. A keyboard-only user cannot Tab to or open an interview from this screen at all.

Both are real WCAG 2.1 AA failures (keyboard operability + accessible name), and [[Enterprise
Must-Haves Checklist]] §5 already flags WCAG conformance as "unverified" — this confirms it's
not just unverified, it's currently failing on two of the most-used screens in the app.

**Fixed:** `CandidatesList` (and the identical pattern found in `RankedShortlist` while fixing
this) row buttons now carry `aria-label={"Open " + name + "'s profile"}`. `InterviewsList`
cards now have `role="button"`, `tabIndex={0}`, an Enter/Space key handler, and an `aria-label`
naming the interview. Re-verified live: `read_page` now reports `button "Open Daniel Wright's
profile"` etc. for every candidate row, and `button "Edit Staff SRE — Incident Leadership"` etc.
for every interview card.

## P2 — Real, but lower blast radius

### 8. Session device-readiness check is inconsistent across interview modes
The Chat/Voice flow always runs `OnboardingConsent` → `OnboardingDeviceCheck` (a real
`getUserMedia` camera/mic test) before the session starts. The Avatar flow goes straight from
`AIDisclosure` to the live interview — **no device check at all**, despite Avatar being the one
mode that most needs a working camera. If a candidate's camera is blocked or absent, they find
out only after the AI interviewer is already mid-question, which is a worse failure mode than
what the other two modes already prevent.

### 9. Raw ISO timestamps shown directly to recruiters
`CandidatesList` rows show `applied 2026-12-12T18:30:00Z` verbatim instead of a formatted
relative/absolute date, even though `formatRelativeTime()` already exists in `lib/utils.ts`
(per [[Frontend Overview]]) and is presumably used elsewhere (Dashboard's "Recent activity").
Separately, several seed rows show *future* application dates relative to the app's "today"
(2027-01-05, 2026-12-29) — worth a data fix before anyone outside the team sees a demo, since a
candidate who "applied" in the future reads as broken, not charming.

### 10. Jobs and Interviews feel like two disconnected apps sharing a sidebar
`JobDetail` (viewed for "Engineering Manager") has no visible link to any associated interview
— no "Interview template," no count, nothing. `InterviewsList` cards show a role name but not
a clickable link back to the job. With only 3 interviews total against 34 jobs / 228
candidates, the connective tissue between "we screened this candidate" and "here's their
interview" barely exists in the UI yet. This is exactly the "one vertical slice, not five
glued-together tools" differentiation claimed in [[Competitive Landscape]] — the backend may
well support the link (`interviews.job_id`), but the UI doesn't surface it anywhere I could find.

### 11. `JobsList` and `CandidatesList` have inconsistent filtering power
`CandidatesList` has a genuinely strong filter bar: search, stage, decision, score-band chips,
source, sort. `JobsList` — the same kind of "browse 34+ records" screen — has only a plain text
search box, no status or department filter, despite the table itself having Status and
Department columns. At real enterprise volume (hundreds of open reqs), this gap will be felt
first on Jobs, not Candidates.

## Automated re-verification (Playwright)

`frontend/e2e/ux-audit.mjs` is a standalone Playwright script (not `@playwright/test` — plain
`chromium.launch()` so every check, pass or fail, still gets a screenshot) that re-runs the
checks behind findings #1–#11 as real DOM assertions against the live dev stack, and saves a
labeled screenshot for each (`NN-description-PASS.png` / `-FAIL.png`) plus a `report.md` /
`report.json` summary, into `frontend/e2e/screenshots/` (gitignored — regenerate, don't commit).

```bash
# backend on :8000 and frontend on :5173 must already be running — see Runbook.md
cd frontend
npx playwright install chromium   # once
node e2e/ux-audit.mjs
```

Latest run: **10 PASS / 5 FAIL / 6 tour shots**. The 5 FAILs are *expected* — each asserts the
condition that would only be true if that still-open finding were fixed (e.g. #4 asserts the
rubric weight is a real `<input>`; it isn't, so it fails, which is the honest, correct outcome
for a feature deliberately left out of scope). A FAIL on #1, #2, #3, #5, #6, or #7 in a future
run would mean a real regression, not an expected gap.

## P3 — Polish

- **Dashboard "Recent activity" and "+12 this week" captions are hardcoded**, not derived from
  data (confirmed in [[Frontend Overview]]) — fine for a demo, but will read as a lie the
  moment real usage doesn't match the static numbers.
- **`ComparativeReport`'s "Print/PDF" and "Regenerate" buttons are decorative** — clicking them
  does nothing. Either wire them or remove them; a dead button on a report screen (the one place
  a hiring manager is deciding) is a bad place to break trust.
- **`AddCandidateModal`'s Email field has no required-field asterisk**, though the backend
  functionally requires it for dedupe (`POST /candidates` dedupes by email). Only "Name *" is
  marked.
- **Modal state is lost on refresh** (`?add=1`, `?new=1`, `?share=1` pattern) — already
  documented as a known tradeoff in [[Frontend Overview]], not new, but worth grouping with
  finding #1 since both are "the URL lies about what's recoverable."

## What's genuinely working — don't touch these

A fair review says what's good, not just what's broken:

- **The Candidate Detail scorecard is the strongest screen in the app.** Per-criterion weight,
  score, and a one-line evidence citation ("Direct evidence of Kafka on resume") is exactly the
  "explainable scoring" that [[Enterprise Buyer Research]] identifies as a real enterprise
  buying criterion — and unlike the rubric-editor issue above, this screen doesn't overpromise
  anything it can't do.
- **The AI disclosure screen content is genuinely good** — plain language, states what's
  recorded, states a human reviews it, states the candidate can opt for a human-led interview
  instead. This is close to what [[Enterprise Buyer Research]] says candidates are explicitly
  asking for (38% want human-review confirmation, 29% want bias-audit evidence). The mode-label
  bug (#2) is the only thing undermining it.
- **`CandidatesList`'s bulk toolbar** (shortlist/approve/hold/reject/move-stage across a
  selection, plus CSV export) is real, enterprise-appropriate functionality that most of the
  point-solution competitors in [[Competitive Landscape]] don't clearly have.
- **The design token system is disciplined** — every screen actually uses `brand-primary` /
  `status-strong-text` etc. rather than one-off hex values (per [[Frontend Overview]]'s own
  warning about this). Whoever touches these screens next should keep doing that.

## Suggested sequencing (original) / what's left (updated 2026-08-09)

Original read on cost vs. damage, kept for record — items 1–3 below (findings #1, #2, #3, #5,
#6, #7) are now done, per "Fix status" at the top:

1. ~~Fix #1 (blank pages) first.~~ ✅ Done.
2. ~~Fix #2 and #3 (mode mismatch, archived-but-startable).~~ ✅ Done.
3. ~~#6 (decorative SSO) and #7 (accessibility).~~ ✅ Done — SSO neutralized (not built);
   accessibility fixed. Real SSO remains [[Identity & Access Overview]] (M6)'s job.
4. **#4 (rubric editing) still needs a product decision** — real inline weight editing is a
   feature (UI + store action + backend PATCH), not a bug fix; deliberately left untouched this
   pass. #5 (boilerplate descriptions) was fixed as a cheap, deterministic, in-scope
   improvement without waiting on that decision.
5. **P2/P3 are all still open**: session device-check inconsistency (#8), raw ISO timestamps +
   future-dated seed rows (#9), Jobs↔Interviews IA disconnect (#10), JobsList/CandidatesList
   filter-power gap (#11), and the P3 polish list (hardcoded dashboard activity, dead
   Print/PDF buttons, missing email required-asterisk, modal-state-lost-on-refresh).
