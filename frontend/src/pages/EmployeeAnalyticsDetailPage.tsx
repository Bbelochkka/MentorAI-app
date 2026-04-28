import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AnalyticsCourseResultDto,
  AnalyticsEmployeeDetailDto,
  getAnalyticsEmployeeDetail,
} from '../api';
import '../styles/analytics.css';

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('ru-RU');
}

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function getExperienceLabel(hireDate: string) {
  const start = new Date(hireDate);
  const now = new Date();

  let months =
    (now.getFullYear() - start.getFullYear()) * 12 +
    (now.getMonth() - start.getMonth());

  if (now.getDate() < start.getDate()) {
    months -= 1;
  }

  months = Math.max(months, 0);

  const mod10 = months % 10;
  const mod100 = months % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return `${months} месяц`;
  }
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) {
    return `${months} месяца`;
  }
  return `${months} месяцев`;
}

function toneClass(value: number) {
  if (value < 40) return 'is-low';
  if (value < 70) return 'is-medium';
  return 'is-high';
}

function CircleMetricCard({
  value,
  title,
  subtitle,
  tone,
}: {
  value: number;
  title: string;
  subtitle: string;
  tone: 'green' | 'orange' | 'red';
}) {
  const safeValue = Math.max(0, Math.min(100, value));
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - safeValue / 100);

  return (
    <article className="analytics-circle-card ui-card ui-card--padded">
      <div className={`analytics-circle analytics-circle--${tone}`}>
        <svg viewBox="0 0 120 120" className="analytics-circle__svg">
          <circle cx="60" cy="60" r={radius} className="analytics-circle__track" />
          <circle
            cx="60"
            cy="60"
            r={radius}
            className="analytics-circle__progress"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="analytics-circle__value">{formatPercent(safeValue)}</div>
      </div>

      <div className="analytics-circle-card__content">
        <h3 className="analytics-circle-card__title">{title}</h3>
        <p className="analytics-circle-card__subtitle">{subtitle}</p>
      </div>
    </article>
  );
}

function CourseRow({ item }: { item: AnalyticsCourseResultDto }) {
  const value = Math.max(0, Math.min(100, item.correct_answers_percent));
  const tone = toneClass(value);

  return (
    <div className="analytics-progress-row">
      <div className="analytics-progress-row__label">{item.course_title}</div>
      <div className="analytics-progress-row__track">
        <div
          className={`analytics-progress-row__fill ${tone}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <div className={`analytics-progress-row__value ${tone}`}>{formatPercent(value)}</div>
    </div>
  );
}

export function EmployeeAnalyticsDetailPage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<AnalyticsEmployeeDetailDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDetail() {
    if (!employeeId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await getAnalyticsEmployeeDetail(Number(employeeId));
      setDetail(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить сотрудника');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDetail();
  }, [employeeId]);

  const sortedCourses = useMemo(() => {
    if (!detail) return [];
    return [...detail.course_results].sort(
      (a, b) => b.correct_answers_percent - a.correct_answers_percent
    );
  }, [detail]);

  if (isLoading) {
    return (
      <section className="ui-page">
        <div className="ui-card ui-empty-card">Загрузка аналитики сотрудника…</div>
      </section>
    );
  }

  if (error || !detail) {
    return (
      <section className="ui-page">
        <button type="button" className="ui-back-link" onClick={() => navigate('/app/analytics')}>
          ← Назад к аналитике
        </button>
        <div className="feedback-banner feedback-banner--error">
          {error ?? 'Сотрудник не найден'}
        </div>
      </section>
    );
  }

  return (
    <section className="ui-page analytics-page">
      <button type="button" className="ui-back-link" onClick={() => navigate('/app/analytics')}>
        ← Назад к аналитике
      </button>

      <div className="analytics-employee-header ui-card ui-card--padded">
        <h1 className="analytics-employee-header__name">{detail.employee.full_name}</h1>
        <p className="analytics-employee-header__line">
          {detail.employee.role_label}, {detail.employee.email}
        </p>
        <p className="analytics-employee-header__line">
          Дата приёма: {formatDate(detail.employee.hire_date)}
        </p>
        <p className="analytics-employee-header__line">
          Стаж: {getExperienceLabel(detail.employee.hire_date)}
        </p>
      </div>

      <div className="analytics-circle-grid">
        <CircleMetricCard
          value={detail.employee.adaptation_index}
          title="Индекс адаптации"
          subtitle={`M ${formatPercent(detail.employee.material_progress_percent)} · D ${formatPercent(detail.employee.dialog_score_percent)}`}
          tone="green"
        />

        <CircleMetricCard
          value={detail.employee.tests_completed_percent}
          title="Пройдено тестов"
          subtitle={`${detail.completed_tests_count} завершённых тестов`}
          tone="orange"
        />

        <CircleMetricCard
          value={detail.employee.correct_answers_percent}
          title="Процент правильных ответов"
          subtitle={`${detail.completed_dialogs_count} завершённых диалогов`}
          tone="red"
        />
      </div>

      <div className="ui-card ui-card--padded analytics-block">
        <h2 className="analytics-block__title">Процент правильных ответов по курсам</h2>

        {sortedCourses.length === 0 ? (
          <div className="ui-empty-card">Пока нет данных по курсам.</div>
        ) : (
          <div className="analytics-progress-list">
            {sortedCourses.map((item) => (
              <CourseRow key={item.course_id} item={item} />
            ))}
          </div>
        )}
      </div>

      <div className="ui-card ui-card--padded analytics-block">
        <h2 className="analytics-block__title">Типичные ошибки</h2>

        {detail.typical_errors.length === 0 ? (
          <div className="ui-empty-card">Пока нет зафиксированных типичных ошибок.</div>
        ) : (
          <div className="analytics-errors-list">
            {detail.typical_errors.map((errorItem) => (
              <article key={errorItem.question_id} className="analytics-error-card">
                <div className="analytics-error-card__top">
                  <span className="analytics-error-card__course">{errorItem.course_title}</span>
                  <span className="analytics-error-card__rate">
                    {formatPercent(errorItem.error_rate)}
                  </span>
                </div>

                <p className="analytics-error-card__question">{errorItem.question_text}</p>

                <p className="analytics-error-card__meta">
                  Неверных ответов: {errorItem.wrong_answers} из {errorItem.total_answers}
                </p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}