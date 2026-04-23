import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  TestAttemptResultDto,
  TestAttemptStartDto,
  TestDraftDto,
  deleteTest,
  finishTestAttempt,
  getStoredUser,
  getTest,
  isLearnerUser,
  startTestAttempt,
  updateTestDraft,
  updateTestStatus,
} from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import '../styles/ui.css';

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

function LearnerTestView({ test }: { test: TestDraftDto }) {
  const [attempt, setAttempt] = useState<TestAttemptStartDto | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [localMessage, setLocalMessage] = useState<string | null>(null);
  const [result, setResult] = useState<TestAttemptResultDto | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);

  const currentQuestion = attempt?.questions[currentQuestionIndex] ?? null;
  const answeredCount = attempt
    ? attempt.questions.filter((question) => selectedAnswers[question.id] != null).length
    : 0;

  async function handleStartAttempt() {
    setIsStarting(true);
    setLocalError(null);
    setLocalMessage(null);
    try {
      const data = await startTestAttempt(test.test_id);
      setAttempt(data);
      setResult(null);
      setSelectedAnswers({});
      setCurrentQuestionIndex(0);
    } catch (startError) {
      setLocalError(startError instanceof Error ? startError.message : 'Не удалось начать тест');
    } finally {
      setIsStarting(false);
    }
  }

  function handleSelectOption(questionId: number, optionId: number) {
    setSelectedAnswers((current) => ({ ...current, [questionId]: optionId }));
  }

  function handleGoToQuestion(index: number) {
    if (!attempt) return;
    if (index < 0 || index >= attempt.questions.length) return;
    setCurrentQuestionIndex(index);
  }

  async function handleFinishAttempt() {
    if (!attempt) return;

    const unanswered = attempt.questions.filter((question) => selectedAnswers[question.id] == null).length;
    if (unanswered > 0) {
      const shouldFinish = window.confirm(
        `Остались вопросы без ответа (${unanswered}). Завершить тестирование?`
      );
      if (!shouldFinish) return;
    }

    setIsFinishing(true);
    setLocalError(null);
    setLocalMessage(null);
    try {
      const finishPayload = {
        answers: attempt.questions.map((question) => ({
          question_id: question.id,
          selected_option_id: selectedAnswers[question.id] ?? null,
        })),
      };
      const data = await finishTestAttempt(attempt.attempt_id, finishPayload);
      setResult(data);
      setAttempt(null);
      setLocalMessage(`Тест завершён. Правильных ответов: ${data.correct_answers} из ${data.question_count}.`);
    } catch (finishError) {
      setLocalError(finishError instanceof Error ? finishError.message : 'Не удалось завершить тест');
    } finally {
      setIsFinishing(false);
    }
  }

  if (result) {
    return (
      <section className="ui-page">
        {localError ? <div className="feedback-banner feedback-banner--error">{localError}</div> : null}
        {localMessage ? <div className="feedback-banner feedback-banner--success">{localMessage}</div> : null}
        <div style={{ marginBottom: 18 }}>
          <Link to="/app/tests" className="ui-back-link">← Назад к списку тестов</Link>
        </div>

        <div className="ui-card ui-card--padded" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div>
              <h1 className="ui-page__title" style={{ fontSize: 32 }}>{result.title}</h1>
              <p className="ui-page__subtitle" style={{ marginTop: 10 }}>
                Результат: {result.correct_answers} из {result.question_count} ({result.percent.toFixed(2)}%)
              </p>
              <p className="document-list-item__meta" style={{ marginTop: 8 }}>
                Попытка №{result.attempt_no}
              </p>
            </div>
            <div className="ui-course-card__actions">
              <Button variant="primary" onClick={() => void handleStartAttempt()} disabled={isStarting}>
                {isStarting ? 'Подготовка…' : 'Пройти тест заново'}
              </Button>
            </div>
          </div>
        </div>

        <div className="ui-list">
          {result.questions.map((question) => (
            <article key={question.id} className="ui-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <h2 className="ui-topic-title" style={{ marginTop: 0 }}>Вопрос {question.order_index}</h2>
                  <p style={{ margin: '0 0 14px', color: 'var(--ui-text)', fontSize: 16, lineHeight: 1.6 }}>
                    {question.question_text}
                  </p>
                </div>
                
              </div>

              <div className="ui-list">
                {question.options.map((option, index) => {
                  const isSelectedCorrect = option.is_selected && option.is_correct;
                  const isSelectedWrong = option.is_selected && !option.is_correct;

                  const borderColor = isSelectedCorrect
                    ? 'var(--ui-success-border)'
                    : isSelectedWrong
                      ? '#efc2c0'
                      : 'var(--ui-border-soft)';

                  const background = isSelectedCorrect
                    ? 'var(--ui-success-bg)'
                    : isSelectedWrong
                      ? '#fff2f1'
                      : '#fffdfa';

                  const color = isSelectedCorrect
                    ? 'var(--ui-success-text)'
                    : isSelectedWrong
                      ? '#b64942'
                      : 'var(--ui-text)';

                  return (
                    <div
                      key={option.id}
                      className="ui-card ui-card--padded"
                      style={{ borderColor, background, padding: '14px 18px' }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center' }}>
                        <span style={{ color, lineHeight: 1.5 }}>
                          {String.fromCharCode(65 + index)}. {option.text}
                        </span>
                        {option.is_selected ? (
                          <span
                            style={{
                              flexShrink: 0,
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '6px 10px',
                              borderRadius: 999,
                              border: `1px solid ${isSelectedCorrect ? 'var(--ui-success-border)' : '#efc2c0'}`,
                              background: isSelectedCorrect ? 'var(--ui-success-bg)' : '#fff2f1',
                              color: isSelectedCorrect ? 'var(--ui-success-text)' : '#b64942',
                              fontSize: 13,
                              fontWeight: 600,
                            }}
                          >
                            {isSelectedCorrect ? 'Ваш ответ — верно' : 'Ваш ответ — неверно'}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (!attempt) {
    return (
      <section className="ui-page">
        {localError ? <div className="feedback-banner feedback-banner--error">{localError}</div> : null}
        {localMessage ? <div className="feedback-banner feedback-banner--success">{localMessage}</div> : null}
        <div style={{ marginBottom: 18 }}>
          <Link to="/app/tests" className="ui-back-link">← Назад к списку тестов</Link>
        </div>

        <article className="ui-card ui-card--padded ui-course-card">
          <div>
            <div className="ui-course-card__meta">
              <StatusBadge status={test.status} />
            </div>
            <h1 className="ui-course-card__title">{test.title}</h1>
            <p className="ui-course-card__description">Курс-источник: {test.course_title}</p>
            <p className="ui-course-card__documents">Вопросов: {test.questions.length}</p>
          </div>

          <div className="ui-course-card__actions">
            <Button variant="primary" onClick={() => void handleStartAttempt()} disabled={isStarting} fullWidth>
              {isStarting ? 'Подготовка…' : 'Начать тест'}
            </Button>
          </div>
        </article>
      </section>
    );
  }

  return (
    <section className="ui-page">
      {localError ? <div className="feedback-banner feedback-banner--error">{localError}</div> : null}
      {localMessage ? <div className="feedback-banner feedback-banner--success">{localMessage}</div> : null}
      <div className="ui-card ui-card--padded" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0, flex: '1 1 500px' }}>
            <h1 className="ui-page__title" style={{ fontSize: 32, marginBottom: 18 }}>{attempt.title}</h1>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {attempt.questions.map((question, index) => {
                const isAnswered = selectedAnswers[question.id] != null;
                const isActive = index === currentQuestionIndex;
                return (
                  <button
                    key={question.id}
                    type="button"
                    onClick={() => handleGoToQuestion(index)}
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 10,
                      border: `1px solid ${isActive ? '#d6a76e' : isAnswered ? '#9bbc7c' : 'var(--ui-border-soft)'}`,
                      background: isActive ? '#d6a76e' : isAnswered ? '#f4fbf0' : '#fffdfa',
                      color: isActive ? '#ffffff' : 'var(--ui-text)',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {index + 1}
                  </button>
                );
              })}
            </div>
            <p className="document-list-item__meta">
              Отвечено: {answeredCount} из {attempt.question_count}
            </p>
          </div>

          <div className="ui-course-card__actions">
            <Button variant="outline" onClick={() => void handleFinishAttempt()} disabled={isFinishing}>
              {isFinishing ? 'Завершение…' : 'Завершить тест'}
            </Button>
          </div>
        </div>
      </div>

      {currentQuestion ? (
        <article className="ui-section" style={{ padding: '28px 30px' }}>
          <h2 className="ui-topic-title" style={{ marginTop: 0, marginBottom: 12 }}>
            Вопрос {currentQuestionIndex + 1}
          </h2>
          <p style={{ margin: '0 0 20px', color: 'var(--ui-text)', fontSize: 18, lineHeight: 1.6 }}>
            {currentQuestion.question_text}
          </p>

          <div
            style={{
              display: 'grid',
              gap: 16,
              gridTemplateColumns: currentQuestion.options.length > 2 ? 'repeat(2, minmax(0, 1fr))' : '1fr',
            }}
          >
            {currentQuestion.options.map((option, index) => {
              const selected = selectedAnswers[currentQuestion.id] === option.id;
              return (
                <label
                  key={option.id}
                  className="ui-card ui-card--padded"
                  style={{
                    display: 'flex',
                    gap: 12,
                    alignItems: 'flex-start',
                    cursor: 'pointer',
                    borderColor: selected ? '#d6a76e' : 'var(--ui-border-soft)',
                    background: selected ? '#fff7ef' : '#fffdfa',
                    padding: '16px 18px',
                  }}
                >
                  <input
                    type="radio"
                    name={`question-${currentQuestion.id}`}
                    checked={selected}
                    onChange={() => handleSelectOption(currentQuestion.id, option.id)}
                    style={{ marginTop: 3 }}
                  />
                  <span style={{ color: 'var(--ui-text)', lineHeight: 1.5 }}>
                    <strong style={{ marginRight: 6 }}>{String.fromCharCode(65 + index)}.</strong>
                    {option.text}
                  </span>
                </label>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 24, flexWrap: 'wrap' }}>
            <Button
              variant="outline"
              onClick={() => handleGoToQuestion(currentQuestionIndex - 1)}
              disabled={currentQuestionIndex === 0}
            >
              Назад
            </Button>

            {currentQuestionIndex < attempt.questions.length - 1 ? (
              <Button variant="primary" onClick={() => handleGoToQuestion(currentQuestionIndex + 1)}>
                Вперёд
              </Button>
            ) : (
              <Button variant="primary" onClick={() => void handleFinishAttempt()} disabled={isFinishing}>
                {isFinishing ? 'Завершение…' : 'Завершить тест'}
              </Button>
            )}
          </div>
        </article>
      ) : null}
    </section>
  );
}

export function TestDetailPage() {
  const { testId } = useParams();
  const navigate = useNavigate();
  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);
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
          },
      ),
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
          },
      ),
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
          },
      ),
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

  if (learner) {
    return <LearnerTestView test={testToRender as TestDraftDto} />;
  }

  return (
    <section className="ui-page">
      <div style={{ marginBottom: 18 }}>
        <button
          type="button"
          className="ui-back-link"
          onClick={() => navigate('/app/tests')}
          style={{ background: 'transparent', border: 'none', padding: 0 }}
        >
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
