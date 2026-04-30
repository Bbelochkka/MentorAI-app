import { Navigate, Route, Routes } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { getStoredUser, isLearnerUser, isAdminUser } from '../api';
import { HomePage } from './HomePage';
import { EmployeesAdminPage } from './EmployeesAdminPage';
import { CoursesPage } from './CoursesPage';
import { CourseDetailPage } from './CourseDetailPage';
import { DocumentsPage } from './DocumentsPage';
import { TestsPage } from './TestsPage';
import { TestDetailPage } from './TestDetailPage';
import ChatbotPage from './ChatbotPage';
import DialogTrainerPage from './DialogTrainerPage';
import { AnalyticsEmployeesPage } from './AnalyticsEmployeesPage';
import { EmployeeAnalyticsDetailPage } from './EmployeeAnalyticsDetailPage';
import { AnalyticsTestsPage } from './AnalyticsTestsPage';
import { TestAnalyticsDetailPage } from './TestAnalyticsDetailPage';

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
  const admin = isAdminUser(currentUser);
  const fallbackPath = admin ? '/app/employees' : '/app';

  return (
    <main className="app-layout">
      <Sidebar />
      <section className="app-content">
        <Routes>
          <Route path="/" element={admin ? <Navigate to="employees" replace /> : <HomePage />} />

          <Route
            path="employees"
            element={admin ? <EmployeesAdminPage /> : <Navigate to={fallbackPath} replace />}
          />

          <Route
            path="documents"
            element={learner || admin ? <Navigate to={fallbackPath} replace /> : <DocumentsPage />}
          />

          <Route
            path="courses"
            element={admin ? <Navigate to={fallbackPath} replace /> : <CoursesPage />}
          />

          <Route
            path="courses/:courseId"
            element={admin ? <Navigate to={fallbackPath} replace /> : <CourseDetailPage />}
          />

          <Route
            path="tests"
            element={admin ? <Navigate to={fallbackPath} replace /> : <TestsPage />}
          />

          <Route
            path="tests/:testId"
            element={admin ? <Navigate to={fallbackPath} replace /> : <TestDetailPage />}
          />

          <Route
            path="chatbot"
            element={admin ? <Navigate to={fallbackPath} replace /> : <ChatbotPage />}
          />

          <Route
            path="trainer"
            element={admin ? <Navigate to={fallbackPath} replace /> : <DialogTrainerPage />}
          />

          <Route
            path="analytics/tests"
            element={
              learner || admin ? <Navigate to={fallbackPath} replace /> : <AnalyticsTestsPage />
            }
          />

          <Route
            path="analytics/tests/:testId"
            element={
              learner || admin ? <Navigate to={fallbackPath} replace /> : <TestAnalyticsDetailPage />
            }
          />

          <Route
            path="analytics"
            element={
              learner || admin ? <Navigate to={fallbackPath} replace /> : <AnalyticsEmployeesPage />
            }
          />

          <Route
            path="analytics/employees/:employeeId"
            element={
              learner || admin ? (
                <Navigate to={fallbackPath} replace />
              ) : (
                <EmployeeAnalyticsDetailPage />
              )
            }
          />

          <Route
            path="guide"
            element={
              admin ? (
                <Navigate to={fallbackPath} replace />
              ) : (
                <PlaceholderPage
                  title="Руководство пользователя"
                  description="Здесь позже можно разместить инструкции по работе с системой."
                />
              )
            }
          />

          <Route path="*" element={<Navigate to={fallbackPath} replace />} />
        </Routes>
      </section>
    </main>
  );
}