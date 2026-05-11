import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import '../styles/dialog-trainer.css';

type TrainerScenario = {
  id: number;
  title: string;
  scenario_type: string;
  funnel_stage: string;
  is_full_funnel: boolean;
  description?: string | null;
  stage_hint?: string | null;
  final_goal?: string | null;
};

type TrainerClient = {
  id: number;
  name: string;
  position?: string | null;
  age?: number | null;
  temperament?: string | null;
  attitude?: string | null;
  communication_style?: string | null;
  buying_history?: string | null;
  decision_role?: string | null;
  tech_level?: string | null;
  persona?: string | null;
  pain_points?: string | null;
  typical_objections?: string | null;
};

type TrainerDifficulty = {
  code: string;
  title: string;
  description: string;
};

type TrainerOptions = {
  scenarios: TrainerScenario[];
  clients: TrainerClient[];
  products?: unknown[];
  difficulties: TrainerDifficulty[];
};

type TrainerMessage = {
  id: number;
  sender_type: 'user' | 'virtual_client' | 'system';
  message_text: string;
  created_at: string;
};

type TrainerSessionProduct = {
  id: number;
  product_id?: number | null;
  product_title: string;
  product_context?: string | null;
};

type TrainerResult = {
  total_score: number;
  strong_sides?: string | null;
  weak_sides?: string | null;
  recommendations?: string | null;
  created_at?: string | null;
};

type TrainerSessionSummary = {
  id: number;
  scenario_id: number;
  scenario_title: string;
  scenario_description?: string | null;
  funnel_stage: string;
  current_stage: string;
  stage_hint?: string | null;
  final_goal?: string | null;
  is_full_funnel: boolean;
  client_id: number;
  client_name: string;
  client_position?: string | null;
  client_age?: number | null;
  client_temperament?: string | null;
  client_attitude?: string | null;
  client_communication_style?: string | null;
  client_buying_history?: string | null;
  client_decision_role?: string | null;
  client_tech_level?: string | null;
  client_persona?: string | null;
  client_pain_points?: string | null;
  client_typical_objections?: string | null;
  difficulty: string;
  mode: string;
  status: string;
  goal_reached: boolean;
  auto_completed: boolean;
  brief_start_tip: string;
  started_at: string;
  completed_at?: string | null;
  total_score?: number | null;
  last_message?: string | null;
  selected_products?: TrainerSessionProduct[];
};

type TrainerSession = TrainerSessionSummary & {
  messages: TrainerMessage[];
  result?: TrainerResult | null;
};

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const DEFAULT_SCENARIOS: TrainerScenario[] = [
  {
    id: 1,
    title: 'Полная воронка продаж',
    scenario_type: 'custom',
    funnel_stage: 'intro',
    is_full_funnel: true,
    description: 'Полная тренировка от первого контакта до договорённости о следующем шаге.',
    stage_hint: 'Тренировка проходит через все этапы: холодный звонок, выявление потребности, презентация, обработка возражений и закрытие сделки.',
    final_goal: 'Клиент согласился на конкретный следующий шаг: заявку, подключение, КП, демо, встречу или повторный контакт.',
  },
  {
    id: 2,
    title: 'Холодный звонок',
    scenario_type: 'cold_call',
    funnel_stage: 'intro',
    is_full_funnel: false,
    description: 'Первый контакт с потенциальным клиентом.',
    stage_hint: 'Менеджер должен представиться, назвать компанию, объяснить повод обращения и получить разрешение продолжить разговор.',
    final_goal: 'Клиент согласился продолжить разговор или ответить на 1–2 уточняющих вопроса.',
  },
  {
    id: 3,
    title: 'Выявление потребности',
    scenario_type: 'custom',
    funnel_stage: 'need_discovery',
    is_full_funnel: false,
    description: 'Этап уточнения задачи клиента.',
    stage_hint: 'Менеджер задаёт открытые вопросы, чтобы понять боль клиента, текущую ситуацию и критерии выбора.',
    final_goal: 'Клиент сформулировал проблему, потребность или критерии выбора.',
  },
  {
    id: 4,
    title: 'Презентация продукта',
    scenario_type: 'custom',
    funnel_stage: 'presentation',
    is_full_funnel: false,
    description: 'Этап объяснения ценности продукта.',
    stage_hint: 'Менеджер связывает продукт с потребностью клиента и объясняет пользу без перегруза деталями.',
    final_goal: 'Клиент понял ценность предложения и готов обсуждать условия или следующий шаг.',
  },
  {
    id: 5,
    title: 'Обработка возражений',
    scenario_type: 'objection_handling',
    funnel_stage: 'objection',
    is_full_funnel: false,
    description: 'Этап обработки сомнений клиента.',
    stage_hint: 'Менеджер признаёт сомнение, уточняет причину и даёт аргумент без спора и давления.',
    final_goal: 'Клиент принял аргумент или согласился продолжить обсуждение.',
  },
  {
    id: 6,
    title: 'Закрытие сделки',
    scenario_type: 'closing',
    funnel_stage: 'closing',
    is_full_funnel: false,
    description: 'Финальный этап перевода клиента к конкретному действию.',
    stage_hint: 'Менеджер подводит итог, предлагает конкретный следующий шаг и согласует время или действие.',
    final_goal: 'Клиент согласился на заявку, подключение, демо, КП, встречу или повторный контакт.',
  },
];

