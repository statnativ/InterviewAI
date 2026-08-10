import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { CheckCircle2 } from "lucide-react";

export function SessionCompleted() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const [answeredCount, setAnsweredCount] = useState<number | null>(null);

  // M4: mark the session complete server-side if the candidate navigated here before the
  // interviewer's own [INTERVIEW_COMPLETE] sentinel already did it (e.g. they closed the
  // recording mid-answer) — no-ops if already complete. Also pulls the real answered-turn
  // count instead of guessing from the interview's static question list, since a Voice
  // session can end with follow-ups that don't map 1:1 to Interview.questions.
  useEffect(() => {
    if (!interviewId) return;
    const cached = sessionStorage.getItem(`interview-session:${interviewId}`);
    if (!cached) return;
    const { sessionId } = JSON.parse(cached) as { sessionId: string };
    api
      .completeSession(sessionId)
      .then((info) => {
        setAnsweredCount(info.turns.filter((t) => t.transcript).length);
        sessionStorage.removeItem(`interview-session:${interviewId}`);
      })
      .catch(() => {
        // Best-effort — the candidate-facing "done" state doesn't hinge on this succeeding.
      });
  }, [interviewId]);

  return (
    <CandidateShell minimal>
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-status-strong-bg text-status-strong-text">
          <CheckCircle2 className="h-7 w-7" />
        </span>
        <h1 className="mt-4 text-2xl font-semibold text-neutral-900">
          You're all done!
        </h1>
        <p className="mt-2 text-neutral-500">
          Thanks for completing {interview?.title ?? "your interview"}. The
          hiring team will review your responses and follow up soon.
        </p>

        <Card className="mt-8 text-left">
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-neutral-500">Questions answered</span>
              <span className="font-medium text-neutral-900">
                {answeredCount ?? interview?.questions.length ?? 0}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Interview mode</span>
              <span className="font-medium text-neutral-900">{interview?.mode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Submitted</span>
              <span className="font-medium text-neutral-900">Just now</span>
            </div>
          </CardContent>
        </Card>

        <Button className="mt-8 w-full" size="lg" onClick={() => navigate("/candidate")}>
          Back to dashboard
        </Button>
      </div>
    </CandidateShell>
  );
}
