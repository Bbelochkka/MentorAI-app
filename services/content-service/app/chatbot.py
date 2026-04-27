







from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .config import settings
from .infrastructure import get_postgres_connection
from .security import get_current_user

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])
logger = logging.getLogger(__name__)


class ChatbotAskRequest(BaseModel):
    query: str


class ChatbotSourceResponse(BaseModel):
    document_id: int
    # Оставлено для совместимости со старым фронтом. Теперь здесь лежит НЕ документ,
    # а название курса или список курсов, где используется найденный документ.
    document_title: str
    course_titles: list[str] = Field(default_factory=list)
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
    "с", "со", "у", "же", "бы", "быть", "его", "ее", "их", "мой", "моя", "мои", "мне",
    "меня", "тебя", "себя", "там", "тут", "здесь", "тот", "той", "тем", "при", "под",
    "над", "за", "без", "да", "нет", "ну", "же", "бы", "были", "был", "была", "будет",
    "можно", "нужно", "надо", "пожалуйста", "расскажи", "скажи", "объясни",
}

_BAD_PHRASES = (
    "по документу можно выделить несколько важных моментов",
    "по загруженным документам можно выделить",
    "по предоставленному документу",
    "по данному документу",
    "в документе говорится",
    "контекст из документа",
    "сравнение черных и белых дыр в виде таблицы",
    "оглавление",
    "текст:",
    "источник:",
    "фрагмент:",
)

_GIBBERISH_MESSAGE = (
    "Ошибка: я не смог понять вопрос. Похоже, что введён случайный набор символов. "
    "Попробуй сформулировать вопрос обычными словами, например: «какие есть тарифы?», "
    "«кто целевой клиент?» или «как обработать возражение клиента?»."
)

_NOT_FOUND_MESSAGE = (
    "Я не нашёл точного ответа на этот вопрос в материалах курса. "
    "Попробуй уточнить формулировку или спросить про конкретный продукт, тариф, этап продажи, правило CRM или действие менеджера."
)

_RU_VOWELS = "аеёиоуыэюя"
_EN_VOWELS = "aeiouy"
_RU_CONSONANTS = "бвгджзйклмнпрстфхцчшщ"
_EN_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_RANDOM_RU_SEQUENCES = (
    "зщ", "щз", "щв", "щф", "щй", "щц", "щк", "щп", "щг", "щд", "щж", "щч",
    "ъь", "ьы", "ыь", "ыъ", "эъ", "ъэ", "йъ", "ъй",
)


def _normalize_token(token: str) -> str:
    token = token.lower().replace("ё", "е")
    for suffix in (
        "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими", "его", "ее", "ие", "ые",
        "ая", "яя", "ой", "ий", "ый", "ое", "ам", "ям", "ах", "ях", "ом", "ем",
        "ов", "ев", "ей", "ия", "ья", "ию", "ью", "ать", "ять", "ить", "еть",
        "а", "я", "ы", "и", "у", "ю", "о", "е", "ь",
    ):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9\-]+", text.lower())
    result: list[str] = []
    for token in tokens:
        token = token.strip("-")
        if not token or token in _STOP_WORDS:
            continue
        normalized = _normalize_token(token)
        if len(normalized) >= 2 and normalized not in _STOP_WORDS:
            result.append(normalized)
    return result


def _letters_only(text: str) -> str:
    return "".join(re.findall(r"[а-яa-zё]", text.lower(), flags=re.IGNORECASE)).replace("ё", "е")


def _has_too_many_repeated_chars(text: str) -> bool:
    return bool(re.search(r"(.)\1\1", text.lower()))


def _has_long_consonant_chain(text: str) -> bool:
    lowered = text.lower().replace("ё", "е")
    return bool(
        re.search(rf"[{_RU_CONSONANTS}]{{5,}}", lowered)
        or re.search(rf"[{_EN_CONSONANTS}]{{5,}}", lowered)
    )


