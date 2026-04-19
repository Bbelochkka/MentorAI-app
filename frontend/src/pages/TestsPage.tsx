import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  CourseSummaryDto,
  TestSummaryDto,
  deleteTest,
  generateTestDraft,
  getCourses,
  getTests,
  updateTestStatus,
} from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';

export function TestsPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<CourseSummaryDto[]>([]);
  const [tests, setTests] = useState<TestSummaryDto[]>([]);
  const [title, setTitle] = useState('');
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [desiredQuestionCount, setDesiredQuestionCount] = useState('10');
  const [requiredQuestions, setRequiredQuestions] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const [courseItems, testItems] = await Promise.all([getCourses(), getTests()]);
      const eligibleCourses = courseItems.filter((course) => course.source_documents && course.source_documents.length > 0);
      setCourses(eligibleCourses);
      setTests(testItems);
      setSelectedCourseId((prev) => prev ?? eligibleCourses[0]?.course_id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить тесты');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const selectedCourse = useMemo(() => courses.find((course) => course.course_id === selectedCourseId) ?? null, [courses, selectedCourseId]);

  async function handleGenerate() {
    if (!title.trim()) {
      setError('Введите название теста');
      return;
    }
    if (!selectedCourseId) {
      setError('Выберите курс');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setMessage(null);
    try {
      const created = await generateTestDraft({
        title: title.trim(),
        course_id: selectedCourseId,
        desired_question_count: desiredQuestionCount.trim() || undefined,
        required_questions: requiredQuestions.trim() || undefined,
      });
      setTitle('');
      setRequiredQuestions('');
      setDesiredQuestionCount('10');
      setMessage('Черновик теста успешно создан');
      await loadData();
      navigate(`/app/tests/${created.test_id}`);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : 'Не удалось сгенерировать тест');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDelete(testId: number) {
    if (!window.confirm('Удалить тест? Это действие нельзя отменить.')) return;
    try {
      await deleteTest(testId);
      setMessage('Тест удалён');
      await loadData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Не удалось удалить тест');
    }
  }

  async function handlePublishToggle(test: TestSummaryDto) {
    const nextStatus = test.status === 'published' ? 'draft' : 'published';
    try {
      await updateTestStatus(test.test_id, { status: nextStatus });
      setMessage(nextStatus === 'published' ? 'Тест опубликован' : 'Тест снят с публикации');
      await loadData();
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Не удалось обновить статус теста');
    }
  }

  return (
    <section className="ui-page">
      <div className="ui-page__header">
        <div>
          <h1 className="ui-page__title">Тесты</h1>
          <p className="ui-page__subtitle">
            Выберите один курс вашей компании и сгенерируйте по нему тест с закрытыми вопросами.
          </p>
        </div>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      <div className="ui-card ui-card--padded" style={{ marginBottom: 24 }}>
        <div style={{ display: 'grid', gap: 18, gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
          <div className="ui-field">
            <label className="ui-field__label">Название теста</label>
            <input className="ui-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Например: Итоговый тест по NovaCRM" />
          </div>
          <div className="ui-field">
            <label className="ui-field__label">Курс-источник</label>
            <select className="ui-input" value={selectedCourseId ?? ''} onChange={(event) => setSelectedCourseId(event.target.value ? Number(event.target.value) : null)}>
              <option value="">Выберите курс</option>
              {courses.map((course) => (
                <option key={course.course_id} value={course.course_id}>
                  {course.title}
                </option>
              ))}
            </select>
          </div>
          <div className="ui-field">
            <label className="ui-field__label">Желаемое количество вопросов</label>
            <input className="ui-input" value={desiredQuestionCount} onChange={(event) => setDesiredQuestionCount(event.target.value)} placeholder="От 1 до 30" />
          </div>
          <div className="ui-field">
            <label className="ui-field__label">Обязательные вопросы</label>
            <textarea
              className="ui-textarea"
              rows={4}
              value={requiredQuestions}
              onChange={(event) => setRequiredQuestions(event.target.value)}
              placeholder={'Каждый пункт с новой строки или через ;\nНапример:\nматрица скидок\nKPI менеджера\nправила пилотного периода'}
            />
          </div>
        </div>

        {selectedCourse ? <p className="ui-page__subtitle" style={{ marginTop: 14 }}>Источник: <strong>{selectedCourse.title}</strong></p> : null}

        <div className="ui-detail-actions" style={{ marginTop: 18 }}>
          <Button onClick={() => void handleGenerate()} disabled={isGenerating}>
            {isGenerating ? 'Генерация…' : 'Сгенерировать тест'}
          </Button>
          <Button variant="outline" onClick={() => void loadData()} disabled={isLoading}>
            Обновить
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="ui-card ui-empty-card">Загрузка тестов…</div>
      ) : tests.length === 0 ? (
        <div className="ui-card ui-empty-card">Тесты ещё не созданы.</div>
      ) : (
        <div className="ui-list">
          {tests.map((test) => (
            <article key={test.test_id} className="ui-card ui-card--padded course-list-card">
              <div className="course-list-card__body">
                <div className="course-list-card__left">
                  <div className="course-list-card__top">
                    <StatusBadge status={test.status} />
                    <Button variant={test.status === 'published' ? 'outline' : 'primary'} onClick={() => void handlePublishToggle(test)}>
                      {test.status === 'published' ? 'Снять с публикации' : 'Опубликовать'}
                    </Button>
                  </div>
                  <h2 className="course-list-card__title">{test.title}</h2>
                  <p className="course-list-card__description">Курс-источник: {test.course_title}</p>
                  <p className="course-list-card__meta">Вопросов: {test.question_count}</p>
                </div>
                <div className="course-list-card__actions">
                  <Link className="ui-btn ui-btn--primary ui-btn--sm" to={`/app/tests/${test.test_id}`}>
                    Перейти
                  </Link>
                  <Button variant="outline" onClick={() => void handleDelete(test.test_id)}>Удалить</Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
