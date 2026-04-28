import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AnalyticsEmployeeCardDto,
  AnalyticsEmployeeSort,
  getAnalyticsEmployees,
  getStoredUser,
  isLearnerUser,
} from '../api';
import { Button } from '../components/ui/Button';
import '../styles/analytics.css';

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('ru-RU');
}

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

export function AnalyticsEmployeesPage() {
  const navigate = useNavigate();
  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);

  const [employees, setEmployees] = useState<AnalyticsEmployeeCardDto[]>([]);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<AnalyticsEmployeeSort>('hire_date');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadEmployees(currentSearch: string, currentSort: AnalyticsEmployeeSort) {
    setIsLoading(true);
    setError(null);

    try {
      const items = await getAnalyticsEmployees(currentSearch, currentSort);
      setEmployees(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить аналитику');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (learner) return;

    const timer = window.setTimeout(() => {
      void loadEmployees(search, sort);
    }, 250);

    return () => window.clearTimeout(timer);
  }, [search, sort, learner]);

  if (learner) {
    return (
      <section className="ui-page">
        <div className="ui-card ui-empty-card">
          Раздел аналитики пока доступен только руководителю.
        </div>
      </section>
    );
  }

  return (
    <section className="ui-page analytics-page">
      <div className="analytics-breadcrumbs">Главная &gt; Аналитика</div>

      <div className="analytics-tabs">
        <button type="button" className="analytics-tab analytics-tab--active">
          Сотрудники
        </button>
        <button
    type="button"
    className="analytics-tab"
    onClick={() => navigate('/app/analytics/tests')}
  >
    Тест
  </button>
      </div>

      <div className="analytics-toolbar">
        <input
          className="analytics-search"
          type="text"
          placeholder="Введите ФИО сотрудника"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select
          className="analytics-select"
          value={sort}
          onChange={(event) => setSort(event.target.value as AnalyticsEmployeeSort)}
        >
          <option value="hire_date">По дате приёма</option>
          <option value="adaptation">По индексу адаптации</option>
          <option value="correct_answers">По правильным ответам</option>
        </select>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка аналитики…</div>
      ) : employees.length === 0 ? (
        <div className="ui-card ui-empty-card">Сотрудники не найдены.</div>
      ) : (
        <div className="analytics-employee-list">
          {employees.map((employee) => (
            <article key={employee.employee_id} className="analytics-employee-card">
              <div className="analytics-employee-card__name-block">
                <h3 className="analytics-employee-card__name">{employee.full_name}</h3>
                <p className="analytics-employee-card__meta">{employee.role_label}</p>
              </div>

              <div className="analytics-employee-card__metric">
                <div className="analytics-employee-card__value">{formatDate(employee.hire_date)}</div>
                <div className="analytics-employee-card__label">Дата приёма</div>
              </div>

              <div className="analytics-employee-card__metric">
                <div className="analytics-employee-card__value analytics-employee-card__value--accent">
                  {formatPercent(employee.adaptation_index)}
                </div>
                <div className="analytics-employee-card__label">Индекс адаптации</div>
              </div>

              <div className="analytics-employee-card__metric">
                <div className="analytics-employee-card__value analytics-employee-card__value--success">
                  {formatPercent(employee.correct_answers_percent)}
                </div>
                <div className="analytics-employee-card__label">Правильных ответов</div>
              </div>

              <div className="analytics-employee-card__actions">
                <Button
                  variant="primary"
                  onClick={() => navigate(`/app/analytics/employees/${employee.employee_id}`)}
                >
                  Подробнее
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}