import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { Bot } from "lucide-react";

export function AIDisclosure() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));

  return (
    <CandidateShell minimal>
      <div className="mx-auto max-w-lg px-6 py-14">
        <div className="mb-6 flex justify-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-primary-subtle text-brand-primary">
            <Bot className="h-6 w-6" />
          </span>
        </div>
        <h1 className="text-center text-2xl font-semibold text-neutral-900">
          You'll be interviewed by an AI
        </h1>
        <p className="mt-1 text-center text-sm text-neutral-500">
          {interview?.title ?? "This interview"} uses an AI-generated avatar
          interviewer, not a live human.
        </p>

        <Card className="mt-8">
          <CardContent className="space-y-3 text-sm text-neutral-700">
            <p>
              The interviewer you'll see and hear is an AI-generated persona.
              It will ask questions, listen to your spoken responses, and
              adapt follow-ups based on what you say.
            </p>
            <p>
              Your video, audio, and responses will be recorded and evaluated
              by both AI and a human reviewer on the hiring team.
            </p>
            <p>
              You can request a human-led interview instead at any time by
              contacting the hiring team.
            </p>
          </CardContent>
        </Card>

        <Button
          className="mt-6 w-full"
          size="lg"
          onClick={() => navigate(`/avatar/${interviewId}/interview`)}
        >
          I understand, continue
        </Button>
      </div>
    </CandidateShell>
  );
}
