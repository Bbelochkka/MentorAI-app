import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnalyticsTestCardDto, getAnalyticsTests } from '../api';
import { Button } from '../components/ui/Button';
import '../styles/analytics.css';

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

export function AnalyticsTestsPage() {
  const navigate = useNavigate();

  const [tests, setTests] = useState<AnalyticsTestCardDto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadTests() {
    setIsLoading(true);
    setError(null);

    try {
      const items = await getAnalyticsTests();
      setTests(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить аналитику по тестам');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTests();
  }, []);

  return (
    <section className="ui-page analytics-page">
      <div className="analytics-breadcrumbs">Главная &gt; Аналитика</div>

      <div className="analytics-tabs">
        <button
          type="button"
          className="analytics-tab"
          onClick={() => navigate('/app/analytics')}
        >
          Сотрудники
        </button>
        <button type="button" className="analytics-tab analytics-tab--active">
          Тест
        </button>
      </div>

      <div className="ui-page__header" style={{ marginBottom: 0 }}>
        <div>
          <h1 className="ui-page__title">Тесты</h1>
          <p className="ui-page__subtitle">
            Выберите тест и откройте подробную аналитику по его прохождению.
          </p>
        </div>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка аналитики по тестам…</div>
      ) : tests.length === 0 ? (
        <div className="ui-card ui-empty-card">Тесты пока не найдены.</div>
      ) : (
        <div className="analytics-test-list">
          {tests.map((test) => (
            <article key={test.test_id} className="analytics-test-card">
              <div className="analytics-test-card__main">
                <h3 className="analytics-test-card__title">{test.title}</h3>
                <p className="analytics-test-card__meta">Курс: {test.course_title}</p>
              </div>

              <div className="analytics-test-card__metric">
                <div className="analytics-test-card__value">{test.question_count}</div>
                <div className="analytics-test-card__label">Вопросов</div>
              </div>

              <div className="analytics-test-card__metric">
                <div className="analytics-test-card__value">{test.unique_employees_count}</div>
                <div className="analytics-test-card__label">Сотрудников проходили</div>
              </div>

              <div className="analytics-test-card__metric">
                <div className="analytics-test-card__value analytics-test-card__value--accent">
                  {formatPercent(test.avg_best_percent)}
                </div>
                <div className="analytics-test-card__label">Средний лучший результат</div>
              </div>

              <div className="analytics-test-card__actions">
                <Button
                  variant="primary"
                  onClick={() => navigate(`/app/analytics/tests/${test.test_id}`)}
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