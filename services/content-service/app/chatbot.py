from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .config import settings
from .infrastructure import get_postgres_connection
from .security import get_current_user

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


class ChatbotAskRequest(BaseModel):
    query: str


class ChatbotSourceResponse(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int | None = None
    relevance_score: float | None = None


class ChatbotTurnResponse(BaseModel):
    id: int
    query_text: str
    answer_text: str
    created_at: datetime
    sources: list[ChatbotSourceResponse]


class ChatbotSessionSummaryResponse(BaseModel):
    id: int
    created_at: datetime
    last_question: str | None = None


class ChatbotSessionResponse(BaseModel):
    id: int
    created_at: datetime
    last_question: str | None = None
    interactions: list[ChatbotTurnResponse]


_STOP_WORDS = {
    "и", "в", "во", "на", "по", "для", "о", "об", "от", "до", "не", "но", "что", "кто",
    "как", "где", "какой", "какая", "какие", "какое", "это", "этот", "эта", "эти", "есть",
    "ли", "а", "я", "ты", "мы", "вы", "они", "он", "она", "оно", "про", "из", "или",
    "с", "со", "у", "же", "бы", "быть", "его", "ее", "их", "мой", "моя", "мои",
}

_BAD_PHRASES = (
    "по документу можно выделить несколько важных моментов",
    "по загруженным документам можно выделить",
    "сравнение черных и белых дыр в виде таблицы",
    "оглавление",
    "текст:",
    "источник:",
)


def _normalize_token(token: str) -> str:
    token = token.lower().replace("ё", "е")
    for suffix in (
        "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими", "его", "ее", "ие", "ые",
        "ая", "яя", "ой", "ий", "ый", "ое", "ам", "ям", "ах", "ях", "ом", "ем",
        "ов", "ев", "ей", "ия", "ья", "ию", "ью", "а", "я", "ы", "и", "у", "ю", "о", "е", "ь",
    ):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9\-]+", text.lower())
    result: list[str] = []
    for token in tokens:
        if token in _STOP_WORDS:
            continue
        normalized = _normalize_token(token)
        if len(normalized) >= 2 and normalized not in _STOP_WORDS:
            result.append(normalized)
    return result


def _looks_like_gibberish(text: str) -> bool:
    cleaned = text.strip().lower()
    if len(cleaned) < 3:
        return True
    letters = re.findall(r"[а-яa-z]", cleaned, flags=re.IGNORECASE)
    if len(letters) < 3:
        return True
    vowels = re.findall(r"[аеёиоуыэюяaeiouy]", cleaned, flags=re.IGNORECASE)
    if letters and len(vowels) / len(letters) < 0.12:
        return True
    tokens = _tokenize(cleaned)
    if not tokens:
        return True
    long_tokens = [t for t in tokens if len(t) >= 4]
    if not long_tokens:
        return True
    return False


def _score_text(query: str, text: str) -> float:
    query_clean = query.strip().lower()
    text_clean = text.lower()
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    text_joined = f" {' '.join(text_tokens)} "

    score = 0.0
    if query_clean and query_clean in text_clean:
        score += 40.0

    for token in query_tokens:
        if f" {token} " in text_joined:
            score += 7.0
        elif token in text_joined:
            score += 3.0

    if query_clean:
        for pattern in (rf"{re.escape(query_clean)}\s*[—:-]", rf"{re.escape(query_clean)}\s+это"):
            if re.search(pattern, text_clean):
                score += 18.0
                break

    return score


def _split_long_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    if len(compact) <= chunk_size:
        return [compact]

    pieces: list[str] = []
    start = 0
    while start < len(compact):
        end = min(len(compact), start + chunk_size)
        pieces.append(compact[start:end].strip())
        if end >= len(compact):
            break
        start = max(0, end - overlap)
    return pieces


def _split_document_into_passages(raw_text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text) if block.strip()]
    passages: list[str] = []
    for block in blocks:
        if len(block) <= 1400:
            passages.append(block)
        else:
            passages.extend(_split_long_text(block))
    if not passages:
        passages = _split_long_text(raw_text)
    return passages


def _clean_context_text(text: str) -> str:
    text = re.sub(r"\[\[.*?\]\]", "", text)
    text = re.sub(r"\|\s*---.*", "", text)
    text = re.sub(r"(^|\n)\s*Источник\s*:.*?(?=\n|$)", "\n", text, flags=re.IGNORECASE)
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("оглавление"):
            continue
        if line.count("|") >= 2:
            continue
        if re.fullmatch(r"[-—|\s]+", line):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [part.strip() for part in re.split(r"(?<=[\.!?])\s+", compact) if part.strip()]


