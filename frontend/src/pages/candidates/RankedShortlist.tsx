import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { ScorePill } from "@/components/ui/ScorePill";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { FilterBar, BulkToolbar, defaultFilters } from "@/components/candidates/CandidateToolbar";
import { filterCandidates, type CandidateFilters } from "@/lib/candidates";
import { candidatesToCsv, downloadCsv } from "@/lib/export";
import { UserPlus, FileBarChart, Columns3, Download } from "lucide-react";
import { canWrite } from "@/lib/utils";

export function RankedShortlist() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const job = useAppStore((s) => s.jobs.find((j) => j.id === jobId));
  const allCandidates = useAppStore((s) => s.candidates);
  const currentUser = useAppStore((s) => s.currentUser);
  const ready = useAppStore((s) => s.ready);
  const jobCandidates = useMemo(
    () =>
      allCandidates
        .filter((c) => c.jobId === jobId)
        .sort((a, b) => b.score - a.score),
    [allCandidates, jobId]
  );
  const bulkToggleShortlist = useAppStore((s) => s.bulkToggleShortlist);
  const bulkSetDecision = useAppStore((s) => s.bulkSetDecision);
  const bulkMoveStage = useAppStore((s) => s.bulkMoveStage);
  const [filters, setFilters] = useState<CandidateFilters>(defaultFilters);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const rows = useMemo(
    () => filterCandidates(jobCandidates, filters),
    [jobCandidates, filters]
  );

  if (!ready) {
    return (
      <OrgAppShell>
        <LoadingState label="Loading candidates…" />
      </OrgAppShell>
    );
  }

  if (!job) {
    return (
      <OrgAppShell>
        <NotFoundState
          message="This job doesn't exist or may have been removed."
          backLabel="Back to jobs"
          onBack={() => navigate("/jobs")}
        />
      </OrgAppShell>
    );
  }

  const toggleAll = () =>
    setSelected((prev) =>
      prev.size === rows.length ? new Set() : new Set(rows.map((c) => c.id))
    );

  const toggleOne = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const selectedCandidates = rows.filter((c) => selected.has(c.id));

  const exportCsv = () =>
    downloadCsv(
      `${job.id}-candidates-${new Date().toISOString().slice(0, 10)}.csv`,
      candidatesToCsv(rows, new Map([[job.id, job]]))
    );

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb={`Jobs / ${job.title}`}
        title="Candidates"
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate(`/jobs/${job.id}/pipeline`)}>
              <Columns3 className="h-4 w-4" /> Pipeline
            </Button>
            <Button variant="secondary" onClick={() => navigate(`/jobs/${job.id}/compare`)}>
              <FileBarChart className="h-4 w-4" /> Compare
            </Button>
            {canWrite(currentUser.role) && (
              <Button onClick={() => navigate(`/jobs/${job.id}?add=1`)}>
                <UserPlus className="h-4 w-4" /> Add candidate
              </Button>
            )}
          </>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <FilterBar filters={filters} onChange={setFilters} />
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-neutral-500">
              <input
                type="checkbox"
                checked={rows.length > 0 && selected.size === rows.length}
                onChange={toggleAll}
                className="h-4 w-4 rounded border-neutral-300 text-brand-primary focus:ring-brand-primary/30"
              />
              Select all
            </label>
            <p className="text-sm text-neutral-500">
              {rows.length} candidates · ranked by score
            </p>
            <Button variant="secondary" onClick={exportCsv} disabled={rows.length === 0}>
              <Download className="h-4 w-4" /> Export
            </Button>
          </div>
        </div>

        {canWrite(currentUser.role) && (
          <BulkToolbar
            selectedIds={[...selected]}
            selectedCandidates={selectedCandidates}
            onShortlist={() => bulkToggleShortlist([...selected])}
            onDecision={(d) => bulkSetDecision([...selected], d)}
            onStage={(s) => bulkMoveStage([...selected], s)}
            onClear={() => setSelected(new Set())}
          />
        )}

        <Card className="divide-y divide-neutral-100 overflow-hidden">
          {rows.map((c) => (
            <div key={c.id} className="flex w-full items-center gap-4 px-5 py-4 hover:bg-neutral-50">
              <input
                type="checkbox"
                checked={selected.has(c.id)}
                onChange={() => toggleOne(c.id)}
                className="h-4 w-4 shrink-0 rounded border-neutral-300 text-brand-primary focus:ring-brand-primary/30"
              />
              <button
                onClick={() => navigate(`/jobs/${job.id}/candidates/${c.id}`)}
                aria-label={`Open ${c.name}'s profile`}
                className="flex flex-1 items-center gap-4 text-left"
              >
                <ScorePill score={c.score} size="sm" />
                <Avatar name={c.name} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-neutral-900">{c.name}</span>
                    {c.shortlisted && <Badge tone="brand">Shortlisted</Badge>}
                    {c.decision !== "None" && (
                      <Badge
                        tone={
                          c.decision === "Approved"
                            ? "strong"
                            : c.decision === "Rejected"
                            ? "weak"
                            : "possible"
                        }
                      >
                        {c.decision}
                      </Badge>
                    )}
                    <Badge tone="pending">{c.pipelineStage}</Badge>
                  </div>
                  <p className="truncate text-xs text-neutral-500">
                    {c.email} · {c.yearsExp} yrs experience
                  </p>
                </div>
                <div className="hidden max-w-xs flex-wrap justify-end gap-1 md:flex">
                  {c.skills.slice(0, 3).map((s) => (
                    <Badge key={s} tone="neutral">
                      {s}
                    </Badge>
                  ))}
                </div>
              </button>
            </div>
          ))}
          {rows.length === 0 && (
            <p className="py-10 text-center text-sm text-neutral-400">
              No candidates match your filters.
            </p>
          )}
        </Card>
      </div>
    </OrgAppShell>
  );
}
