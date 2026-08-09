---
tags: [product, research, enterprise, compliance, security, integrations]
status: current — initial research pass, web-sourced
last-updated: 2026-08-09
---

# Enterprise Must-Haves Checklist — What It Takes to Get Past Procurement

Companion to [[Enterprise Buyer Research]], [[Cost Savings & ROI Model]], and
[[Competitive Landscape]]. Those notes cover *why* enterprises buy and *who* they compare us
to; this note is the concrete checklist — the specific features, integrations, and paperwork a
real enterprise security/procurement review will ask for, checked against what we've actually
built (per [[Backend Overview]] / [[Frontend Overview]]). Source credibility: mostly Tier B
(SaaS-enterprise-readiness content, largely convergent across sources) plus Tier A legal
analysis for the AI-specific compliance section. See [[Cost Savings & ROI Model]] for the
tiering definition.

**Read this as a gap list, not a to-do list for M2/M3.** Nothing here should jump the roadmap
queue on its own — it's here so that when a real enterprise pilot conversation happens, we know
exactly what will get asked and aren't rediscovering it live on a call.

## 1. Identity & access — near-universal for any buyer with 500+ employees

| Requirement                | What it means                                                                                                                                    | Our status                                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| SSO (SAML 2.0 and/or OIDC) | Login via the company's identity provider (Okta, Azure AD, Google Workspace) — enterprise IT will not create/manage passwords for another vendor | ❌ None — no auth layer at all yet (`jobs.posted_by` is a stub per [[Project Overview]])                                                               |
| SCIM 2.0 provisioning      | Automatic user creation/deprovisioning when someone joins/leaves the company, driven by the IdP                                                  | ❌ None                                                                                                                                                |
| MFA                        | Multi-factor auth, usually inherited from SSO/IdP rather than built natively                                                                     | ❌ None (follows from no auth)                                                                                                                         |
| RBAC with custom roles     | Recruiter / Hiring Manager / Admin separation, least-privilege                                                                                   | 🔶 Roles exist as a concept in the PRD persona table and `users.role` enum, but there's no enforcement layer yet — anyone can call any endpoint today |
| Tenant isolation           | One company's data provably can't leak into another's                                                                                            | ❌ None — no `tenant_id` anywhere in the schema (open decision D3, [[Project Overview]])                                                               |

**Read:** this entire section is M6 territory ("JWT auth, tenant isolation, RBAC" — already on
the roadmap). The research doesn't change *what* M6 needs to do, it confirms none of it is
optional once a real enterprise conversation starts — this is usually the **first** thing a
security questionnaire asks about, before anyone even gets to AI-specific concerns.

## 2. Data protection & security certifications

| Requirement                                          | What it means                                                                                                | Our status                                                                                                                                                      |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SOC 2 Type II                                        | Independent audit that security controls operated effectively over 6–12 months (not just "we have a policy") | ❌ None — and can't start the clock until there's something stable to audit                                                                                      |
| ISO 27001                                            | Required by many EU/APAC enterprise buyers specifically                                                      | ❌ None                                                                                                                                                          |
| Encryption in transit (TLS 1.2+) & at rest (AES-256) | Baseline expectation, usually the easiest box to check                                                       | 🔶 Likely true in transit (HTTPS/standard deploy), unverified at rest for Postgres/local file storage — worth confirming, not assuming                          |
| Data residency (US/EU/APAC options)                  | Where customer data is physically stored — EU buyers in particular usually require an EU option              | ❌ Not applicable yet — single deployment target, no residency story                                                                                             |
| Configurable data retention & deletion (GDPR/CCPA)   | Buyer sets how long resumes/interview recordings are kept, with real deletion on request                     | 🔶 PRD lists this as a requirement (§6) and an assumption (§9: "configurable retention period"), but nothing in the schema enforces retention or deletion today |
| Queryable audit trail                                | Not just "logs exist" — customers want to query who accessed/changed what, when                              | ❌ None — `ai_processing_logs` table exists but isn't written to yet ([[Backend Overview]])                                                                      |
| Penetration test report (recent, third-party)        | Standard ask alongside SOC 2                                                                                 | ❌ None                                                                                                                                                          |

## 3. AI-hiring-specific compliance — the part generic SaaS checklists miss

This is the layer specific to *this* product category, not generic enterprise SaaS. Detail on
the underlying laws is in [[Enterprise Buyer Research]]; this is the checklist form.

| Requirement | Trigger | Our status |
|---|---|---|
| Independent annual bias audit + public summary | NYC Local Law 144, if any candidate is in NYC (increasingly treated as a de facto national baseline, not just an NYC-only concern) | ❌ None |
| ≥10 business days' candidate notice before AEDT use | NYC LL 144 | ❌ None — no candidate-facing disclosure flow at all |
| EU AI Act conformity statement | Reportedly requested by a majority of enterprise buyers now, even those without EU hiring, as a proxy for "this vendor takes AI governance seriously" | ❌ None |
| Documented human-in-the-loop review before an adverse decision | OFCCP guidance explicitly holds federal contractors liable for AI-driven decisions *even when a third-party vendor built the tool* — contractors can't delegate this liability away, so they will push the requirement onto us contractually | 🔶 PRD assumption (§9: "human oversight remains available") and the frontend has human-adjustable scores, but there's no enforced gate or audit trail proving a human actually reviewed before a rejection |
| Candidate-facing AI disclosure/consent screen | Both a legal requirement (LL 144) and, per [[Enterprise Buyer Research]], something 70% of candidates report never getting today — a place to visibly do better than the market average | ❌ None in the current onboarding flow |
| Adverse-impact / disparate-impact testing capability | OFCCP's stated evaluation criterion for federal contractors | ❌ None |