def _extractive_answer(question: str, context_sections: list[dict[str, Any]]) -> str:
    ranked_sentences: list[tuple[float, str]] = []
    for section in context_sections:
        for sentence in _sentences(_clean_context_text(section["text"])):
            score = _score_text(question, sentence)
            if score > 0 and len(sentence) >= 45:
                ranked_sentences.append((score, sentence))

    ranked_sentences.sort(key=lambda item: item[0], reverse=True)
    unique_sentences: list[str] = []
    for _, sentence in ranked_sentences:
        if sentence not in unique_sentences:
            unique_sentences.append(sentence)
        if len(unique_sentences) >= 5:
            break

    if not unique_sentences:
        return "Я не смог найти в документе достаточно информации, чтобы дать аккуратный ответ на этот вопрос."

    if len(unique_sentences) <= 2:
        return " ".join(unique_sentences)

    split_point = min(2, len(unique_sentences) - 1)
    return " ".join(unique_sentences[:split_point]) + "\n\n" + " ".join(unique_sentences[split_point:])


def _cleanup_answer_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("источник"):
            continue
        if any(phrase in lower for phrase in _BAD_PHRASES):
            continue
        if line.count("|") >= 2:
            continue
        if re.fullmatch(r"[-—|\s]+", line):
            continue
        lines.append(line)

    cleaned = "\n\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\b([А-ЯЁ]{4,}(?:\s+[А-ЯЁ]{3,})+)\b", lambda m: m.group(1).capitalize(), cleaned)
    return cleaned.strip()


def _answer_is_bad(question: str, answer_text: str) -> bool:
    cleaned = _cleanup_answer_text(answer_text)
    lowered = cleaned.lower()
    if not cleaned or len(cleaned) < 120:
        return True
    if any(phrase in lowered for phrase in _BAD_PHRASES):
        return True
    if "|" in cleaned or "---" in cleaned:
        return True
    question_tokens = [t for t in _tokenize(question) if len(t) >= 4]
    if question_tokens and not any(t in _tokenize(cleaned) for t in question_tokens):
        return True
    short_lines = [line for line in cleaned.splitlines() if line.strip() and len(line.strip()) < 35]
    if len(short_lines) >= 3:
        return True
    return False


def _get_gigachat_token() -> str:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": settings.gigachat_auth_key if settings.gigachat_auth_key.startswith("Basic ") else f"Basic {settings.gigachat_auth_key}",
    }
    timeout = httpx.Timeout(connect=20.0, read=60.0, write=60.0, pool=60.0)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(settings.gigachat_oauth_url, headers=headers, data={"scope": settings.gigachat_scope})

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось получить токен GigaChat: status={response.status_code}, body={response.text}",
        )

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="GigaChat не вернул access_token")
    return token


