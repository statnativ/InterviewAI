import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";
import { ShareInterviewModal } from "./ShareInterviewModal";
import { Share2, Trash2, Plus, GripVertical } from "lucide-react";
import type { InterviewQuestion } from "@/data/types";

const difficultyTone: Record<InterviewQuestion["difficulty"], "strong" | "possible" | "weak"> = {
  Easy: "strong",
  Medium: "possible",
  Hard: "weak",
};

export function InterviewEditor() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const addQuestion = useAppStore((s) => s.addQuestion);
  const removeQuestion = useAppStore((s) => s.removeQuestion);
  const [draft, setDraft] = useState("");

  if (!interview) return null;

  const submitQuestion = () => {
    if (!draft.trim()) return;
    addQuestion(interview.id, { prompt: draft, type: "Technical", difficulty: "Medium" });
    setDraft("");
  };

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Interviews"
        title={interview.title}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate("/interviews")}>
              Done
            </Button>
            <Button onClick={() => setParams({ share: "1" })}>
              <Share2 className="h-4 w-4" /> Share
            </Button>
          </>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="mx-auto max-w-2xl space-y-4">
          <Card>
            <CardContent className="flex items-center justify-between text-sm text-neutral-500">
              <span>{interview.jobTitle}</span>
              <div className="flex items-center gap-2">
                <Badge tone="info">{interview.mode}</Badge>
                <span>{interview.duration} min</span>
              </div>
            </CardContent>
          </Card>

          {interview.questions.map((q, i) => (
            <Card key={q.id}>
              <CardContent className="flex items-start gap-3">
                <GripVertical className="mt-1 h-4 w-4 shrink-0 text-neutral-300" />
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-xs font-semibold text-neutral-400">
                      Q{i + 1}
                    </span>
                    <Badge tone="neutral">{q.type}</Badge>
                    <Badge tone={difficultyTone[q.difficulty]}>{q.difficulty}</Badge>
                  </div>
                  <p className="text-sm text-neutral-800">{q.prompt}</p>
                </div>
                <button
                  onClick={() => removeQuestion(interview.id, q.id)}
                  className="rounded-md p-1.5 text-neutral-400 hover:bg-status-weak-bg hover:text-status-weak-text"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardContent className="flex items-center gap-2">
              <Textarea
                rows={2}
                placeholder="Write a new question..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="flex-1"
              />
              <Button onClick={submitQuestion} disabled={!draft.trim()}>
                <Plus className="h-4 w-4" /> Add
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <ShareInterviewModal
        open={params.get("share") === "1"}
        onClose={() => {
          params.delete("share");
          setParams(params, { replace: true });
        }}
        interviewId={interview.id}
      />
    </OrgAppShell>
  );
}
