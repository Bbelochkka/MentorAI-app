import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import '../styles/chatbot.css';

type ChatbotSourceDto = {
  document_id: number;
  document_title: string;
  course_titles?: string[];
  chunk_id?: number | null;
  relevance_score?: number | null;
};

type ChatbotTurnDto = {
  id: number;
  query_text: string;
  answer_text: string;
  created_at: string;
  sources: ChatbotSourceDto[];
};

type ChatbotSessionDto = {
  id: number;
  created_at: string;
  last_question: string | null;
  interactions: ChatbotTurnDto[];
};

type ChatbotSessionSummaryDto = {
  id: number;
  created_at: string;
  last_question: string | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

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
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(input, {
    ...init,
    headers,
  });
}

async function getChatbotSessions(): Promise<ChatbotSessionSummaryDto[]> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function createChatbotSession(): Promise<ChatbotSessionSummaryDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions`, { method: 'POST' });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function getChatbotSession(sessionId: number): Promise<ChatbotSessionDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions/${sessionId}`);
  if (!response.ok) throw await parseError(response);
  return response.json();
}

async function sendChatbotMessage(sessionId: number, query: string): Promise<ChatbotTurnDto> {
  const response = await authorizedFetch(`${API_URL}/api/chatbot/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

function buildSources(turn: ChatbotTurnDto): string[] {
  const titles = turn.sources.flatMap((source) => {
    if (source.course_titles && source.course_titles.length > 0) {
      return source.course_titles;
    }
    return source.document_title ? [source.document_title] : [];
  });

  return Array.from(new Set(titles.map((title) => title.trim()).filter(Boolean)));
}

function formatStamp(value: string) {
  return new Date(value).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ChatbotPage() {
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeSession, setActiveSession] = useState<ChatbotSessionDto | null>(null);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  async function bootstrapSession() {
    setIsLoading(true);
    setError(null);

    try {
      const sessions = await getChatbotSessions();
      if (sessions.length === 0) {
        setActiveSessionId(null);
        setActiveSession(null);
        return;
      }

      const latest = sessions[0];
      setActiveSessionId(latest.id);
      const session = await getChatbotSession(latest.id);
      setActiveSession(session);
    } catch (sessionError) {
      setError(sessionError instanceof Error ? sessionError.message : 'Не удалось открыть чат-бот');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void bootstrapSession();
  }, []);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTo({
        top: threadRef.current.scrollHeight,
        behavior: isLoading ? 'auto' : 'smooth',
      });
    }
  }, [activeSession, isSending, isLoading]);

  const interactions = useMemo(() => activeSession?.interactions ?? [], [activeSession]);
  const isEmpty = !isLoading && interactions.length === 0;

  async function handleNewChat() {
    setActiveSessionId(null);
    setActiveSession(null);
    setQuery('');
    setError(null);
  }

  async function ensureSession(): Promise<number> {
    if (activeSessionId) return activeSessionId;
    const created = await createChatbotSession();
    setActiveSessionId(created.id);
    setActiveSession({
      id: created.id,
      created_at: created.created_at,
      last_question: null,
      interactions: [],
    });
    return created.id;
  }

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const normalized = query.trim();
    if (!normalized || isSending) return;

    setIsSending(true);
    setError(null);

    try {
      const sessionId = await ensureSession();
      const turn = await sendChatbotMessage(sessionId, normalized);
      setQuery('');

      setActiveSession((prev) => {
        if (!prev || prev.id !== sessionId) {
          return {
            id: sessionId,
            created_at: new Date().toISOString(),
            last_question: normalized,
            interactions: [turn],
          };
        }

        return {
          ...prev,
          last_question: normalized,
          interactions: [...prev.interactions, turn],
        };
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Не удалось получить ответ');
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <section className="chatgpt-page">
      <div className="chatgpt-shell">
        <div className="chatgpt-topbar">
          <div>
            <h1 className="chatgpt-title">Чат-бот</h1>
            <p className="chatgpt-subtitle">Задавай вопросы по материалам уже созданных курсов.</p>
          </div>
          <button type="button" className="chatgpt-reset" onClick={() => void handleNewChat()}>
            Новый чат
          </button>
        </div>

        {error ? <div className="feedback-banner feedback-banner--error">{error}</div> : null}

        <div className={`chatgpt-board ${isEmpty ? 'chatgpt-board--empty' : ''}`}>
          <div className="chatgpt-thread" ref={threadRef}>
            {isLoading ? <div className="chatgpt-status">Открываю чат…</div> : null}

            {isEmpty ? (
              <div className="chatgpt-empty-state">
                <h2>Какой вопрос тебя интересует?</h2>
                <p>
                  Например: кто типичный покупатель, сколько стоит продукт, какие есть тарифы, как проходит продажа и какие боли клиента закрывает продукт.
                </p>
              </div>
            ) : null}

            {interactions.map((turn) => {
              const sourceTitles = buildSources(turn);
              return (
                <div key={turn.id} className="chatgpt-turn">
                  <div className="chatgpt-turn__user">
                    <div className="chatgpt-user-bubble">{turn.query_text}</div>
                    <div className="chatgpt-turn__stamp">{formatStamp(turn.created_at)}</div>
                  </div>

                  <div className="chatgpt-turn__assistant">
                    <div className="chatgpt-avatar">AI</div>
                    <div className="chatgpt-assistant-card">
                      <div className="chatgpt-answer">
                        {turn.answer_text.split('\n').map((line, index) => (
                          <p key={`${turn.id}-${index}`}>{line}</p>
                        ))}
                      </div>

                      {sourceTitles.length > 0 ? (
                        <div className="chatgpt-sources">
                          <span className="chatgpt-sources__label">{sourceTitles.length === 1 ? 'Курс:' : 'Курсы:'}</span>
                          <div className="chatgpt-source-list">
                            {sourceTitles.map((title) => (
                              <span key={title} className="chatgpt-source-pill">{title}</span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}

            {isSending ? (
              <div className="chatgpt-turn">
                <div className="chatgpt-turn__assistant">
                  <div className="chatgpt-avatar">AI</div>
                  <div className="chatgpt-assistant-card chatgpt-assistant-card--loading">
                    Ищу ответ по материалам курса…
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <form className="chatgpt-composer" onSubmit={(event) => void handleSubmit(event)}>
            <div className="chatgpt-composer__inner">
              <textarea
                className="chatgpt-composer__input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Напиши вопрос по материалам курса"
                rows={1}
              />
              <button type="submit" className="chatgpt-composer__send" disabled={isSending || !query.trim()}>
                ↑
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

export default ChatbotPage;
