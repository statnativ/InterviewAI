# ADR-001: Local PostgreSQL via Docker Compose for development

- Status: Accepted
- Date: 2026-08-05
- Owners: Amit Tiwari
- Related product decision: PD-002 (cost-sensitive POC scope)
- Supersedes: none
- Superseded by: none

## Context
The project needed a relational database from M0 onward (jobs, candidates, resumes, and later
the full ATS schema). Amit has Docker and a pre-existing local Homebrew Postgres installation
on the same machine.

## Decision drivers
- Zero cloud cost during active local development (explicit cost-sensitive POC).
- Fast iteration loop — schema changes happen frequently while learning.
- Environment parity with an eventual production Postgres target.
- Must not disturb the pre-existing local Postgres install already in use for other work.

## Considered options

### Option 1: Docker Compose–managed Postgres container
Isolated, disposable, versioned via `docker-compose.yml`, doesn't touch the host's existing
Postgres install.

### Option 2: Use the existing local Homebrew Postgres directly
No container overhead, but risks collision with whatever else that instance is used for, and
the exact server version/extensions aren't controlled by this repo.

### Option 3: SQLite for local dev, Postgres only in a later "real" environment
Zero setup friction, but pgvector, JSONB behavior, and Postgres-specific SQL (used from M1
onward) wouldn't be testable locally at all.

## Decision
Use Docker Compose–managed Postgres (Option 1).

## Rationale
Isolation from the pre-existing local Postgres was the deciding factor — confirmed necessary
in practice when the default port 5432 collided with the existing install (see Consequences).
Docker Compose also makes the exact server image (later: `pgvector/pgvector:pg16`) reproducible
and disposable, which mattered once the schema needed a full reset (ADR-003).

## Consequences

### Positive
- Fully disposable — `docker compose down -v` gives a clean slate with zero risk to the host's
  other Postgres usage.
- Reproducible image/version across any machine this repo is cloned to.

### Negative
- Adds Docker as a hard local dependency for anyone running this project.
- One extra manual step (`docker compose up -d`) before the app can start.

### Risks
- Docker Desktop/Engine itself is a dependency; if it's not installed or running, nothing else
  works. No mitigation currently beyond documenting it in `CLAUDE.md`.

## Validation plan
None formal. Validated implicitly: the container has been used continuously since M0 for every
migration and API test this session without incident.

## Migration and rollout
N/A — this was the initial choice, not a migration from something else.

## Rollback or exit strategy
Switch `DATABASE_URL` to point at any other reachable Postgres (local Homebrew install, a
managed cloud instance). No app code depends on the container specifically.

## Revisit triggers
- Moving to a shared/team dev environment where a single shared dev DB might be preferable.
- Deploying to production (tracked separately — see the cloud deployment ADR when it exists).

## Unresolved questions
- None currently blocking.
