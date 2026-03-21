import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import LandingPage from "@/pages/LandingPage";
import ChatPage from "@/pages/ChatPage";
import LessonsPage from "@/pages/LessonsPage";
import LessonDetailPage from "@/pages/LessonDetailPage";
import StudentsPage from "@/pages/StudentsPage";
import StudentDetailPage from "@/pages/StudentDetailPage";
import Showcase from "@/pages/Showcase";
import ShowcaseClasstime from "@/pages/ShowcaseClasstime";
import VoicePractice from "@/views/VoicePractice/VoicePractice";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/showcase" element={<Showcase />} />
          <Route path="/showcase-classtime" element={<ShowcaseClasstime />} />
          <Route element={<AppShell />}>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:conversationId" element={<ChatPage />} />
            <Route path="/lessons" element={<LessonsPage />} />
            <Route path="/lessons/:lessonId" element={<LessonDetailPage />} />
            <Route path="/lessons/:lessonId/:tab" element={<LessonDetailPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route
              path="/students/:studentId"
              element={<StudentDetailPage />}
            />
            <Route path="/voice-practice" element={<VoicePractice />} />
            <Route path="*" element={<Navigate to="/students" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
