import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { CheckCircle2 } from "lucide-react";

export function SessionCompleted() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));

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
                {interview?.questions.length ?? 0}
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
