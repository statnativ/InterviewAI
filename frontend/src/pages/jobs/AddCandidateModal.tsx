import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input, Label, Textarea } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";
import { extractTextFromPdf, readPdfName } from "@/lib/pdf";
import type { Candidate } from "@/data/types";
import { FileUp, Loader2 } from "lucide-react";

const SOURCES = [
  "Manual Entry",
  "LinkedIn",
  "Employee Referral",
  "Company Careers Page",
  "Job Board",
  "Hacker News",
  "University Recruiting",
];

export function AddCandidateModal({
  open,
  onClose,
  jobId,
}: {
  open: boolean;
  onClose: () => void;
  jobId: string;
}) {
  const navigate = useNavigate();
  const addCandidate = useAppStore((s) => s.addCandidate);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [source, setSource] = useState("Manual Entry");
  const [resumeText, setResumeText] = useState("");
  const [pdfName, setPdfName] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [added, setAdded] = useState<Candidate | null>(null);
  const [duplicate, setDuplicate] = useState<Candidate | null>(null);

  const onPdfUpload = async (file: File | undefined) => {
    if (!file) return;
    if (!/\.pdf$/i.test(file.name)) {
      setParseError("Only .pdf files are supported.");
      return;
    }
    setParsing(true);
    setParseError(null);
    try {
      const { text, pageCount } = await extractTextFromPdf(file);
      setResumeText(text);
      setPdfName(`${file.name} (${pageCount} page${pageCount > 1 ? "s" : ""})`);
      if (!name.trim()) setName(readPdfName(file.name));
    } catch (e) {
      setParseError("Could not read this PDF. Check the file and try again.");
      console.error("PDF parse failed", e);
    } finally {
      setParsing(false);
    }
  };

  const submit = async () => {
    if (!name.trim()) return;
    const result = await addCandidate(jobId, { name, email, phone, source, resumeText });
    if (result.duplicate) {
      setDuplicate(result.duplicate);
      setAdded(null);
    } else {
      setAdded(result.candidate);
      setDuplicate(null);
    }
  };

  const close = () => {
    setAdded(null);
    setDuplicate(null);
    setName("");
    setEmail("");
    setPhone("");
    setSource("Manual Entry");
    setResumeText("");
    setPdfName(null);
    setParseError(null);
    setResumeText("");
    onClose();
  };

  const verdictTone =
    added?.compareVerdict === "Advance"
      ? ("strong" as const)
      : added?.compareVerdict === "Maybe"
      ? ("possible" as const)
      : ("weak" as const);

  return (
    <Modal
      open={open}
      onClose={close}
      title="Add candidate"
      footer={
        added || duplicate ? (
          <>
            <Button variant="secondary" onClick={close}>
              Close
            </Button>
            <Button onClick={() => navigate(`/jobs/${jobId}/candidates`)}>
              View candidates
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={!name.trim()}>
              Add & screen
            </Button>
          </>
        )
      }
    >
      {duplicate ? (
        <div className="space-y-4">
          <div className="rounded-md border border-status-possible-border bg-status-possible-bg p-4">
            <p className="text-sm font-medium text-neutral-900">
              Duplicate email detected
            </p>
            <p className="mt-1 text-sm text-neutral-600">
              <span className="font-medium">{duplicate.email}</span> already exists as{" "}
              <span className="font-medium">{duplicate.name}</span> (score {duplicate.score})
              for this ATS. No new record was created to avoid a duplicate application.
            </p>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
              Existing candidate
            </p>
            <p className="text-sm text-neutral-700">{duplicate.name}</p>
            <p className="text-xs text-neutral-500">
              {duplicate.currentTitle} · {duplicate.currentCompany} · {duplicate.source}
            </p>
          </div>
        </div>
      ) : added ? (
        <div className="space-y-4">
          <div className="rounded-md border border-brand-primary/20 bg-brand-primary-subtle/40 p-4">
            <p className="text-sm font-medium text-neutral-900">
              {added.name} — screening complete
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-3xl font-semibold text-neutral-900">
                {added.score}
              </span>
              <Badge tone={verdictTone}>{added.compareVerdict}</Badge>
              <span className="text-sm text-neutral-500">
                {added.scorecard.length} rubric criteria
              </span>
            </div>
            <p className="mt-2 text-xs text-neutral-500">{added.aiNote}</p>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
              Matched skills
            </p>
            <div className="flex flex-wrap gap-1.5">
              {added.skills.length > 0 ? (
                added.skills.map((s) => (
                  <Badge key={s} tone="neutral">
                    {s}
                  </Badge>
                ))
              ) : (
                <p className="text-sm text-neutral-400">
                  No dictionary skills detected in the pasted resume.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="c-name">Name *</Label>
              <Input
                id="c-name"
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="c-email">Email</Label>
              <Input
                id="c-email"
                type="email"
                placeholder="jane@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="c-phone">Phone</Label>
              <Input
                id="c-phone"
                type="tel"
                placeholder="(555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="c-source">Source</Label>
              <select
                id="c-source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20"
              >
                {SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="c-pdf">Upload CV (PDF)</Label>
            <label
              htmlFor="c-pdf"
              className={`flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-neutral-300 bg-neutral-50 px-3 py-3 text-sm text-neutral-500 transition-colors hover:border-brand-primary hover:text-brand-primary ${
                parsing ? "cursor-wait opacity-60" : ""
              }`}
            >
              {parsing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Reading PDF…
                </>
              ) : (
                <>
                  <FileUp className="h-4 w-4" />
                  Choose a PDF to auto-fill the resume text
                </>
              )}
            </label>
            <input
              id="c-pdf"
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              disabled={parsing}
              onChange={(e) => {
                void onPdfUpload(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            {pdfName && (
              <p className="mt-1 text-xs text-emerald-600">
                Parsed: {pdfName}
              </p>
            )}
            {parseError && (
              <p className="mt-1 text-xs text-red-600">{parseError}</p>
            )}
          </div>
          <div>
            <Label htmlFor="c-resume">Resume text</Label>
            <Textarea
              id="c-resume"
              rows={8}
              placeholder="Paste the resume text here. Skills are matched against the job's rubric — try including e.g. 'Go, PostgreSQL, Kubernetes'."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}
