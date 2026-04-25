import { Navigate, Route, Routes } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { getStoredUser, isLearnerUser } from '../api';
import { CoursesPage } from './CoursesPage';
import { CourseDetailPage } from './CourseDetailPage';
import { DocumentsPage } from './DocumentsPage';
import { TestsPage } from './TestsPage';
import { TestDetailPage } from './TestDetailPage';
import ChatbotPage from './ChatbotPage';

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="placeholder-page">
      <h1 className="page-title page-title--documents">{title}</h1>
      <div className="placeholder-card">
        <p>{description}</p>
      </div>
    </section>
  );
}

export function DashboardPage() {
  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);
  const defaultPath = learner ? 'courses' : 'documents';

  return (
    <main className="app-layout">
      <Sidebar />
      <section className="app-content">
        <Routes>
          <Route path="/" element={<Navigate to={defaultPath} replace />} />
          <Route path="documents" element={learner ? <Navigate to="/app/courses" replace /> : <DocumentsPage />} />
          <Route path="courses" element={<CoursesPage />} />
          <Route path="courses/:courseId" element={<CourseDetailPage />} />
          <Route path="tests" element={<TestsPage />} />
          <Route path="tests/:testId" element={<TestDetailPage />} />
          <Route path="chatbot" element={<ChatbotPage />} />
          <Route
            path="trainer"
            element={
              <PlaceholderPage
                title="Диалоговый тренажёр"
                description="Этот раздел позже будет доработан в рамках общего проекта."
              />
            }
          />
          <Route
            path="analytics"
            element={
              <PlaceholderPage
                title="Аналитика"
                description="Этот раздел позже будет доработан в рамках общего проекта."
              />
            }
          />
          <Route
            path="guide"
            element={
              <PlaceholderPage
                title="Руководство пользователя"
                description="Здесь позже можно разместить инструкции по работе с системой."
              />
            }
          />
          <Route path="*" element={<Navigate to={defaultPath} replace />} />
        </Routes>
      </section>
    </main>
  );
}