def _call_llm(prompt: str, *, system_prompt: str) -> str:
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        timeout = httpx.Timeout(connect=20.0, read=settings.llm_timeout_seconds, write=60.0, pool=60.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{settings.llm_base_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.15, "num_predict": 1000},
                },
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Ошибка запроса к Ollama: status={response.status_code}, body={response.text}",
            )
        return (response.json().get("response") or "").strip()

    if provider == "gigachat":
        token = _get_gigachat_token()
        timeout = httpx.Timeout(connect=20.0, read=settings.llm_timeout_seconds, write=60.0, pool=60.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{settings.gigachat_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.gigachat_model,
                    "temperature": 0.15,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Ошибка запроса к GigaChat: status={response.status_code}, body={response.text}",
            )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    raise HTTPException(status_code=500, detail=f"Неизвестный LLM_PROVIDER: {settings.llm_provider}")


def _generate_answer_with_llm(question: str, context_sections: list[dict[str, Any]]) -> str:
    rendered_context = "\n\n".join(
        f"[Фрагмент {idx}]\n{_clean_context_text(section['text'])}"
        for idx, section in enumerate(context_sections, start=1)
    )

    system_prompt = (
        "Ты корпоративный ИИ-ассистент MentorAI. "
        "Отвечай только на основе переданного контекста из документов. "
        "Пиши красивым, естественным русским языком, без заголовков, без таблиц, без списков, без капса, "
        "без названия файла в начале ответа, без строки 'Источник'. "
        "Ответ должен состоять из 2-4 связных абзацев обычного текста. "
        "Не переписывай оглавление, не копируй сырой текст кусками. "
        "Если в документах нет точного ответа, честно скажи об этом в 1-2 предложениях."
    )

    prompt = f"""
Вопрос пользователя:
{question}

Контекст из документа:
{rendered_context}

Сформулируй ответ на русском языке в 2-4 абзацах. Объясни по сути и без лишнего мусора.
""".strip()

    answer = _call_llm(prompt, system_prompt=system_prompt)
    answer = _cleanup_answer_text(answer)

    if _answer_is_bad(question, answer):
        rewrite_prompt = f"""
Ниже приведён неудачный черновой ответ. Перепиши его как аккуратный, понятный ответ пользователю.

Вопрос:
{question}

Контекст:
{rendered_context}

Черновик:
{answer}

Требования:
- только обычный текст по абзацам;
- без таблиц, списков, заголовков и капса;
- без строки 'Источник';
- не начинай с названия документа.
""".strip()
        answer = _call_llm(rewrite_prompt, system_prompt=system_prompt)
        answer = _cleanup_answer_text(answer)

    return answer


def _load_processed_documents(company_id: int) -> list[dict[str, Any]]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, raw_text
                FROM documents
                WHERE company_id = %s
                  AND status = 'processed'
                  AND COALESCE(raw_text, '') <> ''
                ORDER BY created_at DESC
                """,
                (company_id,),
            )
            rows = cur.fetchall()

    return [{"id": row[0], "title": row[1], "raw_text": row[2]} for row in rows]


def _build_context(company_id: int, query: str) -> tuple[list[dict[str, Any]], list[ChatbotSourceResponse], float]:
    documents = _load_processed_documents(company_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузи и обработай хотя бы один документ. Бот отвечает только по обработанным файлам.",
        )

    scored_docs = []
    for doc in documents:
        score = _score_text(query, doc["raw_text"] or "")
        scored_docs.append({**doc, "score": score})
    scored_docs.sort(key=lambda item: item["score"], reverse=True)
    best_doc = scored_docs[0]

    passages: list[dict[str, Any]] = []
    for index, passage in enumerate(_split_document_into_passages(best_doc["raw_text"] or ""), start=1):
        passages.append(
            {
                "document_id": best_doc["id"],
                "chunk_id": index,
                "title": best_doc["title"],
                "text": passage,
                "score": _score_text(query, passage),
                "order": index,
            }
        )

    passages.sort(key=lambda item: item["score"], reverse=True)
    top = [item for item in passages if item["score"] > 0][:4]
    if not top:
        top = passages[:3]

    chosen_orders = sorted({item["order"] for item in top})
    expanded_orders = set()
    for order in chosen_orders:
        expanded_orders.update({order - 1, order, order + 1})

    selected = [item for item in passages if item["order"] in expanded_orders and item["order"] > 0]
    selected.sort(key=lambda item: item["order"])

    sources = [
        ChatbotSourceResponse(
            document_id=best_doc["id"],
            document_title=best_doc["title"],
            chunk_id=None,
            relevance_score=round(best_doc["score"], 2),
        )
    ]

    return selected[:6], sources, float(best_doc["score"])


def _ensure_session_owner(session_id: int, user_id: int) -> tuple[int, datetime]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, started_at
                FROM chat_sessions
                WHERE id = %s AND user_id = %s
                """,
                (session_id, user_id),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return row[0], row[1]


def _load_sources_by_turn_ids(turn_ids: list[int]) -> dict[int, list[ChatbotSourceResponse]]:
    if not turn_ids:
        return {}

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT bqs.bot_query_id, bqs.document_id, d.title, bqs.chunk_id, bqs.relevance_score
                FROM bot_query_sources bqs
                JOIN documents d ON d.id = bqs.document_id
                WHERE bqs.bot_query_id = ANY(%s)
                ORDER BY bqs.bot_query_id, bqs.id
                """,
                (turn_ids,),
            )
            rows = cur.fetchall()

    result: dict[int, list[ChatbotSourceResponse]] = {}
    for bot_query_id, document_id, title, chunk_id, relevance_score in rows:
        result.setdefault(bot_query_id, []).append(
            ChatbotSourceResponse(
                document_id=document_id,
                document_title=title,
                chunk_id=chunk_id,
                relevance_score=float(relevance_score) if relevance_score is not None else None,
            )
        )
    return result


@router.get("/sessions", response_model=list[ChatbotSessionSummaryResponse])
def list_chatbot_sessions(current_user: dict = Depends(get_current_user)) -> list[ChatbotSessionSummaryResponse]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    cs.id,
                    cs.started_at,
                    (
                        SELECT bq.query_text
                        FROM bot_queries bq
                        WHERE bq.chat_session_id = cs.id
                        ORDER BY bq.created_at DESC
                        LIMIT 1
                    ) AS last_question
                FROM chat_sessions cs
                WHERE cs.user_id = %s
                ORDER BY COALESCE((
                    SELECT MAX(bq.created_at)
                    FROM bot_queries bq
                    WHERE bq.chat_session_id = cs.id
                ), cs.started_at) DESC
                """,
                (current_user["id"],),
            )
            rows = cur.fetchall()

    return [ChatbotSessionSummaryResponse(id=row[0], created_at=row[1], last_question=row[2]) for row in rows]


