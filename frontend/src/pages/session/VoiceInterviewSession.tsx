import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { useAppStore } from "@/store/useAppStore";
import { AntiCheatingModal } from "./AntiCheatingModal";
import { Mic, Square, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export function VoiceInterviewSession() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));

  const [step, setStep] = useState(0);
  const [recording, setRecording] = useState(false);
  const [recSeconds, setRecSeconds] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [violationOpen, setViolationOpen] = useState(false);
  const [violationCount, setViolationCount] = useState(0);

  const questions = interview?.questions ?? [];

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!recording) return;
    const t = setInterval(() => setRecSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

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

  if (!interview) return null;

  const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");

  const toggleRecord = () => {
    if (recording) {
      setRecording(false);
      const isLast = step + 1 >= questions.length;
      setTimeout(() => {
        if (isLast) {
          navigate(`/session/${interviewId}/completed`);
        } else {
          setStep((s) => s + 1);
          setRecSeconds(0);
        }
      }, 500);
    } else {
      setRecording(true);
      setRecSeconds(0);
    }
  };

  return (
    <CandidateShell>
      <div className="mx-auto flex h-[calc(100vh-53px)] max-w-2xl flex-col items-center justify-center px-6">
        <div className="mb-8 flex w-full items-center justify-between">
          <p className="text-sm font-medium text-neutral-900">{interview.title}</p>
          <span className="flex items-center gap-1.5 text-sm text-neutral-500">
            <Clock className="h-3.5 w-3.5" /> {mins}:{secs}
          </span>
        </div>

        <Card className="w-full">
          <CardContent className="flex flex-col items-center py-10 text-center">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
              Question {step + 1} of {questions.length}
            </p>
            <p className="max-w-md text-lg font-medium text-neutral-900">
              {questions[step]?.prompt}
            </p>

            <div className="my-10 flex h-16 items-center gap-1">
              {Array.from({ length: 24 }).map((_, i) => (
                <span
                  key={i}
                  className={cn(
                    "w-1.5 rounded-full bg-brand-primary transition-all duration-300",
                    recording ? "opacity-100" : "opacity-20"
                  )}
                  style={{
                    height: recording
                      ? `${20 + Math.abs(Math.sin((i + recSeconds) * 0.9)) * 40}px`
                      : "8px",
                  }}
                />
              ))}
            </div>

            <button
              onClick={toggleRecord}
              className={cn(
                "flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition-colors",
                recording
                  ? "bg-status-weak-text hover:opacity-90"
                  : "bg-brand-primary hover:bg-brand-primary-hover"
              )}
            >
              {recording ? <Square className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
            </button>
            <p className="mt-3 text-sm text-neutral-500">
              {recording ? `Recording · ${recSeconds}s — tap to finish` : "Tap to record your answer"}
            </p>
          </CardContent>
        </Card>
      </div>

      <AntiCheatingModal
        open={violationOpen}
        onClose={() => setViolationOpen(false)}
        violationCount={violationCount}
      />
    </CandidateShell>
  );
}
