import { useNavigate } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/store/useAppStore";
import { Plus, MessageSquare, Mic, Video, Share2 } from "lucide-react";
import type { InterviewMode } from "@/data/types";

const modeIcon: Record<InterviewMode, typeof MessageSquare> = {
  Chat: MessageSquare,
  Voice: Mic,
  Avatar: Video,
};

const statusTone: Record<string, "strong" | "pending" | "neutral"> = {
  Active: "strong",
  Draft: "pending",
  Archived: "neutral",
};

export function InterviewsList() {
  const navigate = useNavigate();
  const interviews = useAppStore((s) => s.interviews);

  return (
    <OrgAppShell>
      <PageTopbar
        title="Interviews"
        actions={
          <Button onClick={() => navigate("/interviews/new")}>
            <Plus className="h-4 w-4" /> New interview
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="grid grid-cols-2 gap-4">
          {interviews.map((interview) => {
            const Icon = modeIcon[interview.mode];
            return (
              <Card
                key={interview.id}
                role="button"
                tabIndex={0}
                aria-label={`Edit ${interview.title}`}
                onClick={() => navigate(`/interviews/${interview.id}/edit`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    navigate(`/interviews/${interview.id}/edit`);
                  }
                }}
                className="cursor-pointer p-5 hover:border-brand-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-primary-subtle text-brand-primary">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-neutral-900">
                        {interview.title}
                      </p>
                      <p className="text-xs text-neutral-500">{interview.jobTitle}</p>
                    </div>
                  </div>
                  <Badge tone={statusTone[interview.status]}>{interview.status}</Badge>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs text-neutral-500">
                  <span>
                    {interview.questions.length} questions · {interview.duration} min
                  </span>
                  {interview.shared && (
                    <span className="flex items-center gap-1 text-brand-primary">
                      <Share2 className="h-3 w-3" /> Shared
                    </span>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </OrgAppShell>
  );
}
