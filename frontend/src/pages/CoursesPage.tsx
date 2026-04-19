import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CourseSummaryDto,
  DocumentDto,
  deleteCourse,
  generateCourseDraft,
  getCourses,
  getDocuments,
  updateCourseStatus,
} from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';
import '../styles/ui.css';

type CourseStatus = 'draft' | 'published';

function truncateDescription(value: string, max = 150) {
  const clean = value.trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1).trimEnd()}…`;
}

export function CoursesPage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentDto[]>([]);
  const [courses, setCourses] = useState<CourseSummaryDto[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<number[]>([]);
  const [courseTitle, setCourseTitle] = useState('');
  const [additionalRequirements, setAdditionalRequirements] = useState('');
  const [desiredStructure, setDesiredStructure] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isLoadingCourses, setIsLoadingCourses] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeletingCourse, setIsDeletingCourse] = useState<number | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const processedDocuments = useMemo(
    () => documents.filter((document) => document.status === 'processed'),
    [documents]
  );

  async function loadDocuments() {
    setIsLoadingDocuments(true);
    try {
      const items = await getDocuments();
      setDocuments(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить документы');
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  async function loadCourses() {
    setIsLoadingCourses(true);
    try {
      const items = await getCourses();
      setCourses(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить курсы');
    } finally {
      setIsLoadingCourses(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
    void loadCourses();
  }, []);

  function resetGeneratorForm() {
    setCourseTitle('');
    setSelectedDocumentIds([]);
    setAdditionalRequirements('');
    setDesiredStructure('');
  }

  function toggleDocument(documentId: number) {
    setSelectedDocumentIds((prev) =>
      prev.includes(documentId) ? prev.filter((id) => id !== documentId) : [...prev, documentId]
    );
  }

  async function handleGenerateCourse() {
    if (!courseTitle.trim()) {
      setError('Введите название курса');
      return;
    }
    if (selectedDocumentIds.length === 0) {
      setError('Выберите хотя бы один обработанный документ');
      return;
    }

    setError(null);
    setMessage(null);
    setIsGenerating(true);

    try {
      const course = await generateCourseDraft({
        title: courseTitle.trim(),
        document_ids: selectedDocumentIds,
        additional_requirements: additionalRequirements.trim() || undefined,
        desired_structure: desiredStructure.trim() || undefined,
      });

      setShowCreateForm(false);
      resetGeneratorForm();
      setMessage('Черновик курса успешно сохранён');
      await loadCourses();
      navigate(`/app/courses/${course.course_id}`);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : 'Не удалось сгенерировать курс');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDeleteCourse(courseId: number) {
    if (!window.confirm('Удалить выбранный курс?')) return;
    setError(null);
    setMessage(null);
    setIsDeletingCourse(courseId);
    try {
      await deleteCourse(courseId);
      setMessage('Курс успешно удалён');
      await loadCourses();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Не удалось удалить курс');
    } finally {
      setIsDeletingCourse(null);
    }
  }

  async function handleStatusChange(courseId: number, status: CourseStatus) {
    const confirmText =
      status === 'published' ? 'Опубликовать курс?' : 'Снять курс с публикации и перевести в черновик?';
    if (!window.confirm(confirmText)) return;

    setError(null);
    setMessage(null);
    setIsUpdatingStatus(courseId);
    try {
      await updateCourseStatus(courseId, { status });
      setMessage(status === 'published' ? 'Курс опубликован' : 'Курс снят с публикации');
      await loadCourses();
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Не удалось обновить статус курса');
    } finally {
      setIsUpdatingStatus(null);
    }
  }

  return (
    <section className="ui-page">
      <div className="ui-page__header">
        <div>
          <h1 className="ui-page__title">Курсы</h1>
          <p className="ui-page__subtitle">Список черновиков и опубликованных курсов компании.</p>
        </div>
        <Button variant="primary" size="md" onClick={() => setShowCreateForm((prev) => !prev)}>
          {showCreateForm ? 'Скрыть форму' : 'Создать курс'}
        </Button>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      {showCreateForm ? (
        <div className="ui-card ui-card--padded" style={{ marginBottom: '24px' }}>
          <div className="ui-field" style={{ marginBottom: '20px' }}>
            <label className="ui-field__label">Название курса</label>
            <input
              className="ui-input"
              type="text"
              value={courseTitle}
              onChange={(event) => setCourseTitle(event.target.value)}
              placeholder="Например, Онбординг менеджеров по продажам"
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'baseline', marginBottom: '10px', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0, color: '#4f433b' }}>Документы</h3>
              <span style={{ fontSize: '14px', color: '#8f8177' }}>Выберите обработанные документы для генерации курса</span>
            </div>
            {isLoadingDocuments ? (
              <p style={{ margin: 0, color: '#8f8177' }}>Загрузка документов…</p>
            ) : processedDocuments.length === 0 ? (
              <p style={{ margin: 0, color: '#8f8177' }}>
                Нет обработанных документов. Сначала загрузите и обработайте документы на странице «Документы».
              </p>
            ) : (
              <div style={{ display: 'grid', gap: '12px' }}>
                {processedDocuments.map((document) => {
                  const checked = selectedDocumentIds.includes(document.id);
                  return (
                    <label
                      key={document.id}
                      className="ui-section"
                      style={{ cursor: 'pointer', display: 'flex', gap: '12px', alignItems: 'flex-start', padding: '14px 16px' }}
                    >
                      <input type="checkbox" checked={checked} onChange={() => toggleDocument(document.id)} style={{ marginTop: '2px' }} />
                      <div>
                        <div style={{ fontWeight: 700, color: '#4f433b' }}>{document.file_name}</div>
                        <div style={{ color: '#8f8177', fontSize: '13px', marginTop: '4px' }}>
                          {document.file_type.toUpperCase()} · {new Date(document.created_at).toLocaleDateString('ru-RU')}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            <div className="ui-field">
              <label className="ui-field__label">Что исключить из курса</label>
              <textarea
                className="ui-textarea"
                rows={4}
                value={additionalRequirements}
                onChange={(event) => setAdditionalRequirements(event.target.value)}
                placeholder={'Формат: модуль: ... или тема: ...\nНапример: модуль: Глоссарий; тема: KPI менеджера'}
              />
            </div>
            <div className="ui-field">
              <label className="ui-field__label">Где нужен блок «Важно запомнить»</label>
              <textarea
                className="ui-textarea"
                rows={4}
                value={desiredStructure}
                onChange={(event) => setDesiredStructure(event.target.value)}
                placeholder={'Формат: модуль: ... или тема: ...\nНапример: модуль: Целевая аудитория; тема: Коммерческое предложение'}
              />
            </div>
          </div>

          <div className="ui-detail-actions" style={{ marginTop: '20px' }}>
            <Button variant="primary" size="md" onClick={() => void handleGenerateCourse()} disabled={isGenerating}>
              {isGenerating ? 'Генерация…' : 'Сгенерировать курс'}
            </Button>
            <Button variant="outline" size="md" onClick={resetGeneratorForm} disabled={isGenerating}>
              Очистить
            </Button>
          </div>
        </div>
      ) : null}

      {isLoadingCourses ? (
        <div className="ui-card ui-empty-card">Загрузка курсов…</div>
      ) : courses.length === 0 ? (
        <div className="ui-card ui-empty-card">Курсы ещё не созданы. Сгенерируйте первый курс из обработанных документов.</div>
      ) : (
        <div className="ui-list">
          {courses.map((course) => {
            const isPublished = course.status === 'published';
            const linkedDocumentsLabel = Array.isArray(course.source_documents) && course.source_documents.length
              ? course.source_documents.join(', ')
              : 'Ручной курс';

            return (
              <article key={course.course_id} className="ui-card ui-card--padded ui-course-card">
                <div>
                  <div className="ui-course-card__meta">
                    <StatusBadge status={course.status} />
                    <Button
                      variant={isPublished ? 'outline' : 'primary'}
                      onClick={() => void handleStatusChange(course.course_id, isPublished ? 'draft' : 'published')}
                      disabled={isUpdatingStatus === course.course_id}
                    >
                      {isPublished ? 'Снять с публикации' : 'Опубликовать'}
                    </Button>
                  </div>
                  <h2 className="ui-course-card__title">{course.title}</h2>
                  <p className="ui-course-card__description">
                    {truncateDescription(course.description || 'Описание курса пока не заполнено.')}
                  </p>
                  <p className="ui-course-card__documents">{linkedDocumentsLabel}</p>
                </div>

                <div className="ui-course-card__actions">
                  <Button variant="primary" onClick={() => navigate(`/app/courses/${course.course_id}`)} fullWidth>
                    Перейти
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void handleDeleteCourse(course.course_id)}
                    disabled={isDeletingCourse === course.course_id}
                    fullWidth
                  >
                    {isDeletingCourse === course.course_id ? 'Удаление…' : 'Удалить'}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
