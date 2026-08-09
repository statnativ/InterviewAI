# Product Requirements Document (PRD)

**Product Name:** AI Interview Platform (working title)
**Version:** 1.0 (MVP Focus)
**Date:** August 2026
**Owner:** Amit Tiwari

## 1. Overview
An enterprise-grade AI-powered platform that automates and enhances the candidate interview process.

The system combines:
- ATS capabilities (resume parsing + scoring against job descriptions)
- AI-generated interview questions tailored to the role and candidate
- Video + audio interview delivery (live or asynchronous)
- Automated evaluation and structured feedback reports

**Primary Goal:** Help enterprises screen and evaluate candidates faster, more consistently, and at lower cost while maintaining (or improving) quality of hire.

## 2. Problem Statement
Traditional hiring is slow, expensive, and inconsistent:
- Recruiters spend significant time screening resumes and conducting repetitive first-round interviews.
- Interview quality varies heavily by interviewer.
- Scheduling live interviews creates friction.
- Bias and subjectivity are hard to control.
- Scaling high-volume hiring is difficult.

Enterprises need a reliable, auditable, AI-assisted system that can handle screening + first-round interviews at scale.

## 3. Goals & Success Metrics

**Business Goals**
- Reduce time-to-first-interview by ≥ 60%
- Reduce recruiter hours spent on screening/initial interviews by ≥ 50%
- Improve consistency of evaluation across candidates
- Support high-volume hiring without linear increase in human effort

**Product Success Metrics (MVP)**
- Resume-to-scored report turnaround < 2 minutes
- Question generation latency < 10 seconds
- Interview completion rate ≥ 80%
- Average candidate satisfaction score ≥ 4.0 / 5
- Recruiter time saved per candidate ≥ 30 minutes
- System uptime ≥ 99.5%

## 4. Target Users & Personas

| Persona | Description | Key Needs |
|---|---|---|
| Recruiter / TA Lead | Manages high-volume hiring | Speed, consistency, clear reports, easy setup |
| Hiring Manager | Decides on candidates | Role-specific questions, reliable scores, evidence |
| Candidate | Job seeker | Fair process, clear instructions, smooth experience |
| Admin / HR Ops | Enterprise administrator | Security, compliance, multi-tenancy, audit logs |

## 5. Core Features (MVP Scope)

### 5.1 ATS – Resume Scoring
- Upload resume (PDF / DOCX)
- Parse and extract structured data (experience, skills, education, etc.)
- Score resume against a given Job Description (0–100 + breakdown)
- Highlight matching and missing skills/experience
- Store parsed resume + score with version history

### 5.2 AI Question Generation
- Generate 8–12 interview questions based on:
  - Job Description
  - Candidate resume
  - Interview type (technical / behavioral / mixed)
- Support question categories (must-ask, follow-up, role-specific)
- Allow recruiter to edit / approve / reorder questions before interview
- Ability to regenerate individual questions

### 5.3 Interview Experience (Video + Audio)
- Two modes:
  - **Asynchronous**: Candidate records answers to questions one by one
  - **Live AI-moderated** (stretch for MVP): Real-time conversation with AI interviewer
- Browser-based video + audio (WebRTC)
- Clear instructions, timer, progress indicator
- Ability for candidate to re-record individual answers (limited times)
- Automatic transcription of answers

### 5.4 Evaluation & Reporting
- Automatic scoring of each answer (content relevance, depth, communication)
- Overall interview score + section-wise breakdown
- Structured report for recruiter/hiring manager (key strengths, gaps, recommended next steps)
- Side-by-side view: Resume score + Interview score
- Ability for human reviewer to adjust scores with comments

