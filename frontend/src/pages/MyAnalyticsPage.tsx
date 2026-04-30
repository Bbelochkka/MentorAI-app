import { useEffect, useMemo, useState } from 'react';
import {
  AnalyticsCourseResultDto,
  AnalyticsEmployeeDetailDto,
  getMyAnalytics,
} from '../api';
import '../styles/analytics.css';

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('ru-RU');
}

function toneClass(value: number) {
  if (value < 40) return 'is-low';
  if (value < 70) return 'is-medium';
  return 'is-high';
}

function ProgressRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const safeValue = Math.max(0, Math.min(100, value));
  const tone = toneClass(safeValue);

  return (
    <div className="analytics-progress-row">
      <div className="analytics-progress-row__label">{label}</div>

      <div className="analytics-progress-row__track">
        <div
          className={`analytics-progress-row__fill ${tone}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>

      <div className={`analytics-progress-row__value ${tone}`}>
        {formatPercent(safeValue)}
      </div>
    </div>
  );
}

function CourseRow({ item }: { item: AnalyticsCourseResultDto }) {
  return (
    <ProgressRow
      label={item.course_title}
      value={item.correct_answers_percent}
    />
  );
}

export function MyAnalyticsPage() {
  const [detail, setDetail] = useState<AnalyticsEmployeeDetailDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadMyAnalytics() {
    setIsLoading(true);
    setError(null);

    try {
      const data = await getMyAnalytics();
      setDetail(data);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Не удалось загрузить личную аналитику'
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadMyAnalytics();
  }, []);

  const sortedCourses = useMemo(() => {
    if (!detail) return [];

    return [...detail.course_results].sort(
      (a, b) => b.correct_answers_percent - a.correct_answers_percent
    );
  }, [detail]);

  if (isLoading) {
    return (
      <div className="analytics-page">
        <p>Загрузка личной аналитики…</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="analytics-page">
        <div className="analytics-breadcrumbs">Главная &gt; Моя аналитика</div>
        <div className="ui-alert ui-alert--error">
          {error ?? 'Данные аналитики не найдены'}
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="analytics-breadcrumbs">Главная &gt; Моя аналитика</div>

      <div className="analytics-employee-header">
        <h1 className="analytics-employee-header__name">Моя аналитика</h1>
        <p className="analytics-employee-header__line">
          {detail.employee.full_name}
        </p>
        <p className="analytics-employee-header__line">
          Дата приёма: {formatDate(detail.employee.hire_date)}
        </p>
      </div>

      <section className="analytics-block">
        <h2 className="analytics-block__title">Общий прогресс адаптации</h2>

        <div className="analytics-progress-list">
          <ProgressRow
            label="Индекс адаптации"
            value={detail.employee.adaptation_index}
          />
          <ProgressRow
            label="Освоение материалов"
            value={detail.employee.material_progress_percent}
          />
          <ProgressRow
            label="Пройденные тесты"
            value={detail.employee.tests_completed_percent}
          />
          <ProgressRow
            label="Правильные ответы"
            value={detail.employee.correct_answers_percent}
          />
          <ProgressRow
            label="Диалоговый тренажёр"
            value={detail.employee.dialog_score_percent}
          />
        </div>
      </section>

      <section className="analytics-block">
        <h2 className="analytics-block__title">Результаты по курсам</h2>

        {sortedCourses.length === 0 ? (
          <p>Пока нет данных по курсам.</p>
        ) : (
          <div className="analytics-progress-list">
            {sortedCourses.map((item) => (
              <CourseRow key={item.course_id} item={item} />
            ))}
          </div>
        )}
      </section>

      <section className="analytics-block">
        <h2 className="analytics-block__title">Мои типичные ошибки</h2>

        {detail.typical_errors.length === 0 ? (
          <p>Пока нет зафиксированных типичных ошибок.</p>
        ) : (
          <div className="analytics-errors-list">
            {detail.typical_errors.map((errorItem) => (
              <div
                className="analytics-error-card"
                key={errorItem.question_id}
              >
                <div className="analytics-error-card__top">
                  <span className="analytics-error-card__course">
                    {errorItem.course_title}
                  </span>
                  <span className="analytics-error-card__rate">
                    {formatPercent(errorItem.error_rate)}
                  </span>
                </div>

                <p className="analytics-error-card__question">
                  {errorItem.question_text}
                </p>

                <p className="analytics-error-card__meta">
                  Неверных ответов: {errorItem.wrong_answers} из{' '}
                  {errorItem.total_answers}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}