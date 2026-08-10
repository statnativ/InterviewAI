import { useAppStore } from "@/store/useAppStore";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { Zap, PlayCircle, HelpCircle, Bookmark } from "lucide-react";

import { LoginOrg } from "@/pages/auth/LoginOrg";
import { LoginCandidate } from "@/pages/auth/LoginCandidate";
import { LandingCandidate } from "@/pages/auth/LandingCandidate";
import { Dashboard } from "@/pages/Dashboard";

import { JobsList } from "@/pages/jobs/JobsList";
import { JobDetail } from "@/pages/jobs/JobDetail";

import { CandidatesList } from "@/pages/candidates/CandidatesList";
import { RankedShortlist } from "@/pages/candidates/RankedShortlist";
import { CandidateDetail } from "@/pages/candidates/CandidateDetail";
import { PipelineBoard } from "@/pages/candidates/PipelineBoard";
import { ComparativeReport } from "@/pages/candidates/ComparativeReport";

import { InterviewsList } from "@/pages/interviews/InterviewsList";
import { NewInterview } from "@/pages/interviews/NewInterview";
import { InterviewEditor } from "@/pages/interviews/InterviewEditor";

import { OnboardingConsent } from "@/pages/session/OnboardingConsent";
import { OnboardingDeviceCheck } from "@/pages/session/OnboardingDeviceCheck";
import { ChatInterviewSession } from "@/pages/session/ChatInterviewSession";
import { VoiceInterviewSession } from "@/pages/session/VoiceInterviewSession";
import { SessionCompleted } from "@/pages/session/SessionCompleted";

import { AIDisclosure } from "@/pages/avatar/AIDisclosure";
import { AvatarVideoInterview } from "@/pages/avatar/AvatarVideoInterview";
import { PersonaBuilder } from "@/pages/avatar/PersonaBuilder";

import { PlaceholderPage } from "@/pages/PlaceholderPage";

import { AdminShell } from "@/components/layout/AdminShell";
import { AdminLogin } from "@/pages/admin/AdminLogin";
import { AdminTenants } from "@/pages/admin/AdminTenants";
import { AdminUsers } from "@/pages/admin/AdminUsers";
import { AdminPracticeTests } from "@/pages/admin/AdminPracticeTests";

export default function App() {
  const init = useAppStore((s) => s.init);
  useEffect(() => {
    void init();
  }, [init]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Auth & Landing */}
        <Route path="/login" element={<LoginOrg />} />
        <Route path="/candidate/login" element={<LoginCandidate />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/candidate" element={<LandingCandidate />} />

        {/* Job Requisition */}
        <Route path="/jobs" element={<JobsList />} />
        <Route path="/jobs/:jobId" element={<JobDetail />} />

        {/* Resume ATS */}
        <Route path="/candidates" element={<CandidatesList />} />
        <Route path="/jobs/:jobId/candidates" element={<RankedShortlist />} />
        <Route
          path="/jobs/:jobId/candidates/:candidateId"
          element={<CandidateDetail />}
        />
        <Route path="/jobs/:jobId/pipeline" element={<PipelineBoard />} />
        <Route path="/jobs/:jobId/compare" element={<ComparativeReport />} />

        {/* Interview Builder */}
        <Route path="/interviews" element={<InterviewsList />} />
        <Route path="/interviews/new" element={<NewInterview />} />
        <Route path="/interviews/:interviewId/edit" element={<InterviewEditor />} />
        <Route path="/persona-builder" element={<PersonaBuilder />} />

        {/* Live Session Runtime (candidate-facing) */}
        <Route path="/session/:interviewId/consent" element={<OnboardingConsent />} />
        <Route path="/session/:interviewId/device" element={<OnboardingDeviceCheck />} />
        <Route path="/session/:interviewId/chat" element={<ChatInterviewSession />} />
        <Route path="/session/:interviewId/voice" element={<VoiceInterviewSession />} />
        {/* M4b: Video mode shares the same (generalized) component as Voice — same backend
            session/turn mechanics, only the capture type differs. See VoiceInterviewSession.tsx. */}
        <Route path="/session/:interviewId/video" element={<VoiceInterviewSession />} />
        <Route path="/session/:interviewId/completed" element={<SessionCompleted />} />

        {/* Avatar Interviewer (candidate-facing) */}
        <Route path="/avatar/:interviewId/disclosure" element={<AIDisclosure />} />
        <Route path="/avatar/:interviewId/interview" element={<AvatarVideoInterview />} />

        {/* Nav placeholders */}
        <Route
          path="/practices"
          element={
            <PlaceholderPage
              title="Practices"
              description="Practice interview templates candidates can use to warm up before the real thing."
              icon={Zap}
            />
          }
        />
        <Route
          path="/sessions"
          element={
            <PlaceholderPage
              title="Sessions"
              description="A log of every live interview session, in progress or completed."
              icon={PlayCircle}
            />
          }
        />
        <Route
          path="/questions"
          element={
            <PlaceholderPage
              title="Questions"
              description="Your organization's shared question library, tagged by type and difficulty."
              icon={HelpCircle}
            />
          }
        />
        <Route
          path="/answer-bank"
          element={
            <PlaceholderPage
              title="Answer Bank"
              description="Reference answers and rubric anchors your team has saved for reuse."
              icon={Bookmark}
            />
          }
        />

        {/* Master admin (real session auth — separate from the dev-header org flow above) */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminShell />}>
          <Route index element={<Navigate to="/admin/tenants" replace />} />
          <Route path="tenants" element={<AdminTenants />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="practice-tests" element={<AdminPracticeTests />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