def _looks_like_random_short_token(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    tokens = _tokenize(cleaned)
    if len(tokens) != 1:
        return False

    letters = _letters_only(tokens[0])
    if len(letters) < 5 or len(letters) > 14:
        return False

    if _has_too_many_repeated_chars(letters) or _has_long_consonant_chain(letters):
        return True

    if any(seq in letters for seq in _RANDOM_RU_SEQUENCES):
        return True

    vowels = re.findall(rf"[{_RU_VOWELS}{_EN_VOWELS}]", letters, flags=re.IGNORECASE)
    vowel_ratio = len(vowels) / max(len(letters), 1)
    if vowel_ratio < 0.18 or vowel_ratio > 0.72:
        return True

    return False


def _looks_like_gibberish(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    if len(cleaned) < 3:
        return True
    if re.fullmatch(r"[\W_]+", cleaned, flags=re.UNICODE):
        return True

    letters = _letters_only(cleaned)
    if len(letters) < 3:
        return True

    vowels = re.findall(rf"[{_RU_VOWELS}{_EN_VOWELS}]", letters, flags=re.IGNORECASE)
    if letters and len(vowels) / len(letters) < 0.12:
        return True

    tokens = _tokenize(cleaned)
    if not tokens:
        return True

    if _looks_like_random_short_token(cleaned):
        return True

    return False


def _extract_query_focus(query: str) -> str:
    """Возвращает смысловой объект вопроса: например, из 'что такое черная дыра' -> 'черная дыра'."""
    focus = re.sub(r"\s+", " ", query.strip().lower().replace("ё", "е"))
    focus = re.sub(
        r"^(?:пожалуйста\s+)?(?:расскажи|скажи|объясни|опиши|напиши|подскажи)\s+(?:мне\s+)?(?:про|о|об|что такое|что значит)?\s*",
        "",
        focus,
        flags=re.IGNORECASE,
    )
    focus = re.sub(r"^(?:что\s+такое|что\s+это|кто\s+такой|кто\s+такая|что\s+значит|дай\s+определение)\s+", "", focus)
    focus = re.sub(r"[?!.]+$", "", focus).strip(" ,;:-")
    words = [word for word in re.findall(r"[a-zа-яё0-9\-]+", focus, flags=re.IGNORECASE) if word not in _STOP_WORDS]
    return " ".join(words[:6]).strip()


def _is_definition_question(query: str) -> bool:
    lowered = query.lower().replace("ё", "е")
    return bool(re.search(r"\b(что\s+такое|что\s+это|что\s+значит|кто\s+такой|кто\s+такая|дай\s+определение|объясни\s+понятие)\b", lowered))


def _score_text(query: str, text: str) -> float:
    query_clean = re.sub(r"\s+", " ", query.strip().lower().replace("ё", "е"))
    text_clean = re.sub(r"\s+", " ", text.lower().replace("ё", "е"))
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    text_token_set = set(text_tokens)
    text_joined = f" {' '.join(text_tokens)} "
    focus = _extract_query_focus(query)
    focus_tokens = _tokenize(focus)

    if not query_tokens:
        return 0.0

    score = 0.0
    if query_clean and query_clean in text_clean:
        score += 45.0

    if focus:
        focus_clean = re.sub(r"\s+", " ", focus.lower().replace("ё", "е"))
        if focus_clean and focus_clean in text_clean:
            score += 65.0
        if focus_tokens and all(token in text_token_set for token in focus_tokens):
            score += 35.0
        if focus_clean and re.search(rf"{re.escape(focus_clean)}\s*(?:—|-|–|:|это|является|представляет собой|называется)", text_clean):
            score += 55.0

    query_bigrams = list(zip(query_tokens, query_tokens[1:]))
    for first, second in query_bigrams:
        if f" {first} {second} " in text_joined:
            score += 12.0

    for token in query_tokens:
        if token in text_token_set:
            score += 9.0
        elif any(token in text_token or text_token in token for text_token in text_token_set if len(token) >= 4):
            score += 3.0

    coverage = len(set(query_tokens) & text_token_set) / max(len(set(query_tokens)), 1)
    score += coverage * 20.0

    if query_clean:
        for pattern in (rf"{re.escape(query_clean)}\s*[—:-]", rf"{re.escape(query_clean)}\s+это"):
            if re.search(pattern, text_clean):
                score += 18.0
                break

    if _looks_like_toc_or_heading_list(text):
        score -= 120.0
    elif _has_enough_explanatory_text(text):
        score += 12.0

    return max(score, 0.0)

def _split_long_text(text: str, chunk_size: int = 1400, overlap: int = 220) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    if len(compact) <= chunk_size:
        return [compact]

    pieces: list[str] = []
    start = 0
    while start < len(compact):
        end = min(len(compact), start + chunk_size)
        piece = compact[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(compact):
            break
        start = max(0, end - overlap)
    return pieces


def _split_document_into_passages(raw_text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text) if block.strip()]
    passages: list[str] = []
    for block in blocks:
        if len(block) <= 1600:
            passages.append(block)
        else:
            passages.extend(_split_long_text(block))
    if not passages:
        passages = _split_long_text(raw_text)
    return passages


def _non_empty_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if re.sub(r"\s+", " ", line).strip()]


def _is_heading_like_line(line: str) -> bool:
    cleaned = re.sub(r"\s+", " ", line.strip())
    if not cleaned:
        return False
    lower = cleaned.lower().replace("ё", "е")
    if len(cleaned) > 120:
        return False
    if re.search(r"(?:\bэто\b|\bявляется\b|представляет собой|называется|означает|—|–)", lower):
        return False
    if cleaned.endswith(('.', '!', '?')):
        return False
    if re.match(r"^(?:\d+(?:\.\d+)*\.?\s+|[-•*]\s+)?[A-ZА-ЯЁ]", cleaned):
        return True
    if ":" in cleaned:
        before, after = cleaned.split(":", 1)
        # Короткая строка вида "Белые дыры:" — заголовок. Строка с длинным пояснением после двоеточия — полезный текст.
        if len(before.split()) <= 6 and len(after.strip()) < 45:
            return True
    return False


def _has_enough_explanatory_text(text: str) -> bool:
    lines = _non_empty_lines(text)
    if not lines:
        return False
    explanatory = 0
    for line in lines:
        lower = line.lower().replace("ё", "е")
        if len(line) >= 70 and (
            line.endswith(('.', '!', '?'))
            or re.search(r"(?:\bэто\b|\bявляется\b|представляет собой|означает|позволяет|используется|нужно|должен|важно)", lower)
            or "—" in line
            or "–" in line
        ):
            explanatory += 1
    return explanatory >= 1


def _looks_like_toc_or_heading_list(text: str) -> bool:
    lines = _non_empty_lines(text)
    if not lines:
        return True

    compact = " ".join(lines).lower().replace("ё", "е")
    first_part = " ".join(lines[:4]).lower().replace("ё", "е")
    if re.search(r"\b(оглавление|содержание)\b", first_part) and len(lines) >= 3:
        return True

    if len(lines) >= 3:
        heading_like = sum(1 for line in lines if _is_heading_like_line(line))
        explanatory = sum(1 for line in lines if _has_enough_explanatory_text(line))
        if heading_like / len(lines) >= 0.6 and explanatory <= 1:
            return True

    punctuation_count = len(re.findall(r"[.!?]", compact))
    if len(lines) >= 4 and punctuation_count <= 1 and not re.search(r"\b(это|является|представляет собой|означает)\b", compact):
        return True

    return False


def _clean_context_text(text: str) -> str:
    text = re.sub(r"\[\[.*?\]\]", "", text)
    text = re.sub(r"(^|\n)\s*Источник\s*:.*?(?=\n|$)", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*\|\s*[-:]+\s*\|\s*$", "", text, flags=re.MULTILINE)
    lines = _non_empty_lines(text)
    cleaned_lines: list[str] = []

    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line).strip()
        lower = line.lower().replace("ё", "е")
        if lower.startswith(("оглавление", "содержание", "текст:", "источник:", "фрагмент:")):
            continue
        if re.fullmatch(r"[-—|\s]+", line):
            continue
        if line.count("|") >= 3:
            continue
        # Убираем одиночные заголовки/пункты оглавления, чтобы они не превращались в ответ.
        if _is_heading_like_line(line) and len(line) <= 100:
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def _sentences(text: str) -> list[str]:
    prepared = re.sub(r"\s+", " ", text.replace("\n", ". ")).strip()
    if not prepared:
        return []
    raw_parts = re.split(r"(?<=[\.!?])\s+", prepared)
    result: list[str] = []
    for part in raw_parts:
        sentence = part.strip(" .;:-")
        if not sentence:
            continue
        if _is_heading_like_line(sentence):
            continue
        if _looks_like_toc_or_heading_list(sentence):
            continue
        result.append(sentence)
    return result


def _sentence_matches_focus(sentence: str, focus: str) -> bool:
    if not focus:
        return True
    sentence_tokens = set(_tokenize(sentence))
    focus_tokens = _tokenize(focus)
    if not focus_tokens:
        return True
    return all(token in sentence_tokens or any(token in st or st in token for st in sentence_tokens if len(token) >= 4) for token in focus_tokens)


def _build_definition_answer(question: str, context_sections: list[dict[str, Any]]) -> str:
    focus = _extract_query_focus(question)
    candidates: list[tuple[float, str]] = []

    for section in context_sections:
        cleaned = _clean_context_text(section["text"])
        for sentence in _sentences(cleaned):
            lower = sentence.lower().replace("ё", "е")
            if not _sentence_matches_focus(sentence, focus):
                continue
            score = _score_text(question, sentence)
            if re.search(r"(?:\bэто\b|\bявляется\b|представляет собой|означает|называется|—|–)", lower):
                score += 40.0
            if len(sentence) < 35:
                score -= 20.0
            if score > 0:
                candidates.append((score, sentence))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates:
        return ""

    main = candidates[0][1].strip()
    if not main.endswith(('.', '!', '?')):
        main += "."

    # Добавляем максимум одно поясняющее предложение, если оно действительно про тот же объект.
    extra = ""
    for _, sentence in candidates[1:]:
        if sentence == candidates[0][1]:
            continue
        if _sentence_matches_focus(sentence, focus) and 45 <= len(sentence) <= 240:
            extra = sentence.strip()
            if not extra.endswith(('.', '!', '?')):
                extra += "."
            break

    if extra:
        return f"{main}\n\n{extra}"
    return main


def _extractive_answer(question: str, context_sections: list[dict[str, Any]]) -> str:
    if _is_definition_question(question):
        definition = _build_definition_answer(question, context_sections)
        if definition:
            return definition

    focus = _extract_query_focus(question)
    ranked_sentences: list[tuple[float, str]] = []
    for section in context_sections:
        for sentence in _sentences(_clean_context_text(section["text"])):
            if not _sentence_matches_focus(sentence, focus) and _is_definition_question(question):
                continue
            score = _score_text(question, sentence)
            if score > 0 and len(sentence) >= 45:
                ranked_sentences.append((score, sentence))

    ranked_sentences.sort(key=lambda item: item[0], reverse=True)
    unique_sentences: list[str] = []
    seen: set[str] = set()
    for _, sentence in ranked_sentences:
        if _looks_like_toc_or_heading_list(sentence):
            continue
        fingerprint = re.sub(r"\W+", "", sentence.lower())[:180]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        if not sentence.endswith(('.', '!', '?')):
            sentence += "."
        unique_sentences.append(sentence)
        if len(unique_sentences) >= 3:
            break

    if not unique_sentences:
        return _NOT_FOUND_MESSAGE

    return "\n\n".join(unique_sentences)

def _cleanup_answer_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("```", "")
    text = re.sub(r"\[/?INST\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith(("источник", "документ:", "файл:", "контекст:")):
            continue
        if any(phrase in lower for phrase in _BAD_PHRASES):
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
    lowered = cleaned.lower().replace("ё", "е")
    if not cleaned or len(cleaned) < 45:
        return True
    if any(phrase in lowered for phrase in _BAD_PHRASES):
        return True
    if "```" in cleaned or "<table" in lowered:
        return True
    if cleaned.count("|") >= 4 or "---" in cleaned:
        return True
    if cleaned.lower().startswith(("вот ответ", "ответ:", "конечно", "фрагмент")):
        return True
    if _looks_like_toc_or_heading_list(cleaned):
        return True

    # Плохой признак: длинная строка почти без пунктуации, похожая на склеенные заголовки.
    punctuation_count = len(re.findall(r"[.!?]", cleaned))
    if len(cleaned) > 120 and punctuation_count == 0:
        return True

    # Для вопроса 'что такое ...' ответ должен хотя бы объяснять объект, а не пересказывать соседние темы.
    if _is_definition_question(question):
        focus = _extract_query_focus(question)
        if focus and not _sentence_matches_focus(cleaned, focus):
            return True
        if not re.search(r"(?:\bэто\b|\bявляется\b|представляет собой|означает|называется|—|–)", lowered):
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


def _call_llm(prompt: str, *, system_prompt: str, max_tokens: int = 900) -> str:
    """Общий вызов LLM через провайдера из LLM_PROVIDER.

    Используется как резервный сценарий для чат-бота, если GigaChat
    недоступен или у него закончилась квота.
    """
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
                    "options": {
                        "temperature": 0.05,
                        "top_p": 0.8,
                        "repeat_penalty": 1.15,
                        "num_predict": max_tokens,
                    },
                },
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Ошибка запроса к Ollama: status={response.status_code}, body={response.text}",
            )
        return (response.json().get("response") or "").strip()

    if provider == "gigachat":
        return _call_gigachat_llm(prompt, system_prompt=system_prompt, max_tokens=max_tokens)

    raise HTTPException(status_code=500, detail=f"Неизвестный LLM_PROVIDER: {settings.llm_provider}")