### 5.5 Basic Platform Features
- Job / Requisition creation
- Candidate invitation via email/link
- Dashboard for recruiters (pipeline view)
- Role-based access (Recruiter, Hiring Manager, Admin)
- Basic multi-tenancy (company-level isolation)

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | Resume scoring < 2 min, question gen < 10s, video start < 5s |
| Scalability | Support 500 concurrent interviews initially |
| Availability | 99.5% uptime |
| Security | Encryption in transit & at rest, PII protection |
| Privacy | GDPR / CCPA ready data handling & deletion |
| Compliance | Audit logs of all scoring & access actions |
| Accessibility | Basic WCAG 2.1 AA for candidate interface |
| Browser Support | Latest Chrome, Edge, Firefox, Safari |

## 7. Key User Flows (MVP)

1. **Recruiter creates job** → uploads/pastes JD → system ready
2. **Candidate applies / is invited** → uploads resume → receives score + invitation
3. **Recruiter reviews resume score** → approves/edits AI-generated questions → sends interview link
4. **Candidate completes video/audio interview**
5. **System generates evaluation report**
6. **Recruiter / Hiring Manager reviews report** → decides next steps

## 8. Out of Scope (MVP)
- Full live human interviewer co-pilot
- Advanced emotion / body language analysis
- Deep technical coding assessments (whiteboard / IDE)
- Full ATS replacement (sourcing, offer management, etc.)
- Mobile native apps (web-first)
- Advanced analytics / bias detection dashboards
- Integration marketplace (Greenhouse, Lever, Workday, etc.) — planned for later

## 9. Assumptions & Constraints
- Candidates have a modern browser + stable internet + webcam/mic
- Primary language for MVP: English
- AI models will be used via APIs initially (with option to self-host later)
- Recordings will be stored for a configurable retention period
- Human oversight remains available on all AI scores

## 10. Future Considerations (Post-MVP)
- Real-time adaptive questioning
- Multi-language support
- Coding / system design interview modules
- Bias and fairness monitoring
- Deep integrations with existing ATS/HRIS
- White-label / on-premise options for large enterprises
- Advanced proctoring and fraud detection

---

## Appendix: System Design Learning Plan

This PRD doubles as the subject matter for a hands-on system design learning track. The
original learning plan (superseded operationally by [docs/architecture/overview.md](../architecture/overview.md)'s
milestone roadmap, kept here for the original reasoning) was:

1. **Core product understanding first** — map the major capabilities (ATS, question
   generation, interview delivery, evaluation, enterprise/compliance needs) before designing.
2. **Foundational system design concepts** — requirements gathering, high-level architecture,
   scalability, reliability/availability, consistency models, caching, message queues/event-driven
   design, databases (SQL + vector), API design, microservices vs. modular monolith, observability.
3. **Domain-specific design topics**:
   - Media (video + audio) pipeline: WebRTC, SFUs, adaptive bitrate, recording/storage, STT
     (streaming vs. batch), audio quality handling, latency budgets.
   - ATS + resume scoring: parsing, embeddings, scoring models, format/language handling,
     model versioning and auditability.
   - AI question generation & interview orchestration: prompt engineering + RAG, LLM
     orchestration, guardrails, conversation state management, cost/token budgeting.
   - Evaluation & scoring pipeline: transcription → answer evaluation, multi-modal signals,
     structured LLM output + deterministic scoring, explainability, human-in-the-loop review.
   - Enterprise & compliance: multi-tenancy, authn/authz (SSO/SAML/OIDC, RBAC), data privacy
     and security, audit logs, retention, GDPR/CCPA/SOC 2, rate limiting, abuse prevention.
4. **Recommended learning order**: basics → real-time systems/WebRTC → AI system design
   patterns (RAG, orchestration, evaluation, cost/latency tradeoffs, vector search) → media/speech
   pipelines → enterprise multi-tenant architecture → end-to-end design of the full product.
5. **Practical approach**: design the high-level architecture first, identify the hardest parts
   early (real-time media, reliable AI evaluation, continuous LLM cost, data privacy), build a
   thin vertical slice before adding full video/enterprise features, and study real systems
   (ATS platforms, HireVue-style video interview tools, multi-tenant SaaS) — optimizing for
   understanding tradeoffs (latency vs. cost vs. accuracy, real-time vs. async, managed vs.
   self-hosted) over memorizing diagrams.
