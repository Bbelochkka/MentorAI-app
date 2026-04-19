type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'failed';
type CourseStatus = 'draft' | 'published';

type AnyStatus = DocumentStatus | CourseStatus | string;

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  published: 'Published',
  uploaded: 'Загружен',
  processing: 'Обрабатывается',
  processed: 'Обработан',
  failed: 'Ошибка',
};

function normalizeStatus(status: AnyStatus): string {
  const value = String(status || '').toLowerCase();
  if (value === 'published') return 'published';
  if (value === 'processed') return 'processed';
  if (value === 'processing') return 'processing';
  if (value === 'failed') return 'failed';
  return 'draft';
}

export function StatusBadge({ status }: { status: AnyStatus }) {
  const normalized = normalizeStatus(status);
  const label = STATUS_LABELS[String(status).toLowerCase()] ?? STATUS_LABELS[normalized] ?? String(status);

  return <span className={`status-badge status-badge--${normalized}`}>{label}</span>;
}
