import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { OrgAppShell } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Avatar } from "@/components/ui/Avatar";
import { Input, Textarea } from "@/components/ui/Input";
import { ScorePill, scoreTone } from "@/components/ui/ScorePill";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { ArrowLeft, Link2, Sparkles, ThumbsUp, ThumbsDown, Bookmark, Mail, Phone, MapPin, FileText, Check } from "lucide-react";
import { canWrite, cn } from "@/lib/utils";

export function CandidateDetail() {
  const { jobId, candidateId } = useParams();
  const navigate = useNavigate();
  const job = useAppStore((s) => s.jobs.find((j) => j.id === jobId));
  const candidate = useAppStore((s) => s.candidates.find((c) => c.id === candidateId));
  const currentUser = useAppStore((s) => s.currentUser);
  const ready = useAppStore((s) => s.ready);
  const toggleShortlist = useAppStore((s) => s.toggleShortlist);
  const setDecision = useAppStore((s) => s.setDecision);
  const updateCandidate = useAppStore((s) => s.updateCandidate);
  const judgeCandidate = useAppStore((s) => s.judgeCandidate);
  const pollCandidate = useAppStore((s) => s.pollCandidate);

  const [notes, setNotes] = useState(candidate?.notes ?? "");
  const [tagInput, setTagInput] = useState("");
  const [copied, setCopied] = useState(false);
  // Only for synchronous failures on the POST itself (400/404/409) — the
  // background job's own success/failure is real server state, read
  // directly off `candidate.judgeStatus`/`judgeError` below, not local state
  // (which would be lost on navigation, unlike the server-persisted version).
  const [requestError, setRequestError] = useState<string | null>(null);

  useEffect(() => {
    setNotes(candidate?.notes ?? "");
    setTagInput("");
  }, [candidateId, candidate?.notes]);

  // IA-003: poll while a background AI-judge job is in flight. Declared
  // unconditionally (before the early returns below) per the rules of
  // hooks; guards internally for candidate being undefined/not pending.
  useEffect(() => {
    if (!candidate || candidate.judgeStatus !== "pending") return;
    let attempts = 0;
    const maxAttempts = 30; // ~60s at a 2s interval, then give up polling
    const id = setInterval(() => {
      attempts += 1;
      if (attempts > maxAttempts) {
        clearInterval(id);
        return;
      }
      pollCandidate(candidate.id);
    }, 2000);
    return () => clearInterval(id);
  }, [candidate?.id, candidate?.judgeStatus, pollCandidate]);

  if (!ready) {
    return (
      <OrgAppShell>
        <LoadingState label="Loading candidate…" />
      </OrgAppShell>
    );
  }

  if (!job || !candidate) {
    return (
      <OrgAppShell>
        <NotFoundState
          message="This candidate doesn't exist or may have been removed."
          backLabel="Back to candidates"
          onBack={() => navigate("/candidates")}
        />
      </OrgAppShell>
    );
  }

  const editable = canWrite(currentUser.role);

  const commitNotes = () => updateCandidate(candidate.id, { notes });

  const addTag = () => {
    const tag = tagInput.trim();
    if (!tag || candidate.tags.includes(tag)) return;
    updateCandidate(candidate.id, { tags: [...candidate.tags, tag] });
    setTagInput("");
  };

  const removeTag = (tag: string) =>
    updateCandidate(candidate.id, { tags: candidate.tags.filter((t) => t !== tag) });

  const copyLink = async () => {
    const url = `${window.location.origin}/jobs/${candidate.jobId}/candidates/${candidate.id}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleJudge = async () => {
    setRequestError(null);
    try {
      // Fires the background job (IA-003) and returns almost immediately —
      // the polling effect above picks up completion/failure from there.
      await judgeCandidate(candidate.id);
    } catch (e) {
      setRequestError(e instanceof Error ? e.message : "Failed to start AI screening");
    }
  };

  return (
    <OrgAppShell>
      <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-8 py-4">
        <div>
          <button
            onClick={() => navigate(`/jobs/${job.id}/candidates`)}
            className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600"
          >
            <ArrowLeft className="h-3 w-3" /> Jobs / {job.title} / Candidates
          </button>
          <h1 className="text-xl font-semibold text-neutral-900">{candidate.name}</h1>
        </div>
        <button
          onClick={() => navigate(`/jobs/${job.id}/candidates`)}
          className="text-sm font-medium text-neutral-500 hover:text-neutral-800"
        >
          ← Back to list
        </button>
      </div>

      <div className="flex-1 px-8 py-6">
        <div className="mb-6 flex items-center gap-4">
          <ScorePill score={candidate.score} />
          <Avatar name={candidate.name} size="lg" />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-neutral-900">
                {candidate.name}
              </h2>
              {candidate.shortlisted && <Badge tone="brand">Shortlisted</Badge>}
              {candidate.source && <Badge tone="info">{candidate.source}</Badge>}
              {candidate.tags.map((t) => (
                <Badge key={t} tone="neutral">
                  {t}
                </Badge>
              ))}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-neutral-500">
              <span className="inline-flex items-center gap-1">
                <Mail className="h-3.5 w-3.5" /> {candidate.email}
              </span>
              {candidate.phone && (
                <span className="inline-flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5" /> {candidate.phone}
                </span>
              )}
              {candidate.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" /> {candidate.location}
                </span>
              )}
              <span>· {candidate.yearsExp} yrs experience</span>
              {candidate.resumeFile && (
                <span className="inline-flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  <a
                    href={`/resumes/${candidate.resumeFile}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-primary underline underline-offset-2 hover:text-brand-primary/80"
                  >
                    {candidate.resumeFile}
                  </a>
                </span>
              )}
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant={candidate.shortlisted ? "primary" : "secondary"}
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can shortlist candidates"}
              onClick={() => toggleShortlist(candidate.id)}
            >
              <Bookmark className="h-3.5 w-3.5" /> Shortlist
            </Button>
            <Button
              variant={candidate.decision === "Approved" ? "primary" : "secondary"}
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision(candidate.id, "Approved")}
            >
              <ThumbsUp className="h-3.5 w-3.5" /> Approve
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision(candidate.id, "Hold")}
            >
              Hold
            </Button>
            <Button
              variant={candidate.decision === "Rejected" ? "danger" : "secondary"}
              size="sm"
              disabled={!editable}
              title={editable ? undefined : "Only recruiters and admins can set a decision"}
              onClick={() => setDecision(candidate.id, "Rejected")}
            >
              <ThumbsDown className="h-3.5 w-3.5" /> Reject
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!editable || candidate.judgeStatus === "pending"}
              title={editable ? undefined : "Only recruiters and admins can run AI screening"}
              onClick={handleJudge}
            >
              <Sparkles className="h-3.5 w-3.5" /> {candidate.judgeStatus === "pending" ? "Judging…" : "AI Judge"}
            </Button>
            <Button variant="ghost" size="sm" onClick={copyLink}>
              {copied ? <Check className="h-3.5 w-3.5" /> : <Link2 className="h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy link"}
            </Button>
          </div>
        </div>
        {(requestError || (candidate.judgeStatus === "failed" && candidate.judgeError)) && (
          <p className="border-b border-status-weak-border bg-status-weak-bg px-8 py-2 text-sm text-status-weak-text">
            {requestError ?? candidate.judgeError}
          </p>
        )}

        <div className="grid grid-cols-2 gap-6">
          <Card>
            <CardContent className="space-y-5">
              <div>
                <h3 className="mb-1 text-sm font-semibold text-neutral-900">
                  Candidate Profile
                </h3>
                <p className="text-sm text-neutral-600">{candidate.summary}</p>
              </div>

              {candidate.skills.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
                    Skills
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.skills.map((s) => (
                      <Badge key={s} tone="neutral">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {candidate.experience.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
                    Experience
                  </p>
                  <div className="space-y-2">
                    {candidate.experience.map((e, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <div>
                          <p className="font-medium text-neutral-900">{e.title}</p>
                          <p className="text-neutral-500">{e.company}</p>
                        </div>
                        <span className="text-xs text-neutral-400">{e.period}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="mb-0.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
                    Education
                  </p>
                  <p className="text-neutral-700">{candidate.education}</p>
                </div>
                <div>
                  <p className="mb-0.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
                    Certifications
                  </p>
                  <p className="text-neutral-700">{candidate.certifications}</p>
                </div>
              </div>

              <div className="border-t border-neutral-100 pt-4">
                <div className="mb-1.5 flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
                    Tags
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  {candidate.tags.map((t) => (
                    <button
                      key={t}
                      onClick={() => removeTag(t)}
                      title="Remove tag"
                      className="group inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700 hover:border-status-weak-border hover:bg-status-weak-bg hover:text-status-weak-text"
                    >
                      {t}
                      <span className="text-neutral-400 group-hover:text-status-weak-text">×</span>
                    </button>
                  ))}
                  <span className="inline-flex items-center gap-1">
                    <Input
                      placeholder="Add tag…"
                      className="h-6 w-24 px-2 py-0 text-xs"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") addTag();
                      }}
                    />
                  </span>
                </div>
              </div>

              <div className="border-t border-neutral-100 pt-4">
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
                  Notes
                </p>
                <Textarea
                  rows={4}
                  placeholder="Add private recruiter notes about this candidate…"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  onBlur={commitNotes}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-neutral-900">
                  Screening Scorecard
                </h3>
                <div className="flex items-center gap-2">
                  {candidate.judgeStatus === "pending" && <Badge tone="pending">AI Judging…</Badge>}
                  {candidate.judgeStatus !== "pending" && candidate.scoreMethod === "llm_judge" && (
                    <Badge tone="brand">AI Judged</Badge>
                  )}
                  <ScorePill score={candidate.score} size="sm" />
                </div>
              </div>
              <p className="mb-3 text-xs text-neutral-400">Weighted against rubric v2</p>

              <div className="space-y-3">
                {candidate.scorecard.map((row) => {
                  const tone = scoreTone(row.score);
                  return (
                    <div key={row.criterion}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-neutral-800">
                          {row.criterion}
                        </span>
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
                {candidate.scorecard.length === 0 && (
                  <p className="text-sm text-neutral-400">Screening not yet run.</p>
                )}
              </div>

              {candidate.strengths.length > 0 && (
                <div className="mt-5">
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-status-strong-text">
                    Strengths
                  </p>
                  <ul className="space-y-1 text-sm text-neutral-700">
                    {candidate.strengths.map((s, i) => (
                      <li key={i}>• {s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {candidate.gaps.length > 0 && (
                <div className="mt-4">
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-status-weak-text">
                    Gaps
                  </p>
                  <ul className="space-y-1 text-sm text-neutral-700">
                    {candidate.gaps.map((g, i) => (
                      <li key={i}>• {g}</li>
                    ))}
                  </ul>
                </div>
              )}

              {candidate.aiNote && (
                <div className="mt-5 flex gap-2 rounded-md bg-status-strong-bg/50 p-3 text-sm text-neutral-700">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-status-strong-text" />
                  <p>{candidate.aiNote}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </OrgAppShell>
  );
}
