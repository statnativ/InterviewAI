import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { Avatar } from "@/components/ui/Avatar";
import { useAppStore } from "@/store/useAppStore";
import { AntiCheatingModal } from "./AntiCheatingModal";
import { Clock, Send } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/data/types";

export function ChatInterviewSession() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const candidate = useAppStore((s) => s.currentCandidate);

  const [step, setStep] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [violationOpen, setViolationOpen] = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const questions = interview?.questions ?? [];

  useEffect(() => {
    if (questions.length === 0) return;
    setMessages([
      {
        id: "m0",
        from: "ai",
        text: questions[0].prompt,
        timestamp: new Date().toISOString(),
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interview?.id]);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) {
        setViolationCount((c) => c + 1);
        setViolationOpen(true);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  if (!interview) return null;

  const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");

  const submitAnswer = () => {
    if (!draft.trim()) return;
    const answerMsg: ChatMessage = {
      id: `m-${messages.length}`,
      from: "candidate",
      text: draft,
      timestamp: new Date().toISOString(),
    };
    const nextStep = step + 1;
    const isLast = nextStep >= questions.length;

    setMessages((m) => [...m, answerMsg]);
    setDraft("");

    if (isLast) {
      setTimeout(() => navigate(`/session/${interviewId}/completed`), 700);
    } else {
      setStep(nextStep);
      setTimeout(() => {
        setMessages((m) => [
          ...m,
          {
            id: `m-${m.length}`,
            from: "ai",
            text: questions[nextStep].prompt,
            timestamp: new Date().toISOString(),
          },
        ]);
      }, 600);
    }
  };

  return (
    <CandidateShell>
      <div className="mx-auto flex h-[calc(100vh-53px)] max-w-3xl flex-col px-6 py-6">
        <div className="mb-4 flex items-center justify-between rounded-md border border-neutral-200 bg-white px-4 py-2.5">
          <div>
            <p className="text-sm font-medium text-neutral-900">{interview.title}</p>
            <p className="text-xs text-neutral-500">
              Question {Math.min(step + 1, questions.length)} of {questions.length}
            </p>
          </div>
          <span className="flex items-center gap-1.5 text-sm text-neutral-500">
            <Clock className="h-3.5 w-3.5" /> {mins}:{secs}
          </span>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-1 py-2">
          {messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "flex items-start gap-2.5",
                m.from === "candidate" && "flex-row-reverse"
              )}
            >
              {m.from === "ai" ? (
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-primary text-xs font-bold text-white">
                  A
                </span>
              ) : (
                <Avatar name={candidate.name} size="sm" />
              )}
              <div
                className={cn(
                  "max-w-md rounded-lg px-4 py-2.5 text-sm",
                  m.from === "ai"
                    ? "bg-white border border-neutral-200 text-neutral-800"
                    : "bg-brand-primary text-white"
                )}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-end gap-2 rounded-md border border-neutral-200 bg-white p-2">
          <Textarea
            rows={2}
            placeholder="Type your answer..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitAnswer();
              }
            }}
            className="border-none focus:ring-0"
          />
          <Button onClick={submitAnswer} disabled={!draft.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <AntiCheatingModal
        open={violationOpen}
        onClose={() => setViolationOpen(false)}
        violationCount={violationCount}
      />
    </CandidateShell>
  );
}
