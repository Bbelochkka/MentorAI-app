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
function getPercentTone(value: number): 'green' | 'orange' | 'red' {
  if (value < 40) {
    return 'red';
  }

  if (value < 70) {
    return 'orange';
  }

  return 'green';
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
function ManagerSummaryCard({
  title,
  value,
  subtitle,
  tone = 'default',
}: {
  title: string;
  value: string;
  subtitle: string;
  tone?: 'default' | 'green' | 'orange' | 'red';
}) {
  return (
    <article className={`manager-summary-card manager-summary-card--${tone}`}>
      <div className="manager-summary-card__badge">
        <div className="manager-summary-card__value">{value}</div>
      </div>

      <div className="manager-summary-card__content">
        <h3 className="manager-summary-card__title">{title}</h3>
        {subtitle ? <p className="manager-summary-card__subtitle">{subtitle}</p> : null}
      </div>
    </article>
  );
}

function isEmployeeAtRisk(employee: AnalyticsEmployeeCardDto) {
  return (
    employee.adaptation_index < 40 ||
    employee.tests_completed_percent < 50 ||
    employee.correct_answers_percent < 50 ||
    employee.material_progress_percent < 50
  );
}

function getRiskReason(employee: AnalyticsEmployeeCardDto) {
  if (employee.adaptation_index < 40) {
    return 'низкий индекс адаптации';
  }

  if (employee.tests_completed_percent < 50) {
    return 'пройдено мало тестов';
  }

  if (employee.correct_answers_percent < 50) {
    return 'низкий результат по тестам';
  }

  if (employee.material_progress_percent < 50) {
    return 'не завершены учебные материалы';
  }

  return 'требуется внимание руководителя';
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

  const averageAdaptation = employees.length
    ? employees.reduce((sum, employee) => sum + employee.adaptation_index, 0) / employees.length
    : 0;

  const averageCorrectAnswers = employees.length
    ? employees.reduce((sum, employee) => sum + employee.correct_answers_percent, 0) / employees.length
    : 0;

  const riskEmployees = employees.filter(isEmployeeAtRisk);

  return (
    <section className="ui-page home-page manager-home-page">
      <div className="manager-home-header">
        <h1 className="home-title">Добро пожаловать, {currentUser?.name ?? 'руководитель'}!</h1>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка главного экрана…</div>
      ) : employees.length === 0 ? (
        <div className="ui-card ui-empty-card">
          Сотрудники не найдены. Проверьте, что сотрудники прикреплены к этому руководителю.
        </div>
      ) : (
        <>
          <div className="manager-summary-grid">
            <ManagerSummaryCard
              title="Всего сотрудников"
              value={String(employees.length)}
              subtitle="под вашим руководством"
              tone="green"
            />

            <MetricCard
              title="Средняя адаптация"
              value={averageAdaptation}
              subtitle="средний индекс по команде"
              tone={getPercentTone(averageAdaptation)}
            />

            <MetricCard
              title="Правильных ответов"
              value={averageCorrectAnswers}
              subtitle="средний результат тестов"
              tone={getPercentTone(averageCorrectAnswers)}
            />
          </div>

          <div className="home-section">
            <div className="manager-section-header">
              <div>
                <h2 className="home-section__title">Сотрудники, требующие внимания</h2>
                <p className="manager-section-subtitle">
                  В этот блок попадают сотрудники с низким индексом адаптации, слабым результатом тестов
                  или незавершёнными материалами.
                </p>
              </div>
            </div>

            {riskEmployees.length === 0 ? (
              <div className="ui-card ui-empty-card">
                Сейчас нет сотрудников в зоне риска. Команда проходит адаптацию стабильно.
              </div>
            ) : (
              <div className="manager-risk-list">
                {riskEmployees.map((employee) => (
                  <article key={employee.employee_id} className="manager-risk-card">
                    <div>
                      <div className="manager-risk-card__top">
                        <h3 className="manager-risk-card__name">{employee.full_name}</h3>
                        <span className="manager-risk-badge">в риске</span>
                      </div>

                      <p className="manager-risk-card__reason">
                        Причина: {getRiskReason(employee)}
                      </p>

                      <div className="manager-risk-card__metrics">
                        <span>Адаптация: {formatPercent(employee.adaptation_index)}</span>
                        <span>Материалы: {formatPercent(employee.material_progress_percent)}</span>
                        <span>Тесты: {formatPercent(employee.tests_completed_percent)}</span>
                        <span>Ответы: {formatPercent(employee.correct_answers_percent)}</span>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      onClick={() => navigate(`/app/analytics/employees/${employee.employee_id}`)}
                    >
                      Подробнее
                    </Button>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="home-section">
            <h2 className="home-section__title">Все сотрудники</h2>

            <div className="manager-employee-grid">
              {employees.map((employee) => {
                const atRisk = isEmployeeAtRisk(employee);

                return (
                  <button
                    key={employee.employee_id}
                    type="button"
                    className={`manager-employee-card ${atRisk ? 'manager-employee-card--risk' : ''}`}
                    onClick={() => navigate(`/app/analytics/employees/${employee.employee_id}`)}
                  >
                    <div className="manager-employee-card__header">
                      <h3 className="manager-employee-card__name">{employee.full_name}</h3>
                      <span className={`manager-status ${atRisk ? 'manager-status--risk' : 'manager-status--ok'}`}>
                        {atRisk ? 'требует внимания' : 'стабильно'}
                      </span>
                    </div>

                    <div className="manager-employee-card__metrics">
                      <div>
                        <span>Индекс адаптации</span>
                        <strong>{formatPercent(employee.adaptation_index)}</strong>
                      </div>

                      <div>
                        <span>Правильных ответов</span>
                        <strong>{formatPercent(employee.correct_answers_percent)}</strong>
                      </div>
                    </div>

                    <span className="manager-employee-card__link">перейти к информации</span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
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