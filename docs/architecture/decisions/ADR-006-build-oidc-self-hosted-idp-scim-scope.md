# ADR-006: Build OIDC ourselves with a self-hosted dev IdP; SCIM 2.0 narrowly scoped

- Status: Accepted
- Date: 2026-08-09
- Owners: Amit Tiwari
- Related product decision: PD-002 (cost-sensitive POC scope)
- Related ADRs: ADR-005 (OIDC-first), ADR-002 (single gateway pattern for AI)
- Supersedes: none
- Superseded by: none

## Context
The enterprise requirements add SSO and SCIM 2.0 provisioning. Two build-vs-buy forks exist:
(1) the SSO **client** side — build the OIDC client + JWT verification in our FastAPI app vs
embed a managed identity service (Auth0/Okta); and (2) the **IdP** side for development —
how do we get a real OIDC provider to test against locally, without a paid account. SCIM is
a separate, much larger question: RFC 7643/7644 is enormous (bulk, filtering, etags,
pagination, schemas), and the realistic enterprise ask is user lifecycle (hire/promote/fire)
pushed from the customer's IdP.

## Decision drivers
- The project's core is learning system design by building — outsourcing the interesting
  parts to a vendor would empty M6 of content.
- PD-002: cost-sensitive POC; a self-hosted IdP (Keycloak/Dex) costs nothing.
- SCIM's value to this project is understanding lifecycle automation + RFC-shaped APIs, not
  claiming full spec compliance.

## Considered options

### Option 1: Build OIDC client (authlib + pyjwt), Keycloak in Docker as dev IdP
App side: `authlib` OIDC client for discovery + code exchange, JWT/JWKS verification with
`pyjwt`. Dev/CI IdP: Keycloak container (or Dex if Keycloak's footprint is a problem) in the
existing docker-compose pattern. SCIM: build the server side ourselves, narrowly.

### Option 2: Managed identity (Auth0/Okta)
Vendor handles OIDC/SAML/SCIM/MFA. Realistic for production, but: recurring cost, the
interesting protocol work disappears, and local dev still needs a sandbox/tenant that
requires an account. Rejected for the same reason ADR-002 rejected per-vendor SDKs: one
learning project, build the layer.

### Option 3: Fully self-built mock IdP (hand-rolled OIDC server for tests)
In addition to (1), write our own toy OIDC issuer for tests instead of Keycloak. Rejected for
tests' sake — a fake issuer is fine for unit-testing *verification* (self-signed JWKS
fixture) but a real IdP is needed to shake out the redirect/exchange/cookie flow honestly.

## Decision
**Option 1**: build the OIDC client + verification in the app (authlib + pyjwt), run
Keycloak in Docker as the dev/CI IdP (fallback: Dex), and implement SCIM 2.0 server-side in
a **narrow scope**: `ServiceProviderConfig`, `Users` CRUD + deactivate, `Groups` read-only;
bulk/filtering/etags/pagination explicitly out of scope.

## Rationale
Matches the learning goal (build the client, run a real IdP, see the whole flow) while
keeping the biggest scope item honest: a narrow SCIM surface that a driver script can
exercise end-to-end, with the rest of RFC 7643/7644 documented as deliberately excluded.
Keycloak was chosen over Dex because it is the most widely used OSS IdP and ships both OIDC
and SCIM user federation, so the optional "connect Keycloak's SCIM to our SCIM" integration
test is available for free.

## Consequences

### Positive
- Real OIDC flows against a real IdP locally, zero cost, reproducible in CI via docker-compose.
- The auth boundary stays protocol-agnostic (ADR-005) and vendor-free.
- SCIM scope is defensible: user lifecycle works end-to-end; RFC extras are documented as
  out of scope rather than half-built.
- authlib/pyjwt are small, well-known libraries — not a framework takeover of the app.

### Negative
- Keycloak is a heavy container (JVM); it needs memory and start time on every dev/CI run
  (mitigated by Dex fallback).
- We own the security details ourselves (session cookies, nonce handling, key rotation
  handling) — no vendor safety net.
- Narrow SCIM may not satisfy a real enterprise customer's checklist (bulk/filtering).

### Risks
- authlib's behavior across IdP quirks (Okta/Entra/Google claim differences) — mitigated by
  per-provider manual verification in Phase 3.
- JIT provisioning creates users on first login without approval — email-domain allowlist
  noted as the control.
- SCIM bearer-token security is our job — hashed `scim_credentials`, rate limiting in Phase 6.

## Validation plan
Phase 3–5 of the Identity & Access plan: JWKS fixture unit tests; full redirect flow against
Keycloak; Playwright E2E login; SCIM create/update/deactivate round-trip via
`scripts/scim_demo.py`; cross-tenant leak tests remain the isolation gate.

## Migration and rollout
N/A — additive. Keycloak joins docker-compose behind a `profiles:` flag (or separate
compose file) so it doesn't burden runs that don't need it.

## Rollback or exit strategy
All identity code is behind `get_current_user` / `require_roles` dependencies and the
login/callback/SCIM routers. If the self-hosted IdP path fails, the app code survives
unchanged against a managed IdP (Auth0/Okta) — only the IdP configuration changes. SCIM
endpoints can be disabled by removing the router; no app feature depends on them.

## Revisit triggers
- Keycloak's footprint makes CI unreliable → switch to Dex, app-side code unchanged.
- A customer demands SCIM bulk/filtering or SAML (ADR-005) → scope expansion decision
  recorded at that point.
- Managed identity becomes the right call (e.g., real production launch with no auth
  engineers) → documented path above.

## Unresolved questions
- Session storage: DB table (revocable, planned) vs signed-cookie-only — the plan chooses DB
  sessions; revisit if auth volume ever demands it.
- Whether `require_mfa` should trigger IdP step-up auth or simply reject — plan rejects;
  step-up documented as the production answer.
