# Pilot Spec — 3 jobs, 3 domains

Human-approved scope for the pilot. Run the agents against THIS spec, review the output,
then scale to the full 37-job portfolio.

## Jobs (one per domain)

| id | title | domain | seniority | yearsRequired |
|---|---|---|---|---|
| `job-001-senior-backend-go` | Senior Backend Engineer (Go) | backend | Senior | 5 |
| `job-002-senior-frontend-react` | Senior Frontend Engineer (React) | frontend | Senior | 5 |
| `job-003-data-engineer` | Data Engineer | data | Mid | 3 |

## Domain archetype pools

Each pool contains 5 people. Pool members apply to their domain's job; a few also apply to a
plausible cross-domain job (so the `applications` join table is actually exercised).

| pool | members | cross-domain overlap |
|---|---|---|
| backend | strong Staff-Go fit, mid Go fit, Python/Django dev with a Go gap, junior backend, backend→cloud switcher | Python dev also applies to Data Engineer |
| frontend | strong Senior-React fit, mid React/TS fit, Angular dev with a React gap, junior frontend, design-systems frontend | design-systems frontend also applies to nothing else (stays 1 job) |
| data | strong Spark/SQL/airflow fit, mid data engineer, SQL-heavy data analyst (weak for DE), Python backend→data mover, junior analytics | Python mover also applies to Senior Backend (Go)? NO — keep data pool self-contained; the Go gap is covered by the backend pool |

## Per-job candidate spread (so the ATS has something to rank)

For each job, among its 5 applicants: **1-2 strong fits** (all must-haves present),
**2 mid** (most must-haves, a gap or two), **1 deliberately weak** (missing a must-have or
well below seniority).

## Naming conventions (mandatory)

- Jobs: `job-001-senior-backend-go` … already fixed above. File: `jobs/job-001-….json`.
- People: `person-001-…`, `person-002-…` sequential, slug = first-name-last-name.
  File: `people/person-001-….json`.
- Emails: `firstname.lastname@example.com` — unique across the whole pool.
- Phone: US format `(555) 0XX-0XXX` with a unique 4-digit tail.
- All `experience[].from/to` as `YYYY-MM`. `to: null` means "current". Timelines must be
  contiguous and monotonic (a new role never starts before the previous one ended).

## Status spread across the pipeline

Among each job's 5 applicants, statuses should be varied: e.g. `Interview`, `Screening`,
`Applied`, `Applied`, `Rejected` — realistic, not all identical.

## Consistency rules every file must obey

1. `yearsExp` ≈ sum of `experience` durations (present role is "now").
2. Titles progress forward — never a more senior title before a junior one.
3. `skills[]` must contain every must-have skill name spelled identically to the job's
   `requiredSkills[].name` for strong fits (so deterministic scoring actually matches).
4. Weak candidates must be missing at least one must-have skill.
5. `gaps[]` and `strengths[]` must be consistent with `skills[]` and `summary`.
