import { useNavigate, useParams } from "react-router-dom";
import { useMemo } from "react";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { Printer, Sparkles } from "lucide-react";
import type { Candidate } from "@/data/types";
const verdictTone: Record<Candidate["compareVerdict"], "strong" | "possible" | "weak"> = {
  Advance: "strong",
  Maybe: "possible",
  Pass: "weak",
};

export function ComparativeReport() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const job = useAppStore((s) => s.jobs.find((j) => j.id === jobId));
  const allCandidates = useAppStore((s) => s.candidates);
  const ready = useAppStore((s) => s.ready);
  const candidates = useMemo(
    () =>
      allCandidates
        .filter((c) => c.jobId === jobId)
        .sort((a, b) => b.score - a.score)
        .filter((c) => c.scorecard.length > 0),
    [allCandidates, jobId]
  );

  if (!ready) {
    return (
      <OrgAppShell>
        <LoadingState label="Loading report…" />
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

  const top = candidates.slice(0, 2);

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb={`Jobs / ${job.title}`}
        title="Comparative report"
        actions={
          <>
            <Button variant="secondary" onClick={() => window.print()}>
              <Printer className="h-4 w-4" /> Print / PDF
            </Button>
            <Button
              onClick={() => {
                const el = document.getElementById("comparative-report");
                if (el) {
                  el.style.opacity = "0.4";
                  setTimeout(() => (el.style.opacity = "1"), 350);
                }
              }}
            >
              <Sparkles className="h-4 w-4" /> Regenerate
            </Button>
          </>
        }
      />

      <div id="comparative-report" className="flex-1 px-8 py-6 transition-opacity duration-300">
        <Card className="mb-5 border-brand-primary/20 bg-brand-primary-subtle/40">
          <CardContent>
            <h3 className="mb-1 text-sm font-semibold text-neutral-900">
              Panel summary
            </h3>
            <p className="text-sm text-neutral-700">
              {top.map((c) => c.name).join(" and ")} are the strongest fits for{" "}
              {job.title}, both showing deep distributed-systems experience and
              hands-on Kubernetes ownership.{" "}
              {candidates[2] && `${candidates[2].name} is a reasonable second-tier candidate but lacks production experience in a key area. `}
              Recommend advancing {top.map((c) => c.name.split(" ")[0]).join(" and ")} to
              the panel interview.
            </p>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {candidates.map((c, i) => (
            <button
              key={c.id}
              onClick={() => navigate(`/jobs/${job.id}/pipeline`)}
              className="block w-full text-left"
            >
              <Card className="transition-colors hover:border-brand-primary/40">
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-neutral-400">
                        #{i + 1}
                      </span>
                      <Avatar name={c.name} />
                      <span className="text-sm font-semibold text-neutral-900">
                        {c.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-neutral-700">
                        {c.score}/100
                      </span>
                      <Badge tone={verdictTone[c.compareVerdict]}>
                        {c.compareVerdict}
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-status-strong-text">
                        Strengths
                      </p>
                      <ul className="space-y-0.5 text-neutral-600">
                        {c.strengths.slice(0, 2).map((s, idx) => (
                          <li key={idx}>• {s}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-status-weak-text">
                        Concerns
                      </p>
                      <ul className="space-y-0.5 text-neutral-600">
                        {c.gaps.slice(0, 2).map((g, idx) => (
                          <li key={idx}>• {g}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
                        Evidence
                      </p>
                      <ul className="space-y-0.5 text-neutral-600">
                        <li>• {c.scorecard[0]?.note}</li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </button>
          ))}
        </div>
      </div>
    </OrgAppShell>
  );
}
