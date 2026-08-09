import { useNavigate } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAppStore } from "@/store/useAppStore";
import { formatRelativeTime } from "@/lib/utils";
import { Plus, UserPlus, FileText, CheckCircle2, Sparkles, UserCheck } from "lucide-react";

const activity = [
  { icon: CheckCircle2, text: "Maria Chen was shortlisted for Senior Backend Engineer", time: "2026-08-08T15:00:00Z" },
  { icon: UserPlus, text: "New candidate added to Product Designer", time: "2026-08-08T12:00:00Z" },
  { icon: Sparkles, text: "Rubric approved for Staff SRE — Version 2", time: "2026-08-07T10:00:00Z" },
  { icon: FileText, text: "Job description updated for Marketing Manager", time: "2026-08-06T09:00:00Z" },
  { icon: UserCheck, text: "David Kim completed his interview", time: "2026-08-05T09:00:00Z" },
];

export function Dashboard() {
  const navigate = useNavigate();
  const jobs = useAppStore((s) => s.jobs);
  const candidates = useAppStore((s) => s.candidates);
  const currentUser = useAppStore((s) => s.currentUser);

  const openJobs = jobs.filter((j) => j.status === "Open").length;
  const shortlisted = candidates.filter((c) => c.shortlisted).length;
  const avgScore = Math.round(
    candidates.reduce((sum, c) => sum + c.score, 0) / (candidates.length || 1)
  );

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Statnativ"
        title="Dashboard"
        actions={
          <Button onClick={() => navigate("/jobs?new=1")}>
            <Plus className="h-4 w-4" /> New job
          </Button>
        }
      />

      <div className="flex-1 space-y-6 px-8 py-6">
        <div>
          <h2 className="text-2xl font-semibold text-neutral-900">
            Good morning, {currentUser.name.split(" ")[0]} 👋
          </h2>
          <p className="mt-1 text-neutral-500">
            Here's what's happening across your hiring pipeline today.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent>
              <p className="text-sm text-neutral-500">Open jobs</p>
              <p className="mt-1 text-3xl font-semibold text-neutral-900">{openJobs}</p>
              <p className="mt-1 text-xs text-neutral-400">2 opened this month</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-neutral-500">Total candidates</p>
              <p className="mt-1 text-3xl font-semibold text-neutral-900">{candidates.length}</p>
              <p className="mt-1 text-xs text-status-strong-text">↑ +12 this week</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-neutral-500">Avg. screening score</p>
              <p className="mt-1 text-3xl font-semibold text-neutral-900">{avgScore}</p>
              <p className="mt-1 text-xs text-status-strong-text">↑ +5 vs last month</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-neutral-500">Shortlisted</p>
              <p className="mt-1 text-3xl font-semibold text-neutral-900">{shortlisted}</p>
              <p className="mt-1 text-xs text-neutral-400">Awaiting interview</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <Card>
              <CardContent>
                <h3 className="mb-3 text-sm font-semibold text-neutral-900">Quick actions</h3>
                <div className="grid grid-cols-3 gap-3">
                  <Button onClick={() => navigate("/jobs?new=1")} className="justify-center">
                    <Plus className="h-4 w-4" /> New job
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => navigate(`/jobs/${jobs[0].id}?add=1`)}
                    className="justify-center"
                  >
                    <UserPlus className="h-4 w-4" /> Add candidate
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => navigate(`/jobs/${jobs[0].id}/compare`)}
                    className="justify-center"
                  >
                    Generate report
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-neutral-900">Your jobs</h3>
                  <button
                    onClick={() => navigate("/jobs")}
                    className="text-sm font-medium text-brand-primary hover:underline"
                  >
                    View all →
                  </button>
                </div>
                <div className="divide-y divide-neutral-100">
                  {jobs.slice(0, 3).map((job) => (
                    <button
                      key={job.id}
                      onClick={() => navigate(`/jobs/${job.id}`)}
                      className="flex w-full items-center justify-between py-3 text-left hover:bg-neutral-50"
                    >
                      <span className="text-sm font-medium text-neutral-900">{job.title}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-neutral-500">
                          {candidates.filter((c) => c.jobId === job.id).length} candidates
                        </span>
                        <Badge
                          tone={
                            job.status === "Open"
                              ? "strong"
                              : job.status === "Closed"
                              ? "neutral"
                              : job.status === "Draft"
                              ? "pending"
                              : "possible"
                          }
                        >
                          {job.status}
                        </Badge>
                      </div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="h-fit">
            <CardContent>
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Recent activity</h3>
              <ul className="space-y-4">
                {activity.map((item, i) => (
                  <li key={i} className="flex gap-3">
                    <item.icon className="mt-0.5 h-4 w-4 shrink-0 text-brand-primary" />
                    <div>
                      <p className="text-sm text-neutral-800">{item.text}</p>
                      <p className="text-xs text-neutral-400">
                        {formatRelativeTime(item.time)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </OrgAppShell>
  );
}
