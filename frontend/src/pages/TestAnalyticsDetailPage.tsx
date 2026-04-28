import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AnalyticsTestDetailDto, getAnalyticsTestDetail } from '../api';
import '../styles/analytics.css';

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function formatDateTime(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('ru-RU');
}

export function TestAnalyticsDetailPage() {
  const { testId } = useParams();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<AnalyticsTestDetailDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDetail() {
    if (!testId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await getAnalyticsTestDetail(Number(testId));
      setDetail(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить аналитику по тесту');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDetail();
  }, [testId]);

  if (isLoading) {
    return (
      <section className="ui-page">
        <div className="ui-card ui-empty-card">Загрузка теста…</div>
      </section>
    );
  }

  if (error || !detail) {
    return (
      <section className="ui-page">
        <button
          type="button"
          className="ui-back-link"
          onClick={() => navigate('/app/analytics/tests')}
        >
          ← Назад к тестам
        </button>

        <div className="feedback-banner feedback-banner--error">
          {error ?? 'Тест не найден'}
        </div>
      </section>
    );
  }

  return (
    <section className="ui-page analytics-page">
      <button
        type="button"
        className="ui-back-link"
        onClick={() => navigate('/app/analytics/tests')}
      >
        ← Назад к тестам
      </button>

      <div className="analytics-test-detail-header ui-card ui-card--padded">
        <h1 className="analytics-test-detail-header__title">{detail.title}</h1>
        <p className="analytics-test-detail-header__line">Основан на курсе: {detail.course_title}</p>
        <p className="analytics-test-detail-header__line">Количество вопросов: {detail.question_count}</p>
        <p className="analytics-test-detail-header__line">Всего попыток: {detail.attempts_count}</p>
        <p className="analytics-test-detail-header__line">
          Сотрудников проходили: {detail.unique_employees_count}
        </p>
        <p className="analytics-test-detail-header__line">
          Средний лучший результат: {formatPercent(detail.avg_best_percent)}
        </p>
      </div>

      <div className="ui-card ui-card--padded analytics-block">
        <h2 className="analytics-block__title">Сотрудники, проходившие тест</h2>

        {detail.participants.length === 0 ? (
          <div className="ui-empty-card">Пока никто не проходил этот тест.</div>
        ) : (
          <div className="analytics-participants-list">
            {detail.participants.map((participant) => (
              <article key={participant.employee_id} className="analytics-participant-card">
                <div className="analytics-participant-card__main">
                  <h3 className="analytics-participant-card__name">{participant.full_name}</h3>
                  <p className="analytics-participant-card__email">{participant.email}</p>
                </div>

                <div className="analytics-participant-card__metric">
                  <div className="analytics-participant-card__value">
                    {formatPercent(participant.best_percent)}
                  </div>
                  <div className="analytics-participant-card__label">Лучший результат</div>
                </div>

                <div className="analytics-participant-card__metric">
                  <div className="analytics-participant-card__value">
                    {participant.attempts_count}
                  </div>
                  <div className="analytics-participant-card__label">Попыток</div>
                </div>

                <div className="analytics-participant-card__metric">
                  <div className="analytics-participant-card__value analytics-participant-card__value--small">
                    {formatDateTime(participant.last_completed_at)}
                  </div>
                  <div className="analytics-participant-card__label">Последнее прохождение</div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="ui-card ui-card--padded analytics-block">
        <h2 className="analytics-block__title">Топ-5 вопросов с ошибками</h2>

        {detail.top_errors.length === 0 ? (
          <div className="ui-empty-card">Пока нет данных по ошибкам в этом тесте.</div>
        ) : (
          <div className="analytics-errors-list">
            {detail.top_errors.map((errorItem) => (
              <article key={errorItem.question_id} className="analytics-error-card">
                <div className="analytics-error-card__top">
                  <span className="analytics-error-card__course">
                    Вопрос #{errorItem.question_id}
                  </span>
                  <span className="analytics-error-card__rate">
                    {formatPercent(errorItem.error_rate)}
                  </span>
                </div>

                <p className="analytics-error-card__question">{errorItem.question_text}</p>

                <p className="analytics-error-card__meta">
                  Ошибок: {errorItem.wrong_answers} из {errorItem.total_answers}
                </p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}