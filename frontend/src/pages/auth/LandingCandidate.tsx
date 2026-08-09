import { useNavigate } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAppStore } from "@/store/useAppStore";
import { CalendarClock, Sparkles, ArrowRight } from "lucide-react";

export function LandingCandidate() {
  const navigate = useNavigate();
  const candidate = useAppStore((s) => s.currentCandidate);
  const interviews = useAppStore((s) => s.interviews);
  const activeInterviews = interviews.filter((i) => i.status === "Active");
  const practice = activeInterviews[0] ?? interviews[0];

  return (
    <CandidateShell>
      <div className="mx-auto max-w-4xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-neutral-900">
          Welcome back, {candidate.name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-neutral-500">
          Here's what's next in your interview process.
        </p>

        <div className="mt-8 grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <Card>
              <CardContent>
                <div className="mb-3 flex items-center gap-2">
                  <CalendarClock className="h-4 w-4 text-brand-primary" />
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Upcoming interviews
                  </h3>
                </div>
                <div className="space-y-3">
                  {activeInterviews.slice(0, 2).map((interview) => (
                    <div
                      key={interview.id}
                      className="flex items-center justify-between rounded-md border border-neutral-200 p-4"
                    >
                      <div>
                        <p className="text-sm font-medium text-neutral-900">
                          {interview.title}
                        </p>
                        <p className="text-xs text-neutral-500">
                          {interview.jobTitle} · {interview.duration} min · {interview.mode}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() =>
                          navigate(
                            interview.mode === "Avatar"
                              ? `/avatar/${interview.id}/disclosure`
                              : `/session/${interview.id}/consent`
                          )
                        }
                      >
                        Start <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                  {activeInterviews.length === 0 && (
                    <p className="py-4 text-center text-sm text-neutral-400">
                      No upcoming interviews right now.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-brand-primary" />
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Continue practicing
                  </h3>
                </div>
                <p className="text-sm text-neutral-500">
                  Run a mock interview to sharpen your answers before the real thing.
                </p>
                <Button
                  variant="secondary"
                  className="mt-3"
                  onClick={() =>
                    practice && navigate(`/session/${practice.id}/chat`)
                  }
                  disabled={!practice}
                >
                  Start a practice session
                </Button>
              </CardContent>
            </Card>
          </div>

          <Card className="h-fit">
            <CardContent>
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">
                Your applications
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-neutral-800">Senior Backend Engineer</span>
                  <Badge tone="info">In review</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-neutral-800">Staff SRE</span>
                  <Badge tone="neutral">Closed</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </CandidateShell>
  );
}
