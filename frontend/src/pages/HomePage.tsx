import { CSSProperties, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AnalyticsEmployeeCardDto,
  CourseSummaryDto,
  TestSummaryDto,
  getAnalyticsEmployees,
  getCourses,
  getStoredUser,
  getTests,
  isLearnerUser,
} from '../api';
import { Button } from '../components/ui/Button';
import '../styles/ui.css';
import '../styles/home.css';

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function isCompletedTest(test: TestSummaryDto) {
  return test.best_attempt_percent !== null && test.best_attempt_percent !== undefined;
}

function MetricCard({
  title,
  value,
  subtitle,
  tone,
}: {
  title: string;
  value: number;
  subtitle: string;
  tone: 'green' | 'orange' | 'red';
}) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value)));
  const ringStyle = { '--metric-value': String(safeValue) } as CSSProperties;

  return (
    <article className={`home-metric-card home-metric-card--${tone}`}>
      <div className="home-metric-card__ring" style={ringStyle}>
        <div className="home-metric-card__inner">{safeValue}%</div>
      </div>

      <div>
        <h3 className="home-metric-card__title">{title}</h3>
        <p className="home-metric-card__subtitle">{subtitle}</p>
      </div>
    </article>
  );
}

function LearnerHome() {
  const navigate = useNavigate();
  const currentUser = getStoredUser();

  const [courses, setCourses] = useState<CourseSummaryDto[]>([]);
  const [tests, setTests] = useState<TestSummaryDto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setIsLoading(true);
    setError(null);

    try {
      const [courseItems, testItems] = await Promise.all([getCourses(), getTests()]);
      setCourses(courseItems);
      setTests(testItems);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить главный экран');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const completedTests = useMemo(() => tests.filter(isCompletedTest), [tests]);

  const completedCourseIds = useMemo(() => {
    return new Set(completedTests.map((test) => test.course_id));
  }, [completedTests]);

  const notCompletedCourses = useMemo(() => {
    return courses.filter((course) => !completedCourseIds.has(course.course_id));
  }, [courses, completedCourseIds]);

  const notCompletedTests = useMemo(() => {
    return tests.filter((test) => !isCompletedTest(test));
  }, [tests]);

  const materialProgressPercent = courses.length
    ? (completedCourseIds.size * 100) / courses.length
    : 0;

  const testsCompletedPercent = tests.length
    ? (completedTests.length * 100) / tests.length
    : 0;

  const correctAnswersPercent = completedTests.length
    ? completedTests.reduce((sum, test) => sum + (test.best_attempt_percent ?? 0), 0) / completedTests.length
    : 0;

const dialogScorePercent = 0;

const adaptationIndex =
  materialProgressPercent * 0.3 +
  correctAnswersPercent * 0.3 +
  dialogScorePercent * 0.4;
  const tasks = [
    ...notCompletedCourses.map((course) => ({
      id: `course-${course.course_id}`,
      title: `Пройти курс «${course.title}»`,
      type: 'course' as const,
      path: `/app/courses/${course.course_id}`,
    })),
    ...notCompletedTests.map((test) => ({
      id: `test-${test.test_id}`,
      title: `Пройти тест «${test.title}»`,
      type: 'test' as const,
      path: `/app/tests/${test.test_id}`,
    })),
  ];

  return (
    <section className="ui-page home-page">
      <h1 className="home-title">Добро пожаловать, {currentUser?.name ?? 'стажёр'}!</h1>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка главного экрана…</div>
      ) : (
        <>
          <div className="home-metrics-grid">
            <MetricCard
              title="Индекс адаптации"
              value={adaptationIndex}
              subtitle="по курсам, тестам и диалогам"
              tone="green"
            />
            <MetricCard
              title="Пройдено тестов"
              value={testsCompletedPercent}
              subtitle={`${completedTests.length} из ${tests.length}`}
              tone="orange"
            />
            <MetricCard
              title="Правильных ответов"
              value={correctAnswersPercent}
              subtitle="средний лучший результат"
              tone="red"
            />
          </div>

          <div className="home-section">
            <h2 className="home-section__title">Ваши задачи</h2>

            {tasks.length === 0 ? (
              <div className="ui-card ui-empty-card">
                На данный момент нет непройденных курсов и тестов.
              </div>
            ) : (
              <div className="home-task-list">
                {tasks.map((task, index) => (
                  <article key={task.id} className="home-task-row">
                    <div className="home-task-row__content">
                      <span className="home-task-row__number">{index + 1}.</span>
                      <span className="home-task-row__title">{task.title}</span>
                    </div>

                    <Button variant="outline" onClick={() => navigate(task.path)}>
                      перейти к задаче
                    </Button>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="home-section home-about-company">
            <h2 className="home-section__title">О компании</h2>
            <p>
              Компания занимается продажей продуктов и услуг, с которыми менеджер знакомится во время
              адаптации. Обучающие курсы, тесты и диалоговый тренажёр помогают быстрее освоить продукт,
              стандарты коммуникации и типовые сценарии работы с клиентами.
            </p>
          </div>
        </>
      )}
    </section>
  );
}

function ManagerHome() {
  const navigate = useNavigate();
  const currentUser = getStoredUser();

  const [employees, setEmployees] = useState<AnalyticsEmployeeCardDto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadEmployees() {
    setIsLoading(true);
    setError(null);

    try {
      const items = await getAnalyticsEmployees('', 'hire_date');
      setEmployees(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить сотрудников');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadEmployees();
  }, []);

  return (
    <section className="ui-page home-page">
      <h1 className="home-title">Добро пожаловать, {currentUser?.name ?? 'руководитель'}!</h1>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

      <div className="home-section">
        <h2 className="home-section__title">Ваши сотрудники</h2>

        {isLoading ? (
          <div className="ui-card ui-empty-card">Загрузка сотрудников…</div>
        ) : employees.length === 0 ? (
          <div className="ui-card ui-empty-card">
            Сотрудники не найдены. Проверьте, что в админ-панели сотрудники прикреплены к этому руководителю.
          </div>
        ) : (
          <div className="home-employee-list">
            {employees.map((employee, index) => (
              <button
                key={employee.employee_id}
                type="button"
                className="home-employee-row"
                onClick={() => navigate(`/app/analytics/employees/${employee.employee_id}`)}
              >
                <div className="home-employee-row__main">
                  <span className="home-employee-row__number">{index + 1}.</span>
                  <div>
                    <div className="home-employee-row__name">{employee.full_name}</div>
                    <div className="home-employee-row__meta">
                      Индекс адаптации: {formatPercent(employee.adaptation_index)} · Правильных ответов:{' '}
                      {formatPercent(employee.correct_answers_percent)}
                    </div>
                  </div>
                </div>

                <span className="home-employee-row__link">перейти к информации</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export function HomePage() {
  const currentUser = getStoredUser();

  if (isLearnerUser(currentUser)) {
    return <LearnerHome />;
  }

  return <ManagerHome />;
}