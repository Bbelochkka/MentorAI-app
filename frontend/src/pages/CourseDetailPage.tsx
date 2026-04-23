import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CourseDraftDto, TestSummaryDto, getCourse, getStoredUser, getTests, isLearnerUser, updateCourseDraft, updateCourseStatus } from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import '../styles/ui.css';

function cloneCourse(course: CourseDraftDto): CourseDraftDto {
  return JSON.parse(JSON.stringify(course)) as CourseDraftDto;
}

function normalizeForCompare(course: CourseDraftDto | null) {
  if (!course) return '';
  return JSON.stringify(course);
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="ui-course-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="ui-table-wrap">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function CourseDetailPage() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const currentUser = getStoredUser();
  const learner = isLearnerUser(currentUser);
  const tempIdRef = useRef(-1);

  const [selectedCourse, setSelectedCourse] = useState<CourseDraftDto | null>(null);
  const [editableCourse, setEditableCourse] = useState<CourseDraftDto | null>(null);
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [relatedTest, setRelatedTest] = useState<TestSummaryDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function nextTempId() {
    const value = tempIdRef.current;
    tempIdRef.current -= 1;
    return value;
  }

  const courseToRender = isEditingDraft ? editableCourse : selectedCourse;
  const hasUnsavedChanges = useMemo(() => {
    if (!isEditingDraft || !selectedCourse || !editableCourse) return false;
    return normalizeForCompare(selectedCourse) !== normalizeForCompare(editableCourse);
  }, [editableCourse, isEditingDraft, selectedCourse]);

  async function loadCourse() {
    if (!courseId) {
      setError('Курс не найден');
      return;
    }

    setIsLoadingCourse(true);
    setError(null);
    try {
      const course = await getCourse(Number(courseId));
      setSelectedCourse(course);
      setEditableCourse(null);
      setIsEditingDraft(false);

      try {
        const tests = await getTests();
        const matchedTest = tests.find((test) => test.course_id === course.course_id) ?? null;
        setRelatedTest(matchedTest);
      } catch {
        setRelatedTest(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось открыть курс');
    } finally {
      setIsLoadingCourse(false);
    }
  }

  useEffect(() => {
    void loadCourse();
  }, [courseId]);

  function handleBack() {
    if (hasUnsavedChanges && !window.confirm('Есть несохранённые изменения. Вернуться к списку курсов?')) {
      return;
    }
    navigate('/app/courses');
  }

  function handleStartEditing() {
    if (!selectedCourse) return;
    setEditableCourse(cloneCourse(selectedCourse));
    setIsEditingDraft(true);
    setMessage(null);
    setError(null);
  }

  function handleCancelEditing() {
    if (hasUnsavedChanges && !window.confirm('Отменить несохранённые изменения?')) return;
    setEditableCourse(null);
    setIsEditingDraft(false);
  }

  function updateEditableCourse(updater: (draft: CourseDraftDto) => CourseDraftDto) {
    setEditableCourse((current) => (current ? updater(current) : current));
  }

  function handleCourseMetaChange(field: 'title' | 'description', value: string) {
    updateEditableCourse((draft) => ({ ...draft, [field]: value }));
  }

  function handleModuleTitleChange(moduleId: number, value: string) {
    updateEditableCourse((draft) => ({
      ...draft,
      modules: draft.modules.map((module) => (module.id === moduleId ? { ...module, title: value } : module)),
    }));
  }

  function handleDeleteModule(moduleId: number) {
    if (!window.confirm('Удалить весь модуль из черновика?')) return;
    updateEditableCourse((draft) => ({
      ...draft,
      modules: draft.modules
        .filter((module) => module.id !== moduleId)
        .map((module, index) => ({ ...module, order_index: index + 1 })),
    }));
  }

  function handleTopicTitleChange(moduleId: number, topicId: number, value: string) {
    updateEditableCourse((draft) => ({
      ...draft,
      modules: draft.modules.map((module) =>
        module.id !== moduleId
          ? module
          : {
              ...module,
              topics: module.topics.map((topic) => (topic.id === topicId ? { ...topic, title: value } : topic)),
            }
      ),
    }));
  }

  function handleTopicContentChange(moduleId: number, topicId: number, value: string) {
    updateEditableCourse((draft) => ({
      ...draft,
      modules: draft.modules.map((module) =>
        module.id !== moduleId
          ? module
          : {
              ...module,
              topics: module.topics.map((topic) => (topic.id === topicId ? { ...topic, content: value } : topic)),
            }
      ),
    }));
  }

  function handleDeleteTopic(moduleId: number, topicId: number) {
    if (!window.confirm('Удалить тему из черновика?')) return;
    updateEditableCourse((draft) => {
      const nextModules = draft.modules
        .map((module) => {
          if (module.id !== moduleId) return module;
          const nextTopics = module.topics
            .filter((topic) => topic.id !== topicId)
            .map((topic, index) => ({ ...topic, order_index: index + 1 }));
          if (nextTopics.length === 0) return null;
          return { ...module, topics: nextTopics };
        })
        .filter(Boolean) as CourseDraftDto['modules'];

      return { ...draft, modules: nextModules.map((module, index) => ({ ...module, order_index: index + 1 })) };
    });
  }

  function handleAddModule() {
    updateEditableCourse((draft) => ({
      ...draft,
      modules: [
        ...draft.modules,
        {
          id: nextTempId(),
          title: 'Новый модуль',
          order_index: draft.modules.length + 1,
          topics: [
            {
              id: nextTempId(),
              title: 'Новая тема',
              content: 'Заполните содержание темы.',
              order_index: 1,
            },
          ],
        },
      ],
    }));
  }

  function handleAddTopic(moduleId: number) {
    updateEditableCourse((draft) => ({
      ...draft,
      modules: draft.modules.map((module) =>
        module.id !== moduleId
          ? module
          : {
              ...module,
              topics: [
                ...module.topics,
                {
                  id: nextTempId(),
                  title: 'Новая тема',
                  content: 'Заполните содержание темы.',
                  order_index: module.topics.length + 1,
                },
              ],
            }
      ),
    }));
  }

  async function handleSaveDraft() {
    if (!selectedCourse || !editableCourse) return;
    setIsSavingDraft(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateCourseDraft(selectedCourse.course_id, {
        title: editableCourse.title,
        description: editableCourse.description,
        modules: editableCourse.modules.map((module, moduleIndex) => ({
          id: module.id > 0 ? module.id : undefined,
          title: module.title,
          order_index: moduleIndex + 1,
          topics: module.topics.map((topic, topicIndex) => ({
            id: topic.id > 0 ? topic.id : undefined,
            title: topic.title,
            content: topic.content,
            order_index: topicIndex + 1,
          })),
        })),
      });

      setSelectedCourse(updated);
      setEditableCourse(null);
      setIsEditingDraft(false);
      setMessage('Изменения сохранены');
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Не удалось сохранить изменения');
    } finally {
      setIsSavingDraft(false);
    }
  }

  async function handlePublishToggle() {
    if (!selectedCourse) return;
    const nextStatus = selectedCourse.status === 'published' ? 'draft' : 'published';
    const confirmText = nextStatus === 'published' ? 'Опубликовать курс?' : 'Снять курс с публикации и перевести в черновик?';
    if (!window.confirm(confirmText)) return;

    setIsUpdatingStatus(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateCourseStatus(selectedCourse.course_id, { status: nextStatus });
      setSelectedCourse(updated);
      setMessage(nextStatus === 'published' ? 'Курс опубликован' : 'Курс снят с публикации');
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Не удалось обновить статус курса');
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  if (isLoadingCourse) {
    return <section className="ui-page"><div className="ui-card ui-empty-card">Загрузка курса…</div></section>;
  }

  if (error && !courseToRender) {
    return (
      <section className="ui-page">
        <div className="feedback-banner feedback-banner--error">{error}</div>
        <Link to="/app/courses" className="ui-back-link">← Назад к списку курсов</Link>
      </section>
    );
  }

  if (!courseToRender) {
    return (
      <section className="ui-page">
        <div className="ui-card ui-empty-card">Курс не найден.</div>
        <Link to="/app/courses" className="ui-back-link">← Назад к списку курсов</Link>
      </section>
    );
  }

  return (
    <section className="ui-page">
      <div style={{ marginLeft: 0, marginBottom: '8px' }}>
        <button type="button" onClick={handleBack} className="ui-back-link" style={{ background: 'transparent', border: 'none', padding: 0 }}>
          ← Назад к списку курсов
        </button>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      <div className="ui-card ui-card--padded" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0, flex: '1 1 420px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
              <StatusBadge status={courseToRender.status} />
            </div>
            {isEditingDraft ? (
              <div className="ui-field">
                <label className="ui-field__label">Название курса</label>
                <input className="ui-input" value={editableCourse?.title ?? ''} onChange={(event) => handleCourseMetaChange('title', event.target.value)} />
              </div>
            ) : (
              <h1 className="ui-page__title" style={{ fontSize: '32px' }}>{courseToRender.title}</h1>
            )}

            {isEditingDraft ? (
              <div className="ui-field" style={{ marginTop: '16px' }}>
                <label className="ui-field__label">Описание курса</label>
                <textarea className="ui-textarea" rows={4} value={editableCourse?.description ?? ''} onChange={(event) => handleCourseMetaChange('description', event.target.value)} />
              </div>
            ) : (
              <p className="ui-page__subtitle" style={{ marginTop: '10px', maxWidth: '920px', lineHeight: 1.6 }}>
                {courseToRender.description}
              </p>
            )}
          </div>

          <div className="ui-course-card__actions" style={{ justifyContent: 'flex-start' }}>
            {relatedTest && !isEditingDraft ? (
              <Button variant="primary" onClick={() => navigate(`/app/tests/${relatedTest.test_id}`)} fullWidth>
                Перейти к тесту
              </Button>
            ) : null}

            {!learner ? (
              !isEditingDraft ? (
                <>
                  <Button variant="outline" onClick={handleStartEditing} fullWidth>
                    Редактировать курс
                  </Button>
                  <Button variant="primary" onClick={() => void handlePublishToggle()} disabled={isUpdatingStatus} fullWidth>
                    {courseToRender.status === 'published' ? 'Снять с публикации' : 'Опубликовать курс'}
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
                  <Button variant="outline" onClick={handleAddModule} disabled={isSavingDraft} fullWidth>
                    Добавить модуль
                  </Button>
                </>
              )
            ) : null}
          </div>
        </div>
      </div>

      {courseToRender.modules.map((module) => (
        <div key={module.id} className="ui-section">
          {isEditingDraft ? (
            <div className="ui-field">
              <label className="ui-field__label">Название модуля</label>
              <input className="ui-input" value={module.title} onChange={(event) => handleModuleTitleChange(module.id, event.target.value)} />
            </div>
          ) : (
            <h2 className="ui-module-title">Модуль {module.order_index}. {module.title}</h2>
          )}

          {isEditingDraft ? (
            <div className="ui-edit-actions">
              <Button variant="outline" onClick={() => handleAddTopic(module.id)}>Добавить тему</Button>
              <Button variant="outline" onClick={() => handleDeleteModule(module.id)}>Удалить модуль</Button>
            </div>
          ) : null}

          {module.topics.map((topic) => (
            <div key={topic.id} style={{ marginTop: '18px' }}>
              {isEditingDraft ? (
                <>
                  <div className="ui-field">
                    <label className="ui-field__label">Название темы</label>
                    <input className="ui-input" value={topic.title} onChange={(event) => handleTopicTitleChange(module.id, topic.id, event.target.value)} />
                  </div>
                  <div className="ui-field" style={{ marginTop: '12px' }}>
                    <label className="ui-field__label">Содержание темы</label>
                    <textarea className="ui-textarea" value={topic.content} onChange={(event) => handleTopicContentChange(module.id, topic.id, event.target.value)} />
                  </div>
                  <div className="ui-edit-actions">
                    <Button variant="outline" onClick={() => handleDeleteTopic(module.id, topic.id)}>Удалить тему</Button>
                  </div>
                </>
              ) : (
                <>
                  <h3 className="ui-topic-title">Тема {topic.order_index}. {topic.title}</h3>
                  <MarkdownContent content={topic.content} />
                </>
              )}
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
