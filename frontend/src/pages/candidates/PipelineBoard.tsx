import { useNavigate, useParams } from "react-router-dom";
import { useState } from "react";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Avatar } from "@/components/ui/Avatar";
import { ScorePill } from "@/components/ui/ScorePill";
import { useAppStore } from "@/store/useAppStore";
import type { PipelineStage } from "@/data/types";
import { cn } from "@/lib/utils";

const stages: PipelineStage[] = [
  "Applied",
  "Screening",
  "Interview",
  "Offer",
  "Rejected",
];

const stageDot: Record<PipelineStage, string> = {
  Applied: "bg-neutral-400",
  Screening: "bg-status-info-text",
  Interview: "bg-status-possible-text",
  Offer: "bg-status-strong-text",
  Rejected: "bg-status-weak-text",
};

export function PipelineBoard() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const getJob = useAppStore((s) => s.getJob);
  const getCandidatesForJob = useAppStore((s) => s.getCandidatesForJob);
  const movePipelineStage = useAppStore((s) => s.movePipelineStage);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<PipelineStage | null>(null);

  const job = getJob(jobId!);
  const candidates = getCandidatesForJob(jobId!);
  if (!job) return null;

  return (
    <OrgAppShell>
      <PageTopbar breadcrumb={`Jobs / ${job.title}`} title="Pipeline Board" />

      <div className="flex-1 overflow-x-auto px-8 py-6">
        <div className="flex min-w-max gap-4">
          {stages.map((stage) => {
            const items = candidates.filter((c) => c.pipelineStage === stage);
            return (
              <div
                key={stage}
                onDragOver={(e) => {
                  e.preventDefault();
                  setOverStage(stage);
                }}
                onDragLeave={() => setOverStage((s) => (s === stage ? null : s))}
                onDrop={() => {
                  if (dragId) movePipelineStage(dragId, stage);
                  setDragId(null);
                  setOverStage(null);
                }}
                className={cn(
                  "w-72 shrink-0 rounded-lg border border-neutral-200 bg-neutral-100/60 p-3 transition-colors",
                  overStage === stage && "border-brand-primary bg-brand-primary-subtle/50"
                )}
              >
                <div className="mb-3 flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <span className={cn("h-2 w-2 rounded-full", stageDot[stage])} />
                    <span className="text-sm font-semibold text-neutral-800">
                      {stage}
                    </span>
                  </div>
                  <span className="text-xs text-neutral-400">{items.length}</span>
                </div>

                <div className="space-y-2">
                  {items.map((c) => (
                    <div
                      key={c.id}
                      draggable
                      onDragStart={() => setDragId(c.id)}
                      onClick={() => navigate(`/jobs/${job.id}/candidates/${c.id}`)}
                      className="cursor-grab rounded-md border border-neutral-200 bg-white p-3 shadow-sm hover:border-brand-primary/40 active:cursor-grabbing"
                    >
                      <div className="flex items-center gap-2">
                        <Avatar name={c.name} size="sm" />
                        <span className="truncate text-sm font-medium text-neutral-900">
                          {c.name}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs text-neutral-500">
                          {c.currentTitle}
                        </span>
                        <ScorePill score={c.score} size="sm" />
                      </div>
                    </div>
                  ))}
                  {items.length === 0 && (
                    <p className="rounded-md border border-dashed border-neutral-300 py-6 text-center text-xs text-neutral-400">
                      Drop here
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </OrgAppShell>
  );
}
