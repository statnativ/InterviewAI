import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { AddCandidateModal } from "./AddCandidateModal";
import { Sparkles, Users } from "lucide-react";
import type { JobStatus } from "@/data/types";
import { cn } from "@/lib/utils";

const tagTone: Record<string, "weak" | "info" | "possible"> = {
  "Must-have": "weak",
  "Nice-to-have": "info",
  Disqualifying: "possible",
};

export function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const getJob = useAppStore((s) => s.getJob);
  const candidates = useAppStore((s) => s.candidates);
  const updateJobStatus = useAppStore((s) => s.updateJobStatus);
  const generateRubric = useAppStore((s) => s.generateRubric);
  const saveJobVersion = useAppStore((s) => s.saveJobVersion);
  const job = getJob(jobId!);

  if (!job) return null;

  const totalWeight = job.rubric.reduce((sum, r) => sum + r.weight, 0);
  const candidateCount = candidates.filter((c) => c.jobId === job.id).length;

  const closeModal = () => {
    params.delete("add");
    setParams(params, { replace: true });
  };

  const statuses: JobStatus[] = ["Draft", "Open", "Paused", "Closed"];

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Jobs"
        title={job.title}
        actions={
          <Button onClick={() => navigate(`/jobs/${job.id}/candidates`)}>
            <Users className="h-4 w-4" /> View candidates
          </Button>
        }
      />

      <div className="flex-1 space-y-6 px-8 py-6">
        <Card>
          <CardContent className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">{job.title}</h2>
              <p className="text-sm text-neutral-500">
                {job.department} · {job.location} · {job.type}
              </p>
            </div>
            <div className="flex gap-2">
              {statuses.map((s) => (
                <button
                  key={s}
                  onClick={() => updateJobStatus(job.id, s)}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                    job.status === s
                      ? "border-brand-primary bg-brand-primary text-white"
                      : "border-neutral-300 text-neutral-600 hover:bg-neutral-50"
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <Card>
              <CardContent>
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      Evaluation Criteria
                    </h3>
                    <p className="text-xs text-neutral-500">
                      {job.rubric.length
                        ? "Rubric generated from the attached job description — weights auto-balanced to 100%."
                        : "No rubric generated yet — add a job description and regenerate."}
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!job.description.trim()}
                    onClick={() => generateRubric(job.id)}
                  >
                    <Sparkles className="h-3.5 w-3.5" /> Regenerate rubric
                  </Button>
                </div>
                {job.rubric.length > 0 && (
                  <p className="mb-3 text-right text-xs text-neutral-400">
                    Total weight: {totalWeight}%
                  </p>
                )}

                <div className="divide-y divide-neutral-100">
                  {job.rubric.map((c) => (
                    <div key={c.id} className="py-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-neutral-900">
                            {c.label}
                          </span>
                          <Badge tone={tagTone[c.tag]}>{c.tag}</Badge>
                          <Badge tone="neutral">{c.category}</Badge>
                        </div>
                        <span className="flex h-8 min-w-11 items-center justify-center rounded-md border border-neutral-300 px-2 text-sm font-semibold">
                          {c.weight}%
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-neutral-500">{c.description}</p>
                    </div>
                  ))}
                </div>
                {job.rubric.length === 0 && (
                  <p className="py-6 text-center text-sm text-neutral-400">
                    No criteria yet.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardContent>
                <h3 className="mb-3 text-sm font-semibold text-neutral-900">
                  Version History
                </h3>
                <div className="space-y-3">
                  {job.versions.map((v) => (
                    <div
                      key={v.version}
                      className={cn(
                        "rounded-md border p-3",
                        v.status === "Approved"
                          ? "border-status-strong-border bg-status-strong-bg/40"
                          : "border-neutral-200"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-neutral-900">
                          {v.label}
                        </span>
                        <Badge tone={v.status === "Approved" ? "strong" : "neutral"}>
                          {v.status.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-neutral-500">
                        {v.status === "Approved" ? `Approved by ${v.by}` : v.by} · {v.date}
                      </p>
                    </div>
                  ))}
                  {job.versions.length === 0 && (
                    <p className="text-sm text-neutral-400">No versions saved yet.</p>
                  )}
                </div>
                <Button
                  variant="secondary"
                  className="mt-3 w-full"
                  onClick={() => saveJobVersion(job.id)}
                >
                  Save as new version
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <h3 className="mb-1 text-sm font-semibold text-neutral-900">
                  Candidates
                </h3>
                <p className="text-2xl font-semibold text-neutral-900">
                  {candidateCount}
                </p>
                <Button
                  variant="secondary"
                  className="mt-3 w-full"
                  onClick={() => setParams({ add: "1" })}
                >
                  Add candidate
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <AddCandidateModal
        open={params.get("add") === "1"}
        onClose={closeModal}
        jobId={job.id}
      />
    </OrgAppShell>
  );
}
