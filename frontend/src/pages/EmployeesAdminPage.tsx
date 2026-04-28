import { useEffect, useMemo, useState } from 'react';
import {
  AdminUserListItemDto,
  CreateUserPayload,
  SupervisorOptionDto,
  createAdminUser,
  deleteAdminUser,
  getAdminUsers,
  getSupervisorOptions,
  updateAdminUser,
} from '../api';
import { Button } from '../components/ui/Button';
import '../styles/employees-admin.css';

function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('ru-RU');
}

function getToday() {
  return new Date().toISOString().slice(0, 10);
}

const initialForm: CreateUserPayload = {
  full_name: '',
  email: '',
  password: '',
  role: 'employer',
  hire_date: getToday(),
  job_title: '',
  department: '',
  supervisor_id: null,
};

export function EmployeesAdminPage() {
  const [users, setUsers] = useState<AdminUserListItemDto[]>([]);
  const [supervisors, setSupervisors] = useState<SupervisorOptionDto[]>([]);
  const [form, setForm] = useState<CreateUserPayload>(initialForm);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    setIsLoading(true);
    setError(null);

    try {
      const [usersData, supervisorsData] = await Promise.all([
        getAdminUsers(),
        getSupervisorOptions(),
      ]);
      setUsers(usersData);
      setSupervisors(supervisorsData);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Не удалось загрузить сотрудников');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const managers = useMemo(
    () => users.filter((item) => item.role === 'manager'),
    [users]
  );

  const employees = useMemo(
    () => users.filter((item) => item.role === 'employer'),
    [users]
  );

  function updateForm<K extends keyof CreateUserPayload>(key: K, value: CreateUserPayload[K]) {
    setForm((current) => {
      const next = { ...current, [key]: value };
      if (key === 'role' && value === 'manager') {
        next.supervisor_id = null;
      }
      return next;
    });
  }

  function resetForm() {
    setForm(initialForm);
    setEditingUserId(null);
  }

  function handleEdit(user: AdminUserListItemDto) {
    setEditingUserId(user.id);
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: '',
      role: user.role as 'employer' | 'manager',
      hire_date: user.hire_date ? user.hire_date.slice(0, 10) : getToday(),
      job_title: user.job_title ?? '',
      department: user.department ?? '',
      supervisor_id: user.role === 'employer' ? (user.supervisor_id ?? null) : null,
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function handleDelete(user: AdminUserListItemDto) {
    const confirmDelete = window.confirm(
      `Удалить пользователя «${user.full_name}»? Пользователь исчезнет из активного списка.`
    );
    if (!confirmDelete) return;

    setError(null);
    setMessage(null);

    try {
      await deleteAdminUser(user.id);
      setMessage('Пользователь удалён');
      if (editingUserId === user.id) {
        resetForm();
      }
      await loadData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Не удалось удалить пользователя');
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (editingUserId) {
        await updateAdminUser(editingUserId, {
          ...form,
          password: form.password.trim() || undefined,
          supervisor_id: form.role === 'manager' ? null : form.supervisor_id ?? null,
        });

        setMessage(form.role === 'manager' ? 'Менеджер обновлён' : 'Стажер обновлён');
      } else {
        await createAdminUser({
          ...form,
          supervisor_id: form.role === 'manager' ? null : form.supervisor_id ?? null,
        });

        setMessage(form.role === 'manager' ? 'Менеджер добавлен' : 'Стажер добавлен');
      }

      resetForm();
      await loadData();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Не удалось сохранить пользователя');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="ui-page employees-admin-page">
      <div className="ui-page__header">
        <div>
          <h1 className="ui-page__title">Сотрудники</h1>
          <p className="ui-page__subtitle">
            Добавление сотрудников и менеджеров, назначение супервизора для сотрудников.
          </p>
        </div>
      </div>

      {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}
      {message ? <div className="feedback-banner feedback-banner--success">{message}</div> : null}

      <div className="employees-admin-grid">
        <form className="ui-card ui-card--padded employees-admin-form" onSubmit={handleSubmit}>
          <div className="employees-admin-form__header">
            <h2 className="employees-admin-form__title">
              {editingUserId ? 'Редактировать пользователя' : 'Добавить пользователя'}
            </h2>
            {editingUserId ? (
              <span className="employees-admin-form__mode-badge">Режим редактирования</span>
            ) : null}
          </div>

          <div className="employees-admin-form__fields">
            <div className="ui-field">
              <label className="ui-field__label">Роль</label>
              <select
                className="ui-input"
                value={form.role}
                onChange={(event) =>
                  updateForm('role', event.target.value as CreateUserPayload['role'])
                }
              >
                <option value="employer">Стажер</option>
                <option value="manager">Менеджер</option>
              </select>
            </div>

            <div className="ui-field">
              <label className="ui-field__label">ФИО</label>
              <input
                className="ui-input"
                value={form.full_name}
                onChange={(event) => updateForm('full_name', event.target.value)}
                placeholder="Иванов Иван Иванович"
              />
            </div>

            <div className="ui-field">
              <label className="ui-field__label">E-mail</label>
              <input
                className="ui-input"
                type="email"
                value={form.email}
                onChange={(event) => updateForm('email', event.target.value)}
                placeholder="user@example.com"
              />
            </div>

            <div className="ui-field">
              <label className="ui-field__label">
                {editingUserId ? 'Новый пароль (необязательно)' : 'Пароль'}
              </label>
              <input
                className="ui-input"
                type="text"
                value={form.password}
                onChange={(event) => updateForm('password', event.target.value)}
                placeholder={
                  editingUserId
                    ? 'Оставьте пустым, чтобы не менять пароль'
                    : 'Минимум 6 символов'
                }
              />
            </div>

            <div className="ui-field">
              <label className="ui-field__label">Дата приёма</label>
              <input
                className="ui-input"
                type="date"
                value={form.hire_date}
                onChange={(event) => updateForm('hire_date', event.target.value)}
              />
            </div>

            <div className="ui-field">
              <label className="ui-field__label">Должность</label>
              <input
                className="ui-input"
                value={form.job_title}
                onChange={(event) => updateForm('job_title', event.target.value)}
                placeholder={form.role === 'manager' ? 'Руководитель отдела продаж' : 'Менеджер по продажам'}
              />
            </div>

            <div className="ui-field">
              <label className="ui-field__label">Отдел</label>
              <input
                className="ui-input"
                value={form.department}
                onChange={(event) => updateForm('department', event.target.value)}
                placeholder="Отдел продаж"
              />
            </div>

            {form.role === 'employer' ? (
              <div className="ui-field">
                <label className="ui-field__label">Супервизор</label>
                <select
                  className="ui-input"
                  value={form.supervisor_id ?? ''}
                  onChange={(event) =>
                    updateForm(
                      'supervisor_id',
                      event.target.value ? Number(event.target.value) : null
                    )
                  }
                >
                  <option value="">Выберите менеджера</option>
                  {supervisors.map((supervisor) => (
                    <option key={supervisor.id} value={supervisor.id}>
                      {supervisor.full_name}
                      {supervisor.department ? ` — ${supervisor.department}` : ''}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="employees-admin-hint">
                Для менеджера супервизор назначается автоматически: администратор.
              </div>
            )}
          </div>

          <div className="ui-detail-actions">
            <Button type="submit" disabled={isSaving}>
              {isSaving
                ? 'Сохранение…'
                : editingUserId
                ? 'Сохранить изменения'
                : 'Добавить'}
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={resetForm}
              disabled={isSaving}
            >
              {editingUserId ? 'Отменить редактирование' : 'Очистить'}
            </Button>
          </div>
        </form>

        <div className="employees-admin-lists">
          <div className="ui-card ui-card--padded">
            <h2 className="employees-admin-list__title">Менеджеры</h2>

            {isLoading ? (
              <div className="ui-empty-card">Загрузка…</div>
            ) : managers.length === 0 ? (
              <div className="ui-empty-card">Пока нет менеджеров.</div>
            ) : (
              <div className="employees-admin-list">
                {managers.map((user) => (
                  <article key={user.id} className="employees-admin-user-card">
                    <div>
                      <h3 className="employees-admin-user-card__name">{user.full_name}</h3>
                      <p className="employees-admin-user-card__meta">{user.email}</p>
                    </div>

                    <p className="employees-admin-user-card__meta">
                      Дата приёма: {formatDate(user.hire_date)}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Должность: {user.job_title ?? '—'}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Отдел: {user.department ?? '—'}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Супервизор: {user.supervisor_name ?? '—'}
                    </p>

                    <div className="employees-admin-user-card__actions">
                      <Button variant="outline" onClick={() => handleEdit(user)}>
                        Редактировать
                      </Button>
                      <Button variant="danger" onClick={() => void handleDelete(user)}>
                        Удалить
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="ui-card ui-card--padded">
            <h2 className="employees-admin-list__title">Стажеры</h2>

            {isLoading ? (
              <div className="ui-empty-card">Загрузка…</div>
            ) : employees.length === 0 ? (
              <div className="ui-empty-card">Пока нет сотрудников.</div>
            ) : (
              <div className="employees-admin-list">
                {employees.map((user) => (
                  <article key={user.id} className="employees-admin-user-card">
                    <div>
                      <h3 className="employees-admin-user-card__name">{user.full_name}</h3>
                      <p className="employees-admin-user-card__meta">{user.email}</p>
                    </div>

                    <p className="employees-admin-user-card__meta">
                      Дата приёма: {formatDate(user.hire_date)}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Должность: {user.job_title ?? '—'}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Отдел: {user.department ?? '—'}
                    </p>
                    <p className="employees-admin-user-card__meta">
                      Супервизор: {user.supervisor_name ?? '—'}
                    </p>

                    <div className="employees-admin-user-card__actions">
                      <Button variant="outline" onClick={() => handleEdit(user)}>
                        Редактировать
                      </Button>
                      <Button variant="danger" onClick={() => void handleDelete(user)}>
                        Удалить
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}