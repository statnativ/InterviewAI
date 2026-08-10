import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ScorePill, scoreTone } from "@/components/ui/ScorePill";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { canWrite, cn } from "@/lib/utils";
import { Pause, Play, RefreshCw, ThumbsDown, ThumbsUp, Sparkles } from "lucide-react";
import type { InterviewReport as InterviewReportType } from "@/data/types";

type Playing = { key: string; url: string; kind: "audio" | "video" } | null;

export function InterviewReport() {
  const { interviewId, sessionId } = useParams();
  const navigate = useNavigate();
  const currentUser = useAppStore((s) => s.currentUser);
  const editable = canWrite(currentUser.role);

  const [report, setReport] = useState<InterviewReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [playing, setPlaying] = useState<Playing>(null);
  const playingUrl = useRef<string | null>(null);

  const fetchReport = async () => {
    if (!sessionId) return;
    try {
      const data = await api.getInterviewReport(sessionId);
      setReport(data);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Same 2s-interval, ~30-attempt-cap pattern CandidateDetail.tsx uses for judgeStatus.
  useEffect(() => {
    if (!report || report.evaluationStatus !== "pending") return;
    let attempts = 0;
    const maxAttempts = 30;
    const id = setInterval(() => {
      attempts += 1;
      if (attempts > maxAttempts) {
        clearInterval(id);
        return;
      }
      void fetchReport();
    }, 2000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report?.evaluationStatus, sessionId]);

  // Revoke whatever blob URL is currently held whenever it changes or the page unmounts —
  // a recruiter scrubbing through several turns would otherwise leak one blob per play.
  useEffect(() => {
    return () => {
      if (playingUrl.current) URL.revokeObjectURL(playingUrl.current);
    };
  }, []);

  if (loading) {
    return (
      <OrgAppShell>
        <LoadingState label="Loading interview report…" />
      </OrgAppShell>
    );
  }

  if (notFound || !report || !sessionId) {
    return (
      <OrgAppShell>
        <NotFoundState
          message="This interview session doesn't exist or may have been removed."
          backLabel="Back to interview"
          onBack={() => navigate(`/interviews/${interviewId}/edit`)}
        />
      </OrgAppShell>
    );
  }

  const setDecision = async (decision: InterviewReportType["decision"]) => {
    setActionError(null);
    try {
      const updated = await api.setSessionDecision(sessionId, decision);
      setReport(updated);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Failed to set decision");
    }
  };

  const retryEvaluation = async () => {
    setActionError(null);
    setRetrying(true);
    try {
      const updated = await api.retryEvaluation(sessionId);
      setReport(updated);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Failed to retry evaluation");
    } finally {
      setRetrying(false);
    }
  };

  const play = async (key: string, turnIndex: number, speaker: "candidate" | "ai", kind: "audio" | "video") => {
    if (playing?.key === key) {
      if (playingUrl.current) URL.revokeObjectURL(playingUrl.current);
      playingUrl.current = null;
      setPlaying(null);
      return;
    }
    setActionError(null);
    try {
      const blob = await api.fetchInterviewMedia(sessionId, turnIndex, speaker);
      if (playingUrl.current) URL.revokeObjectURL(playingUrl.current);
      const url = URL.createObjectURL(blob);
      playingUrl.current = url;
      setPlaying({ key, url, kind });
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Couldn't load that recording");
    }
  };

  return (
    <OrgAppShell>
      <PageTopbar
        breadcrumb="Interviews"
        title={report.candidateName ?? "Interview session"}
        actions={
          <Button variant="secondary" onClick={() => navigate(`/interviews/${interviewId}/edit`)}>
            Back to interview
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="mb-6 flex items-center gap-4">
          {report.score !== null ? <ScorePill score={report.score} /> : <Badge tone="neutral">Not scored</Badge>}
          <div>
            <h2 className="text-base font-semibold text-neutral-900">
              {report.candidateName ?? "Unnamed candidate"}
            </h2>
            <div className="mt-1 flex items-center gap-2 text-sm text-neutral-500">
              <Badge tone={report.status === "complete" ? "strong" : "pending"}>{report.status}</Badge>
              {report.evaluationStatus === "pending" && <Badge tone="pending">Evaluating…</Badge>}
              {report.evaluationStatus === "idle" && <Badge tone="neutral">Not evaluated yet</Badge>}
              {report.evaluationStatus === "failed" && <Badge tone="weak">Evaluation failed</Badge>}
              {report.aiVerdict && <Badge tone="brand">{report.aiVerdict}</Badge>}
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant={report.decision === "Approved" ? "primary" : "secondary"}
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision("Approved")}
            >
              <ThumbsUp className="h-3.5 w-3.5" /> Approve
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision("Hold")}
            >
              Hold
            </Button>
            <Button
              variant={report.decision === "Rejected" ? "danger" : "secondary"}
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision("Rejected")}
            >
              <ThumbsDown className="h-3.5 w-3.5" /> Reject
            </Button>
            {report.evaluationStatus === "failed" && (
              <Button variant="secondary" size="sm" disabled={!editable || retrying} onClick={retryEvaluation}>
                <RefreshCw className={cn("h-3.5 w-3.5", retrying && "animate-spin")} />
                {retrying ? "Retrying…" : "Retry evaluation"}
              </Button>
            )}
          </div>
        </div>

        {(actionError || (report.evaluationStatus === "failed" && report.evaluationError)) && (
          <p className="mb-4 rounded-md border border-status-weak-border bg-status-weak-bg px-4 py-2 text-sm text-status-weak-text">
            {actionError ?? report.evaluationError}
          </p>
        )}

        <div className="grid grid-cols-2 gap-6">
          <Card>
            <CardContent>
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Transcript</h3>
              <div className="space-y-4">
                {report.turns.map((turn) => (
                  <div key={turn.turnIndex} className="border-b border-neutral-100 pb-3 last:border-0">
                    <div className="mb-1 flex items-center justify-between">
                      <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
                        Turn {turn.turnIndex}
                      </p>
                      {turn.aiText && (
                        <button
                          onClick={() => play(`${turn.turnIndex}-ai`, turn.turnIndex, "ai", "audio")}
                          className="inline-flex items-center gap-1 text-xs font-medium text-brand-primary hover:text-brand-primary/80"
                        >
                          {playing?.key === `${turn.turnIndex}-ai` ? (
                            <Pause className="h-3 w-3" />
                          ) : (
                            <Play className="h-3 w-3" />
                          )}
                          Question
                        </button>
                      )}
                    </div>
                    {turn.aiText && <p className="mb-1.5 text-sm text-neutral-700">{turn.aiText}</p>}
                    {playing?.key === `${turn.turnIndex}-ai` && (
                      <audio className="mb-2 w-full" src={playing.url} autoPlay controls />
                    )}
                    {turn.transcript && (
                      <>
                        <div className="mb-1 flex items-center justify-between">
                          <span className="text-xs font-medium text-neutral-400">Candidate</span>
                          <button
                            onClick={() =>
                              play(`${turn.turnIndex}-candidate`, turn.turnIndex, "candidate", turn.mediaType)
                            }
                            className="inline-flex items-center gap-1 text-xs font-medium text-brand-primary hover:text-brand-primary/80"
                          >
                            {playing?.key === `${turn.turnIndex}-candidate` ? (
                              <Pause className="h-3 w-3" />
                            ) : (
                              <Play className="h-3 w-3" />
                            )}
                            {turn.mediaType === "video" ? "Watch answer" : "Play answer"}
                          </button>
                        </div>
                        <p className="text-sm text-neutral-800">{turn.transcript}</p>
                        {playing?.key === `${turn.turnIndex}-candidate` &&
                          (playing.kind === "video" ? (
                            <video className="mt-2 w-full rounded-md" src={playing.url} autoPlay controls />
                          ) : (
                            <audio className="mt-2 w-full" src={playing.url} autoPlay controls />
                          ))}
                      </>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <h3 className="mb-3 text-sm font-semibold text-neutral-900">Evaluation</h3>
              <div className="space-y-3">
                {report.scorecard.map((row) => {
                  const tone = scoreTone(row.score);
                  return (
                    <div key={row.criterion}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-neutral-800">{row.criterion}</span>
                        <span className="text-xs text-neutral-400">
                          w{row.weight}% · {row.score}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            tone === "strong" && "bg-status-strong-text",
                            tone === "possible" && "bg-status-possible-text",
                            tone === "weak" && "bg-status-weak-text"
                          )}
                          style={{ width: `${row.score}%` }}
                        />
                      </div>
                      <p className="mt-1 text-xs text-neutral-500">{row.note}</p>
                    </div>
                  );
                })}
                {report.scorecard.length === 0 && (
                  <p className="text-sm text-neutral-400">
                    {report.evaluationStatus === "pending"
                      ? "Evaluating the transcript…"
                      : "No evaluation yet."}
                  </p>
                )}
              </div>

              {report.strengths.length > 0 && (
                <div className="mt-5">
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-status-strong-text">
                    Strengths
                  </p>
                  <ul className="space-y-1 text-sm text-neutral-700">
                    {report.strengths.map((s, i) => (
                      <li key={i}>• {s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {report.gaps.length > 0 && (
                <div className="mt-4">
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-status-weak-text">Gaps</p>
                  <ul className="space-y-1 text-sm text-neutral-700">
                    {report.gaps.map((g, i) => (
                      <li key={i}>• {g}</li>
                    ))}
                  </ul>
                </div>
              )}

              {report.aiNote && (
                <div className="mt-5 flex gap-2 rounded-md bg-status-strong-bg/50 p-3 text-sm text-neutral-700">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-status-strong-text" />
                  <p>{report.aiNote}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </OrgAppShell>
  );
}
