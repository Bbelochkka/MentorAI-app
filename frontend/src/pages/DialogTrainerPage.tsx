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
    buying_history: 'раньше услугами компании не пользовался',
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
    buying_history: 'покупала SIM-карту NovaMobile для себя',
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
    buying_history: 'с компанией не работал, есть негативный опыт с другим оператором',
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
    buying_history: 'пользовался услугами компании несколько лет назад',
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
  return mode === 'exam' ? 'Экзамен' : 'Тестовая сессия';
}

function buildStartTip(scenario: TrainerScenario) {
  if (scenario.is_full_funnel) {
    return 'Вы выбрали полную воронку. Начните с холодного звонка: представьтесь, назовите компанию, объясните повод обращения и получите разрешение продолжить разговор.';
  }

  const tips: Record<string, string> = {
    intro: 'Начните с короткого приветствия: представьтесь, назовите компанию, объясните повод обращения и спросите, удобно ли клиенту говорить.',
    need_discovery: 'Первые этапы воронки уже прошли: контакт установлен, клиент готов продолжить разговор. Начните с открытого вопроса о текущей ситуации, потребностях и критериях выбора.',
    presentation: 'Первые этапы воронки уже прошли: контакт установлен и базовая потребность клиента известна. Начните с короткой связки: какую задачу клиента вы услышали и как продукт компании помогает её решить.',
    objection: 'Первые этапы воронки уже прошли: клиент знает предложение, но сомневается. Начните с признания сомнения, уточните причину возражения и только потом давайте аргумент.',
    closing: 'Первые этапы воронки уже прошли: клиент заинтересован и основные сомнения сняты. Начните с короткого итога пользы и предложите конкретный следующий шаг: заявку, КП, демо, встречу или подключение.',
  };

  return tips[scenario.funnel_stage] ?? 'Начните с уточнения ситуации клиента и аккуратно ведите разговор к цели, указанной в карточке сценария.';
}

function splitLines(value?: string | null) {
  return (value || '').split('\n').map((line) => line.trim()).filter(Boolean);
}

