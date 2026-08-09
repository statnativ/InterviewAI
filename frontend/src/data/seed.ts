import type {
  Job,
  Interview,
  OrgUser,
  CandidateUser,
  Tenant,
} from "./types";

// Must match SEED_TENANT_ID in the backend's app/deps.py — the one seed
// tenant every M6-Phase-1 migration/seed script agrees on.
export const currentTenant: Tenant = {
  id: "11111111-1111-1111-1111-111111111111",
  slug: "northwind-health",
  name: "Northwind Health",
};

export const orgUser: OrgUser = {
  name: "Riley Hoffman",
  email: "riley@northwindhealth.com",
  company: "Northwind Health",
  role: "recruiter",
};

export const candidateUser: CandidateUser = {
  name: "Sophia Martinez",
  email: "sophia.martinez@gmail.com",
};

const backendRubric: Job["rubric"] = [
  {
    id: "c1",
    label: "5+ years backend engineering experience",
    description: "Track record building and operating production backend systems at scale.",
    tag: "Must-have",
    category: "Experience",
    weight: 20,
  },
  {
    id: "c2",
    label: "Proficiency in Go or a comparable statically-typed language",
    description: "Must demonstrate production experience, not just familiarity.",
    tag: "Must-have",
    category: "Technical Skills",
    weight: 20,
  },
  {
    id: "c3",
    label: "Kubernetes & container orchestration",
    description: "Hands-on operating Kubernetes clusters in production.",
    tag: "Must-have",
    category: "Technical Skills",
    weight: 15,
  },
  {
    id: "c4",
    label: "Distributed systems design experience",
    description: "Has designed or scaled multi-service distributed systems.",
    tag: "Nice-to-have",
    category: "Technical Skills",
    weight: 15,
  },
  {
    id: "c5",
    label: "Experience mentoring or leading engineers",
    description: "Tech-lead or mentorship experience preferred, not required.",
    tag: "Nice-to-have",
    category: "Soft Skills",
    weight: 10,
  },
  {
    id: "c6",
    label: "Kafka or equivalent streaming platform",
    description: "Bonus if familiar with event-driven architectures.",
    tag: "Nice-to-have",
    category: "Technical Skills",
    weight: 10,
  },
  {
    id: "c7",
    label: "No unexplained employment gaps > 1 year",
    description: "Flag for recruiter review if present; not an automatic reject.",
    tag: "Disqualifying",
    category: "Other",
    weight: 10,
  },
];

