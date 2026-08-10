export type JobStatus = "Draft" | "Open" | "Paused" | "Closed";

export interface RubricCriterion {
  id: string;
  label: string;
  description: string;
  tag: "Must-have" | "Nice-to-have" | "Disqualifying";
  category: string;
  weight: number;
}

export interface JobVersion {
  version: number;
  label: string;
  status: "Approved" | "Superseded";
  by: string;
  date: string;
}

export interface Job {
  id: string;
  title: string;
  department: string;
  location: string;
  type: string;
  status: JobStatus;
  description: string;
  rubric: RubricCriterion[];
  versions: JobVersion[];
  createdAt: string;
}

export type PipelineStage =
  | "Applied"
  | "Screening"
  | "Interview"
  | "Offer"
  | "Rejected";

export interface ScorecardRow {
  criterion: string;
  weight: number;
  score: number;
  note: string;
}

export interface Candidate {
  id: string;
  jobId: string;
  name: string;
  email: string;
  phone: string;
  location: string;
  source: string;
  tags: string[];
  notes: string;
  resumeFile?: string;
  yearsExp: number;
  currentTitle: string;
  currentCompany: string;
  skills: string[];
  score: number;
  shortlisted: boolean;
  decision: "None" | "Approved" | "Hold" | "Rejected";
  pipelineStage: PipelineStage;
  summary: string;
  experience: { title: string; company: string; period: string }[];
  education: string;
  certifications: string;
  scorecard: ScorecardRow[];
  strengths: string[];
  gaps: string[];
  aiNote: string;
  compareVerdict: "Advance" | "Maybe" | "Pass";
  scoreMethod: "deterministic" | "llm_judge";
  appliedAt: string;
}

export interface InterviewQuestion {
  id: string;
  prompt: string;
  type: "Technical" | "Behavioral" | "System Design" | "Culture";
  difficulty: "Easy" | "Medium" | "Hard";
}

export type InterviewMode = "Chat" | "Voice" | "Avatar";

export interface Interview {
  id: string;
  title: string;
  jobTitle: string;
  jobId: string | null;
  candidateId: string | null;
  candidateName: string | null;
  mode: InterviewMode;
  status: "Draft" | "Active" | "Archived";
  questions: InterviewQuestion[];
  duration: number;
  createdAt: string;
  shared: boolean;
}

export interface SessionInfo {
  id: string;
  candidateName: string;
  jobTitle: string;
  interviewTitle: string;
  mode: InterviewMode;
}

export interface ChatMessage {
  id: string;
  from: "ai" | "candidate";
  text: string;
  timestamp: string;
}

export type OrgRole = "admin" | "recruiter" | "hiring_manager";

export interface OrgUser {
  name: string;
  email: string;
  company: string;
  role: OrgRole;
}

export interface Tenant {
  id: string;
  slug: string;
  name: string;
}

export interface CandidateUser {
  name: string;
  email: string;
}
