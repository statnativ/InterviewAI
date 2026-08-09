# ADR-005: OIDC-first for SSO; SAML 2.0 deferred

- Status: Accepted
- Date: 2026-08-09
- Owners: Amit Tiwari
- Related product decision: PD-002 (cost-sensitive POC scope)
- Supersedes: none
- Superseded by: none

## Context
Enterprise SSO comes in two protocol flavors: **SAML 2.0** (XML-based assertions, signed
SOAP-ish exchanges, certificate pair management) and **OIDC** (JSON tokens — JWTs — over
standard HTTPS, with discovery metadata and JWKS key rotation). The requirements call for
"SSO (SAML 2.0 and/or OIDC)". The platform currently has no auth layer at all (M6 is the
first identity milestone), so the protocol choice shapes everything from Phase 3 onward.
Modern IdPs that the target market actually runs — Okta, Microsoft Entra ID (Azure AD),
Google Workspace — all speak OIDC natively; SAML is retained mainly for legacy on-prem
deployments.

## Decision drivers
- Learning-first project: OIDC's Authorization Code + PKCE flow, discovery, and JWKS
  verification teach the same concepts as SAML with a fraction of the XML/signing machinery.
- One protocol to build, test, and secure; the auth boundary (middleware + session layer)
  is protocol-agnostic, so SAML can be added later behind the same interface.
- OIDC plays naturally with the existing stack (JSON everywhere, Python ecosystem support).

## Considered options

### Option 1: OIDC first, SAML later
Build the SSO phase around OIDC only. A per-tenant `oidc_providers` record (issuer, client,
discovery URL) plus JWT/JWKS verification covers Okta, Entra ID, and Google out of the box.

### Option 2: SAML first (or both from day one)
Build the SAML service-provider side (XML assertion validation, certificate trust, binding
handling) instead of or alongside OIDC. More faithful to the literal requirement but roughly
double the auth surface to build, test, and secure for no functional gain against modern IdPs.

### Option 3: Managed SSO service (Auth0/Okta embedded)
Outsource both protocols to a vendor. Rejected for this project: the point of M6 is to learn
the protocols by building them, and PD-002 favors a cost-sensitive, self-hosted approach.

## Decision
**OIDC-first** (Option 1). SAML is explicitly deferred: documented as a "when a customer
demands it" item that lands behind the same auth boundary, not built now.

## Rationale
OIDC covers the realistic IdP set for the product's target market; SAML's value (legacy
enterprise) can be added later without re-architecting because the middleware/session layer
does not care which protocol produced the identity. Cost and learning value both favor
building one protocol well.

## Consequences

### Positive
- One flow to build: authorize redirect → code exchange → ID-token/JWKS verification →
  session. Well-documented with strong library support.
- Per-tenant OIDC config means each company connects its own IdP — the actual enterprise
  deployment shape.
- PKCE + discovery are included; the flow is secure-by-default for a public client.

### Negative
- A customer whose IdP is SAML-only cannot be onboarded until the SAML phase exists.
- IdP-specific quirks (claim mapping, `amr` MFA claims) still need per-provider verification
  even within OIDC.

### Risks
- Discovery/JWKS behavior varies slightly between IdPs (Okta vs Entra vs Google) — mitigated
  by the dev Keycloak plus per-provider manual verification in Phase 3.
- If a customer demands SAML earlier than planned, the deferral becomes a schedule risk, not
  a technical one (see rollback below).

## Validation plan
Phase 3 of the Identity & Access plan: unit tests against a self-signed JWKS fixture
(wrong issuer / expired / wrong audience / tampered signature) + full redirect flow against
Keycloak + Playwright E2E login.

## Migration and rollout
N/A — no auth exists to migrate. The `oidc_providers` table is additive and tenant-scoped.

## Rollback or exit strategy
The auth boundary is a single dependency (`get_current_user`) plus the login/callback
routers. If OIDC proves unworkable, those two files change; no route handlers or UI depend
on the protocol. SAML later plugs into the same boundary.

## Revisit triggers
- A real customer or prospect with a SAML-only IdP.
- Entra ID/Okta deprecate or materially change OIDC behaviors we depend on.

## Unresolved questions
- Which claims to map (email, name, role claim from IdP vs role set by app) — the app-owned
  role model (users.role) is planned; an IdP-sourced role claim would need a mapping policy.
- Whether JIT-provisioned users should carry an email-domain allowlist per tenant (noted in
  the plan's risks).
