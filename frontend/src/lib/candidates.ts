import type { Candidate, PipelineStage } from "@/data/types";

export type SortKey = "score" | "name" | "appliedAt" | "yearsExp";
export type ScoreBand = "all" | "strong" | "possible" | "weak";

export interface CandidateFilters {
  query: string;
  stage: PipelineStage | "all";
  decision: Candidate["decision"] | "all";
  band: ScoreBand;
  source: string;
  sortKey: SortKey;
  sortDir: "asc" | "desc";
}

export const defaultFilters: CandidateFilters = {
  query: "",
  stage: "all",
  decision: "all",
  band: "all",
  source: "all",
  sortKey: "score",
  sortDir: "desc",
};

const STAGES: PipelineStage[] = ["Applied", "Screening", "Interview", "Offer", "Rejected"];
const DECISIONS: Candidate["decision"][] = ["None", "Approved", "Hold", "Rejected"];
export const SOURCE_OPTIONS = [
  "LinkedIn",
  "Employee Referral",
  "Company Careers Page",
  "Job Board",
  "Hacker News",
  "University Recruiting",
  "Manual Entry",
];

export const stageOptions = STAGES;
export const decisionOptions = DECISIONS;

export function scoreBand(score: number): Exclude<ScoreBand, "all"> {
  if (score >= 80) return "strong";
  if (score >= 55) return "possible";
  return "weak";
}

export function matchesScoreBand(score: number, band: ScoreBand): boolean {
  if (band === "all") return true;
  return scoreBand(score) === band;
}

export function filterCandidates(candidates: Candidate[], f: CandidateFilters): Candidate[] {
  const q = f.query.trim().toLowerCase();
  const filtered = candidates.filter((c) => {
    if (q && !`${c.name} ${c.email}`.toLowerCase().includes(q)) return false;
    if (f.stage !== "all" && c.pipelineStage !== f.stage) return false;
    if (f.decision !== "all" && c.decision !== f.decision) return false;
    if (!matchesScoreBand(c.score, f.band)) return false;
    if (f.source !== "all" && c.source !== f.source) return false;
    return true;
  });

  return filtered.sort((a, b) => {
    const dir = f.sortDir === "asc" ? 1 : -1;
    switch (f.sortKey) {
      case "score":
        return (a.score - b.score) * dir;
      case "yearsExp":
        return (a.yearsExp - b.yearsExp) * dir;
      case "appliedAt":
        return a.appliedAt.localeCompare(b.appliedAt) * dir;
      case "name":
        return a.name.localeCompare(b.name) * dir;
      default:
        return 0;
    }
  });
}