const DEFAULT_CLIENTS: TrainerClient[] = [
  {
    id: 1,
    name: 'Евгений',
    position: 'Руководитель отдела продаж',
    age: 38,
    temperament: 'рациональный, быстрый, требовательный',
    attitude: 'занят, готов слушать только конкретику',
    communication_style: 'отвечает коротко, перебивает длинные презентации, просит цифры и сроки',
    buying_history: 'Нет',
    decision_role: 'лицо, влияющее на решение',
    tech_level: 'высокий',
    persona: 'Деловой и занятый клиент. Если менеджер говорит общо, быстро теряет интерес.',
    pain_points: 'Хочет контролировать расходы команды, быстро подключать сотрудников и видеть прозрачную детализацию.',
    typical_objections: 'нет времени; у нас уже есть оператор; покажите выгоду в цифрах',
  },
  {
    id: 2,
    name: 'Ольга',
    position: 'Частный клиент, мама двоих детей',
    age: 42,
    temperament: 'доброжелательная, осторожная',
    attitude: 'открыта к разговору, но боится сложных условий',
    communication_style: 'задаёт бытовые вопросы, просит объяснять простыми словами',
    buying_history: 'Да',
    decision_role: 'самостоятельно принимает решение',
    tech_level: 'средний',
    persona: 'Вежлива и готова слушать, если менеджер не давит и объясняет человеческим языком.',
    pain_points: 'Хочет контролировать расходы детей и не получать неожиданные списания.',
    typical_objections: 'сложно переносить номера; дети не разберутся; боюсь скрытых платежей',
  },
  {
    id: 3,
    name: 'Игорь',
    position: 'Коммерческий директор',
    age: 45,
    temperament: 'скептичный, жёсткий, аналитичный',
    attitude: 'сомневается и проверяет каждое обещание',
    communication_style: 'может грубить, если слышит рекламные фразы; уважает точные аргументы',
    buying_history: 'Нет',
    decision_role: 'ключевое лицо, принимающее решение',
    tech_level: 'высокий',
    persona: 'Не любит мягкие обещания. Ему нужны риски, экономика, пилот и понятный контроль результата.',
    pain_points: 'Нужны экономия бюджета, контроль корпоративных номеров и отсутствие хаоса при подключении сотрудников.',
    typical_objections: 'дорого; уже есть оператор; не верю обещаниям; нужен пилот',
  },
  {
    id: 4,
    name: 'Николай Петрович',
    position: 'Пенсионер',
    age: 68,
    temperament: 'спокойный, осторожный, медленный в принятии решения',
    attitude: 'вежливый, но плохо воспринимает технические термины',
    communication_style: 'часто просит повторить, не любит англицизмы и сложные тарифные формулировки',
    buying_history: 'Да',
    decision_role: 'самостоятельно принимает решение, но может советоваться с семьёй',
    tech_level: 'низкий',
    persona: 'Не грубит, но легко теряется, если менеджер говорит быстро или технически сложно.',
    pain_points: 'Хочет простой тариф без скрытых списаний и непонятных услуг.',
    typical_objections: 'я не понимаю гигабайты; мне бы без лишнего; не хочу, чтобы списывали деньги',
  },
];

