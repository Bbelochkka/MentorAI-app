
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { TestDraftDto, deleteTest, getTest, updateTestDraft, updateTestStatus } from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';

type EditableOption = {
  id: number;
  text: string;
  is_correct: boolean;
  order_index: number;
};

type EditableQuestion = {
  id: number;
  question_text: string;
  order_index: number;
  options: EditableOption[];
};

type EditableTest = {
  test_id: number;
  title: string;
  status: string;
  course_id: number;
  course_title: string;
  question_count: number;
  questions: EditableQuestion[];
};

function cloneTest(test: TestDraftDto): EditableTest {
  return {
    ...test,
    questions: test.questions.map((question) => ({
      ...question,
      options: question.options.map((option) => ({ ...option })),
    })),
  };
}

function normalizeForCompare(test: EditableTest | TestDraftDto | null): string {
  if (!test) return '';
  return JSON.stringify({
    title: test.title,
    questions: test.questions.map((question) => ({
      question_text: question.question_text.trim(),
      order_index: question.order_index,
      options: question.options.map((option) => ({
        text: option.text.trim(),
        is_correct: option.is_correct,
        order_index: option.order_index,
      })),
    })),
  });
}

export function TestDetailPage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const tempIdRef = useRef(-1);
  const [test, setTest] = useState<TestDraftDto | null>(null);
  const [editableTest, setEditableTest] = useState<EditableTest | null>(null);
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function nextTempId() {
    const value = tempIdRef.current;
    tempIdRef.current -= 1;
    return value;
  }

  const testToRender = isEditingDraft ? editableTest : test;
  const hasUnsavedChanges = useMemo(() => {
    if (!isEditingDraft || !test || !editableTest) return false;
    return normalizeForCompare(test) !== normalizeForCompare(editableTest);
  }, [editableTest, isEditingDraft, test]);

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
      setEditableTest(null);
      setIsEditingDraft(false);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить тест');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTest();
  }, [testId]);

  function handleStartEditing() {
    if (!test) return;
    setEditableTest(cloneTest(test));
    setIsEditingDraft(true);
    setMessage(null);
    setError(null);
  }

  function handleCancelEditing() {
    if (hasUnsavedChanges && !window.confirm('Отменить несохранённые изменения?')) return;
    setEditableTest(null);
    setIsEditingDraft(false);
  }

  function updateEditableTest(updater: (draft: EditableTest) => EditableTest) {
    setEditableTest((current) => (current ? updater(current) : current));
  }

  function handleTestTitleChange(value: string) {
    updateEditableTest((draft) => ({ ...draft, title: value }));
  }

  function handleQuestionTextChange(questionId: number, value: string) {
    updateEditableTest((draft) => ({
      ...draft,
      questions: draft.questions.map((question) => question.id === questionId ? { ...question, question_text: value } : question),
    }));
  }

  function handleOptionTextChange(questionId: number, optionId: number, value: string) {
    updateEditableTest((draft) => ({
      ...draft,
      questions: draft.questions.map((question) => question.id !== questionId
        ? question
        : {
            ...question,
            options: question.options.map((option) => option.id === optionId ? { ...option, text: value } : option),
          }),
    }));
  }

  function handleCorrectOptionChange(questionId: number, optionId: number) {
    updateEditableTest((draft) => ({
      ...draft,
      questions: draft.questions.map((question) => question.id !== questionId
        ? question
        : {
            ...question,
            options: question.options.map((option) => ({ ...option, is_correct: option.id === optionId })),
          }),
    }));
  }

  function handleAddQuestion() {
    updateEditableTest((draft) => ({
      ...draft,
      questions: [
        ...draft.questions,
        {
          id: nextTempId(),
          question_text: 'Новый вопрос',
          order_index: draft.questions.length + 1,
          options: [
            { id: nextTempId(), text: 'Вариант 1', is_correct: true, order_index: 1 },
            { id: nextTempId(), text: 'Вариант 2', is_correct: false, order_index: 2 },
            { id: nextTempId(), text: 'Вариант 3', is_correct: false, order_index: 3 },
            { id: nextTempId(), text: 'Вариант 4', is_correct: false, order_index: 4 },
          ],
        },
      ],
      question_count: draft.questions.length + 1,
    }));
  }

  function handleDeleteQuestion(questionId: number) {
    if (!window.confirm('Удалить вопрос из теста?')) return;
    updateEditableTest((draft) => {
      const nextQuestions = draft.questions
        .filter((question) => question.id !== questionId)
        .map((question, index) => ({ ...question, order_index: index + 1 }));
      return { ...draft, questions: nextQuestions, question_count: nextQuestions.length };
    });
  }

  function handleAddOption(questionId: number) {
    updateEditableTest((draft) => ({
      ...draft,
      questions: draft.questions.map((question) => question.id !== questionId
        ? question
        : {
            ...question,
            options: [
              ...question.options,
              { id: nextTempId(), text: `Вариант ${question.options.length + 1}`, is_correct: false, order_index: question.options.length + 1 },
            ],
          }),
    }));
  }

  function handleDeleteOption(questionId: number, optionId: number) {
    const target = editableTest?.questions.find((question) => question.id === questionId);
    if (!target || target.options.length <= 2) {
      setError('У вопроса должно остаться минимум два варианта ответа');
      return;
    }
    updateEditableTest((draft) => ({
      ...draft,
      questions: draft.questions.map((question) => {
        if (question.id !== questionId) return question;
        const nextOptions = question.options
          .filter((option) => option.id !== optionId)
          .map((option, index) => ({ ...option, order_index: index + 1 }));
        if (!nextOptions.some((option) => option.is_correct)) {
          nextOptions[0] = { ...nextOptions[0], is_correct: true };
        }
        return { ...question, options: nextOptions };
      }),
    }));
  }

  async function handleSaveDraft() {
    if (!test || !editableTest) return;
    setIsSavingDraft(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateTestDraft(test.test_id, {
        title: editableTest.title,
        questions: editableTest.questions.map((question, questionIndex) => ({
          id: question.id > 0 ? question.id : undefined,
          question_text: question.question_text,
          order_index: questionIndex + 1,
          options: question.options.map((option, optionIndex) => ({
            id: option.id > 0 ? option.id : undefined,
            text: option.text,
            is_correct: option.is_correct,
            order_index: optionIndex + 1,
          })),
        })),
      });
      setTest(updated);
      setEditableTest(null);
      setIsEditingDraft(false);
      setMessage('Изменения сохранены');
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Не удалось сохранить изменения');
    } finally {
      setIsSavingDraft(false);
    }
  }

  async function handlePublishToggle() {
    if (!test) return;
    const nextStatus = test.status === 'published' ? 'draft' : 'published';
    setIsUpdatingStatus(true);
    setError(null);
    setMessage(null);

    try {
      const updated = await updateTestStatus(test.test_id, { status: nextStatus });
      setTest(updated);
      if (isEditingDraft) {
        setEditableTest(cloneTest(updated));
      }
      setMessage(nextStatus === 'published' ? 'Тест опубликован' : 'Тест снят с публикации');
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Не удалось обновить статус');
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handleDeleteTest() {
    if (!test || !window.confirm('Удалить тест? Это действие нельзя отменить.')) return;
    try {
      await deleteTest(test.test_id);
      navigate('/app/tests');
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Не удалось удалить тест');
    }
  }

  if (isLoading) {
    return <section className="ui-page"><div className="ui-card ui-empty-card">Загрузка теста…</div></section>;
  }

  if (error && !testToRender) {
    return (
      <section className="ui-page">
        <div className="feedback-banner feedback-banner--error">{error}</div>
        <Link to="/app/tests" className="ui-back-link">← Назад к списку тестов</Link>
      </section>
    );
  }

  if (!testToRender) {
    return (
      <section className="ui-page">
        <div className="ui-card ui-empty-card">Тест не найден.</div>
        <Link to="/app/tests" className="ui-back-link">← Назад к списку тестов</Link>
      </section>
    );
  }

  return (
    <section className="ui-page">
      <div style={{ marginBottom: 18 }}>
        <button type="button" className="ui-back-link" onClick={() => navigate('/app/tests')} style={{ background: 'transparent', border: 'none', padding: 0 }}>
          ← Назад к списку тестов
        </button>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      <div className="ui-card ui-card--padded" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0, flex: '1 1 420px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
              <StatusBadge status={testToRender.status} />
              <span className="document-list-item__meta">Курс: {testToRender.course_title}</span>
            </div>
            {isEditingDraft ? (
              <div className="ui-field">
                <label className="ui-field__label">Название теста</label>
                <input className="ui-input" value={editableTest?.title ?? ''} onChange={(event) => handleTestTitleChange(event.target.value)} />
              </div>
            ) : (
              <h1 className="ui-page__title" style={{ fontSize: '32px' }}>{testToRender.title}</h1>
            )}
            <p className="ui-page__subtitle" style={{ marginTop: '10px' }}>Вопросов: {testToRender.questions.length}</p>
          </div>

          <div className="ui-course-card__actions" style={{ justifyContent: 'flex-start' }}>
            {!isEditingDraft ? (
              <>
                <Button variant="outline" onClick={handleStartEditing} fullWidth>
                  Редактировать тест
                </Button>
                <Button variant="primary" onClick={() => void handlePublishToggle()} disabled={isUpdatingStatus} fullWidth>
                  {testToRender.status === 'published' ? 'Снять с публикации' : 'Опубликовать тест'}
                </Button>
                <Link className="ui-btn ui-btn--outline ui-btn--sm ui-btn--full" to={`/app/courses/${testToRender.course_id}`}>
                  Открыть курс-источник
                </Link>
                <Button variant="outline" onClick={() => void handleDeleteTest()} fullWidth>
                  Удалить тест
                </Button>
              </>
            ) : (
              <>
                <Button variant="primary" onClick={() => void handleSaveDraft()} disabled={isSavingDraft} fullWidth>
                  {isSavingDraft ? 'Сохранение…' : 'Сохранить изменения'}
                </Button>
                <Button variant="outline" onClick={handleCancelEditing} disabled={isSavingDraft} fullWidth>
                  Отменить
                </Button>
                <Button variant="outline" onClick={handleAddQuestion} disabled={isSavingDraft} fullWidth>
                  Добавить вопрос
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="ui-list">
        {testToRender.questions.map((question) => (
          <article key={question.id} className="ui-section">
            {isEditingDraft ? (
              <>
                <div className="ui-field">
                  <label className="ui-field__label">Вопрос {question.order_index}</label>
                  <textarea className="ui-textarea" rows={3} value={question.question_text} onChange={(event) => handleQuestionTextChange(question.id, event.target.value)} />
                </div>
                <div className="ui-edit-actions">
                  <Button variant="outline" onClick={() => handleAddOption(question.id)}>Добавить вариант</Button>
                  <Button variant="outline" onClick={() => handleDeleteQuestion(question.id)}>Удалить вопрос</Button>
                </div>
                <div className="ui-list">
                  {question.options.map((option, index) => (
                    <div key={option.id} className="ui-card ui-card--padded" style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'auto 1fr auto' }}>
                        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--ui-text-soft)', marginTop: 10 }}>
                          <input
                            type="radio"
                            name={`correct-${question.id}`}
                            checked={option.is_correct}
                            onChange={() => handleCorrectOptionChange(question.id, option.id)}
                          />
                          {String.fromCharCode(65 + index)}
                        </label>
                        <input className="ui-input" value={option.text} onChange={(event) => handleOptionTextChange(question.id, option.id, event.target.value)} />
                        <Button variant="outline" onClick={() => handleDeleteOption(question.id, option.id)}>Удалить</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <h2 className="ui-topic-title" style={{ marginTop: 0 }}>Вопрос {question.order_index}</h2>
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
              </>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
