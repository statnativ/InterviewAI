import type { Candidate, Interview, InterviewSessionInfo, Job, TurnResult } from "@/data/types";
import { useAppStore } from "@/store/useAppStore";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Dev-mode identity headers (M6 Phase 1/2 stand-ins for real session auth —
  // see app/deps.py). Read via getState() since this module isn't a React
  // component and can't use the useAppStore hook directly.
  const { currentTenant, currentUser } = useAppStore.getState();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-Id": currentTenant.id,
      "X-User-Email": currentUser.email,
    },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// M4: candidate-facing calls send NO tenant/user identity, deliberately — there is no
// candidate identity anywhere in this app. The session/interview id in the URL is itself
// the credential (ADR-008, app/deps.py::get_current_interview_session). Never merge this
// with request() above: that would either leak the recruiter's headers onto candidate calls
// or silently drop them from recruiter calls.
async function sessionRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Jobs
  listJobs: () => request<Job[]>("/jobs"),
  createJob: (input: { title: string; department?: string; location?: string; type?: string; status?: string; description: string }) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify(input) }),
  updateJobStatus: (jobId: string, status: Job["status"]) =>
    request<Job>(`/jobs/${jobId}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  regenerateRubric: (jobId: string) =>
    request<Job>(`/jobs/${jobId}/regenerate-rubric`, { method: "POST" }),
  saveJobVersion: (jobId: string) =>
    request<Job>(`/jobs/${jobId}/save-version`, { method: "POST" }),

  // Candidates
  listCandidates: () => request<Candidate[]>("/candidates"),
  listJobCandidates: (jobId: string) => request<Candidate[]>(`/jobs/${jobId}/candidates`),
  getCandidate: (candidateId: string) => request<Candidate>(`/candidates/${candidateId}`),
  addCandidate: (input: { jobId: string; name: string; email: string; phone?: string; source?: string; resumeText: string }) =>
    request<{ candidate: Candidate; duplicate: boolean }>("/candidates", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateCandidate: (candidateId: string, patch: Partial<Candidate>) =>
    request<Candidate>(`/candidates/${candidateId}`, { method: "PATCH", body: JSON.stringify(patch) }),
  screenCandidate: (candidateId: string) =>
    request<Candidate>(`/candidates/${candidateId}/screen`, { method: "POST" }),
  judgeCandidate: (candidateId: string) =>
    request<Candidate>(`/candidates/${candidateId}/judge`, { method: "POST" }),
  bulk: (candidateIds: string[], action: string, value?: string | boolean) =>
    request<Candidate[]>("/candidates/bulk", {
      method: "POST",
      body: JSON.stringify({ candidateIds, action, value }),
    }),

  // Interviews
  listInterviews: () => request<Interview[]>("/interviews"),
  createInterview: (input: {
    title: string;
    jobTitle: string;
    jobId?: string;
    candidateId?: string;
    mode: string;
    questions?: unknown[];
    duration?: number;
  }) => request<Interview>("/interviews", { method: "POST", body: JSON.stringify(input) }),
  updateInterview: (interviewId: string, patch: Partial<Interview>) =>
    request<Interview>(`/interviews/${interviewId}`, { method: "PATCH", body: JSON.stringify(patch) }),
  regenerateInterview: (interviewId: string) =>
    request<Interview>(`/interviews/${interviewId}/regenerate`, { method: "POST" }),
  regenerateQuestion: (interviewId: string, questionId: string) =>
    request<Interview>(`/interviews/${interviewId}/questions/${questionId}/regenerate`, { method: "POST" }),

  // Interview sessions (M4 — candidate-facing, no recruiter identity sent, see sessionRequest above)
  startInterviewSession: (interviewId: string) =>
    sessionRequest<TurnResult>(`/interviews/${interviewId}/sessions`, { method: "POST" }),
  postTurn: (sessionId: string, turnIndex: number, audioBlob: Blob, audioFormat: string) => {
    const form = new FormData();
    form.append("turn_index", String(turnIndex));
    form.append("audio_format", audioFormat);
    form.append("audio", audioBlob, `turn-${turnIndex}.${audioFormat}`);
    return sessionRequest<TurnResult>(`/interview-sessions/${sessionId}/turns`, { method: "POST", body: form });
  },
  getSession: (sessionId: string) => sessionRequest<InterviewSessionInfo>(`/interview-sessions/${sessionId}`),
  completeSession: (sessionId: string) =>
    sessionRequest<InterviewSessionInfo>(`/interview-sessions/${sessionId}/complete`, { method: "POST" }),
};
