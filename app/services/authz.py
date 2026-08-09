"""RBAC permission matrix (M6 Phase 2). Data, not scattered `if role ==`
checks scattered through routers — one place to read or change who can do
what.

Roles: admin (everything), recruiter (jobs/candidates/interviews CRUD),
hiring_manager (read-only jobs/candidates, full interview management). The
PRD's "hiring manager decides on candidates" need is served by *reading* the
evidence-backed scorecard (GET routes, open to all three roles) — mutating
screening/decision records stays recruiter/admin-only for this pass. If a
real hiring-manager workflow needs write access to decisions later, that's a
product decision to revisit deliberately, not something to default open.
"""

ADMIN = "admin"
RECRUITER = "recruiter"
HIRING_MANAGER = "hiring_manager"

ALL_ROLES = (ADMIN, RECRUITER, HIRING_MANAGER)
WRITE_ROLES = (ADMIN, RECRUITER)
