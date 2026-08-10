import { create } from "zustand";
import type { Candidate, Interview, InterviewQuestion, Job, PipelineStage } from "@/data/types";
import { candidateUser, currentTenant, orgUser } from "@/data/seed";
import { api } from "@/lib/api";

// App state now lives in the backend (FastAPI + Postgres). This store is a
// thin client-side mirror: init() loads everything, and every mutation calls
// the API and then syncs the returned record(s) back into local state so the
// UI updates without a full refetch.

interface AppState {
  currentUser: typeof orgUser;
  currentCandidate: typeof candidateUser;
  currentTenant: typeof currentTenant;
  jobs: Job[];
  candidates: Candidate[];
  interviews: Interview[];
  ready: boolean;
  error: string | null;

  init: () => Promise<void>;

  getCandidate: (candidateId: string) => Candidate | undefined;

  screenCandidate: (candidateId: string) => Promise<void>;
  judgeCandidate: (candidateId: string) => Promise<void>;
  rescreenJob: (jobId: string) => Promise<void>;
  generateRubric: (jobId: string) => Promise<void>;

  toggleShortlist: (candidateId: string) => Promise<void>;
  setDecision: (candidateId: string, decision: Candidate["decision"]) => Promise<void>;
  movePipelineStage: (candidateId: string, stage: PipelineStage) => Promise<void>;
  bulkToggleShortlist: (candidateIds: string[]) => Promise<void>;
  bulkSetDecision: (candidateIds: string[], decision: Candidate["decision"]) => Promise<void>;
  bulkMoveStage: (candidateIds: string[], stage: PipelineStage) => Promise<void>;

  addCandidate: (
    jobId: string,
    input: {
      name: string;
      email: string;
      phone?: string;
      source?: string;
      resumeText: string;
    }
  ) => Promise<{ candidate: Candidate; duplicate?: Candidate }>;
  updateCandidate: (
    candidateId: string,
    patch: Partial<Pick<Candidate, "phone" | "source" | "tags" | "notes" | "location">>
  ) => Promise<void>;

  createJob: (input: { title: string; department: string; location: string; type: string; description: string }) => Promise<Job>;
  updateJobStatus: (jobId: string, status: Job["status"]) => Promise<void>;
  saveJobVersion: (jobId: string) => Promise<void>;

  createInterview: (input: {
    title: string;
    jobTitle: string;
    jobId?: string;
    candidateId?: string;
    mode: Interview["mode"];
  }) => Promise<Interview>;
  toggleInterviewShared: (interviewId: string) => Promise<void>;
  addQuestion: (interviewId: string, q: Omit<InterviewQuestion, "id">) => Promise<void>;
  removeQuestion: (interviewId: string, questionId: string) => Promise<void>;
  updateQuestion: (interviewId: string, questionId: string, patch: Partial<Omit<InterviewQuestion, "id">>) => Promise<void>;
  reorderQuestions: (interviewId: string, orderedQuestions: InterviewQuestion[]) => Promise<void>;
  regenerateQuestions: (interviewId: string) => Promise<void>;
  regenerateQuestion: (interviewId: string, questionId: string) => Promise<void>;
}

function upsertJobs(jobs: Job[], updated: Job): Job[] {
  const idx = jobs.findIndex((j) => j.id === updated.id);
  if (idx === -1) return [updated, ...jobs];
  const copy = [...jobs];
  copy[idx] = updated;
  return copy;
}

function upsertCandidates(candidates: Candidate[], updated: Candidate): Candidate[] {
  const idx = candidates.findIndex((c) => c.id === updated.id);
  if (idx === -1) return [...candidates, updated];
  const copy = [...candidates];
  copy[idx] = updated;
  return copy;
}

