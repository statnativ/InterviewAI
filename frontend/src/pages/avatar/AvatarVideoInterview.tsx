import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppStore } from "@/store/useAppStore";
import { AntiCheatingModal } from "@/pages/session/AntiCheatingModal";
import { Button } from "@/components/ui/Button";
import { Mic, MicOff, PhoneOff, Clock, Bot, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function AvatarVideoInterview() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const ready = useAppStore((s) => s.ready);

  const [step, setStep] = useState(0);
  const [speaking, setSpeaking] = useState(true);
  const [muted, setMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [violationOpen, setViolationOpen] = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const questions = interview?.questions ?? [];

  useEffect(() => {
    navigator.mediaDevices
      ?.getUserMedia({ video: true, audio: true })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => {});
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setSpeaking(false), 2800);
    return () => clearTimeout(t);
  }, [step]);

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

  if (!ready) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 bg-neutral-900 text-sm text-neutral-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading interview…
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-neutral-900 text-center">
        <p className="text-sm text-neutral-400">
          This interview link doesn't exist or may have expired.
        </p>
        <Button variant="secondary" size="sm" onClick={() => navigate("/candidate")}>
          Back to dashboard
        </Button>
      </div>
    );
  }

  const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");

  const nextQuestion = () => {
    const isLast = step + 1 >= questions.length;
    if (isLast) {
      navigate(`/session/${interviewId}/completed`);
    } else {
      setStep((s) => s + 1);
      setSpeaking(true);
    }
  };

  return (
    <div className="relative flex h-screen flex-col bg-neutral-900">
      <div className="flex items-center justify-between px-6 py-4 text-white">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-primary text-xs font-bold">
            A
          </span>
          <span className="text-sm font-medium">{interview.title}</span>
        </div>
        <span className="flex items-center gap-1.5 text-sm text-neutral-300">
          <Clock className="h-3.5 w-3.5" /> {mins}:{secs}
        </span>
      </div>

      <div className="relative flex flex-1 items-center justify-center">
        <div
          className={cn(
            "flex h-56 w-56 items-center justify-center rounded-full bg-gradient-to-br from-brand-primary to-brand-primary-hover transition-transform duration-500",
            speaking && "scale-105 shadow-[0_0_0_12px_rgba(190,90,60,0.15)]"
          )}
        >
          <Bot className="h-24 w-24 text-white" />
        </div>

        <div className="absolute bottom-8 left-8 h-32 w-44 overflow-hidden rounded-lg border-2 border-neutral-700 bg-neutral-800">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="h-full w-full object-cover"
          />
        </div>

        <div className="absolute bottom-8 max-w-xl rounded-lg bg-neutral-800/90 px-5 py-3 text-center text-white backdrop-blur">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
            Question {step + 1} of {questions.length}
          </p>
          <p className="text-sm">{questions[step]?.prompt}</p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 py-6">
        <button
          onClick={() => setMuted((m) => !m)}
          className={cn(
            "flex h-12 w-12 items-center justify-center rounded-full text-white transition-colors",
            muted ? "bg-status-weak-text" : "bg-neutral-700 hover:bg-neutral-600"
          )}
        >
          {muted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>
        <button
          onClick={nextQuestion}
          className="rounded-full bg-brand-primary px-6 py-3 text-sm font-medium text-white hover:bg-brand-primary-hover"
        >
          {step + 1 >= questions.length ? "Finish interview" : "Next question"}
        </button>
        <button
          onClick={() => navigate(`/session/${interviewId}/completed`)}
          className="flex h-12 w-12 items-center justify-center rounded-full bg-status-weak-text text-white hover:opacity-90"
        >
          <PhoneOff className="h-5 w-5" />
        </button>
      </div>

      <AntiCheatingModal
        open={violationOpen}
        onClose={() => setViolationOpen(false)}
        violationCount={violationCount}
      />
    </div>
  );
}
