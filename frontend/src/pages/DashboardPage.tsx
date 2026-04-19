import { Navigate, Route, Routes } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { CoursesPage } from './CoursesPage';
import { CourseDetailPage } from './CourseDetailPage';
import { DocumentsPage } from './DocumentsPage';
import { TestsPage } from './TestsPage';
import { TestDetailPage } from './TestDetailPage';

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
  return (
    <main className="app-layout">
      <Sidebar />
      <section className="app-content">
        <Routes>
          <Route path="/" element={<Navigate to="documents" replace />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="courses" element={<CoursesPage />} />
          <Route path="courses/:courseId" element={<CourseDetailPage />} />
          <Route path="tests" element={<TestsPage />} />
          <Route path="tests/:testId" element={<TestDetailPage />} />
          <Route
            path="trainer"
            element={
              <PlaceholderPage
                title="Диалоговый тренажёр"
                description="Этот раздел позже будет интегрирован с модулем тренажёра."
              />
            }
          />
          <Route
            path="analytics"
            element={
              <PlaceholderPage
                title="Аналитика"
                description="Этот раздел позже будет интегрирован с аналитическим модулем."
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
          <Route path="*" element={<Navigate to="documents" replace />} />
        </Routes>
      </section>
    </main>
  );
}
