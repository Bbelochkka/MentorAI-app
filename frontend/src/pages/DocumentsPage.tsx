import { useEffect, useMemo, useState } from 'react';
import {
  DocumentDto,
  deleteDocument,
  getDocument,
  getDocuments,
  processDocument,
  uploadDocument,
} from '../api';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/StatusBadge';

function formatDate(value: string) {
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getDocumentTitle(document: DocumentDto) {
  return document.title?.trim() || document.file_name;
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentDto[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentDto | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDocumentLoading, setIsDocumentLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadDocuments() {
    setError(null);
    setIsLoading(true);
    try {
      const items = await getDocuments();
      setDocuments(items);
      setSelectedDocument((prev) => {
        if (items.length === 0) return null;
        if (!prev) return items[0];
        return items.find((item) => item.id === prev.id) ?? items[0];
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить документы');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function handleUpload() {
    if (!selectedFile) {
      setError('Сначала выбери файл');
      return;
    }

    setError(null);
    setMessage(null);
    setIsUploading(true);

    try {
      const uploaded = await uploadDocument(selectedFile);
      setSelectedFile(null);
      setMessage(`Файл «${uploaded.file_name}» успешно загружен`);
      const updated = await getDocuments();
      setDocuments(updated);
      setSelectedDocument(updated.find((item) => item.id === uploaded.id) ?? uploaded);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Не удалось загрузить файл');
    } finally {
      setIsUploading(false);
      const input = document.getElementById('document-upload-input') as HTMLInputElement | null;
      if (input) input.value = '';
    }
  }

  async function handleOpenDocument(documentId: number) {
    setError(null);
    setIsDocumentLoading(true);
    try {
      const fullDocument = await getDocument(documentId);
      setSelectedDocument(fullDocument);
    } catch (documentError) {
      setError(documentError instanceof Error ? documentError.message : 'Не удалось открыть документ');
    } finally {
      setIsDocumentLoading(false);
    }
  }

  async function handleDeleteDocument(documentId: number) {
    const target = documents.find((item) => item.id === documentId) ?? selectedDocument;
    if (!target) return;

    const confirmed = window.confirm(`Удалить документ «${target.file_name}»? Это действие нельзя отменить.`);
    if (!confirmed) return;

    setError(null);
    setMessage(null);
    setIsDeleting(true);
    try {
      await deleteDocument(documentId);
      setMessage('Документ успешно удалён');
      const updated = await getDocuments();
      setDocuments(updated);
      setSelectedDocument((prev) => {
        if (updated.length === 0) return null;
        if (!prev || prev.id === documentId) return updated[0];
        return updated.find((item) => item.id === prev.id) ?? updated[0];
      });
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Не удалось удалить документ');
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleProcessDocument(documentId: number) {
    setError(null);
    setMessage(null);
    setIsProcessing(true);
    try {
      const processed = await processDocument(documentId);
      setSelectedDocument(processed);
      setMessage('Документ успешно обработан');
      const updated = await getDocuments();
      setDocuments(updated);
    } catch (processError) {
      setError(processError instanceof Error ? processError.message : 'Не удалось обработать документ');
    } finally {
      setIsProcessing(false);
    }
  }

  const emptyState = useMemo(() => !isLoading && documents.length === 0, [documents.length, isLoading]);
  const previewText = selectedDocument?.raw_text?.trim() || 'После обработки документа здесь появится извлечённый текст.';

  return (
    <section className="ui-page documents-page-ui">
      <div className="ui-page__header">
        <div>
          <h1 className="ui-page__title">Документы</h1>
          <p className="ui-page__subtitle">
            Загружай внутренние материалы компании, чтобы потом генерировать на их основе курсы и тесты.
          </p>
        </div>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      <div className="ui-card ui-card--padded documents-upload-panel">
        <div>
          <h2 className="documents-panel-title">Загрузка документа</h2>
          <p className="documents-panel-subtitle">Поддерживаемые форматы: PDF, DOCX, TXT.</p>
        </div>

        <div className="documents-upload-controls">
          <label className="documents-file-picker" htmlFor="document-upload-input">
            <span>{selectedFile ? selectedFile.name : 'Выбрать файл'}</span>
          </label>
          <input
            id="document-upload-input"
            type="file"
            accept=".pdf,.docx,.txt"
            className="documents-file-picker__input"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
              setError(null);
              setMessage(null);
            }}
          />
          <Button onClick={handleUpload} disabled={isUploading}>
            {isUploading ? 'Загрузка...' : 'Загрузить'}
          </Button>
        </div>
      </div>

      <div className="documents-grid-ui">
        <div className="ui-card ui-card--padded">
          <div className="documents-card-header-ui">
            <div>
              <h2 className="documents-panel-title">Список документов</h2>
              <p className="documents-panel-subtitle">Выбери документ, чтобы открыть карточку и посмотреть извлечённый текст.</p>
            </div>
            <Button variant="outline" onClick={() => void loadDocuments()} disabled={isLoading}>
              Обновить
            </Button>
          </div>

          {isLoading ? <div className="ui-empty-card">Загружаем документы...</div> : null}
          {emptyState ? <div className="ui-empty-card">Документы пока не загружены.</div> : null}

          {!isLoading && documents.length > 0 ? (
            <div className="ui-list">
              {documents.map((document) => {
                const active = selectedDocument?.id === document.id;
                return (
                  <article
                    key={document.id}
                    className={`ui-card ui-card--padded document-list-item ${active ? 'document-list-item--active' : ''}`}
                  >
                    <div className="document-list-item__top">
                      <StatusBadge status={document.status} />
                      <span className="document-list-item__meta">{document.file_type.toUpperCase()}</span>
                    </div>

                    <h3 className="document-list-item__title">{getDocumentTitle(document)}</h3>
                    <p className="document-list-item__filename">{document.file_name}</p>
                    <p className="document-list-item__meta">Добавлен: {formatDate(document.created_at)}</p>

                    <div className="document-list-item__actions">
                      <Button variant="primary" onClick={() => void handleOpenDocument(document.id)} disabled={isDocumentLoading && active}>
                        {isDocumentLoading && active ? 'Открываем...' : 'Перейти'}
                      </Button>
                      <Button variant="outline" onClick={() => void handleDeleteDocument(document.id)} disabled={isDeleting}>
                        {isDeleting && active ? 'Удаление...' : 'Удалить'}
                      </Button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="ui-card ui-card--padded">
          {selectedDocument ? (
            <>
              <div className="documents-detail-header-ui">
                <div>
                  <div className="document-list-item__top">
                    <StatusBadge status={selectedDocument.status} />
                    <span className="document-list-item__meta">{selectedDocument.file_type.toUpperCase()}</span>
                  </div>
                  <h2 className="documents-detail-title">{getDocumentTitle(selectedDocument)}</h2>
                  <p className="documents-panel-subtitle">{selectedDocument.file_name}</p>
                </div>

                <div className="documents-detail-actions-ui">
                  <Button
                    onClick={() => void handleProcessDocument(selectedDocument.id)}
                    disabled={isProcessing || selectedDocument.status === 'processing'}
                  >
                    {isProcessing ? 'Обработка...' : selectedDocument.status === 'processed' ? 'Обработать заново' : 'Обработать документ'}
                  </Button>
                  <Button variant="outline" onClick={() => void handleDeleteDocument(selectedDocument.id)} disabled={isDeleting}>
                    {isDeleting ? 'Удаление...' : 'Удалить'}
                  </Button>
                </div>
              </div>

              <div className="documents-preview-meta">
                <span>Статус: {selectedDocument.status}</span>
                <span>Создан: {formatDate(selectedDocument.created_at)}</span>
              </div>

              <div className="documents-preview-box">
                <pre className="documents-preview-text">{previewText}</pre>
              </div>
            </>
          ) : (
            <div className="ui-empty-card">Выбери документ из списка, чтобы посмотреть его карточку.</div>
          )}
        </div>
      </div>
    </section>
  );
}
