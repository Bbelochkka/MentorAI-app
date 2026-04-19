import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { TestDraftDto, getTest, updateTestStatus } from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';

export function TestDetailPage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const [test, setTest] = useState<TestDraftDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadTest() {
    if (!testId) {
      setError('Тест не найден');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await getTest(Number(testId));
      setTest(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить тест');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTest();
  }, [testId]);

  async function handlePublishToggle() {
    if (!test) return;

    const nextStatus = test.status === 'published' ? 'draft' : 'published';
    setIsUpdatingStatus(true);
    setError(null);
    setMessage(null);

    try {
      const updated = await updateTestStatus(test.test_id, { status: nextStatus });
      setTest(updated);
      setMessage(nextStatus === 'published' ? 'Тест опубликован' : 'Тест снят с публикации');
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Не удалось обновить статус');
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  return (
    <section className="ui-page">
      <div style={{ marginBottom: 18 }}>
        <button type="button" className="ui-back-link" onClick={() => navigate('/app/tests')}>
          ← Назад к списку тестов
        </button>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка теста…</div>
      ) : !test ? (
        <div className="ui-card ui-empty-card">Тест не найден.</div>
      ) : (
        <>
          <div className="ui-page__header">
            <div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
                <StatusBadge status={test.status} />
                <span className="document-list-item__meta">Курс: {test.course_title}</span>
              </div>
              <h1 className="ui-page__title">{test.title}</h1>
              <p className="ui-page__subtitle">Вопросов: {test.question_count}</p>
            </div>
            <div className="ui-detail-actions">
              <Button
                variant={test.status === 'published' ? 'outline' : 'primary'}
                onClick={() => void handlePublishToggle()}
                disabled={isUpdatingStatus}
              >
                {isUpdatingStatus ? 'Сохраняем…' : test.status === 'published' ? 'Снять с публикации' : 'Опубликовать тест'}
              </Button>
              <Link className="ui-btn ui-btn--outline ui-btn--sm" to={`/app/courses/${test.course_id}`}>
                Открыть курс-источник
              </Link>
            </div>
          </div>

          <div className="ui-list">
            {test.questions.map((question) => (
              <article key={question.id} className="ui-section">
                <h2 className="ui-topic-title" style={{ marginTop: 0 }}>
                  Вопрос {question.order_index}
                </h2>
                <p style={{ margin: '0 0 14px', color: 'var(--ui-text)', fontSize: 16, lineHeight: 1.6 }}>
                  {question.question_text}
                </p>
                <div className="ui-list">
                  {question.options.map((option, index) => (
                    <div
                      key={option.id}
                      className="ui-card ui-card--padded"
                      style={{
                        borderColor: option.is_correct ? 'var(--ui-success-border)' : 'var(--ui-border-soft)',
                        background: option.is_correct ? 'var(--ui-success-bg)' : '#fffdfa',
                        padding: '14px 18px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center' }}>
                        <span style={{ color: 'var(--ui-text)', lineHeight: 1.5 }}>
                          {String.fromCharCode(65 + index)}. {option.text}
                        </span>
                        {option.is_correct ? (
                          <span
                            style={{
                              flexShrink: 0,
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '6px 10px',
                              borderRadius: 999,
                              border: '1px solid var(--ui-success-border)',
                              background: 'var(--ui-success-bg)',
                              color: 'var(--ui-success-text)',
                              fontSize: 13,
                              fontWeight: 600,
                            }}
                          >
                            Правильный ответ
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