export const jobs: Job[] = [
  {
    id: "job-backend",
    title: "Senior Backend Engineer",
    department: "Engineering",
    location: "Remote",
    type: "Full-time",
    status: "Open",
    description:
      "We're looking for a Senior Backend Engineer to help scale our core platform services.",
    rubric: backendRubric,
    versions: [
      { version: 2, label: "Version 2", status: "Approved", by: "Riley Hoffman", date: "Aug 3, 2026" },
      { version: 1, label: "Version 1", status: "Superseded", by: "Initial draft from JD", date: "Jul 28, 2026" },
    ],
    createdAt: "2026-07-28",
  },
  {
    id: "job-designer",
    title: "Product Designer",
    department: "Design",
    location: "San Francisco, CA",
    type: "Full-time",
    status: "Open",
    description:
      "Own end-to-end product design for our hiring platform, from research to high-fidelity UI.",
    rubric: [
      { id: "d1", label: "3+ years product design experience", description: "B2B SaaS preferred.", tag: "Must-have", category: "Experience", weight: 25 },
      { id: "d2", label: "Strong portfolio of shipped work", description: "Case studies with measurable outcomes.", tag: "Must-have", category: "Portfolio", weight: 30 },
      { id: "d3", label: "Figma fluency", description: "Comfortable building and maintaining design systems.", tag: "Must-have", category: "Technical Skills", weight: 20 },
      { id: "d4", label: "Front-end collaboration experience", description: "Has worked closely with engineers on implementation.", tag: "Nice-to-have", category: "Technical Skills", weight: 15 },
      { id: "d5", label: "User research experience", description: "Has run interviews or usability studies.", tag: "Nice-to-have", category: "Research", weight: 10 },
    ],
    versions: [
      { version: 1, label: "Version 1", status: "Approved", by: "Riley Hoffman", date: "Jul 15, 2026" },
    ],
    createdAt: "2026-07-10",
  },
  {
    id: "job-sre",
    title: "Staff SRE",
    department: "Infrastructure",
    location: "Remote",
    type: "Full-time",
    status: "Closed",
    description: "Lead reliability engineering across our production infrastructure.",
    rubric: [
      { id: "s1", label: "7+ years SRE / infrastructure experience", description: "Staff-level scope of ownership.", tag: "Must-have", category: "Experience", weight: 25 },
      { id: "s2", label: "On-call incident leadership", description: "Has led incident response at scale.", tag: "Must-have", category: "Technical Skills", weight: 20 },
      { id: "s3", label: "Terraform / IaC expertise", description: "Deep infra-as-code experience.", tag: "Must-have", category: "Technical Skills", weight: 20 },
      { id: "s4", label: "Cross-team technical leadership", description: "Has influenced infra strategy org-wide.", tag: "Nice-to-have", category: "Soft Skills", weight: 20 },
      { id: "s5", label: "Cost optimization experience", description: "Track record reducing cloud spend.", tag: "Nice-to-have", category: "Technical Skills", weight: 15 },
    ],
    versions: [
      { version: 1, label: "Version 1", status: "Approved", by: "Riley Hoffman", date: "Jun 1, 2026" },
    ],
    createdAt: "2026-05-20",
  },
  {
    id: "job-marketing",
    title: "Marketing Manager",
    department: "Marketing",
    location: "New York, NY",
    type: "Full-time",
    status: "Draft",
    description: "Drive demand generation and brand strategy for our hiring platform.",
    rubric: [
      { id: "m1", label: "5+ years B2B SaaS marketing", description: "Demand gen and lifecycle experience.", tag: "Must-have", category: "Experience", weight: 30 },
      { id: "m2", label: "Content & positioning ownership", description: "Has owned messaging and positioning.", tag: "Must-have", category: "Skills", weight: 25 },
      { id: "m3", label: "Analytics fluency", description: "Comfortable with funnel and attribution data.", tag: "Nice-to-have", category: "Skills", weight: 20 },
    ],
    versions: [],
    createdAt: "2026-08-06",
  },
];


export const interviews: Interview[] = [
  {
    id: "int-backend-tech",
    title: "Senior Backend Engineer — Technical Screen",
    jobTitle: "Senior Backend Engineer",
    jobId: null,
    candidateId: null,
    candidateName: null,
    mode: "Chat",
    status: "Active",
    duration: 45,
    createdAt: "2026-07-29",
    shared: true,
    questions: [
      { id: "q1", prompt: "Walk me through how you'd design a rate limiter for a public API.", type: "System Design", difficulty: "Medium" },
      { id: "q2", prompt: "Describe a production incident you led the response for. What was the root cause?", type: "Behavioral", difficulty: "Medium" },
      { id: "q3", prompt: "How would you shard a PostgreSQL database that's outgrown a single instance?", type: "Technical", difficulty: "Hard" },
      { id: "q4", prompt: "Tell me about a time you disagreed with a technical decision on your team.", type: "Culture", difficulty: "Easy" },
    ],
  },
  {
    id: "int-designer-portfolio",
    title: "Product Designer — Portfolio Walkthrough",
    jobTitle: "Product Designer",
    jobId: null,
    candidateId: null,
    candidateName: null,
    mode: "Voice",
    status: "Active",
    duration: 30,
    createdAt: "2026-07-20",
    shared: false,
    questions: [
      { id: "q1", prompt: "Walk me through a project where the initial design didn't work and how you iterated.", type: "Behavioral", difficulty: "Medium" },
      { id: "q2", prompt: "How do you decide when a design is ready to ship vs. needs more research?", type: "Culture", difficulty: "Easy" },
    ],
  },
  {
    id: "int-sre-oncall",
    title: "Staff SRE — Incident Leadership",
    jobTitle: "Staff SRE",
    jobId: null,
    candidateId: null,
    candidateName: null,
    mode: "Avatar",
    status: "Archived",
    duration: 40,
    createdAt: "2026-06-05",
    shared: true,
    questions: [
      { id: "q1", prompt: "Describe the worst production outage you've handled. Walk me through your decisions minute by minute.", type: "Behavioral", difficulty: "Hard" },
      { id: "q2", prompt: "How would you reduce our cloud spend by 20% without impacting reliability?", type: "Technical", difficulty: "Medium" },
    ],
  },
];
