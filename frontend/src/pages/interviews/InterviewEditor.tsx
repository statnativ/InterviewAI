import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { ScorePill } from "@/components/ui/ScorePill";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { ShareInterviewModal } from "./ShareInterviewModal";
import { Share2, Trash2, Plus, GripVertical, Pencil, RefreshCw, Sparkles, User } from "lucide-react";
import type { InterviewQuestion, InterviewSessionSummary } from "@/data/types";
import { cn } from "@/lib/utils";

const difficultyTone: Record<InterviewQuestion["difficulty"], "strong" | "possible" | "weak"> = {
  Easy: "strong",
  Medium: "possible",
  Hard: "weak",
};

const QUESTION_TYPES: InterviewQuestion["type"][] = ["Technical", "Behavioral", "System Design", "Culture"];
const DIFFICULTIES: InterviewQuestion["difficulty"][] = ["Easy", "Medium", "Hard"];

const selectClass =
  "h-9 rounded-md border border-neutral-300 bg-white px-2 text-xs text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30";

export function InterviewEditor() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const ready = useAppStore((s) => s.ready);
  const addQuestion = useAppStore((s) => s.addQuestion);
  const removeQuestion = useAppStore((s) => s.removeQuestion);
  const updateQuestion = useAppStore((s) => s.updateQuestion);
  const reorderQuestions = useAppStore((s) => s.reorderQuestions);
  const regenerateQuestions = useAppStore((s) => s.regenerateQuestions);
  const regenerateQuestion = useAppStore((s) => s.regenerateQuestion);

  const [draft, setDraft] = useState("");
  const [draftType, setDraftType] = useState<InterviewQuestion["type"]>("Technical");
  const [draftDifficulty, setDraftDifficulty] = useState<InterviewQuestion["difficulty"]>("Medium");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPrompt, setEditPrompt] = useState("");
  const [editType, setEditType] = useState<InterviewQuestion["type"]>("Technical");
  const [editDifficulty, setEditDifficulty] = useState<InterviewQuestion["difficulty"]>("Medium");

  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [regeneratingAll, setRegeneratingAll] = useState(false);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  // M5: sessions aren't part of the global store (no other page reads them, unlike
  // jobs/candidates/interviews) — fetched locally, same precedent the admin module's
  // pages use for page-scoped data. Only Voice/Video interviews ever have sessions.
  const [sessions, setSessions] = useState<InterviewSessionSummary[] | null>(null);
  useEffect(() => {
    if (!interview || (interview.mode !== "Voice" && interview.mode !== "Video")) return;
    api
      .listInterviewSessions(interview.id)
      .then(setSessions)
      .catch(() => setSessions([]));
  }, [interview?.id, interview?.mode]);

  if (!ready) {
    return (
      <OrgAppShell>
        <LoadingState label="Loading interview…" />
      </OrgAppShell>
    );
  }

  if (!interview) {
    return (
      <OrgAppShell>
        <NotFoundState
          message="This interview doesn't exist or may have been removed."
          backLabel="Back to interviews"
          onBack={() => navigate("/interviews")}
        />
      </OrgAppShell>
    );
  }

  const submitQuestion = () => {
    if (!draft.trim()) return;
    addQuestion(interview.id, { prompt: draft, type: draftType, difficulty: draftDifficulty });
    setDraft("");
    setDraftType("Technical");
    setDraftDifficulty("Medium");
  };

  const startEdit = (q: InterviewQuestion) => {
    setEditingId(q.id);
    setEditPrompt(q.prompt);
    setEditType(q.type);
    setEditDifficulty(q.difficulty);
  };

  const saveEdit = async () => {
    if (!editingId || !editPrompt.trim()) return;
    await updateQuestion(interview.id, editingId, {
      prompt: editPrompt,
      type: editType,
      difficulty: editDifficulty,
    });
    setEditingId(null);
  };

  const handleRegenerateOne = async (questionId: string) => {
    setRegeneratingId(questionId);
    try {
      await regenerateQuestion(interview.id, questionId);
    } finally {
      setRegeneratingId(null);
    }
  };

  const handleRegenerateAll = async () => {
    setRegeneratingAll(true);
    try {
      await regenerateQuestions(interview.id);
    } finally {
      setRegeneratingAll(false);
    }
  };

  const handleDrop = (targetId: string) => {
    if (!dragId || dragId === targetId) {
      setDragId(null);
      setOverId(null);
      return;
    }
    const questions = [...interview.questions];
    const fromIdx = questions.findIndex((q) => q.id === dragId);
    const toIdx = questions.findIndex((q) => q.id === targetId);
    if (fromIdx === -1 || toIdx === -1) return;
    const [moved] = questions.splice(fromIdx, 1);
    questions.splice(toIdx, 0, moved);
    reorderQuestions(interview.id, questions);
    setDragId(null);
    setOverId(null);
  };

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Interviews"
        title={interview.title}
        actions={
          <>
            <Button
              variant="secondary"
              onClick={handleRegenerateAll}
              disabled={!interview.jobId || regeneratingAll}
              title={!interview.jobId ? "This interview has no linked job to regenerate from" : undefined}
            >
              <Sparkles className="h-4 w-4" />
              {regeneratingAll ? "Regenerating…" : "Regenerate all"}
            </Button>
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
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between text-sm text-neutral-500">
                <span>{interview.jobTitle}</span>
                <div className="flex items-center gap-2">
                  <Badge tone="info">{interview.mode}</Badge>
                  <span>{interview.duration} min</span>
                </div>
              </div>
              {interview.candidateName && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-brand-primary">
                  <User className="h-3.5 w-3.5" />
                  Personalized for {interview.candidateName}
                </div>
              )}
            </CardContent>
          </Card>

          {interview.questions.map((q, i) => (
            <Card
              key={q.id}
              draggable={editingId !== q.id}
              onDragStart={() => setDragId(q.id)}
              onDragOver={(e) => {
                e.preventDefault();
                setOverId(q.id);
              }}
              onDragLeave={() => setOverId((s) => (s === q.id ? null : s))}
              onDrop={() => handleDrop(q.id)}
              className={cn(overId === q.id && dragId !== q.id && "border-brand-primary bg-brand-primary-subtle/30")}
            >
              <CardContent className="flex items-start gap-3">
                <GripVertical className="mt-1 h-4 w-4 shrink-0 cursor-grab text-neutral-300 active:cursor-grabbing" />
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-xs font-semibold text-neutral-400">Q{i + 1}</span>
                    {editingId === q.id ? (
                      <>
                        <select
                          value={editType}
                          onChange={(e) => setEditType(e.target.value as InterviewQuestion["type"])}
                          className={selectClass}
                        >
                          {QUESTION_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                        <select
                          value={editDifficulty}
                          onChange={(e) => setEditDifficulty(e.target.value as InterviewQuestion["difficulty"])}
                          className={selectClass}
                        >
                          {DIFFICULTIES.map((d) => (
                            <option key={d} value={d}>
                              {d}
                            </option>
                          ))}
                        </select>
                      </>
                    ) : (
                      <>
                        <Badge tone="neutral">{q.type}</Badge>
                        <Badge tone={difficultyTone[q.difficulty]}>{q.difficulty}</Badge>
                      </>
                    )}
                  </div>

                  {editingId === q.id ? (
                    <div className="space-y-2">
                      <Textarea
                        rows={3}
                        value={editPrompt}
                        onChange={(e) => setEditPrompt(e.target.value)}
                        autoFocus
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" onClick={saveEdit} disabled={!editPrompt.trim()}>
                          Save
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => setEditingId(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-800">{q.prompt}</p>
                  )}
                </div>

                {editingId !== q.id && (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() => handleRegenerateOne(q.id)}
                      disabled={!interview.jobId || regeneratingId === q.id}
                      title={!interview.jobId ? "This interview has no linked job to regenerate from" : "Regenerate this question"}
                      className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 disabled:opacity-40"
                    >
                      <RefreshCw className={cn("h-4 w-4", regeneratingId === q.id && "animate-spin")} />
                    </button>
                    <button
                      onClick={() => startEdit(q)}
                      className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => removeQuestion(interview.id, q.id)}
                      className="rounded-md p-1.5 text-neutral-400 hover:bg-status-weak-bg hover:text-status-weak-text"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardContent className="space-y-2">
              <Textarea
                rows={2}
                placeholder="Write a new question..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <select value={draftType} onChange={(e) => setDraftType(e.target.value as InterviewQuestion["type"])} className={selectClass}>
                  {QUESTION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <select
                  value={draftDifficulty}
                  onChange={(e) => setDraftDifficulty(e.target.value as InterviewQuestion["difficulty"])}
                  className={selectClass}
                >
                  {DIFFICULTIES.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
                <Button onClick={submitQuestion} disabled={!draft.trim()} className="ml-auto">
                  <Plus className="h-4 w-4" /> Add
                </Button>
              </div>
            </CardContent>
          </Card>

          {(interview.mode === "Voice" || interview.mode === "Video") && (
            <Card>
              <CardContent>
                <h3 className="mb-3 text-sm font-semibold text-neutral-900">Sessions</h3>
                {sessions === null && <p className="text-sm text-neutral-400">Loading sessions…</p>}
                {sessions !== null && sessions.length === 0 && (
                  <p className="text-sm text-neutral-400">No candidate has taken this interview yet.</p>
                )}
                <div className="space-y-2">
                  {sessions?.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => navigate(`/interviews/${interview.id}/report/${s.id}`)}
                      className="flex w-full items-center justify-between rounded-md border border-neutral-200 px-3 py-2 text-left hover:border-brand-primary/40 hover:bg-brand-primary-subtle/20"
                    >
                      <span className="text-sm font-medium text-neutral-800">
                        {s.candidateName ?? "Unnamed candidate"}
                      </span>
                      <span className="flex items-center gap-2">
                        <Badge tone={s.status === "complete" ? "strong" : "pending"}>{s.status}</Badge>
                        {s.evaluationStatus === "pending" && <Badge tone="pending">Evaluating…</Badge>}
                        {s.evaluationStatus === "failed" && <Badge tone="weak">Failed</Badge>}
                        {s.decision !== "None" && <Badge tone="brand">{s.decision}</Badge>}
                        {s.score !== null && <ScorePill score={s.score} size="sm" />}
                      </span>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
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