const DEFAULT_DIFFICULTIES: TrainerDifficulty[] = [
  { code: 'easy', title: 'Лёгкая', description: 'Клиент открыт к разговору, отвечает спокойно и быстрее соглашается на следующий шаг.' },
  { code: 'medium', title: 'Средняя', description: 'Клиент отвечает нейтрально, задаёт уточнения, сомневается и ждёт понятной пользы.' },
  { code: 'hard', title: 'Сложная', description: 'Клиент занят, сопротивляется, может отвечать резко и требует конкретные аргументы.' },
];

const DEFAULT_OPTIONS: TrainerOptions = {
  scenarios: DEFAULT_SCENARIOS,
  clients: DEFAULT_CLIENTS,
  difficulties: DEFAULT_DIFFICULTIES,
};

const STAGE_TITLES: Record<string, string> = {
  intro: 'Холодный звонок',
  need_discovery: 'Выявление потребности',
  presentation: 'Презентация продукта',
  objection: 'Обработка возражений',
  closing: 'Закрытие сделки',
  custom: 'Индивидуальный этап',
};

function getToken(): string | null {
  return localStorage.getItem('mentorai_token');
}

async function parseError(response: Response): Promise<Error> {
  const error = await response.json().catch(() => ({ detail: 'Ошибка запроса' }));
  if (Array.isArray(error.detail)) {
    const message = error.detail
      .map((item: { msg?: string }) => item?.msg)
      .filter(Boolean)
      .join('; ');
    return new Error(message || 'Ошибка запроса');
  }
  return new Error(error.detail ?? 'Ошибка запроса');
}

