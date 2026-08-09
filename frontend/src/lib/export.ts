import type { Candidate, Job } from "@/data/types";

function escapeCell(value: string | number): string {
  const s = String(value ?? "");
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function candidatesToCsv(candidates: Candidate[], jobById: Map<string, Job>): string {
  const header = [
    "Name",
    "Email",
    "Phone",
    "Location",
    "Job",
    "Department",
    "Score",
    "Verdict",
    "Pipeline stage",
    "Decision",
    "Shortlisted",
    "Source",
    "Years experience",
    "Applied",
  ];
  const rows = candidates.map((c) => [
    c.name,
    c.email,
    c.phone,
    c.location,
    jobById.get(c.jobId)?.title ?? c.jobId,
    jobById.get(c.jobId)?.department ?? "",
    c.score,
    c.compareVerdict,
    c.pipelineStage,
    c.decision,
    c.shortlisted ? "Yes" : "No",
    c.source,
    c.yearsExp,
    c.appliedAt,
  ]);
  return [header, ...rows].map((r) => r.map(escapeCell).join(",")).join("\n");
}

export function downloadCsv(filename: string, csv: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
