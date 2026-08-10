import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CandidateShell } from "@/components/layout/CandidateShell";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingState, NotFoundState } from "@/components/ui/RecordState";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import type { TurnResult } from "@/data/types";
import { AntiCheatingModal } from "./AntiCheatingModal";
import { Mic, Camera, Square, Clock, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// M4: how a session id survives from OnboardingDeviceCheck (which creates it) into this
// page, and across a reload — deliberately NOT the global useAppStore, which holds the
// recruiter's identity, not a candidate's. sessionStorage (not the store) is the carry
// mechanism per the plan; see OnboardingDeviceCheck.tsx for the write side.
function sessionStorageKey(interviewId: string) {
  return `interview-session:${interviewId}`;
}

type TranscriptEntry = { role: "ai" | "candidate"; text: string };

function decodeBase64Audio(base64: string, format: string): string {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: `audio/${format}` });
  return URL.createObjectURL(blob);
}

// M4b: this component now serves both Voice (audio-only) and Video mode — "swap the
// browser capture type, not the architecture" (PD-001). Everything below the capture layer
// (turn submission, idempotency, reconciliation, AI-audio playback) is identical for both;
// only getUserMedia's constraints, the MediaRecorder mimeType probe, and an optional
// self-view <video> element differ, gated on `isVideo`.
export function VoiceInterviewSession() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const interview = useAppStore((s) => s.interviews.find((i) => i.id === interviewId));
  const ready = useAppStore((s) => s.ready);
  const isVideo = interview?.mode === "Video";

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [aiText, setAiText] = useState("");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [recording, setRecording] = useState(false);
  const [recSeconds, setRecSeconds] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [violationOpen, setViolationOpen] = useState(false);
  const [violationCount, setViolationCount] = useState(0);

  const nextTurnIndexRef = useRef(1);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const lastFailedRef = useRef<{ blob: Blob; format: string } | null>(null);
  const audioElRef = useRef<HTMLAudioElement>(null);
  const selfViewRef = useRef<HTMLVideoElement>(null);

  const playAiAudio = (base64: string, format: string) => {
    const url = decodeBase64Audio(base64, format);
    if (audioElRef.current) {
      audioElRef.current.src = url;
      audioElRef.current.play().catch(() => {
        // Autoplay can be blocked before the first user gesture — the candidate can hit
        // play manually; not worth a hard error for this POC.
      });
    }
  };

  const applyTurnResult = (result: TurnResult) => {
    setAiText(result.aiText);
    setTranscript((t) => [...t, ...(result.transcript ? [{ role: "candidate" as const, text: result.transcript }] : []), { role: "ai" as const, text: result.aiText }]);
    playAiAudio(result.aiAudio, result.aiAudioFormat);
    if (result.status === "complete") {
      setTimeout(() => navigate(`/session/${interviewId}/completed`), 1800);
    }
  };

  // Initialize from the session OnboardingDeviceCheck already created, and reconcile
  // against the server in case this is a reload mid-conversation (audio for turns before
  // the reload isn't replayable — a known, accepted gap; the text transcript still resumes
  // correctly, which is what actually matters for continuing the interview).
  useEffect(() => {
    if (!interviewId) return;
    const cached = sessionStorage.getItem(sessionStorageKey(interviewId));
    if (!cached) {
      setLoadError("No active interview session — please restart from the consent screen.");
      return;
    }
    const initial: TurnResult = JSON.parse(cached);
    setSessionId(initial.sessionId);
    setAiText(initial.aiText);
    setTranscript([{ role: "ai", text: initial.aiText }]);
    playAiAudio(initial.aiAudio, initial.aiAudioFormat);
    nextTurnIndexRef.current = 1;
    if (initial.status === "complete") {
      navigate(`/session/${interviewId}/completed`);
      return;
    }

    api
      .getSession(initial.sessionId)
      .then((info) => {
        if (info.turns.length <= 1) return; // just the opening turn — nothing to reconcile
        const history: TranscriptEntry[] = [];
        for (const t of info.turns) {
          if (t.transcript) history.push({ role: "candidate", text: t.transcript });
          if (t.aiText) history.push({ role: "ai", text: t.aiText });
        }
        setTranscript(history);
        const lastAi = [...info.turns].reverse().find((t) => t.aiText);
        if (lastAi?.aiText) setAiText(lastAi.aiText);
        nextTurnIndexRef.current = info.turns.length;
        if (info.status === "complete") navigate(`/session/${interviewId}/completed`);
      })
      .catch(() => {
        // Best-effort reconciliation — the cached opening turn is still a valid starting
        // point if this fails, so no hard error here.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

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

  useEffect(() => {
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  const submitTurn = async (blob: Blob, format: string) => {
    if (!sessionId) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.postTurn(sessionId, nextTurnIndexRef.current, blob, format);
      nextTurnIndexRef.current += 1;
      lastFailedRef.current = null;
      applyTurnResult(result);
    } catch (e) {
      // Idempotent retry: turn_index is NOT advanced, and the same blob is kept so a
      // "Retry" resends the identical (turn_index, audio) pair the backend expects.
      lastFailedRef.current = { blob, format };
      setSubmitError(e instanceof Error ? e.message : "Failed to submit your answer — please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const startRecording = async () => {
    setSubmitError(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: isVideo });
    streamRef.current = stream;
    if (isVideo && selfViewRef.current) selfViewRef.current.srcObject = stream;
    const preferredMimeType = isVideo ? "video/webm" : "audio/webm";
    const mimeType = MediaRecorder.isTypeSupported(preferredMimeType) ? preferredMimeType : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
    setRecSeconds(0);
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    recorder.onstop = () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (selfViewRef.current) selfViewRef.current.srcObject = null;
      const fallbackMimeType = isVideo ? "video/webm" : "audio/webm";
      const mimeType = recorder.mimeType || fallbackMimeType;
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const format = mimeType.split("/")[1]?.split(";")[0] || "webm";
      void submitTurn(blob, format);
    };
    recorder.stop();
    setRecording(false);
  };

  const retryLastSubmission = () => {
    if (lastFailedRef.current) {
      void submitTurn(lastFailedRef.current.blob, lastFailedRef.current.format);
    }
  };

  if (!ready) {
    return (
      <CandidateShell>
        <LoadingState label="Loading interview…" />
      </CandidateShell>
    );
  }

  if (!interview) {
    return (
      <CandidateShell>
        <NotFoundState
          message="This interview link doesn't exist or may have expired."
          backLabel="Back to dashboard"
          onBack={() => navigate("/candidate")}
        />
      </CandidateShell>
    );
  }

  if (loadError) {
    return (
      <CandidateShell>
        <NotFoundState
          message={loadError}
          backLabel="Back to consent"
          onBack={() => navigate(`/session/${interviewId}/consent`)}
        />
      </CandidateShell>
    );
  }

  const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");
  const busy = submitting || !sessionId;

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
              AI Interviewer
            </p>
            <p className="max-w-md text-lg font-medium text-neutral-900">{aiText || "Getting started…"}</p>

            <audio ref={audioElRef} className="mt-4 w-full max-w-xs" controls />

            {isVideo && (
              <video
                ref={selfViewRef}
                autoPlay
                muted
                playsInline
                className="mt-4 h-32 w-44 rounded-md bg-neutral-900 object-cover"
              />
            )}

            <div className="my-8 flex h-16 items-center gap-1">
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
              onClick={recording ? stopRecording : startRecording}
              disabled={busy}
              className={cn(
                "flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition-colors disabled:opacity-50",
                recording
                  ? "bg-status-weak-text hover:opacity-90"
                  : "bg-brand-primary hover:bg-brand-primary-hover"
              )}
            >
              {submitting ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : recording ? (
                <Square className="h-6 w-6" />
              ) : isVideo ? (
                <Camera className="h-6 w-6" />
              ) : (
                <Mic className="h-6 w-6" />
              )}
            </button>
            <p className="mt-3 text-sm text-neutral-500">
              {submitting
                ? "Processing your answer…"
                : recording
                  ? `Recording · ${recSeconds}s — tap to finish`
                  : "Tap to record your answer"}
            </p>
            {submitError && (
              <div className="mt-3 text-sm text-status-weak-text">
                {submitError}{" "}
                <button className="font-medium underline" onClick={retryLastSubmission}>
                  Retry
                </button>
              </div>
            )}
            {transcript.length > 1 && (
              <p className="mt-6 text-xs text-neutral-400">{Math.floor(transcript.length / 2)} exchange(s) so far</p>
            )}
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