export function DialogTrainerPage() {
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
      setSessions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
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
      setSessions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (finishError) {
      setError(finishError instanceof Error ? finishError.message : 'Не удалось завершить диалог');
    }
  }

  const completedDialogs = sessions.filter((item) => item.status === 'completed').length;

  return (
    <section className={`trainer-page ${activeSession ? 'trainer-page--chat' : ''}`}>
      <div className="trainer-shell">
        <div className="trainer-breadcrumb">Главная &gt; Диалоговый тренажёр</div>

        {error ? <div className="trainer-alert trainer-alert--error">{error}</div> : null}
        {info && !activeSession ? <div className="trainer-alert trainer-alert--info">{info}</div> : null}

        {!activeSession ? (
          <>
            <div className="trainer-metrics">
              <div className="trainer-metric-card">
                <div className="trainer-ring trainer-ring--green"><span>75%</span></div>
                <div>
                  <b>Индекс адаптации</b>
                  <span>+ 10% за прошлый месяц</span>
                  <small>по диалогам</small>
                </div>
              </div>
              <div className="trainer-metric-card">
                <div className="trainer-ring trainer-ring--orange"><span>60%</span></div>
                <div>
                  <b>Пройдено тестов</b>
                  <span>+ 10% за прошлый месяц</span>
                  <small>по учебному плану</small>
                </div>
              </div>
              <div className="trainer-metric-card">
                <div className="trainer-ring trainer-ring--red"><span>25%</span></div>
                <div>
                  <b>Процент правильных ответов</b>
                  <span>+ 10% за прошлый месяц</span>
                  <small>по тестам</small>
                </div>
              </div>
              <div className="trainer-metric-card">
                <div className="trainer-ring trainer-ring--gray"><span>{completedDialogs}</span></div>
                <div>
                  <b>Пройдено экзаменов</b>
                  <span>+ 10% за прошлый месяц</span>
                  <small>по тренажёру</small>
                </div>
              </div>
            </div>

            <div className="trainer-home">
              <h1>Ваша история диалогов:</h1>
              {isLoading ? <p className="trainer-muted">Загружаю данные тренажёра…</p> : null}
              {!isLoading && sessions.length === 0 ? (
                <p className="trainer-muted">Пока нет завершённых или начатых диалогов. Нажмите «Новый диалог», чтобы начать тренировку.</p>
              ) : null}
              <div className="trainer-history-list">
                {sessions.map((session) => (
                  <button key={session.id} type="button" className="trainer-history-item" onClick={() => void openSession(session.id)}>
                    <span>{session.scenario_title} ({formatDate(session.started_at)})</span>
                    <em>{session.status === 'completed' ? 'перейти к информации' : 'продолжить диалог'}</em>
                  </button>
                ))}
              </div>
              <button type="button" className="trainer-primary-btn trainer-new-btn" onClick={openNewDialogModal}>
                Новый диалог
              </button>
            </div>
          </>
        ) : (
          <div className="trainer-chat-layout">
            <div className="trainer-chat-header">
              <button type="button" className="trainer-secondary-btn trainer-back-btn" onClick={() => setActiveSession(null)}>
                ← К истории
              </button>
              <div className="trainer-chat-meta">
                <p>
                  {activeSession.scenario_title} · {STAGE_TITLES[activeSession.current_stage] || activeSession.current_stage} · {difficultyTitle(options, activeSession.difficulty)} · {modeTitle(activeSession.mode)}
                </p>
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
                  <div className="trainer-message-bubble">Клиент отвечает…</div>
                </div>
              ) : null}
            </div>

            {activeSession.status === 'completed' && activeSession.result ? (
              <div className="trainer-result-card">
                <div className="trainer-result-head">
                  <h2>Итог тренировки</h2>
                  <div className="trainer-result-score">{Math.round(activeSession.result.total_score)}%</div>
                </div>
                <div className="trainer-result-grid">
                  <div>
                    <b>Сильные стороны</b>
                    {splitLines(activeSession.result.strong_sides).map((line) => <p key={line}>{line}</p>)}
                  </div>
                  <div>
                    <b>Зоны роста</b>
                    {splitLines(activeSession.result.weak_sides).map((line) => <p key={line}>{line}</p>)}
                  </div>
                  <div>
                    <b>Рекомендации</b>
                    {splitLines(activeSession.result.recommendations).map((line) => <p key={line}>{line}</p>)}
                  </div>
                </div>
              </div>
            ) : (
              <form className="trainer-composer" onSubmit={(event) => void handleSend(event)}>
                <textarea
                  ref={composerRef}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  onInput={growComposer}
                  onKeyDown={handleComposerKeyDown}
                  placeholder="Введите реплику менеджера"
                  disabled={isSending}
                  rows={1}
                />
                <button type="submit" disabled={isSending || !message.trim()}>
                  ➤
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {isModalOpen ? (
        <div className="trainer-modal-backdrop">
          <div className="trainer-modal trainer-modal--wide">
            <div className="trainer-modal-header">
              <h2>Выберите параметры</h2>
              <button type="button" onClick={() => setIsModalOpen(false)}>×</button>
            </div>

            <div className="trainer-form-grid">
              <label>
                <span>Этап / сценарий:</span>
                <select value={selectedScenarioId} onChange={(event) => setSelectedScenarioId(Number(event.target.value))}>
                  <option value="" disabled hidden>Этап не выбран</option>
                  {options.scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>{scenario.title}</option>
                  ))}
                </select>
              </label>

              <label>
                <span>Сложность:</span>
                <select value={selectedDifficulty} onChange={(event) => setSelectedDifficulty(event.target.value)}>
                  <option value="" disabled hidden>Сложность не выбрана</option>
                  {options.difficulties.map((difficulty) => (
                    <option key={difficulty.code} value={difficulty.code}>{difficulty.title}</option>
                  ))}
                </select>
              </label>

              <label>
                <span>Клиент:</span>
                <select value={selectedClientId} onChange={(event) => setSelectedClientId(Number(event.target.value))}>
                  <option value="" disabled hidden>Клиент не выбран</option>
                  {options.clients.map((client) => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </label>

              <label>
                <span>Режим:</span>
                <select value={selectedMode} onChange={(event) => setSelectedMode(event.target.value)}>
                  <option value="practice">Тестовая сессия</option>
                  <option value="exam">Экзамен</option>
                </select>
              </label>
            </div>

            {(selectedScenario || selectedClient || selectedDifficultyInfo) ? (
              <div className="trainer-parameter-cards">
                {selectedScenario ? (
                  <div className="trainer-hint-card">
                    <b>{selectedScenario.title}</b>
                    <p>{selectedScenario.stage_hint || selectedScenario.description}</p>
                    <p><strong>Финальная точка:</strong> {selectedScenario.final_goal}</p>
                    <p><strong>С чего начать:</strong> {buildStartTip(selectedScenario)}</p>
                  </div>
                ) : null}

                {selectedClient ? (
                  <div className="trainer-hint-card">
                    <b>{selectedClient.name}{selectedClient.age ? `, ${selectedClient.age} лет` : ''}</b>
                    <p>{selectedClient.position}</p>
                    <p>{selectedClient.persona}</p>
                    <p><strong>Темперамент:</strong> {selectedClient.temperament}</p>
                    <p><strong>Настрой:</strong> {selectedClient.attitude}</p>
                    <p><strong>История:</strong> {selectedClient.buying_history}</p>
                  </div>
                ) : null}

                {selectedDifficultyInfo ? (
                  <div className="trainer-hint-card">
                    <b>{selectedDifficultyInfo.title}</b>
                    <p>{selectedDifficultyInfo.description}</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="trainer-modal-note">
              Информация о товарах и услугах для продажи будет взята из опубликованных курсов и обработанных документов компании. Отдельно выбирать товар больше не нужно.
            </div>

            <div className="trainer-modal-actions">
              <button type="button" className="trainer-secondary-btn" onClick={() => setIsModalOpen(false)}>Отмена</button>
              <button type="button" className="trainer-primary-btn" onClick={() => void handleCreateSession()} disabled={isCreating || !canStart}>
                {isCreating ? 'Создаю…' : 'Начать диалог'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isBriefOpen && activeSession ? (
        <div className="trainer-modal-backdrop">
          <div className="trainer-modal trainer-modal--brief">
            <div className="trainer-modal-header">
              <h2>Информация о диалоге</h2>
              <button type="button" onClick={() => setIsBriefOpen(false)}>×</button>
            </div>
            <div className="trainer-brief-content">
              <section>
                <b>Финальная цель</b>
                <p>{activeSession.final_goal}</p>
              </section>
              <section>
                <b>С чего стоит начать</b>
                <p>{activeSession.brief_start_tip}</p>
              </section>
              <section>
                <b>Оппонент</b>
                <p>{activeSession.client_name}{activeSession.client_position ? ` — ${activeSession.client_position}` : ''}</p>
              </section>
              <section>
                <b>Материалы для продажи</b>
                <p>Тренажёр использует опубликованные курсы и обработанные документы компании. В диалоге менеджер может назвать конкретный продукт, а виртуальный клиент будет реагировать на него с учётом корпоративных материалов.</p>
              </section>
              <section>
                <b>Инструкция</b>
                <p>Ваша задача — довести диалог до финальной точки. Если цель достигнута, тренажёр завершит диалог автоматически. Завершить вручную можно, но тогда система отметит, что цель не была достигнута автоматически.</p>
              </section>
            </div>
            <div className="trainer-modal-actions">
              <button type="button" className="trainer-primary-btn" onClick={() => setIsBriefOpen(false)}>Перейти к диалогу</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default DialogTrainerPage;
