import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { ShieldCheck } from "lucide-react";

const items = [
  "I consent to this session being recorded (audio and screen) for evaluation purposes.",
  "I understand my responses will be evaluated with AI assistance alongside human review.",
  "I agree to the platform's Terms of Service and Candidate Privacy Policy.",
  "I will complete this interview independently, without outside assistance.",
];

export function OnboardingConsent() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const [checked, setChecked] = useState<boolean[]>(items.map(() => false));

  const allChecked = checked.every(Boolean);

  return (
    <CandidateShell minimal>
      <div className="mx-auto max-w-lg px-6 py-14">
        <div className="mb-6 flex justify-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-primary-subtle text-brand-primary">
            <ShieldCheck className="h-6 w-6" />
          </span>
        </div>
        <h1 className="text-center text-2xl font-semibold text-neutral-900">
          Before we begin
        </h1>
        <p className="mt-1 text-center text-sm text-neutral-500">
          {interview?.title ?? "Interview session"} · please review and accept
          to continue.
        </p>

        <Card className="mt-8">
          <CardContent className="space-y-4">
            {items.map((item, i) => (
              <label key={i} className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={checked[i]}
                  onChange={() =>
                    setChecked((c) => c.map((v, idx) => (idx === i ? !v : v)))
                  }
                  className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-brand-primary focus:ring-brand-primary/40"
                />
                <span className="text-sm text-neutral-700">{item}</span>
              </label>
            ))}
          </CardContent>
        </Card>

        <Button
          className="mt-6 w-full"
          size="lg"
          disabled={!allChecked}
          onClick={() => navigate(`/session/${interviewId}/device`)}
        >
          I agree, continue
        </Button>
      </div>
    </CandidateShell>
  );
}