export const useAppStore = create<AppState>()((set, get) => ({
  currentUser: orgUser,
  currentCandidate: candidateUser,
  currentTenant,
  jobs: [],
  candidates: [],
  interviews: [],
  ready: false,
  error: null,

  init: async () => {
    try {
      const [jobs, candidates, interviews] = await Promise.all([
        api.listJobs(),
        api.listCandidates(),
        api.listInterviews(),
      ]);
      set({ jobs, candidates, interviews, ready: true, error: null });
    } catch (e) {
      set({ ready: true, error: e instanceof Error ? e.message : "Failed to load data" });
    }
  },

  getCandidate: (candidateId) => get().candidates.find((c) => c.id === candidateId),

  screenCandidate: async (candidateId) => {
    const updated = await api.screenCandidate(candidateId);
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  judgeCandidate: async (candidateId) => {
    const updated = await api.judgeCandidate(candidateId);
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  rescreenJob: async (jobId) => {
    const updated = await api.listJobCandidates(jobId);
    set((s) => {
      const others = s.candidates.filter((c) => c.jobId !== jobId);
      return { candidates: [...others, ...updated] };
    });
  },

  generateRubric: async (jobId) => {
    const job = await api.regenerateRubric(jobId);
    set((s) => ({ jobs: upsertJobs(s.jobs, job) }));
    // Backend re-screens all applications server-side; sync them.
    const updated = await api.listJobCandidates(jobId);
    set((s) => {
      const others = s.candidates.filter((c) => c.jobId !== jobId);
      return { candidates: [...others, ...updated] };
    });
  },

  toggleShortlist: async (candidateId) => {
    const updated = await api.updateCandidate(candidateId, {
      shortlisted: !get().getCandidate(candidateId)?.shortlisted,
    });
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  setDecision: async (candidateId, decision) => {
    const current = get().getCandidate(candidateId);
    const updated = await api.updateCandidate(candidateId, {
      decision,
      shortlisted: decision === "Approved" ? true : current?.shortlisted,
      pipelineStage: decision === "Rejected" ? "Rejected" : current?.pipelineStage,
    });
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  movePipelineStage: async (candidateId, stage) => {
    const updated = await api.updateCandidate(candidateId, { pipelineStage: stage });
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  bulkToggleShortlist: async (candidateIds) => {
    const allShortlisted = candidateIds.every((id) => get().getCandidate(id)?.shortlisted);
    const updated = await api.bulk(candidateIds, allShortlisted ? "unshortlist" : "shortlist");
    set((s) => {
      const ids = new Set(candidateIds);
      const others = s.candidates.filter((c) => !ids.has(c.id));
      return { candidates: [...others, ...updated] };
    });
  },

  bulkSetDecision: async (candidateIds, decision) => {
    const updated = await api.bulk(candidateIds, "decision", decision);
    set((s) => {
      const ids = new Set(candidateIds);
      const others = s.candidates.filter((c) => !ids.has(c.id));
      const enriched = updated.map((c) => ({
        ...c,
        shortlisted: decision === "Approved" ? true : c.shortlisted,
        pipelineStage: decision === "Rejected" ? ("Rejected" as const) : c.pipelineStage,
      }));
      return { candidates: [...others, ...enriched] };
    });
  },

  bulkMoveStage: async (candidateIds, stage) => {
    const updated = await api.bulk(candidateIds, "stage", stage);
    set((s) => {
      const ids = new Set(candidateIds);
      const others = s.candidates.filter((c) => !ids.has(c.id));
      return { candidates: [...others, ...updated] };
    });
  },

  addCandidate: async (jobId, input) => {
    const result = await api.addCandidate({ jobId, ...input });
    if (!result.duplicate) {
      set((s) => ({ candidates: upsertCandidates(s.candidates, result.candidate) }));
    }
    return result.duplicate
      ? { candidate: result.candidate, duplicate: result.candidate }
      : { candidate: result.candidate };
  },

  updateCandidate: async (candidateId, patch) => {
    const updated = await api.updateCandidate(candidateId, patch);
    set((s) => ({ candidates: upsertCandidates(s.candidates, updated) }));
  },

  createJob: async (input) => {
    const job = await api.createJob(input);
    set((s) => ({ jobs: [job, ...s.jobs] }));
    return job;
  },

  updateJobStatus: async (jobId, status) => {
    const job = await api.updateJobStatus(jobId, status);
    set((s) => ({ jobs: upsertJobs(s.jobs, job) }));
  },

  saveJobVersion: async (jobId) => {
    const job = await api.saveJobVersion(jobId);
    set((s) => ({ jobs: upsertJobs(s.jobs, job) }));
  },

  createInterview: async (input) => {
    const interview = await api.createInterview(input);
    set((s) => ({ interviews: [interview, ...s.interviews] }));
    return interview;
  },

  toggleInterviewShared: async (interviewId) => {
    const current = get().interviews.find((i) => i.id === interviewId);
    const updated = await api.updateInterview(interviewId, { shared: !current?.shared });
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  addQuestion: async (interviewId, q) => {
    const current = get().interviews.find((i) => i.id === interviewId);
    const question = { ...q, id: `q-${Date.now()}` };
    const updated = await api.updateInterview(interviewId, {
      questions: [...(current?.questions ?? []), question],
    });
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  removeQuestion: async (interviewId, questionId) => {
    const current = get().interviews.find((i) => i.id === interviewId);
    const updated = await api.updateInterview(interviewId, {
      questions: (current?.questions ?? []).filter((q) => q.id !== questionId),
    });
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  updateQuestion: async (interviewId, questionId, patch) => {
    const current = get().interviews.find((i) => i.id === interviewId);
    const updated = await api.updateInterview(interviewId, {
      questions: (current?.questions ?? []).map((q) => (q.id === questionId ? { ...q, ...patch } : q)),
    });
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  reorderQuestions: async (interviewId, orderedQuestions) => {
    const updated = await api.updateInterview(interviewId, { questions: orderedQuestions });
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  regenerateQuestions: async (interviewId) => {
    const updated = await api.regenerateInterview(interviewId);
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },

  regenerateQuestion: async (interviewId, questionId) => {
    const updated = await api.regenerateQuestion(interviewId, questionId);
    set((s) => ({
      interviews: s.interviews.map((i) => (i.id === interviewId ? updated : i)),
    }));
  },
}));