async function authorizedFetch(input: RequestInfo | URL, init?: RequestInit) {
  const token = getToken();
  const headers = new Headers(init?.headers ?? {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

async function getTrainerOptions(): Promise<TrainerOptions> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/options`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function getTrainerSessions(): Promise<TrainerSessionSummary[]> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/sessions`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function getTrainerSession(sessionId: number): Promise<TrainerSession> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/sessions/${sessionId}`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function createTrainerSession(payload: {
  scenario_id: number;
  client_id: number;
  difficulty: string;
  mode: string;
}): Promise<TrainerSession> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function sendTrainerMessage(sessionId: number, message: string): Promise<TrainerSession> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function finishTrainerSession(sessionId: number): Promise<TrainerSession> {
  const response = await authorizedFetch(`${API_URL}/api/trainer/sessions/${sessionId}/finish`, { method: 'POST' });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function difficultyTitle(options: TrainerOptions, code: string) {
  return options.difficulties.find((item) => item.code === code)?.title ?? code;
}

function modeTitle(mode: string) {
  return mode === 'exam' ? 'Экзамен' : 'Тренировка';
}

function splitLines(value?: string | null) {
  return (value || '').split('\n').map((line) => line.trim()).filter(Boolean);
}

function renderValue(value?: string | number | null) {
  return value === undefined || value === null || value === '' ? 'не указано' : value;
}

function formatCompanyUsage(value?: string | null) {
  const normalized = (value || '').toLowerCase().replace('ё', 'е').trim();
  if (!normalized) return 'Нет';
  if (['да', 'yes', 'true', '1'].includes(normalized)) return 'Да';
  if (['нет', 'no', 'false', '0'].includes(normalized)) return 'Нет';
  if (normalized.includes('не пользов') || normalized.includes('не работал') || normalized.includes('не покуп')) return 'Нет';
  if (normalized.includes('польз') || normalized.includes('покуп') || normalized.includes('работал')) return 'Да';
  return 'Нет';
}

function getRingPercent(value: number, max: number) {
  if (max <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((value / max) * 100)));
}

function AnalyticsCard({
  value,
  label,
  percent,
  tone,
}: {
  value: string | number;
  label: string;
  percent: number;
  tone: 'brown' | 'green' | 'orange' | 'gray';
}) {
  return (
    <article className="trainer-analytics-card">
      <div
        className={`trainer-analytics-ring trainer-analytics-ring--${tone}`}
        style={{ ['--value' as string]: `${percent}%` }}
      >
        <span>{value}</span>
      </div>
      <p>{label}</p>
    </article>
  );
}

export default function DialogTrainerPage() {
  const [options, setOptions] = useState<TrainerOptions>(DEFAULT_OPTIONS);
  const [sessions, setSessions] = useState<TrainerSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<TrainerSession | null>(null);

  const [selectedScenarioId, setSelectedScenarioId] = useState<number | ''>('');
  const [selectedClientId, setSelectedClientId] = useState<number | ''>('');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<string>('practice');

  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBriefOpen, setIsBriefOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const selectedScenario = useMemo(
    () => options.scenarios.find((item) => item.id === Number(selectedScenarioId)) || null,
    [options, selectedScenarioId]
  );

  const selectedClient = useMemo(
    () => options.clients.find((item) => item.id === Number(selectedClientId)) || null,
    [options, selectedClientId]
  );

  const selectedDifficultyInfo = useMemo(
    () => options.difficulties.find((item) => item.code === selectedDifficulty) || null,
    [options, selectedDifficulty]
  );

  const canStart = Boolean(selectedScenario && selectedClient && selectedDifficulty);

  const groupedSessions = useMemo(() => {
    const sortByDateDesc = (items: TrainerSessionSummary[]) =>
      [...items].sort((left, right) => new Date(right.started_at).getTime() - new Date(left.started_at).getTime());

    return {
      exams: sortByDateDesc(sessions.filter((item) => item.mode === 'exam')),
      practice: sortByDateDesc(sessions.filter((item) => item.mode !== 'exam')),
    };
  }, [sessions]);

  const analytics = useMemo(() => {
    const total = sessions.length;
    const completed = sessions.filter((item) => item.status === 'completed').length;
    const scored = sessions.filter((item) => typeof item.total_score === 'number');
    const avgScore = scored.length
      ? Math.round(scored.reduce((sum, item) => sum + Number(item.total_score || 0), 0) / scored.length)
      : 0;

    return {
      total,
      completed,
      avgScore,
      exams: sessions.filter((item) => item.mode === 'exam').length,
      practice: sessions.filter((item) => item.mode !== 'exam').length,
    };
  }, [sessions]);

  useEffect(() => {
    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const loadedOptions = await getTrainerOptions();
        setOptions({
          scenarios: loadedOptions.scenarios.length ? loadedOptions.scenarios : DEFAULT_OPTIONS.scenarios,
          clients: loadedOptions.clients.length ? loadedOptions.clients : DEFAULT_OPTIONS.clients,
          difficulties: loadedOptions.difficulties.length ? loadedOptions.difficulties : DEFAULT_OPTIONS.difficulties,
          products: loadedOptions.products || [],
        });
        const loadedSessions = await getTrainerSessions();
        setSessions(loadedSessions);
      } catch {
        setOptions(DEFAULT_OPTIONS);
        setInfo('Не удалось загрузить данные тренажёра с backend. Проверьте /api/trainer/options и перезапуск content-service.');
      } finally {
        setIsLoading(false);
      }
    }

    void bootstrap();
  }, []);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [activeSession?.messages.length, isSending, activeSession?.status]);

  function resetComposerHeight() {
    if (!composerRef.current) return;
    composerRef.current.style.height = '44px';
  }

  function growComposer() {
    if (!composerRef.current) return;
    composerRef.current.style.height = '44px';
    composerRef.current.style.height = `${Math.min(composerRef.current.scrollHeight, 128)}px`;
  }

  function resetDialogForm() {
    setSelectedScenarioId('');
    setSelectedClientId('');
    setSelectedDifficulty('');
    setSelectedMode('practice');
  }

  function openNewDialogModal() {
    resetDialogForm();
    setError(null);
    setIsModalOpen(true);
  }

  async function openSession(sessionId: number) {
    setError(null);
    try {
      const session = await getTrainerSession(sessionId);
      setActiveSession(session);
      setMessage('');
      resetComposerHeight();
    } catch (sessionError) {
      setError(sessionError instanceof Error ? sessionError.message : 'Не удалось открыть диалог');
    }
  }

  async function refreshSessions(updated?: TrainerSession) {
    try {
      const loaded = await getTrainerSessions();
      setSessions(loaded);
      if (updated) {
        setSessions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      }
    } catch {
      if (updated) {
        setSessions((prev) => [updated, ...prev.filter((item) => item.id !== updated.id)]);
      }
    }
  }

  async function handleCreateSession() {
    if (!canStart || !selectedScenario || !selectedClient || !selectedDifficulty) return;
    setIsCreating(true);
    setError(null);

    try {
      const created = await createTrainerSession({
        scenario_id: selectedScenario.id,
        client_id: selectedClient.id,
        difficulty: selectedDifficulty,
        mode: selectedMode,
      });
      setActiveSession(created);
      setSessions((prev) => [created, ...prev.filter((item) => item.id !== created.id)]);
      setIsModalOpen(false);
      setIsBriefOpen(true);
      setMessage('');
      resetComposerHeight();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Не удалось создать диалог');
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSend(event?: FormEvent) {
    event?.preventDefault();
    if (!activeSession || !message.trim() || isSending || activeSession.status === 'completed') return;

    const normalized = message.trim();
    setMessage('');
    resetComposerHeight();
    setIsSending(true);
    setError(null);

    try {
      const updated = await sendTrainerMessage(activeSession.id, normalized);
      setActiveSession(updated);
      await refreshSessions(updated);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Не удалось отправить реплику');
      setMessage(normalized);
      setTimeout(growComposer, 0);
    } finally {
      setIsSending(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  async function handleFinishManual() {
    if (!activeSession || activeSession.status === 'completed') return;
    setError(null);
    try {
      const updated = await finishTrainerSession(activeSession.id);
      setActiveSession(updated);
      await refreshSessions(updated);
    } catch (finishError) {
      setError(finishError instanceof Error ? finishError.message : 'Не удалось завершить диалог');
    }
  }

  function renderHistoryItems(items: TrainerSessionSummary[]) {
    return items.map((session) => (
      <button
        key={session.id}
        type="button"
        className="trainer-history-item"
        onClick={() => void openSession(session.id)}
      >
        <span className="trainer-history-main">
          <strong>{session.scenario_title}</strong>
          <small>
            {formatDate(session.started_at)}
            {' · '}
            {modeTitle(session.mode)}
            {' · '}
            {session.status === 'completed' ? 'завершён' : 'активный'}
            {typeof session.total_score === 'number' ? ` · результат ${session.total_score}%` : ''}
          </small>
        </span>
        <em>перейти к информации</em>
      </button>
    ));
  }

  const currentStageTitle = activeSession
    ? STAGE_TITLES[activeSession.current_stage] || activeSession.current_stage
    : '';

  const sessionHeader = activeSession
    ? [
        modeTitle(activeSession.mode),
        activeSession.scenario_title !== currentStageTitle ? activeSession.scenario_title : null,
        currentStageTitle,
        difficultyTitle(options, activeSession.difficulty),
      ]
        .filter((item): item is string => Boolean(item))
        .join(' · ')
    : '';

  return (
    <section className={`trainer-page ${activeSession ? 'trainer-page--chat' : ''}`}>
      <div className="trainer-shell">
        {error ? <div className="trainer-alert trainer-alert--error">{error}</div> : null}
        {info && !activeSession ? <div className="trainer-alert trainer-alert--info">{info}</div> : null}

        {!activeSession ? (
          <div className="trainer-home">
            <div className="trainer-home-header">
              <div>
                <h1>Ваша история диалогов</h1>
                <p className="trainer-home-subtitle">Просматривайте результаты тренировок и переходите к информации по каждой сессии.</p>
              </div>

              <button
                type="button"
                className="trainer-primary-btn trainer-new-btn"
                onClick={openNewDialogModal}
              >
                Новый диалог
              </button>
            </div>

            <div className="trainer-history-analytics">
              <AnalyticsCard value={analytics.total} label="Всего сессий" percent={100} tone="brown" />
              <AnalyticsCard
                value={analytics.completed}
                label="Завершено"
                percent={getRingPercent(analytics.completed, analytics.total)}
                tone="green"
              />
              <AnalyticsCard value={`${analytics.avgScore}%`} label="Средний результат" percent={analytics.avgScore} tone="orange" />
              <AnalyticsCard value={analytics.exams} label="Экзамены" percent={getRingPercent(analytics.exams, analytics.total)} tone="gray" />
              <AnalyticsCard
                value={analytics.practice}
                label="Тренировки"
                percent={getRingPercent(analytics.practice, analytics.total)}
                tone="green"
              />
            </div>

            {isLoading ? <p className="trainer-muted">Загружаю данные тренажёра…</p> : null}

            {!isLoading && sessions.length === 0 ? (
              <p className="trainer-muted">Пока нет завершённых или начатых диалогов. Нажмите «Новый диалог», чтобы начать тренировку.</p>
            ) : null}

            <div className="trainer-history-scroll">
              {groupedSessions.exams.length ? (
                <section className="trainer-history-group">
                  <h2>Экзамены</h2>
                  <div className="trainer-history-list">
                    {renderHistoryItems(groupedSessions.exams)}
                  </div>
                </section>
              ) : null}

              {groupedSessions.practice.length ? (
                <section className="trainer-history-group">
                  <h2>Тренировочные диалоги</h2>
                  <div className="trainer-history-list">
                    {renderHistoryItems(groupedSessions.practice)}
                  </div>
                </section>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="trainer-chat-layout">
            <div className="trainer-chat-header">
              <button type="button" className="trainer-secondary-btn trainer-back-btn" onClick={() => setActiveSession(null)}>
                ← К истории
              </button>

              <div className="trainer-chat-meta">
                <p>{sessionHeader}</p>
              </div>

              <button type="button" className="trainer-primary-btn trainer-primary-btn--small" onClick={() => setIsBriefOpen(true)}>
                Информация
              </button>

              {activeSession.status !== 'completed' ? (
                <button type="button" className="trainer-secondary-btn" onClick={() => void handleFinishManual()}>
                  Завершить вручную
                </button>
              ) : null}
            </div>

            <div className="trainer-active-goal">
              <b>Финальная цель:</b>
              <span>{activeSession.final_goal || 'Довести клиента до целевого действия.'}</span>
              {activeSession.status === 'completed' ? (
                <em className={activeSession.goal_reached ? 'trainer-goal-good' : 'trainer-goal-manual'}>
                  {activeSession.goal_reached ? 'Цель достигнута автоматически' : 'Завершено вручную'}
                </em>
              ) : null}
            </div>

            <div className="trainer-thread" ref={threadRef}>
              {activeSession.messages.map((item) => (
                <div key={item.id} className={`trainer-message trainer-message--${item.sender_type}`}>
                  <div className="trainer-message-bubble">
                    {splitLines(item.message_text).map((line, index) => (
                      <p key={`${item.id}-${index}`}>{line}</p>
                    ))}
                  </div>
                </div>
              ))}

              {isSending ? (
                <div className="trainer-message trainer-message--virtual_client">
                  <div className="trainer-message-bubble">
                    <p>Клиент отвечает…</p>
                  </div>
                </div>
              ) : null}
            </div>

            {activeSession.result ? (
              <div className="trainer-result-card">
                <div className="trainer-result-head">
                  <h2>Итоговая информация</h2>
                  <span className="trainer-result-score">{activeSession.result.total_score}%</span>
                </div>

                <div className="trainer-result-grid">
                  <div>
                    <b>Сильные стороны</b>
                    {splitLines(activeSession.result.strong_sides).map((line) => <p key={line}>{line}</p>)}
                  </div>
                  <div>
                    <b>Что улучшить</b>
                    {splitLines(activeSession.result.weak_sides).map((line) => <p key={line}>{line}</p>)}
                  </div>
                  <div>
                    <b>Рекомендации</b>
                    {splitLines(activeSession.result.recommendations).map((line) => <p key={line}>{line}</p>)}
                  </div>
                </div>
              </div>
            ) : null}

            {activeSession.status !== 'completed' ? (
              <form className="trainer-composer" onSubmit={(event) => void handleSend(event)}>
                <textarea
                  ref={composerRef}
                  value={message}
                  placeholder="Напишите реплику менеджера"
                  onChange={(event) => {
                    setMessage(event.target.value);
                    setTimeout(growComposer, 0);
                  }}
                  onKeyDown={handleComposerKeyDown}
                  disabled={isSending}
                />
                <button type="submit" disabled={!message.trim() || isSending}>
                  ↑
                </button>
              </form>
            ) : null}
          </div>
        )}

        {isModalOpen ? (
          <div className="trainer-modal-backdrop" role="presentation">
            <div className="trainer-modal trainer-modal--wide">
              <div className="trainer-modal-header">
                <h2>Новый диалог</h2>
                <button type="button" onClick={() => setIsModalOpen(false)}>×</button>
              </div>

              <div className="trainer-form-grid">
                <label>
                  <span>Сценарий</span>
                  <select value={selectedScenarioId} onChange={(event) => setSelectedScenarioId(Number(event.target.value) || '')}>
                    <option value="">Выберите сценарий</option>
                    {options.scenarios.map((scenario) => (
                      <option key={scenario.id} value={scenario.id}>{scenario.title}</option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Клиент</span>
                  <select value={selectedClientId} onChange={(event) => setSelectedClientId(Number(event.target.value) || '')}>
                    <option value="">Выберите клиента</option>
                    {options.clients.map((client) => (
                      <option key={client.id} value={client.id}>{client.name}</option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Сложность</span>
                  <select value={selectedDifficulty} onChange={(event) => setSelectedDifficulty(event.target.value)}>
                    <option value="">Выберите сложность</option>
                    {options.difficulties.map((difficulty) => (
                      <option key={difficulty.code} value={difficulty.code}>{difficulty.title}</option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Режим</span>
                  <select value={selectedMode} onChange={(event) => setSelectedMode(event.target.value)}>
                    <option value="practice">Тренировка</option>
                    <option value="exam">Экзамен</option>
                  </select>
                </label>
              </div>

              <div className="trainer-parameter-cards">
                <div className="trainer-hint-card">
                  <b>Сценарий</b>
                  <p>{selectedScenario?.description || 'Выберите сценарий тренировки.'}</p>
                  <p>{selectedScenario?.stage_hint || ''}</p>
                </div>

                <div className="trainer-hint-card">
                  <b>Клиент</b>
                  <p>{selectedClient ? `${selectedClient.name}, ${renderValue(selectedClient.position)}` : 'Выберите профиль клиента.'}</p>
                  <p>{selectedClient?.persona || selectedClient?.communication_style || ''}</p>
                </div>

                <div className="trainer-hint-card">
                  <b>Сложность</b>
                  <p>{selectedDifficultyInfo?.description || 'Выберите уровень сложности.'}</p>
                </div>
              </div>

              <div className="trainer-modal-actions">
                <button type="button" className="trainer-secondary-btn" onClick={() => setIsModalOpen(false)}>
                  Отмена
                </button>
                <button type="button" className="trainer-primary-btn" onClick={() => void handleCreateSession()} disabled={!canStart || isCreating}>
                  {isCreating ? 'Создаю…' : 'Начать диалог'}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {isBriefOpen && activeSession ? (
          <div className="trainer-modal-backdrop" role="presentation">
            <div className="trainer-modal trainer-modal--brief">
              <div className="trainer-modal-header">
                <h2>Информация о диалоге</h2>
                <button type="button" onClick={() => setIsBriefOpen(false)}>×</button>
              </div>

              <div className="trainer-brief-content">
                <section>
                  <b>Сценарий</b>
                  <p>{activeSession.scenario_title}</p>
                  <p>{activeSession.scenario_description || 'Описание не указано.'}</p>
                  <p><strong>Текущий этап:</strong> {currentStageTitle}</p>
                  <p><strong>Финальная цель:</strong> {activeSession.final_goal || 'не указана'}</p>
                </section>

                <section>
                  <b>Клиент</b>
                  <p>{activeSession.client_name}, {renderValue(activeSession.client_position)}</p>
                  <p><strong>Возраст:</strong> {renderValue(activeSession.client_age)}</p>
                  <p><strong>Темперамент:</strong> {renderValue(activeSession.client_temperament)}</p>
                  <p><strong>Настрой:</strong> {renderValue(activeSession.client_attitude)}</p>
                  <p><strong>Пользуется услугами компании:</strong> {formatCompanyUsage(activeSession.client_buying_history)}</p>
                  <p><strong>Роль в принятии решения:</strong> {renderValue(activeSession.client_decision_role)}</p>
                </section>

                <section>
                  <b>Боли и возражения</b>
                  <p><strong>Боли:</strong> {renderValue(activeSession.client_pain_points)}</p>
                  <p><strong>Типичные возражения:</strong> {renderValue(activeSession.client_typical_objections)}</p>
                </section>
              </div>

              <div className="trainer-modal-actions">
                <button type="button" className="trainer-primary-btn" onClick={() => setIsBriefOpen(false)}>
                  Понятно
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
