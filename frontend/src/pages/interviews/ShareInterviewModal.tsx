import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";
import { Check, Copy } from "lucide-react";

export function ShareInterviewModal({
  open,
  onClose,
  interviewId,
}: {
  open: boolean;
  onClose: () => void;
  interviewId: string;
}) {
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const toggleShared = useAppStore((s) => s.toggleInterviewShared);
  const [copied, setCopied] = useState(false);

  if (!interview) return null;
  const link = `https://app.statnativ.com/i/${interview.id}`;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Share interview"
      description="Anyone with this link can start this interview as a candidate."
      footer={
        <Button variant="secondary" onClick={onClose}>
          Done
        </Button>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-md border border-neutral-200 p-3">
          <div>
            <p className="text-sm font-medium text-neutral-900">
              Public link {interview.shared ? "enabled" : "disabled"}
            </p>
            <p className="text-xs text-neutral-500">
              Candidates can access without an account invite.
            </p>
          </div>
          <button
            onClick={() => toggleShared(interview.id)}
            className={`relative h-6 w-11 rounded-full transition-colors ${
              interview.shared ? "bg-brand-primary" : "bg-neutral-300"
            }`}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                interview.shared ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>

        {interview.shared && (
          <div className="flex gap-2">
            <Input readOnly value={link} className="text-neutral-600" />
            <Button
              variant="secondary"
              onClick={() => {
                navigator.clipboard?.writeText(link).catch(() => {});
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
