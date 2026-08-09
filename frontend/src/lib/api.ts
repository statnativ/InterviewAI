import type { Candidate, Interview, Job } from "@/data/types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
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
  addCandidate: (input: { jobId: string; name: string; email: string; phone?: string; source?: string; resumeText: string }) =>
    request<{ candidate: Candidate; duplicate: boolean }>("/candidates", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateCandidate: (candidateId: string, patch: Partial<Candidate>) =>
    request<Candidate>(`/candidates/${candidateId}`, { method: "PATCH", body: JSON.stringify(patch) }),
  screenCandidate: (candidateId: string) =>
    request<Candidate>(`/candidates/${candidateId}/screen`, { method: "POST" }),
  bulk: (candidateIds: string[], action: string, value?: string | boolean) =>
    request<Candidate[]>("/candidates/bulk", {
      method: "POST",
      body: JSON.stringify({ candidateIds, action, value }),
    }),

  // Interviews
  listInterviews: () => request<Interview[]>("/interviews"),
  createInterview: (input: { title: string; jobTitle: string; mode: string; questions?: unknown[]; duration?: number }) =>
    request<Interview>("/interviews", { method: "POST", body: JSON.stringify(input) }),
  updateInterview: (interviewId: string, patch: Partial<Interview>) =>
    request<Interview>(`/interviews/${interviewId}`, { method: "PATCH", body: JSON.stringify(patch) }),
};
