# ADR-003: Adopt the full 9-table ATS schema (with pgvector) ahead of the milestones that need it

- Status: Accepted
- Date: 2026-08-05
- Owners: Amit Tiwari
- Related product decision: none logged yet — see Unresolved questions
- Supersedes: the original 3-table schema (`jobs`, `candidates`, `resumes` only, no extensions)
- Superseded by: none

## Context
The original M0/M1 schema had 3 tables and no vector/full-text capability. Amit supplied a
complete 9-table schema (adding `users`, `skills`, `resume_skills`, `job_skills`,
`applications`, `ai_processing_logs`, plus `pgvector` embedding columns, GIN full-text search,
and several new columns on the existing tables) and asked for it to be adopted directly, ahead
of the milestones (M2, M3, M5) that would actually use most of the new tables.

## Decision drivers
- Avoid a second disruptive schema migration once M2 (`applications`/`match_score`) and M5
  (`ai_processing_logs`) are reached.
- Alembic autogenerate only creates tables it can see via `Base.metadata` — partial modeling
  (some tables now, some later) would mean re-running discovery/migration work per milestone
  anyway, so there was no real "cheaper to do it later" option once the full schema was given.
- Several columns were renamed (`jd_text`→`description`, `raw_file_path`→`file_path`,
  `parsed_json`→`parsed_data`) and new NOT NULL columns added to `resumes` — incompatible with
  the old data, forcing a real migration event regardless of scope.

## Considered options

### Option 1: Adopt the full schema now, but only wire up endpoints for tables already in use
Model all 9 tables (required for the ORM/migration to be internally consistent), but don't
build routers/schemas for `users`, `skills`, `resume_skills`, `job_skills`, `applications`,
`ai_processing_logs` until the milestone that actually needs them.

### Option 2: Adopt only the parts of the schema needed for M1 today
Keep `jobs`/`candidates`/`resumes` (with the renamed/new columns), defer the other 6 tables
until M2/M3/M5.

### Option 3: Reject the full schema, keep the original 3-table design
Would have required convincing Amit the given schema was wrong — no technical basis for that;
the schema is a reasonable, fairly standard ATS design.

## Decision
Option 1 — full schema modeled now, endpoints built incrementally per milestone.

## Rationale
Modeling ahead of use is normally a form of speculative work worth challenging (see
`.claude/product-architect.md`'s stance on premature abstraction) — but here the schema was
fully specified by the product owner up front, not invented speculatively during
implementation, and the alternative (partial modeling) doesn't actually save migration work
later since Alembic's autogenerate needs the complete picture to produce a correct diff either
way.

## Consequences

### Positive
- M2/M3/M5 can start writing to `applications`/`ai_processing_logs`/skills tables immediately
  without a schema migration blocking them.
- One clean "init" migration exists instead of an accumulating chain of partial migrations.

### Negative
- 6 of 9 tables currently have zero application code reading or writing them — dead weight
  until those milestones arrive. Anyone reading the schema today sees more surface area than
  the running app actually uses.
- `pgvector` embedding columns (`resumes.embedding`, `skills.embedding`) are unpopulated —
  nothing generates embeddings yet, so the ivfflat indexes exist but are indexing nothing.

### Risks
- Schema/reality drift: it's easy to forget these tables aren't live yet and assume
  functionality exists (e.g. skill matching, application tracking) that hasn't been built.
  Mitigated partially by `docs/architecture/overview.md` explicitly calling out "no endpoints
  yet" tables.
- `ivfflat` index quality depends on having a representative amount of data before the index is
  built (documented pgvector guidance) — building it now, empty, may mean it needs to be
  rebuilt once real embeddings exist rather than tuned once.

## Validation plan
Verified via `\dt`/`\dx`/`\di` in psql that all 9 tables, both extensions, and every specified
index exist and match the given SQL. No validation yet that the schema is *correct* for its
eventual use (e.g. whether `Vector(1536)` is the right dimension for whatever embedding model
ends up generating `resumes.embedding` — 1536 matches OpenAI's `text-embedding-ada-002`/
`text-embedding-3-small`, but no embedding model has been chosen yet).

## Migration and rollout
Executed as a full reset: old 3-table migration deleted, Postgres container recreated on the
`pgvector/pgvector:pg16` image, one new "init" migration generated and hand-corrected (see
Consequences of the image change below), applied to a fresh database. Only threw away
same-session test/fixture data — no real user data existed yet.

## Rollback or exit strategy
None planned — this is the current schema. If it proves wrong, the standard Alembic path
(new migration altering/dropping tables) applies; there is no data yet that raises the stakes
of getting a future correction wrong.

## Revisit triggers
- M2 needs `applications.match_score` populated — will surface whether the column shape
  (`DECIMAL(5,2)`, a single `match_breakdown` JSONB blob) is actually sufficient.
- Whichever embedding model gets chosen for `resumes.embedding`/`skills.embedding` may not be
  1536-dimensional, requiring a column type change before the vector columns are ever used.

## Unresolved questions
- No product decision record exists yet for "why full ATS scope including skills-matching and
  application-tracking, not just resume screening" — the PRD supports it (§5.1, §5.5) but the
  specific choice to schema-model it all now, in one pass, hasn't been logged as a PD. Should
  it be?
- Which embedding model will actually populate the vector columns, and does its output
  dimension match `Vector(1536)`? Unknown — not yet decided.