**This is the section most likely to be underestimated.** It's easy to treat "compliance" as
one line item; in practice it's audits, disclosure UX, retained evidence of human review, and
contractual liability language — closer to a product surface (disclosure screens, review-gate
UI, exportable audit reports) than a checkbox.

## 4. Integrations — table stakes, not a nice-to-have

| Integration | Why it's asked for | Our status |
|---|---|---|
| ATS sync — Greenhouse (Harvest API), Lever (GraphQL), Workday Recruiting | Enterprise TA teams run their pipeline of record in one of these; a tool that doesn't sync becomes "yet another disconnected tab" | ❌ Explicitly out of MVP scope (`prd.md` §8) |
| HRIS sync (Workday HCM, SAP SuccessFactors) | For headcount/req data and post-hire handoff | ❌ Not scoped |
| IdP / SSO integration (Okta, Azure AD, Google Workspace) | Covered in §1 — listed again here because procurement treats it as an "integration" line item specifically | ❌ None |
| Calendar (Outlook/Google Calendar) | Interview scheduling — every competitor profiled in [[Competitive Landscape]] that does live interviews has this | ❌ Not built (async-first per PRD, live scheduling not yet a flow) |
| SCIM provisioning | Covered in §1, listed again as a procurement line item | ❌ None |
| Webhooks / outbound API | Lets the buyer's own systems react to events (candidate scored, interview completed) without polling | ❌ None — API exists (`app/routers/`) but no outbound event/webhook system |
| SSO-gated API access / API keys with scoped permissions | For any buyer wanting to integrate us into their own internal tools | ❌ None (no auth layer at all yet) |

## 5. Platform & operational expectations

| Requirement | Our status |
|---|---|
| Uptime SLA (≥99.5%, matches our own PRD target) | Not measured — no production deployment yet (still local-only per [[Project Overview]] / [[Runbook]]) |
| WCAG 2.1 AA accessibility (candidate-facing, per PRD §6) | Unverified — not audited |
| Multi-language support | English-only (PRD §9 explicit assumption); HireVue supports 40 languages, Ribbon AI 10+ — a real gap if targeting global enterprises |
| Mobile/browser support matrix (latest Chrome/Edge/Firefox/Safari per PRD §6) | Untested against this matrix specifically |
| Admin reporting/analytics dashboard | Not built — recruiter dashboard exists, no tenant-level admin/compliance reporting view |

## 6. Commercial & procurement paperwork

Separate from the product itself, but consistently blocks deals if missing: a standard **Data
Processing Agreement (DPA)**, a **Master Service Agreement (MSA)** with security/liability
terms addressing the OFCCP-style liability point above, **cyber liability insurance**, and a
readiness to answer a **vendor security questionnaire** (reportedly 10–30 hours of vendor
effort per questionnaire, 10–20 per year at real enterprise sales volume — a real ongoing cost
of doing enterprise sales, not a one-time gate).

## Priority read, not a mandate

Roughly in the order a real deal would actually block on (not effort order):

1. **§1 (auth/SSO/RBAC/tenancy)** — blocks everything else; this is already M6, correctly
   sequenced.
2. **§3 (AI-hiring compliance: disclosure UX + human-review gate + audit trail)** — cheaper to
   design into M6's auth/audit work now than retrofit later, and it's the one area a
   *feature-complete but non-compliant* product can still lose a deal outright.
3. **§2 (SOC 2 / ISO 27001)** — genuinely can't start until there's a stable, deployed system
   to audit (needs M6b, cloud deploy); the clock-start is the constraint, not willingness.
4. **§4 (ATS integrations)** — real, but rightly deferred; PRD already scopes this
   post-MVP, and [[Competitive Landscape]] confirms it's a real gap versus incumbents, not a
   surprise.
5. **§5/§6** — mostly a function of §1–§3 landing first; not independently urgent.

## Sources

- [The 10 enterprise features every B2B SaaS needs — WorkOS](https://workos.com/blog/enterprise-readiness-checklist-2026)
- [SOC 2 Customer Security Questionnaire: A 2026 Guide — Konfirmity](https://www.konfirmity.com/blog/soc-2-customer-security-questionnaire)
- [The 2026 AI Procurement Checklist for B2B SaaS — Docket](https://www.docket.io/blog/the-2026-ai-procurement-checklist-vetting-your-ai-agent-for-security-privacy-and-trust)
- [Enterprise-Ready SaaS: SSO, SCIM, and Audit Logs in the Right Order — Hashorn](https://hashorn.com/blog/enterprise-ready-saas-sso-scim-audit-logs)
- [12 Signs Your SaaS Product Isn't Enterprise-Ready — SSOJet](https://ssojet.com/blog/enterprise-ready-saas-checklist)
- [Data residency requirements for sales software teams — Outreach](https://www.outreach.ai/resources/blog/data-residency-requirements-sales-software)
- [Harmonizing AI with EEO Requirements: OFCCP's Blueprint for Federal Contractors — Crowell & Moring](https://www.crowell.com/en/insights/client-alerts/harmonizing-ai-with-eeo-requirements-ofccps-blueprint-for-federal-contractors)
- [OFCCP Releases New AI Guidance for Federal Contractors — Perkins Coie](https://perkinscoie.com/insights/update/ofccp-releases-new-ai-guidance-federal-contractors)
- [OFCCP Issues Workplace AI Guidance for Federal Contractors and Subcontractors — Ogletree](https://ogletree.com/insights-resources/blog-posts/ofccp-releases-guidance-on-federal-contractors-use-of-ai-and-automated-systems/)
- [EEOC AI Hiring Guidance 2026 & Federal AI Laws — EmployArmor](https://www.employarmor.com/resources/federal-ai-hiring-laws)
