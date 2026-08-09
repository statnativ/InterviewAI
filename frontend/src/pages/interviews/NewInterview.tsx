import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { MessageSquare, Mic, Video, Sparkles } from "lucide-react";
import type { Candidate, InterviewMode } from "@/data/types";
import { cn } from "@/lib/utils";

const modes: { mode: InterviewMode; icon: typeof MessageSquare; desc: string }[] = [
  { mode: "Chat", icon: MessageSquare, desc: "Text-based, async-friendly" },
  { mode: "Voice", icon: Mic, desc: "Live spoken conversation" },
  { mode: "Avatar", icon: Video, desc: "AI video interviewer" },
];

export function NewInterview() {
  const navigate = useNavigate();
  const jobs = useAppStore((s) => s.jobs);
  const createInterview = useAppStore((s) => s.createInterview);
  const [title, setTitle] = useState("");
  const [jobId, setJobId] = useState("");
  const [mode, setMode] = useState<InterviewMode>("Chat");
  const [generating, setGenerating] = useState(false);
  const [jobCandidates, setJobCandidates] = useState<Candidate[]>([]);
  const [candidateId, setCandidateId] = useState<string>("");

  // jobs loads asynchronously from the store — seed jobId once it arrives,
  // rather than at useState's initializer (which only ever sees jobs === []
  // on first render and would otherwise leave jobId stuck empty forever).
  useEffect(() => {
    if (!jobId && jobs.length > 0) {
      setJobId(jobs[0].id);
    }
  }, [jobs, jobId]);

  useEffect(() => {
    setCandidateId("");
    if (!jobId) {
      setJobCandidates([]);
      return;
    }
    let cancelled = false;
    api.listJobCandidates(jobId).then((list) => {
      if (!cancelled) setJobCandidates(list);
    });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const selectedJob = jobs.find((j) => j.id === jobId);

  const generate = async () => {
    if (!title.trim()) return;
    setGenerating(true);
    try {
      const interview = await createInterview({
        title,
        jobTitle: selectedJob?.title ?? "",
        jobId: jobId || undefined,
        candidateId: candidateId || undefined,
        mode,
      });
      navigate(`/interviews/${interview.id}/edit`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <OrgAppShell>
      <PageTopbar breadcrumb="Interviews" title="New interview" />

      <div className="flex-1 px-8 py-6">
        <Card className="mx-auto max-w-2xl">
          <CardContent className="space-y-5">
            <div className="flex items-center gap-2 text-brand-primary">
              <Sparkles className="h-4 w-4" />
              <p className="text-sm font-medium">AI Interview Generator</p>
            </div>
            <p className="text-sm text-neutral-500">
              Tell us about the role and we'll draft an interview with relevant
              technical, behavioral, and culture questions.
            </p>

            <div>
              <Label htmlFor="title">Interview title</Label>
              <Input
                id="title"
                placeholder="e.g. Senior Backend Engineer — Technical Screen"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="job">Linked job</Label>
              <select
                id="job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
              >
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
            </div>

            {jobId && (
              <div>
                <Label htmlFor="candidate">Personalize for a candidate (optional)</Label>
                <select
                  id="candidate"
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                  className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
                >
                  <option value="">None — generate from the job description only</option>
                  {jobCandidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-500">
                  Weaves the candidate's résumé into the generated questions. This interview
                  becomes tailored to them specifically, not a shared template.
                </p>
              </div>
            )}

            <div>
              <Label>Interview mode</Label>
              <div className="grid grid-cols-3 gap-3">
                {modes.map(({ mode: m, icon: Icon, desc }) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      "rounded-md border p-4 text-left transition-colors",
                      mode === m
                        ? "border-brand-primary bg-brand-primary-subtle"
                        : "border-neutral-200 hover:bg-neutral-50"
                    )}
                  >
                    <Icon
                      className={cn(
                        "mb-2 h-5 w-5",
                        mode === m ? "text-brand-primary" : "text-neutral-500"
                      )}
                    />
                    <p className="text-sm font-medium text-neutral-900">{m}</p>
                    <p className="text-xs text-neutral-500">{desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <Button
              className="w-full"
              size="lg"
              onClick={generate}
              disabled={!title.trim() || generating}
            >
              <Sparkles className="h-4 w-4" />
              {generating ? "Generating..." : "Generate interview"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </OrgAppShell>
  );
}
