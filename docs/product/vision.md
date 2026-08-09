# Vision

Source of truth for scope and requirements is [prd.md](prd.md) — this page is the one-screen
summary.

## What we're building
An AI-powered platform that automates and enhances candidate interviewing: resume parsing +
scoring against a job description, AI-generated interview questions, video/audio interview
delivery (async first, live later), and automated evaluation with structured feedback.

## Why
Traditional first-round screening is slow, expensive, and inconsistent — recruiters spend
heavy time on repetitive screens, interview quality varies by interviewer, and bias is hard to
control. The goal is a reliable, auditable, AI-assisted system that handles screening and
first-round interviews at scale, without sacrificing quality of hire.

## Who it's for
- **Recruiter / TA Lead** — needs speed, consistency, clear reports, easy setup.
- **Hiring Manager** — needs role-specific questions, reliable scores, evidence.
- **Candidate** — needs a fair process, clear instructions, a smooth experience.
- **Admin / HR Ops** — needs security, compliance, multi-tenancy, audit logs.

## What success looks like (MVP)
- ≥ 60% reduction in time-to-first-interview
- ≥ 50% reduction in recruiter hours spent on screening/first-round interviews
- Resume-to-score turnaround < 2 minutes; question generation < 10 seconds
- ≥ 80% interview completion rate; ≥ 4.0/5 candidate satisfaction
- 99.5% uptime

## Current phase
This is a **cost-sensitive proof of concept**, built and learned incrementally (see
[../architecture/overview.md](../architecture/overview.md) for the milestone roadmap). Live,
real-time video/speech-to-speech interviewing and full enterprise features (SSO, multi-tenant
isolation, compliance tooling) are real requirements per the PRD but are explicitly sequenced
later, not MVP-blocking.