def _call_gigachat_llm(prompt: str, *, system_prompt: str, max_tokens: int = 900) -> str:
    """Прямой вызов GigaChat для чат-бота.

    Эта функция не смотрит на LLM_PROVIDER. Она нужна, чтобы чат-бот
    всегда обращался именно к GigaChat, даже если тренажёр или генератор
    временно работают через Ollama.
    """
    if not (settings.gigachat_auth_key or "").strip():
        raise HTTPException(
            status_code=502,
            detail=(
                "Для чат-бота не задан GIGACHAT_AUTH_KEY. "
                "Добавь ключ в корневой .env и пересоздай content-service."
            ),
        )

    token = _get_gigachat_token()
    timeout = httpx.Timeout(connect=20.0, read=settings.llm_timeout_seconds, write=60.0, pool=60.0)

    logger.info(
        "Chatbot calls GigaChat: model=%s, prompt_chars=%s",
        settings.gigachat_model,
        len(prompt),
    )

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
                "temperature": 0.05,
                "top_p": 0.8,
                "max_tokens": max_tokens,
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
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GigaChat вернул неожиданный формат ответа: {data}",
        ) from exc


def _call_preferred_chatbot_llm(prompt: str, *, system_prompt: str, max_tokens: int = 900) -> str:
    """Для чат-бота сначала пробуем GigaChat, а при сбое возвращаемся к текущей логике.

    Логика:
    1. Если в .env задан GIGACHAT_AUTH_KEY, пробуем GigaChat независимо от LLM_PROVIDER.
    2. Если GigaChat недоступен, закончились токены, ошибка ключа или таймаут —
       пишем причину в логи и пробуем провайдера из LLM_PROVIDER.
    3. Если LLM_PROVIDER тоже gigachat, повторно его не вызываем: ошибка уйдёт выше,
       а send_message_to_chatbot сделает extractive fallback по найденному контексту.
    """
    gigachat_key = (settings.gigachat_auth_key or "").strip()

    if gigachat_key:
        try:
            return _call_gigachat_llm(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
        except Exception as exc:
            logger.warning(
                "GigaChat недоступен для чат-бота, включаю резервную логику: %s",
                exc,
                exc_info=True,
            )

            if settings.llm_provider.lower() == "gigachat":
                raise

    return _call_llm(prompt, system_prompt=system_prompt, max_tokens=max_tokens)


def _render_context(context_sections: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for idx, section in enumerate(context_sections, start=1):
        course_hint = section.get("course_hint") or "Материалы курса"
        text = _clean_context_text(section["text"])
        if not text:
            continue
        parts.append(f"[Фрагмент {idx}. {course_hint}]\n{text}")
    return "\n\n".join(parts)


def _generate_answer_with_llm(question: str, context_sections: list[dict[str, Any]]) -> str:
    rendered_context = _render_context(context_sections)
    focus = _extract_query_focus(question)
    answer_shape = (
        "Начни с прямого определения в одном предложении, затем дай короткое пояснение. "
        if _is_definition_question(question)
        else "Сначала дай прямой ответ на вопрос, затем кратко поясни детали. "
    )

    system_prompt = (
        "Ты ИИ-ассистент MentorAI для обучения менеджеров. "
        "Отвечай строго на вопрос пользователя и только по переданным материалам курса. "
        "Не используй внешние знания и не придумывай факты, цифры, тарифы, этапы, роли или условия. "
        "Не называй документы, файлы и фрагменты. Не пиши слово 'источник'. "
        "Не пересказывай оглавление, названия разделов и соседние темы. "
        "Если точного ответа нет в материалах курса, прямо скажи, что точной информации в материалах нет. "
        "Стиль: естественный, цельный текст, без канцелярита и без набора тезисов. "
        + answer_shape +
        "Обычно пиши 1-3 коротких абзаца. Список используй только если пользователь явно просит список."
    )

    prompt = f"""
Вопрос пользователя:
{question}

Главный объект вопроса:
{focus or 'не выделен'}

Материалы курса, которые можно использовать для ответа:
{rendered_context}

Сформулируй финальный ответ. Важно:
1. Ответь именно на вопрос пользователя, а не на соседние темы из материалов.
2. Не делай перечень заголовков и не пересказывай содержание курса.
3. Не упоминай документы, файлы, источники и фрагменты.
4. Не копируй большой кусок текста дословно: объясни человеческим языком.
5. Если данных недостаточно, так и напиши.
""".strip()

    answer = _call_preferred_chatbot_llm(prompt, system_prompt=system_prompt, max_tokens=750)
    answer = _cleanup_answer_text(answer)

    if _answer_is_bad(question, answer):
        rewrite_prompt = f"""
Черновик ответа получился некачественным. Перепиши его в цельный ответ обычным текстом.

Вопрос:
{question}

Главный объект вопроса:
{focus or 'не выделен'}

Материалы курса:
{rendered_context}

Черновик:
{answer}

Требования к финальному ответу:
- ответь именно на вопрос;
- не перечисляй заголовки и соседние темы;
- без слов 'документ', 'файл', 'источник', 'фрагмент';
- без таблиц и служебных заголовков;
- 1-3 коротких абзаца;
- если точного ответа нет, честно скажи, что информации в материалах курса недостаточно.
""".strip()
        answer = _call_preferred_chatbot_llm(rewrite_prompt, system_prompt=system_prompt, max_tokens=650)
        answer = _cleanup_answer_text(answer)

    return answer

def _load_processed_documents(company_id: int) -> list[dict[str, Any]]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.id,
                    d.title,
                    d.raw_text,
                    dc.id AS chunk_id,
                    dc.chunk_index,
                    dc.chunk_text
                FROM documents d
                LEFT JOIN document_chunks dc ON dc.document_id = d.id
                WHERE d.company_id = %s
                  AND d.status = 'processed'
                  AND COALESCE(d.raw_text, '') <> ''
                ORDER BY d.created_at DESC, dc.chunk_index ASC NULLS LAST
                """,
                (company_id,),
            )
            rows = cur.fetchall()

    documents_by_id: dict[int, dict[str, Any]] = {}
    for document_id, title, raw_text, chunk_id, chunk_index, chunk_text in rows:
        doc = documents_by_id.setdefault(
            document_id,
            {
                "id": document_id,
                "title": title,
                "raw_text": raw_text or "",
                "chunks": [],
            },
        )
        if chunk_id and chunk_text:
            doc["chunks"].append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index or len(doc["chunks"]) + 1,
                    "text": chunk_text,
                }
            )

    return list(documents_by_id.values())


def _load_course_titles_by_document(company_id: int, document_ids: list[int]) -> dict[int, list[str]]:
    if not document_ids:
        return {}

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT x.document_id, x.title
                FROM (
                    SELECT cdl.document_id, c.title
                    FROM course_document_links cdl
                    JOIN courses c ON c.id = cdl.course_id
                    WHERE c.company_id = %s
                      AND c.status <> 'archived'
                      AND cdl.document_id = ANY(%s)

                    UNION

                    SELECT cv.generated_from_document_id AS document_id, c.title
                    FROM course_versions cv
                    JOIN courses c ON c.id = cv.course_id
                    WHERE c.company_id = %s
                      AND c.status <> 'archived'
                      AND cv.generated_from_document_id = ANY(%s)
                ) x
                WHERE x.document_id IS NOT NULL
                ORDER BY x.document_id, x.title
                """,
                (company_id, document_ids, company_id, document_ids),
            )
            rows = cur.fetchall()

    result: dict[int, list[str]] = defaultdict(list)
    for document_id, title in rows:
        if title and title not in result[document_id]:
            result[document_id].append(title)
    return dict(result)


def _make_course_source(
    document_id: int,
    course_titles: list[str],
    *,
    chunk_id: int | None,
    score: float,
) -> ChatbotSourceResponse | None:
    cleaned_titles = [title.strip() for title in course_titles if title and title.strip()]
    if not cleaned_titles:
        return None
    return ChatbotSourceResponse(
        document_id=document_id,
        document_title=", ".join(cleaned_titles),
        course_titles=cleaned_titles,
        chunk_id=chunk_id,
        relevance_score=round(score, 2),
    )


def _build_context(company_id: int, query: str) -> tuple[list[dict[str, Any]], list[ChatbotSourceResponse], float]:
    documents = _load_processed_documents(company_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="Сначала загрузи и обработай хотя бы один документ. Бот отвечает только по обработанным материалам курса.",
        )

    passages: list[dict[str, Any]] = []
    low_value_passages: list[dict[str, Any]] = []

    for doc in documents:
        source_chunks: list[dict[str, Any]] = []
        if doc["chunks"]:
            source_chunks = [
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"] or index,
                    "text": chunk["text"] or "",
                }
                for index, chunk in enumerate(doc["chunks"], start=1)
            ]
        else:
            source_chunks = [
                {"chunk_id": None, "chunk_index": index, "text": passage}
                for index, passage in enumerate(_split_document_into_passages(doc["raw_text"] or ""), start=1)
            ]

        for chunk in source_chunks:
            raw_text = chunk["text"] or ""
            cleaned = _clean_context_text(raw_text)
            if not cleaned:
                continue

            item = {
                "document_id": doc["id"],
                "document_title": doc["title"],
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "text": cleaned,
                "score": _score_text(query, cleaned),
            }

            if _looks_like_toc_or_heading_list(raw_text) or _looks_like_toc_or_heading_list(cleaned):
                low_value_passages.append(item)
                continue
            passages.append(item)

    if not passages and low_value_passages:
        # Фолбэк только на случай, если документ реально состоит из очень коротких блоков.
        passages = low_value_passages

    if not passages:
        raise HTTPException(status_code=400, detail="Обработанные материалы есть, но в них нет текста для поиска ответа.")

    passages.sort(key=lambda item: item["score"], reverse=True)
    best_score = float(passages[0]["score"])

    meaningful = [item for item in passages if item["score"] > 0]
    if not meaningful:
        if _looks_like_random_short_token(query):
            return [], [], 0.0
        return passages[:4], [], 0.0

    # Берем только самые релевантные смысловые фрагменты. Соседние чанки больше не добавляем автоматически,
    # потому что рядом часто лежит оглавление или другой раздел, который портит ответ.
    selected: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for item in meaningful:
        fingerprint = re.sub(r"\W+", "", item["text"].lower())[:220]
        if fingerprint in seen_texts:
            continue
        seen_texts.add(fingerprint)
        selected.append(item)
        if len(selected) >= 6:
            break

    # Для определения лучше дать модели самый сильный фрагмент первым.
    selected.sort(key=lambda item: item["score"], reverse=True)

    document_ids = list({item["document_id"] for item in selected})
    course_titles_by_doc = _load_course_titles_by_document(company_id, document_ids)

    doc_best: dict[int, dict[str, Any]] = {}
    for item in selected:
        current = doc_best.get(item["document_id"])
        if current is None or item["score"] > current["score"]:
            doc_best[item["document_id"]] = item

    for item in selected:
        titles = course_titles_by_doc.get(item["document_id"], [])
        item["course_titles"] = titles
        item["course_hint"] = ", ".join(titles) if titles else "Материалы курса"

    sources: list[ChatbotSourceResponse] = []
    for document_id, item in sorted(doc_best.items(), key=lambda pair: pair[1]["score"], reverse=True):
        source = _make_course_source(
            document_id,
            course_titles_by_doc.get(document_id, []),
            chunk_id=item.get("chunk_id"),
            score=float(item["score"]),
        )
        if source:
            sources.append(source)

    return selected, sources, best_score

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
                SELECT bq.id AS bot_query_id,
                       bqs.document_id,
                       bqs.chunk_id,
                       bqs.relevance_score,
                       csrc.course_title
                FROM bot_queries bq
                JOIN bot_query_sources bqs ON bqs.bot_query_id = bq.id
                JOIN documents d ON d.id = bqs.document_id
                LEFT JOIN LATERAL (
                    SELECT DISTINCT c.title AS course_title
                    FROM courses c
                    WHERE c.company_id = bq.company_id
                      AND c.status <> 'archived'
                      AND (
                          EXISTS (
                              SELECT 1
                              FROM course_document_links cdl
                              WHERE cdl.course_id = c.id
                                AND cdl.document_id = bqs.document_id
                          )
                          OR EXISTS (
                              SELECT 1
                              FROM course_versions cv
                              WHERE cv.course_id = c.id
                                AND cv.generated_from_document_id = bqs.document_id
                          )
                      )
                ) csrc ON TRUE
                WHERE bq.id = ANY(%s)
                ORDER BY bq.id, bqs.id, csrc.course_title
                """,
                (turn_ids,),
            )
            rows = cur.fetchall()

    grouped: dict[tuple[int, int, int | None, float | None], list[str]] = defaultdict(list)
    for bot_query_id, document_id, chunk_id, relevance_score, course_title in rows:
        key = (
            bot_query_id,
            document_id,
            chunk_id,
            float(relevance_score) if relevance_score is not None else None,
        )
        if course_title and course_title not in grouped[key]:
            grouped[key].append(course_title)

    result: dict[int, list[ChatbotSourceResponse]] = defaultdict(list)
    for (bot_query_id, document_id, chunk_id, relevance_score), course_titles in grouped.items():
        source = _make_course_source(
            document_id,
            course_titles,
            chunk_id=chunk_id,
            score=relevance_score or 0.0,
        )
        if source:
            result[bot_query_id].append(source)

    return dict(result)


@router.get("/llm-check")
def chatbot_llm_check(current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    """Проверка LLM-логики чат-бота.

    Сначала проверяем GigaChat. Если он недоступен, проверяем резервный
    провайдер из LLM_PROVIDER. Так видно, чем реально сейчас отвечает чат-бот.
    """
    prompt = "Ответь одним коротким словом: работает?"
    system_prompt = "Ты тестовый ассистент. Ответь кратко."

    if (settings.gigachat_auth_key or "").strip():
        try:
            answer = _call_gigachat_llm(prompt, system_prompt=system_prompt, max_tokens=60)
            return {
                "primary_provider": "gigachat",
                "used_provider": "gigachat",
                "model": settings.gigachat_model,
                "status": "ok",
                "answer": answer,
            }
        except Exception as exc:
            logger.warning("GigaChat llm-check failed: %s", exc, exc_info=True)
            gigachat_error = str(exc)
    else:
        gigachat_error = "GIGACHAT_AUTH_KEY is empty"

    try:
        answer = _call_llm(prompt, system_prompt=system_prompt, max_tokens=60)
        return {
            "primary_provider": "gigachat",
            "used_provider": settings.llm_provider,
            "model": settings.llm_model if settings.llm_provider.lower() == "ollama" else settings.gigachat_model,
            "status": "fallback_ok",
            "gigachat_error": gigachat_error[:800],
            "answer": answer,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Не работает ни GigaChat, ни резервный LLM_PROVIDER. "
                f"GigaChat: {gigachat_error}. Reserve: {exc}"
            ),
        ) from exc


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

    session_id, _ = _ensure_session_owner(session_id, current_user["id"])
    sources: list[ChatbotSourceResponse] = []

    if _looks_like_gibberish(question):
        answer_text = _GIBBERISH_MESSAGE
    else:
        context_sections, sources, best_score = _build_context(current_user["company_id"], question)

        if best_score <= 0 and _looks_like_random_short_token(question):
            answer_text = _GIBBERISH_MESSAGE
            sources = []
        elif best_score <= 0:
            answer_text = _NOT_FOUND_MESSAGE
            sources = []
        else:
            try:
                answer_text = _generate_answer_with_llm(question, context_sections)
            except Exception as exc:
                logger.warning(
                    "LLM не смогла сформировать ответ чат-бота, использую extractive fallback: %s",
                    exc,
                    exc_info=True,
                )
                answer_text = _extractive_answer(question, context_sections)

            if _answer_is_bad(question, answer_text):
                answer_text = _extractive_answer(question, context_sections)

            answer_text = _cleanup_answer_text(answer_text)
            if _answer_is_bad(question, answer_text):
                answer_text = _NOT_FOUND_MESSAGE
                sources = []

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