@router.post("/sessions", response_model=ChatbotSessionSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_chatbot_session(current_user: dict = Depends(get_current_user)) -> ChatbotSessionSummaryResponse:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions (user_id)
                VALUES (%s)
                RETURNING id, started_at
                """,
                (current_user["id"],),
            )
            row = cur.fetchone()
        conn.commit()

    return ChatbotSessionSummaryResponse(id=row[0], created_at=row[1], last_question=None)


@router.get("/sessions/{session_id}", response_model=ChatbotSessionResponse)
def get_chatbot_session(session_id: int, current_user: dict = Depends(get_current_user)) -> ChatbotSessionResponse:
    session_id, started_at = _ensure_session_owner(session_id, current_user["id"])

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, query_text, answer_text, created_at
                FROM bot_queries
                WHERE chat_session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()

    turn_ids = [row[0] for row in rows]
    sources_by_turn = _load_sources_by_turn_ids(turn_ids)
    interactions = [
        ChatbotTurnResponse(
            id=row[0],
            query_text=row[1],
            answer_text=row[2] or "",
            created_at=row[3],
            sources=sources_by_turn.get(row[0], []),
        )
        for row in rows
    ]

    return ChatbotSessionResponse(
        id=session_id,
        created_at=started_at,
        last_question=interactions[-1].query_text if interactions else None,
        interactions=interactions,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatbotTurnResponse)
def send_message_to_chatbot(
    session_id: int,
    payload: ChatbotAskRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatbotTurnResponse:
    question = payload.query.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    if _looks_like_gibberish(question):
        answer_text = "Я не смог понять вопрос. Попробуй сформулировать его обычными словами, например: кто типичный покупатель, какие тарифы есть или чем отличаются продукты."
        sources: list[ChatbotSourceResponse] = []
        session_id, _ = _ensure_session_owner(session_id, current_user["id"])
    else:
        session_id, _ = _ensure_session_owner(session_id, current_user["id"])
        context_sections, sources, _best_score = _build_context(current_user["company_id"], question)

        answer_text = ""
        try:
            answer_text = _generate_answer_with_llm(question, context_sections)
        except Exception:
            answer_text = ""

        if _answer_is_bad(question, answer_text):
            answer_text = _extractive_answer(question, context_sections)

        answer_text = _cleanup_answer_text(answer_text)
        if _answer_is_bad(question, answer_text):
            answer_text = "Я не смог сформировать аккуратный ответ по этому вопросу на основе документа. Попробуй задать вопрос точнее или сформулировать его по-другому."

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bot_queries (
                    chat_session_id,
                    user_id,
                    company_id,
                    training_session_id,
                    query_text,
                    answer_text
                )
                VALUES (%s, %s, %s, NULL, %s, %s)
                RETURNING id, created_at
                """,
                (session_id, current_user["id"], current_user["company_id"], question, answer_text),
            )
            bot_query_id, created_at = cur.fetchone()

            for source in sources:
                cur.execute(
                    """
                    INSERT INTO bot_query_sources (
                        bot_query_id,
                        document_id,
                        chunk_id,
                        relevance_score
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (bot_query_id, source.document_id, source.chunk_id, source.relevance_score),
                )
        conn.commit()

    return ChatbotTurnResponse(
        id=bot_query_id,
        query_text=question,
        answer_text=answer_text,
        created_at=created_at,
        sources=sources,
    )
