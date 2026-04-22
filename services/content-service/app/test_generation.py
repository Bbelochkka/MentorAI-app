from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


# ---------------------------
# Public helpers kept stable
# ---------------------------

def parse_desired_question_count(raw: str | None, default: int = 10) -> int:
    if not raw:
        return default
    match = re.search(r"(\d+)", str(raw))
    if not match:
        return default
    return max(1, min(30, int(match.group(1))))


def parse_required_questions(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[\n;]+", raw)
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        cleaned = _normalize_space(re.sub(r"^[-•*\s]+", "", str(part)))
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


# ---------------------------
# Core dataclasses
# ---------------------------

AREAS = {
    "qualification",
    "tariffs",
    "objections",
    "crm",
    "discounts",
    "kpi",
    "next_step",
    "communication",
    "escalation",
    "implementation",
    "general",
}

CARD_TYPES = {
    "rule_action",
    "prohibition",
    "scenario",
    "objection",
    "tariff_selection",
    "crm_rule",
    "numeric_limit",
    "checklist",
    "entity_fact",
    "escalation_rule",
    "next_step",
    "mistake",
}

AREA_TARGETS = {
    "qualification": 0.16,
    "tariffs": 0.16,
    "objections": 0.12,
    "crm": 0.12,
    "discounts": 0.08,
    "next_step": 0.10,
    "communication": 0.08,
    "kpi": 0.06,
    "escalation": 0.06,
    "implementation": 0.03,
    "general": 0.03,
}

ACTION_PREFIXES = (
    "уточнить", "выяснить", "зафиксировать", "назначить", "пригласить", "согласовать",
    "подключить", "провести", "показать", "предложить", "обсудить", "подтвердить",
    "вернуться", "отразить", "конкретизировать", "собрать", "отправить", "проверить",
    "договориться", "передать", "эскалировать", "заполнить", "обновить", "сохранить",
    "не обещать", "не обсуждать", "не завершать", "не спорить", "не переводить", "не отправлять",
)

NUMBER_RE = re.compile(r"\d+[\d\s]*(?:[.,]\d+)?")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
ORDERED_LIST_RE = re.compile(r"^\s*\d+[.)]\s+")
MAJOR_NUMBERED_HEADING_RE = re.compile(r"^\s*\d+[.)]\s+[A-ZА-ЯЁ][^.!?;]{1,100}$")
HEADING_MARK_RE = re.compile(r"^\s*(?:#{1,6}\s+)?(?:[A-ZА-ЯЁ][^\n]{1,120}|\d+[.)]\s+[^\n]{1,120})\s*$")
GENERIC_ACTION_STEM_RE = re.compile(
    r"^что менеджеру (?:следует|нужно|должен) (?:сделать|делать) (?:по правилу|в ситуации):",
    flags=re.I,
)
BANNED_OPTIONS = {
    "все вышеперечисленное",
    "ничего из вышеперечисленного",
    "все перечисленное",
    "ничего из перечисленного",
}

TABLE_HINTS = {
    "tariffs": ["тариф", "пакет", "plan", "start", "growth", "team", "scale", "enterprise"],
    "objections": ["возраж", "сомнен", "ответ", "реакц"],
    "crm": ["crm", "поле", "карточ", "комментар", "этап", "следующ"],
    "discounts": ["скид", "услов", "соглас"],
    "kpi": ["kpi", "sla", "срок", "метрик", "конверс", "дней", "минут"],
    "escalation": ["эскала", "presale", "legal", "head of sales", "руководит", "юрист"],
}

COMMON_ERRORS = {
    "qualification": [
        "Сразу переходить к демонстрации без уточнения критериев выбора.",
        "Ограничиться общими словами клиента и не конкретизировать процесс.",
        "Не выяснять, кто принимает решение и согласует бюджет.",
        "Оставить разговор без следующего шага и даты продолжения.",
    ],
    "tariffs": [
        "Предложить самый дорогой тариф без привязки к задаче клиента.",
        "Выбрать минимальный тариф только потому, что он дешевле.",
        "Опираться на список функций, а не на проблему бизнеса.",
        "Обещать возможности тарифа без проверки требований клиента.",
    ],
    "objections": [
        "Начать спорить с возражением вместо уточнения контекста.",
        "Сразу давать скидку, не подтвердив ценность решения.",
        "Ограничиться общей фразой без следующего шага.",
        "Давить на срочное решение вместо прояснения сомнения.",
    ],
    "crm": [
        "Оставить информацию только в памяти и не обновлять карточку.",
        "Заполнить CRM задним числом, когда детали уже забылись.",
        "Сделать общий комментарий без боли клиента и следующего шага.",
        "Перенести сделку по ощущениям, без подтверждающего факта.",
    ],
    "discounts": [
        "Сразу пообещать скидку устно, чтобы ускорить сделку.",
        "Обсуждать снижение цены до подтверждения ценности и тарифа.",
        "Сказать клиенту, что условия придумаются позже без согласования.",
        "Свести разговор только к цене, не уточняя причину запроса.",
    ],
    "next_step": [
        "Завершить встречу фразой «я пришлю материалы, а вы посмотрите».",
        "Оставить продолжение без даты, времени и ответственного.",
        "Пытаться закрыть сделку, когда клиенту нужен другой следующий шаг.",
        "Не фиксировать в CRM низкую вероятность движения, если клиент не готов.",
    ],
    "communication": [
        "Писать длинно и без одного понятного действия для клиента.",
        "Использовать заученные продающие фразы вместо ясности и пользы.",
        "Обсуждать скидку раньше, чем понятна ценность решения.",
        "Повторно спрашивать то, что уже обсуждали с клиентом.",
    ],
    "kpi": [
        "Оценивать качество только по количеству касаний без движения по воронке.",
        "Считать хорошей работой любую высокую активность без следующего шага.",
        "Игнорировать качество комментариев в CRM при оценке менеджера.",
        "Не смотреть на причины потерь и отсутствие следующего шага.",
    ],
    "escalation": [
        "Пытаться решить нестандартный запрос самостоятельно без нужного подключения.",
        "Обещать нестандартные условия без внутреннего согласования.",
        "Не подключать профильного специалиста при сложной интеграции.",
        "Скрыть сложный кейс от руководителя, чтобы не замедлять цикл.",
    ],
    "implementation": [
        "Обещать мгновенный результат без участия команды клиента.",
        "Не проверять, кто отвечает за внедрение со стороны клиента.",
        "Игнорировать зрелость клиента и готовность к запуску.",
        "Продавливать сделку, даже если клиент объективно не готов.",
    ],
    "general": [
        "Выбрать формально удобный, но не самый полезный для клиента шаг.",
        "Опираться на шаблонную фразу вместо логики процесса.",
        "Не фиксировать договорённости достаточно ясно для коллег.",
        "Принимать решение без понимания контекста клиента.",
    ],

}

TRUST_PAIR_GROUP = "trust_signals"
ENTITY_CLASS_DEFAULTS = {
    "tariff_selection": "tariff",
    "escalation_rule": "role",
}
GENERIC_ENTITY_FALLBACKS = {
    "tariff": ["Start", "Growth", "Team", "Scale", "Enterprise"],
    "role": ["Presale", "Legal", "Head of Sales", "Аккаунт-менеджер", "Технический специалист"],
}
LOW_VALUE_PREFIXES = (
    "мы продаем", "leadflow ai", "novacrm", "продукт объединяет", "основная аудитория", "облачная платформа",
)
CONTEXT_MARKERS = (
    "если", "клиент", "на встрече", "после", "когда", "при", "запрос", "лид", "звон", "crm",
    "скид", "возраж", "этап", "бюджет", "лпр", "демо", "внедрен", "сделк", "карточк",
)
REQUIRED_FIELD_HINTS = (
    "обязатель", "required", "must", "mandatory", "next step date", "next_step_date",
)
REQUIRED_TRUE_VALUES = {"да", "yes", "true", "обязательное", "required", "mandatory", "must", "y"}
CASE_LABEL_RE = re.compile(r"^(?:кейс|case|ситуация)\s*[:№]", flags=re.I)

NONSENSE_DISTRACTOR_PATTERNS = (
    "если менеджеру так удобнее",
    "материалы курса не требуют",
    "это правило относится только к крупным клиентам",
)

REFERENCE_TABLE_HINTS = (
    "приложение", "ручного заполнения", "manual fill", "registration", "profile",
    "нового менеджера", "new manager", "поля для ручного заполнения", "field list",
    "справочник полей", "карточка сотрудника", "анкета",
)

REFERENCE_FIELD_HINTS = {
    "lead source", "team size", "last activity date", "phone number", "email address",
    "total employees", "project members", "customer base", "дата выхода", "имя менеджера",
    "место работы", "семейное положение", "возраст", "должность", "название компании",
    "email", "phone", "decision role", "роль собеседника",
}

NORMATIVE_HINTS = (
    "обяз", "нельзя", "должен", "когда", "если", "срок", "sla", "эскала", "соглас",
    "required", "mandatory", "must", "owner", "responsible", "approve", "approve",
)

@dataclass
class SourceBlock:

    module_title: str
    topic_title: str
    heading: str
    block_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeCard:
    card_id: str
    card_type: str
    area: str
    module_title: str
    topic_title: str
    heading: str
    source_quote: str
    source_snippet: str
    questionability: int
    answer_type: str
    situation: str
    correct_answer: str
    rationale: str = ""
    common_errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestionCandidate:
    card: KnowledgeCard
    question_text: str
    options: list[str]
    correct_option_index: int
    explanation: str = ""
    source: str = "deterministic"


# ---------------------------
# Generic text helpers
# ---------------------------

def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _clean_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("<br/>", "\n").replace("<br>", "\n")
    value = value.replace("\u2063", "")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("—", " — ").replace("–", " — ")
    value = value.replace("", "•")
    value = re.sub(r"\n{3,}", "\n\n", value)
    lines = [_normalize_space(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _normalize_option(text: str) -> str:
    value = _normalize_space(text)
    value = re.sub(r"^[A-DА-Г]\)\s*", "", value)
    value = re.sub(r"^(Вопрос|Ответ|Правильный ответ|Пояснение):\s*", "", value, flags=re.I)
    return value.strip(" ;")


def _fingerprint(*parts: str) -> str:
    joined = "|".join(_normalize_space(p).casefold() for p in parts if p)
    return re.sub(r"[^a-zа-яё0-9]+", "-", joined)[:240].strip("-") or "item"


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zа-яё0-9]+", str(text).casefold()) if len(t) > 2]


def _word_overlap_ratio(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def _contains_number(text: str) -> bool:
    return bool(NUMBER_RE.search(str(text or "")))


def _is_question_like(text: str) -> bool:
    t = _normalize_space(text)
    if not t:
        return False
    return t.endswith("?") or bool(re.match(r"^(как|что|когда|какой|какая|какие|кто|почему|зачем)\b", t, flags=re.I))


def _looks_like_action(text: str) -> bool:
    t = _normalize_space(text).casefold()
    if not t:
        return False
    return any(t.startswith(prefix) for prefix in ACTION_PREFIXES)


def _looks_like_heading(text: str) -> bool:
    t = _normalize_space(text)
    if not t:
        return False
    if len(t) > 120:
        return False
    if t.endswith(":"):
        return True
    if MAJOR_NUMBERED_HEADING_RE.match(t):
        return True
    if t.count(".") <= 1 and not t.endswith((".", "?", "!", ";")) and len(t.split()) <= 10:
        return True
    return False


def _area_from_text(*parts: str) -> str:
    text = " ".join(_normalize_space(p).casefold() for p in parts if p)
    for area, hints in TABLE_HINTS.items():
        if any(h in text for h in hints):
            return area
    if any(x in text for x in ["лпр", "диагност", "квалификац", "первая встреч"]):
        return "qualification"
    if any(x in text for x in ["следующ", "демонстрац", "коммерческ"]):
        return "next_step"
    if any(x in text for x in ["коммуникац", "довер", "письм", "сообщени"]):
        return "communication"
    if any(x in text for x in ["внедрен", "запуск", "пилот"]):
        return "implementation"
    return "general"


def _entity_class_for_card(card: KnowledgeCard | None) -> str:
    if card is None:
        return ""
    explicit = _normalize_space(str(card.metadata.get("entity_class") or ""))
    if explicit:
        return explicit.casefold()
    return ENTITY_CLASS_DEFAULTS.get(card.card_type, "")


def _looks_like_low_value_context(text: str) -> bool:
    t = _normalize_space(text).casefold()
    if not t:
        return True
    return any(t.startswith(prefix) for prefix in LOW_VALUE_PREFIXES)


def _has_context_markers(text: str) -> bool:
    t = _normalize_space(text).casefold()
    return any(marker in t for marker in CONTEXT_MARKERS)


def _card_has_context(card: KnowledgeCard) -> bool:
    if card.answer_type != "action":
        return True
    situation = _normalize_space(card.situation or "")
    if len(situation) < 18:
        return False
    if _looks_like_low_value_context(situation):
        return False
    if situation.casefold() == _normalize_space(card.correct_answer).casefold():
        return False
    return _has_context_markers(situation) or "ситуац" in _normalize_space(card.heading).casefold()


def _pair_group_for_heading(heading: str) -> tuple[str, str] | tuple[None, None]:
    h = _normalize_space(heading).casefold()
    if "усиливает доверие" in h:
        return TRUST_PAIR_GROUP, "positive"
    if "ослабляет доверие" in h:
        return TRUST_PAIR_GROUP, "negative"
    return None, None


def _same_entity_class(card: KnowledgeCard, other: KnowledgeCard) -> bool:
    left = _entity_class_for_card(card)
    right = _entity_class_for_card(other)
    return bool(left and right and left == right)


def _role_like(text: str) -> bool:
    t = _normalize_space(text)
    return bool(t) and len(t.split()) <= 4 and not _looks_like_action(t) and not _contains_number(t)


def _entity_options_consistent(card: KnowledgeCard, options: list[str]) -> bool:
    entity_class = _entity_class_for_card(card)
    if any(_looks_like_reference_field(opt) for opt in options) and card.area not in {"crm", "escalation"}:
        return False
    if not entity_class:
        return all(not _looks_like_action(opt) for opt in options)
    if entity_class == "tariff":
        return all(len(_normalize_space(opt).split()) <= 3 and not _looks_like_action(opt) for opt in options)
    if entity_class == "role":
        return all(_role_like(opt) for opt in options)
    return all(not _looks_like_action(opt) for opt in options)


def _question_has_context(candidate: QuestionCandidate) -> bool:
    q = _normalize_space(candidate.question_text)
    if candidate.card.answer_type != "action":
        return True
    if ":" in q:
        tail = _normalize_space(q.split(":", 1)[1])
        if len(tail) < 12 or _is_question_like(tail) or _looks_like_low_value_context(tail):
            return False
    return _card_has_context(candidate.card)


def _question_category_matches(candidate: QuestionCandidate) -> bool:
    card = candidate.card
    options = candidate.options
    if card.answer_type == "entity":
        return _entity_options_consistent(card, options)
    if card.card_type == "tariff_selection":
        return _entity_options_consistent(card, options)
    return True


def _looks_like_rule_copy(source_quote: str, question_text: str, correct_answer: str) -> bool:
    return _word_overlap_ratio(question_text, source_quote) > 0.62 and _word_overlap_ratio(correct_answer, source_quote) > 0.74


def _dedupe_strings(values: Iterable[str], *, limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _normalize_option(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if limit is not None and len(result) >= limit:
            break
    return result


# ---------------------------
# Source block extraction
# ---------------------------

def _split_lines(text: str) -> list[str]:
    return [line for line in (_clean_text(text).splitlines())]


def _extract_markdown_tables(lines: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    tables: list[dict[str, Any]] = []
    kept_lines: list[str] = []
    i = 0
    while i < len(lines):
        if TABLE_ROW_RE.match(lines[i]):
            table_lines = [lines[i]]
            i += 1
            while i < len(lines) and TABLE_ROW_RE.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 2:
                rows = []
                for raw in table_lines:
                    cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                    rows.append(cells)
                headers = rows[0]
                body = rows[2:] if len(rows) >= 3 and all(re.match(r"^:?-{2,}:?$", c or "") for c in rows[1]) else rows[1:]
                tables.append({"headers": headers, "rows": body, "raw": "\n".join(table_lines)})
            else:
                kept_lines.extend(table_lines)
        else:
            kept_lines.append(lines[i])
            i += 1
    return tables, kept_lines


def _split_into_sections(content: str) -> list[dict[str, str]]:
    lines = _split_lines(content)
    tables, lines = _extract_markdown_tables(lines)
    sections: list[dict[str, str]] = []
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal heading, buffer
        text = _normalize_space("\n".join(buffer))
        if heading or text:
            sections.append({"heading": heading, "text": text})
        heading, buffer = "", []

    for line in lines:
        stripped = _normalize_space(line)
        if not stripped:
            continue
        if _looks_like_heading(stripped) and (not ORDERED_LIST_RE.match(stripped) or MAJOR_NUMBERED_HEADING_RE.match(stripped)):
            flush()
            heading = stripped.strip(":")
        else:
            buffer.append(stripped)
    flush()

    for table in tables:
        sections.append({"heading": "[TABLE]", "text": table["raw"], "table_headers": table["headers"], "table_rows": table["rows"]})
    return [s for s in sections if s.get("heading") or s.get("text")]


def _topic_to_blocks(module_title: str, topic_title: str, content: str) -> list[SourceBlock]:
    content = _clean_text(content)
    if not content:
        return []
    sections = _split_into_sections(content)
    blocks: list[SourceBlock] = []
    for section in sections:
        heading = _normalize_space(section.get("heading") or topic_title)
        text = _normalize_space(section.get("text") or "")
        if section.get("heading") == "[TABLE]":
            blocks.append(SourceBlock(module_title, topic_title, heading, "table", text, {"headers": section.get("table_headers", []), "rows": section.get("table_rows", [])}))
            continue
        bullets = _extract_bullets(text)
        if bullets:
            blocks.append(SourceBlock(module_title, topic_title, heading, "list", "\n".join(bullets), {"bullets": bullets}))
        elif text:
            blocks.append(SourceBlock(module_title, topic_title, heading, "paragraph", text, {}))
    if not blocks:
        blocks.append(SourceBlock(module_title, topic_title, topic_title, "paragraph", content, {}))
    return blocks


def _extract_bullets(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    explicit = [re.sub(r"^[-•*]\s+", "", line).strip() for line in lines if re.match(r"^[-•*]\s+", line)]
    if explicit:
        return explicit
    numbered = [re.sub(r"^\d+[.)]\s+", "", line).strip() for line in lines if ORDERED_LIST_RE.match(line)]
    if len(numbered) >= 2:
        return numbered
    if len(lines) >= 2 and sum(1 for line in lines if line.endswith(";")) >= 2:
        return [line.rstrip(";") for line in lines]
    semi = [part.strip(" ;") for part in re.split(r";\s+", text) if part.strip(" ;")]
    if len(semi) >= 3:
        return semi
    return []


# ---------------------------
# Deterministic extraction
# ---------------------------

def _make_card(
    *,
    card_type: str,
    area: str,
    module_title: str,
    topic_title: str,
    heading: str,
    source_quote: str,
    source_snippet: str,
    questionability: int,
    answer_type: str,
    situation: str,
    correct_answer: str,
    rationale: str = "",
    common_errors: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeCard:
    area = area if area in AREAS else _area_from_text(area, module_title, topic_title, heading, source_quote)
    card_type = card_type if card_type in CARD_TYPES else "entity_fact"
    return KnowledgeCard(
        card_id=_fingerprint(card_type, area, module_title, topic_title, heading, source_quote, correct_answer),
        card_type=card_type,
        area=area,
        module_title=module_title,
        topic_title=topic_title,
        heading=heading or topic_title,
        source_quote=_normalize_space(source_quote),
        source_snippet=_normalize_space(source_snippet or source_quote),
        questionability=max(1, min(5, questionability)),
        answer_type=answer_type,
        situation=_normalize_space(situation),
        correct_answer=_normalize_option(correct_answer),
        rationale=_normalize_space(rationale),
        common_errors=_dedupe_strings(common_errors or []),
        metadata=metadata or {},
    )


def _deterministic_cards_from_table(block: SourceBlock) -> list[KnowledgeCard]:
    headers = [_normalize_option(h) for h in block.metadata.get("headers", [])]
    rows = block.metadata.get("rows", [])
    table_text = " ".join(headers).casefold() + " " + block.text.casefold()
    area = _area_from_text(block.module_title, block.topic_title, block.heading, table_text)
    cards: list[KnowledgeCard] = []
    if not headers or not rows:
        return cards

    if _is_reference_table_context(block.module_title, block.topic_title, block.heading, block.text) and area not in {"crm", "escalation"}:
        return cards

    if area == "tariffs" and not _tariff_headers_look_valid(headers, rows):
        area = "general"

    for row in rows:
        if not row:
            continue
        cells = [_normalize_option(c) for c in row]
        if not any(cells):
            continue
        source_quote = " | ".join(f"{headers[i]}: {cells[i]}" for i in range(min(len(headers), len(cells))) if cells[i])
        if not source_quote:
            continue

        if area == "tariffs":
            entity = cells[0]
            features = "; ".join(c for c in cells[1:] if c)
            if entity and not _looks_like_reference_field(entity):
                cards.append(_make_card(
                    card_type="tariff_selection",
                    area="tariffs",
                    module_title=block.module_title,
                    topic_title=block.topic_title,
                    heading=block.heading,
                    source_quote=source_quote,
                    source_snippet=block.text,
                    questionability=5,
                    answer_type="entity",
                    situation=features or f"У клиента требования, описанные в строке таблицы для {entity}.",
                    correct_answer=entity,
                    rationale="Выбор тарифа должен опираться на признаки и ограничения из строки таблицы.",
                    common_errors=COMMON_ERRORS["tariffs"],
                    metadata={"entity": entity, "features": features, "entity_class": "tariff"},
                ))
            continue

        if area == "objections":
            situation = cells[0] if cells else ""
            action = cells[1] if len(cells) > 1 else ""
            if situation and action and _looks_like_action(action):
                cards.append(_make_card(
                    card_type="objection",
                    area="objections",
                    module_title=block.module_title,
                    topic_title=block.topic_title,
                    heading=block.heading,
                    source_quote=source_quote,
                    source_snippet=block.text,
                    questionability=5,
                    answer_type="action",
                    situation=situation,
                    correct_answer=action,
                    rationale="Нужно выбрать лучшую реакцию менеджера на возражение.",
                    common_errors=COMMON_ERRORS["objections"],
                ))
            continue

        if area == "crm":
            situation = cells[0] if cells else ""
            action = cells[1] if len(cells) > 1 else ""
            if situation and action and _looks_like_action(action):
                cards.append(_make_card(
                    card_type="crm_rule",
                    area="crm",
                    module_title=block.module_title,
                    topic_title=block.topic_title,
                    heading=block.heading,
                    source_quote=source_quote,
                    source_snippet=block.text,
                    questionability=5,
                    answer_type="action",
                    situation=situation,
                    correct_answer=action,
                    rationale="Нужно проверить корректное действие по регламенту CRM.",
                    common_errors=COMMON_ERRORS["crm"],
                ))
                continue
            # explicit required-field rows only
            if _explicit_required_signal(block.heading, block.topic_title, block.module_title, " ".join(headers), source_quote):
                required_idx = next((i for i, h in enumerate(headers) if _explicit_required_signal(h)), None)
                field_idx = 0
                if required_idx is not None and required_idx < len(cells) and _truthy_required_cell(cells[required_idx]):
                    field_name = cells[field_idx]
                    if field_name and _looks_like_reference_field(field_name):
                        cards.append(_make_card(
                            card_type="entity_fact",
                            area="crm",
                            module_title=block.module_title,
                            topic_title=block.topic_title,
                            heading=block.heading,
                            source_quote=source_quote,
                            source_snippet=block.text,
                            questionability=4,
                            answer_type="entity",
                            situation="Какое поле в CRM помечено как обязательное?",
                            correct_answer=field_name,
                            rationale="Нужно знать действительно обязательные поля CRM, а не любые доступные атрибуты.",
                            common_errors=[],
                            metadata={"entity_class": "field", "required": True},
                        ))
                continue
            # if this is just a field glossary / profile row, skip it
            if _looks_like_reference_field(cells[0] if cells else "") or not _is_normative_label(source_quote):
                continue

        if area == "escalation":
            situation = cells[0] if cells else ""
            who = cells[1] if len(cells) > 1 else ""
            if situation and who and not _looks_like_action(who) and not _looks_like_reference_field(who):
                cards.append(_make_card(
                    card_type="escalation_rule",
                    area="escalation",
                    module_title=block.module_title,
                    topic_title=block.topic_title,
                    heading=block.heading,
                    source_quote=source_quote,
                    source_snippet=block.text,
                    questionability=5,
                    answer_type="entity",
                    situation=situation,
                    correct_answer=who,
                    rationale="Нужно выбрать правильного участника эскалации.",
                    common_errors=COMMON_ERRORS["escalation"],
                    metadata={"entity_class": "role"},
                ))
            continue

        if any(_contains_number(c) for c in cells):
            label = cells[0]
            value = next((c for c in cells[1:] if _contains_number(c)), "")
            if label and value and area in {"kpi", "implementation", "discounts"} and (_is_normative_label(label) or _is_normative_label(source_quote)):
                cards.append(_make_card(
                    card_type="numeric_limit",
                    area=area,
                    module_title=block.module_title,
                    topic_title=block.topic_title,
                    heading=block.heading,
                    source_quote=source_quote,
                    source_snippet=block.text,
                    questionability=4,
                    answer_type="numeric",
                    situation=label,
                    correct_answer=value,
                    rationale="Нужно знать числовой норматив или лимит.",
                    common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
                ))
    return cards


def _deterministic_cards_from_list(block: SourceBlock) -> list[KnowledgeCard]:
    bullets = block.metadata.get("bullets", []) or _extract_bullets(block.text)
    area = _area_from_text(block.module_title, block.topic_title, block.heading)
    heading = block.heading.casefold()
    cards: list[KnowledgeCard] = []

    for bullet in bullets:
        quote = _normalize_space(bullet)
        if not quote:
            continue
        answer_type = "numeric" if _contains_number(quote) else ("action" if _looks_like_action(quote) else "statement")
        if heading.startswith('что обязательно усвоить'):
            continue
        if "ошиб" in heading:
            cards.append(_make_card(
                card_type="mistake",
                area=area if area != "general" else "general",
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=quote,
                source_snippet=block.text,
                questionability=4,
                answer_type="statement",
                situation="Какой вариант относится к типичной ошибке новичка?",
                correct_answer=quote,
                rationale="Нужно распознать ошибочное поведение, а не правильный шаг.",
                common_errors=[],
                metadata={"polarity": "negative", "pair_group": "mistakes"},
            ))
            continue
        pair_group, polarity = _pair_group_for_heading(block.heading)
        if pair_group and polarity:
            cards.append(_make_card(
                card_type="entity_fact",
                area="communication",
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=quote,
                source_snippet=block.text,
                questionability=4,
                answer_type="statement",
                situation=f"Какой вариант { 'усиливает' if polarity == 'positive' else 'ослабляет' } доверие клиента?",
                correct_answer=quote,
                rationale="Нужно отличить усиливающий или ослабляющий коммуникацию паттерн.",
                common_errors=[],
                metadata={"pair_group": pair_group, "polarity": polarity},
            ))
            continue
        if area in {"crm", "discounts", "next_step", "qualification"}:
            if answer_type != "action" and not _is_normative_label(quote):
                continue
            if _looks_like_reference_field(quote):
                continue
            if area == "discounts" and not _looks_like_action(quote):
                continue
            cards.append(_make_card(
                card_type="crm_rule" if area == "crm" else ("next_step" if area == "next_step" else "rule_action"),
                area=area,
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=quote,
                source_snippet=block.text,
                questionability=4,
                answer_type="action" if _looks_like_action(quote) else "statement",
                situation=f"Ситуация описана в разделе «{block.heading}»." if _looks_like_action(quote) else block.heading,
                correct_answer=quote,
                rationale="Нужно проверить применение правила или обязательного пункта.",
                common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
            ))
            continue
        if area == "kpi":
            cards.append(_make_card(
                card_type="numeric_limit" if _contains_number(quote) else "entity_fact",
                area="kpi",
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=quote,
                source_snippet=block.text,
                questionability=4,
                answer_type="numeric" if _contains_number(quote) else "statement",
                situation="Какой показатель или ориентир относится к контролю качества воронки?",
                correct_answer=quote,
                rationale="Нужно отличить KPI и управленческие метрики от шума.",
                common_errors=COMMON_ERRORS["kpi"],
            ))
            continue
        cards.append(_make_card(
            card_type="checklist",
            area=area,
            module_title=block.module_title,
            topic_title=block.topic_title,
            heading=block.heading,
            source_quote=quote,
            source_snippet=block.text,
            questionability=3,
            answer_type="statement",
            situation=f"Что относится к разделу «{block.heading}»?",
            correct_answer=quote,
            rationale="Нужно распознать обязательный пункт или корректный ориентир.",
            common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
        ))
    return cards


def _deterministic_cards_from_paragraph(block: SourceBlock) -> list[KnowledgeCard]:
    text = block.text
    area = _area_from_text(block.module_title, block.topic_title, block.heading, text)
    cards: list[KnowledgeCard] = []

    heading_cf = block.heading.casefold()

    # Skip service and illustrative blocks that rarely make good standalone test items
    if re.match(r"^(редакция|как читать этот документ|пример |документ используется|санкт-петербург)", heading_cf):
        return cards

    # Scenario / objection sections
    if re.search(r"^ситуац", heading_cf):
        action = _extract_recommended_action(text)
        if action:
            cards.append(_make_card(
                card_type="scenario",
                area=_area_from_text(block.module_title, block.topic_title, text),
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=text,
                source_snippet=text,
                questionability=5,
                answer_type="action",
                situation=text,
                correct_answer=action,
                rationale="Нужно выбрать корректное действие по описанной рабочей ситуации.",
                common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
            ))
        return cards

    if "возражение" in heading_cf:
        action = _extract_recommended_action(text)
        situation = re.sub(r"^возражение\s*", "", block.heading, flags=re.I).strip(' "«»')
        if action:
            cards.append(_make_card(
                card_type="objection",
                area="objections",
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=text,
                source_snippet=text,
                questionability=5,
                answer_type="action",
                situation=situation or text,
                correct_answer=action,
                rationale="Нужно выбрать лучшую реакцию на возражение клиента.",
                common_errors=COMMON_ERRORS["objections"],
            ))
        return cards

    if any(k in heading_cf for k in ["start", "team", "scale", "growth", "enterprise"]):
        cards.append(_make_card(
            card_type="tariff_selection",
            area="tariffs",
            module_title=block.module_title,
            topic_title=block.topic_title,
            heading=block.heading,
            source_quote=text,
            source_snippet=text,
            questionability=5,
            answer_type="entity",
            situation=text,
            correct_answer=block.heading,
            rationale="Нужно соотнести признаки клиента с подходящим тарифом.",
            common_errors=COMMON_ERRORS["tariffs"],
            metadata={"entity": block.heading, "features": text, "entity_class": "tariff"},
        ))
        return cards

    # Explicit rule sentences
    for sentence in _split_sentences(text):
        normalized = _normalize_space(sentence)
        if len(normalized) < 25:
            continue
        if re.search(r"\b(должен|обязан|нельзя|не должен|недопустимо|обязательно)\b", normalized, flags=re.I):
            action = _extract_recommended_action(normalized) or normalized
            answer_type = "action" if _looks_like_action(action) else "statement"
            card_type = "prohibition" if re.search(r"\b(нельзя|не должен|недопустимо)\b", normalized, flags=re.I) else ("crm_rule" if area == "crm" else "rule_action")
            if card_type in {"rule_action", "crm_rule", "next_step"} and answer_type != "action":
                continue
            cards.append(_make_card(
                card_type=card_type,
                area=area,
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=normalized,
                source_snippet=text,
                questionability=4,
                answer_type=answer_type,
                situation=_infer_situation_from_sentence(normalized, block.heading),
                correct_answer=action,
                rationale="Правильный ответ должен проверять применение правила, а не дословное воспроизведение.",
                common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
            ))
        elif area == "kpi" and _contains_number(normalized):
            cards.append(_make_card(
                card_type="numeric_limit",
                area="kpi",
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=normalized,
                source_snippet=text,
                questionability=4,
                answer_type="numeric",
                situation=block.heading if block.heading else "Какой норматив или метрика указаны в материале?",
                correct_answer=NUMBER_RE.search(normalized).group(0) if NUMBER_RE.search(normalized) else normalized,
                rationale="Числовой вопрос должен опираться на явный норматив или срок.",
                common_errors=COMMON_ERRORS["kpi"],
            ))

    # If nothing extracted, keep only genuinely testable semantic paragraph, not examples or intro text
    if not cards and len(text) > 110 and not _looks_like_product_description(text) and not re.match(r"^(пример|как читать|редакция)", heading_cf):
        summary = _summarize_fact(text)
        if not _looks_like_reference_field(summary) and _is_normative_label(text):
            cards.append(_make_card(
                card_type="entity_fact",
                area=area,
                module_title=block.module_title,
                topic_title=block.topic_title,
                heading=block.heading,
                source_quote=text,
                source_snippet=text,
                questionability=2,
                answer_type="statement",
                situation=block.heading or block.topic_title,
                correct_answer=summary,
                rationale="Фоновый факт, который все же задает правило или критерий.",
                common_errors=COMMON_ERRORS.get(area, COMMON_ERRORS["general"]),
            ))
    return cards


def _extract_recommended_action(text: str) -> str:
    parts = _split_sentences(text)
    for part in parts:
        p = _normalize_space(part)
        if p.lower().startswith(("правильно:", "лучше", "сначала", "менеджер должен", "нужно", "следует")):
            p = re.sub(r"^(правильно|лучше|сначала|менеджер должен|нужно|следует):?\s*", "", p, flags=re.I)
            if _looks_like_action(p):
                return p
        if _looks_like_action(p):
            return p
    # fallback for quoted recommended answer
    quote_match = re.search(r"[«\"]([^\n]+)[»\"]", text)
    if quote_match:
        quoted = _normalize_space(quote_match.group(1))
        if quoted:
            return quoted
    return ""


def _infer_situation_from_sentence(sentence: str, heading: str) -> str:
    s = _normalize_space(sentence)
    low = s.casefold()
    if "каждый новый лид" in low:
        return "В день поступления нового лида менеджер выбирает корректное действие в CRM."
    if "перестал выходить на связь" in low:
        return "Клиент перестал выходить на связь после контакта."
    if "следующий шаг всегда" in low:
        return "После звонка или встречи нужно зафиксировать продолжение работы."
    if "нельзя переносить сделки" in low:
        return "Менеджер хочет перевести сделку на следующий этап в CRM."
    if "клиент просит уменьшить цену" in low or "скидка не используется" in low:
        return "Клиент просит снизить цену до внутреннего согласования условий."
    if re.search(r"\bесли\b", s, flags=re.I):
        return s
    if re.search(r"\b(нельзя|обязательно|должен|обязан|следует)\b", low):
        if heading:
            return f"Нужно выбрать корректное действие по правилу раздела «{heading}»."
    if heading:
        return f"Ситуация относится к разделу «{heading}»."
    return s


def _looks_like_product_description(text: str) -> bool:
    lower = text.casefold()
    return any(x in lower for x in ["платформа", "продукт объединяет", "основная аудитория", "облачная"]) and not any(
        x in lower for x in ["должен", "нельзя", "обязан", "скидк", "возраж", "лпр", "crm", "эскала"]
    )


def _looks_like_reference_field(text: str) -> bool:
    t = _normalize_space(text).casefold().strip('"«»')
    if not t:
        return False
    if t in REFERENCE_FIELD_HINTS:
        return True
    if len(t.split()) <= 4 and not _looks_like_action(t) and not _contains_number(t):
        if any(h in t for h in ["date", "name", "phone", "email", "source", "role", "field", "company", "manager"]):
            return True
        if any(h in t for h in ["дата", "имя", "телефон", "почта", "источник", "роль", "поле", "компания", "менеджер"]):
            return True
    return False


def _is_reference_table_context(*parts: str) -> bool:
    hay = " ".join(_normalize_space(p).casefold() for p in parts if p)
    if not any(h in hay for h in REFERENCE_TABLE_HINTS):
        return False
    # Do not classify genuinely process-heavy tables as mere reference appendices.
    if any(h in hay for h in NORMATIVE_HINTS):
        return False
    if any(h in hay for group in TABLE_HINTS.values() for h in group):
        return False
    return True


def _is_normative_label(text: str) -> bool:
    t = _normalize_space(text).casefold()
    return any(h in t for h in NORMATIVE_HINTS)

def _explicit_required_signal(*parts: str) -> bool:
    hay = " ".join(_normalize_space(p).casefold() for p in parts if p)
    if not hay:
        return False
    return any(h in hay for h in REQUIRED_FIELD_HINTS)


def _truthy_required_cell(value: str) -> bool:
    v = _normalize_space(value).casefold().strip('"«»')
    return v in REQUIRED_TRUE_VALUES


def _looks_like_case_description(text: str) -> bool:
    t = _normalize_space(text)
    low = t.casefold()
    if not t:
        return False
    if CASE_LABEL_RE.search(t):
        return True
    if low.startswith(("клиент ", "на демонстрации ", "на встрече ", "ситуация ")) and not _looks_like_action(t):
        return True
    return False


def _tariff_headers_look_valid(headers: list[str], rows: list[list[str]]) -> bool:
    hay = " ".join(h.casefold() for h in headers)
    if not any(h in hay for h in TABLE_HINTS["tariffs"]):
        return False
    short_first = 0
    for row in rows:
        if not row:
            continue
        first = _normalize_space(row[0])
        if first and len(first.split()) <= 3 and not _looks_like_action(first):
            short_first += 1
    return short_first >= 2


def _summarize_fact(text: str) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return _normalize_space(text)[:160]
    first = _normalize_space(sentences[0])
    return first[:180]


def _split_sentences(text: str) -> list[str]:
    text = _normalize_space(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [_normalize_space(part) for part in parts if _normalize_space(part)]


def _extract_deterministic_cards(modules: list[dict[str, Any]]) -> list[KnowledgeCard]:
    cards: list[KnowledgeCard] = []
    for module in modules:
        module_title = _normalize_space(module.get("title") or "Модуль")
        for topic in module.get("topics") or []:
            topic_title = _normalize_space(topic.get("title") or "Тема")
            content = str(topic.get("content") or "")
            if not _clean_text(content):
                continue
            for block in _topic_to_blocks(module_title, topic_title, content):
                if block.block_type == "table":
                    cards.extend(_deterministic_cards_from_table(block))
                elif block.block_type == "list":
                    cards.extend(_deterministic_cards_from_list(block))
                else:
                    cards.extend(_deterministic_cards_from_paragraph(block))
    return _dedupe_cards(cards)


# ---------------------------
# AI-first extraction and generation
# ---------------------------

def _chunk_text_for_ai(text: str, chunk_size: int = 1400) -> list[str]:
    text = _clean_text(text)
    if len(text) <= chunk_size:
        return [text] if text else []
    sentences = _split_sentences(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _extract_ai_cards(modules: list[dict[str, Any]], provider: Any | None) -> list[KnowledgeCard]:
    if provider is None or not hasattr(provider, "generate_json"):
        return []
    cards: list[KnowledgeCard] = []
    for module in modules:
        module_title = _normalize_space(module.get("title") or "Модуль")
        for topic in module.get("topics") or []:
            topic_title = _normalize_space(topic.get("title") or "Тема")
            content = _clean_text(topic.get("content") or "")
            if len(content) < 120:
                continue
            for chunk in _chunk_text_for_ai(content):
                try:
                    payload = provider.generate_json(_ai_extract_prompt(module_title, topic_title, chunk))
                except Exception:
                    continue
                for item in payload.get("cards") or []:
                    card = _card_from_ai_item(item, module_title, topic_title, chunk)
                    if card:
                        cards.append(card)
    return _dedupe_cards(cards)


def _extract_ai_cards_relaxed(modules: list[dict[str, Any]], provider: Any | None) -> list[KnowledgeCard]:
    if provider is None or not hasattr(provider, "generate_json"):
        return []
    cards: list[KnowledgeCard] = []
    for module in modules:
        module_title = _normalize_space(module.get("title") or "Модуль")
        for topic in module.get("topics") or []:
            topic_title = _normalize_space(topic.get("title") or "Тема")
            content = _clean_text(topic.get("content") or "")
            if len(content) < 80:
                continue
            chunks = _chunk_text_for_ai(content, chunk_size=2200)
            for chunk in chunks[:3]:
                try:
                    payload = provider.generate_json(_ai_relaxed_extract_prompt(module_title, topic_title, chunk))
                except Exception:
                    continue
                for item in payload.get("cards") or []:
                    card = _card_from_ai_item(item, module_title, topic_title, chunk)
                    if card:
                        # Slightly down-rank rescue cards so primary extraction still wins.
                        card.questionability = max(2, min(card.questionability, 4))
                        cards.append(card)
    return _dedupe_cards(cards)


def _ai_extract_prompt(module_title: str, topic_title: str, chunk: str) -> str:
    allowed_types = sorted(CARD_TYPES)
    allowed_areas = sorted(AREAS)
    return f"""
Ты извлекаешь из корпоративного учебного материала НЕ вопросы, а карточки знаний для последующей генерации теста.

Верни строго JSON-объект вида:
{{
  "cards": [
    {{
      "card_type": "...",
      "area": "...",
      "questionability": 1-5,
      "answer_type": "action|entity|statement|numeric",
      "situation": "краткий контекст, который можно подставить в вопрос",
      "correct_answer": "одно лучшее корректное действие / сущность / значение",
      "rationale": "почему это важно",
      "source_quote": "короткая точная цитата из фрагмента",
      "common_errors": ["ошибка 1", "ошибка 2", "ошибка 3"]
    }}
  ]
}}

Правила:
- Извлекай только знания, полезные для онбординга менеджеров по продажам.
- Не дублируй почти одинаковые карточки.
- Если фрагмент только описывает продукт и не задает правило, кейс, тарифную логику, возражение, KPI, CRM-требование, скидку, эскалацию или следующий шаг — лучше верни меньше карточек.
- Не извлекай карточки из справочников полей, профилей, приложений для ручного заполнения и регистрационных форм, если они не проверяют именно процессное правило или обязательность.
- card_type только из: {allowed_types}
- area только из: {allowed_areas}
- Для action-карточек correct_answer должен начинаться с действия.
- Для card_type=mistake извлекай карточку только из разделов, где явно описаны ошибки, red flags или недопустимые действия.
- Не подменяй правильное действие описанием кейса: строка вида "Ситуация: ..." не может быть correct_answer.
- Не помечай поле CRM как обязательное, если во фрагменте нет явного признака обязательности.
- Не делай карточку, если в ней нет одного лучшего ответа.
- Не делай карточку, если вопрос по ней получится просто дословной копией текста.

Модуль: {module_title}
Тема: {topic_title}
Фрагмент:
{chunk}
""".strip()




def _ai_relaxed_extract_prompt(module_title: str, topic_title: str, chunk: str) -> str:
    allowed_types = sorted(CARD_TYPES)
    allowed_areas = sorted(AREAS)
    return f"""
Ты извлекаешь карточки знаний из учебного материала для теста по продажам. Это rescue-режим: лучше вернуть больше пригодных карточек, чем слишком рано отфильтровать всё полезное.

Верни строго JSON-объект вида:
{{
  "cards": [
    {{
      "card_type": "...",
      "area": "...",
      "questionability": 1-5,
      "answer_type": "action|entity|statement|numeric",
      "situation": "контекст ситуации или проверки",
      "correct_answer": "одно лучшее корректное действие / сущность / значение",
      "rationale": "почему это важно",
      "source_quote": "короткая точная цитата",
      "common_errors": ["ошибка 1", "ошибка 2", "ошибка 3"]
    }}
  ]
}}

Приоритетно извлекай карточки из:
- таблиц тарифов, интеграций, ролей, эскалаций, чек-листов, CRM-полей;
- блоков про возражения, следующий шаг, скидки, внедрение, KPI, red flags;
- кейсов и сценариев, где есть явный лучший следующий шаг.

Разрешается извлекать карточки по таблицам и чек-листам, даже если формулировка не выглядит как жёсткое правило, но из неё можно сделать однозначный вопрос на выбор правильного варианта.

Запрещено:
- делать correct_answer самой формулировкой кейса (строка вида "Ситуация: ...");
- делать action-карточку из названия продукта или абстрактного описания продукта;
- помечать поле CRM как обязательное без явного признака required / обязательности;
- возвращать карточку, если у неё нет одного лучшего ответа.

card_type только из: {allowed_types}
area только из: {allowed_areas}

Модуль: {module_title}
Тема: {topic_title}
Фрагмент:
{chunk}
""".strip()

def _card_from_ai_item(item: Any, module_title: str, topic_title: str, source_snippet: str) -> KnowledgeCard | None:
    if not isinstance(item, dict):
        return None
    card_type = _normalize_space(item.get("card_type") or "")
    area = _normalize_space(item.get("area") or "")
    if card_type not in CARD_TYPES:
        return None
    if area not in AREAS:
        area = _area_from_text(area, module_title, topic_title, source_snippet)
    source_quote = _normalize_space(item.get("source_quote") or "")
    correct_answer = _normalize_option(item.get("correct_answer") or "")
    if not source_quote or not correct_answer:
        return None
    answer_type = _normalize_space(item.get("answer_type") or "statement").casefold()
    if answer_type not in {"action", "entity", "statement", "numeric"}:
        answer_type = "statement"
    if answer_type == "action" and not _looks_like_action(correct_answer):
        return None
    if answer_type == "action":
        situation = _normalize_space(item.get("situation") or source_quote)
        if _looks_like_low_value_context(situation) or not _has_context_markers(situation):
            return None
        if _looks_like_case_description(correct_answer) or correct_answer.casefold().startswith(("кейс", "case", "ситуация")):
            return None
    if card_type == "mistake":
        scope_hay = " ".join([module_title, topic_title, source_quote]).casefold()
        if "ошиб" not in scope_hay and "red flag" not in scope_hay and "red_flag" not in scope_hay:
            return None
    q = item.get("questionability")
    try:
        questionability = int(q)
    except Exception:
        questionability = 3
    card = _make_card(
        card_type=card_type,
        area=area,
        module_title=module_title,
        topic_title=topic_title,
        heading=topic_title,
        source_quote=source_quote,
        source_snippet=source_snippet,
        questionability=questionability,
        answer_type=answer_type,
        situation=_normalize_space(item.get("situation") or source_quote),
        correct_answer=correct_answer,
        rationale=_normalize_space(item.get("rationale") or ""),
        common_errors=[_normalize_option(x) for x in (item.get("common_errors") or []) if _normalize_option(x)],
    )
    return card if _card_is_useful(card) else None


def _generate_ai_candidates(card: KnowledgeCard, provider: Any | None) -> list[QuestionCandidate]:
    if provider is None or not hasattr(provider, "generate_json"):
        return []
    try:
        payload = provider.generate_json(_ai_question_prompt(card))
    except Exception:
        return []
    result: list[QuestionCandidate] = []
    for item in payload.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        q = _normalize_space(item.get("question_text") or "")
        options = [_normalize_option(x) for x in (item.get("options") or [])]
        correct_index = item.get("correct_option_index")
        if len(options) != 4 or not isinstance(correct_index, int) or not 0 <= correct_index < 4:
            continue
        candidate = QuestionCandidate(
            card=card,
            question_text=q,
            options=options,
            correct_option_index=correct_index,
            explanation=_normalize_space(item.get("explanation") or ""),
            source="ai",
        )
        if _candidate_is_valid(candidate):
            result.append(candidate)
    return result


def _ai_question_prompt(card: KnowledgeCard) -> str:
    entity_class = _entity_class_for_card(card) or "generic"
    return f"""
Ты создаешь несколько кандидатов тестового вопроса с ОДНИМ правильным ответом.
Верни строго JSON:
{{
  "candidates": [
    {{
      "question_text": "...",
      "options": ["A", "B", "C", "D"],
      "correct_option_index": 0,
      "explanation": "почему это лучший вариант"
    }}
  ]
}}

Правила:
- Сгенерируй 3 кандидата.
- Нельзя дословно копировать source_quote в question_text и correct option.
- Вопрос должен проверять понимание или применение.
- Нельзя делать два частично правильных ответа.
- Нельзя превращать описание продукта, название решения или название поля формы в action-вопрос.
- Правильный ответ не может быть самой формулировкой кейса или начинаться с "Ситуация:" / "Кейс:".
- Не делай вопросы по справочным полям профиля или приложения, если они не проверяют обязательность, роль, срок, эскалацию или процессное правило.
- Не задавай вопрос про обязательное поле CRM, если source_quote не содержит явного признака обязательности.
- Если в source_quote перечислены только правильные пункты, не делай вопрос, где несколько вариантов окажутся верными одновременно.
- Дистракторы должны быть правдоподобными и близкими по классу, но неверными.
- Если card.answer_type=action, все 4 варианта должны быть действиями.
- Если card.answer_type=entity, все 4 варианта должны быть сущностями одного класса ({entity_class}).
- Если card.answer_type=numeric, все 4 варианта должны быть правдоподобными числами / сроками.
- Не используй варианты "все вышеперечисленное" и "ничего из вышеперечисленного".

Card:
- type: {card.card_type}
- area: {card.area}
- situation: {card.situation}
- correct_answer: {card.correct_answer}
- rationale: {card.rationale}
- source_quote: {card.source_quote}
- common_errors: {json.dumps(card.common_errors, ensure_ascii=False)}
""".strip()


def _critic_choose_best(candidates: list[QuestionCandidate], provider: Any | None) -> QuestionCandidate | None:
    if not candidates:
        return None
    valid = [c for c in candidates if _candidate_is_valid(c)]
    if not valid:
        return None
    if provider is None or not hasattr(provider, "generate_json") or len(valid) == 1:
        return max(valid, key=_candidate_score)
    try:
        payload = provider.generate_json(_ai_critic_prompt(valid))
        chosen = int(payload.get("best_index"))
    except Exception:
        chosen = -1
    if 0 <= chosen < len(valid) and _candidate_is_valid(valid[chosen]):
        return valid[chosen]
    return max(valid, key=_candidate_score)


def _ai_critic_prompt(candidates: list[QuestionCandidate]) -> str:
    serializable = []
    for idx, c in enumerate(candidates):
        serializable.append({
            "index": idx,
            "question_text": c.question_text,
            "options": c.options,
            "correct_option_index": c.correct_option_index,
            "card_type": c.card.card_type,
            "area": c.card.area,
            "source_quote": c.card.source_quote,
            "answer_type": c.card.answer_type,
            "entity_class": _entity_class_for_card(c.card),
        })
    return f"""
Ты — строгий критик тестовых вопросов.
Выбери лучший вариант и верни JSON {{"best_index": N, "reason": "..."}}.
Критерии:
- один однозначный правильный ответ;
- вопрос содержит контекст и не пустой;
- правильный ответ не является почти дословной копией source_quote;
- дистракторы правдоподобны и принадлежат тому же классу сущностей, что и правильный ответ;
- нельзя выбирать вопрос, где несколько вариантов истинны одновременно;
- вопрос проверяет применение или понимание, а не поиск строки в тексте;
- нельзя превращать описание продукта в вопрос о действии менеджера.

Кандидаты:
{json.dumps(serializable, ensure_ascii=False)}
""".strip()


# ---------------------------
# Card quality and dedupe
# ---------------------------

def _card_is_useful(card: KnowledgeCard) -> bool:
    if not card.source_quote or not card.correct_answer:
        return False
    if len(card.correct_answer) < 3:
        return False
    if _looks_like_reference_field(card.correct_answer) and card.area not in {"crm", "escalation"}:
        return False
    if _is_reference_table_context(card.module_title, card.topic_title, card.heading, card.source_quote) and card.area not in {"crm", "escalation"}:
        return False
    if card.questionability < 2 and card.card_type == "entity_fact":
        return False
    if card.card_type in {"entity_fact", "checklist"} and card.area == "general":
        return False
    if card.card_type == "checklist" and not (_looks_like_action(card.correct_answer) or _contains_number(card.correct_answer) or _is_normative_label(card.correct_answer)):
        return False
    if _looks_like_product_description(card.source_quote) and card.card_type not in {"tariff_selection", "objection", "scenario"}:
        return False
    if card.card_type == "mistake":
        scope_hay = " ".join([card.module_title, card.topic_title, card.heading, card.source_quote]).casefold()
        if "ошиб" not in scope_hay and "red flag" not in scope_hay and "red_flag" not in scope_hay:
            return False
    if card.area == "crm" and card.answer_type == "entity":
        if not _explicit_required_signal(card.heading, card.topic_title, card.module_title, card.source_quote, card.rationale, card.situation):
            return False
    if card.answer_type == "action":
        if not _looks_like_action(card.correct_answer):
            return False
        if _looks_like_case_description(card.correct_answer):
            return False
        if not _card_has_context(card):
            return False
    if _looks_like_low_value_context(card.situation):
        return False
    if _looks_like_rule_copy(card.source_quote, card.situation or "", card.correct_answer) and card.card_type in {"crm_rule", "rule_action", "next_step"}:
        return False
    if _word_overlap_ratio(card.source_quote, card.correct_answer) > 0.94 and card.card_type in {"crm_rule", "rule_action", "next_step"}:
        return False
    return True


def _dedupe_cards(cards: list[KnowledgeCard]) -> list[KnowledgeCard]:
    result: list[KnowledgeCard] = []
    seen: set[str] = set()
    for card in sorted(cards, key=lambda c: (-c.questionability, c.area, c.card_id)):
        if not _card_is_useful(card):
            continue
        key = _fingerprint(card.card_type, card.area, card.correct_answer, card.situation or card.source_quote)
        if key in seen:
            continue
        seen.add(key)
        result.append(card)
    return result


# ---------------------------
# Deterministic question generation
# ---------------------------

def _build_numeric_options(correct: str, other_values: list[str]) -> list[str]:
    values = [correct]
    values.extend(v for v in other_values if v and v != correct)
    matches = [v for v in values if _contains_number(v)]
    if not matches:
        return _dedupe_strings(values, limit=4)
    base_match = NUMBER_RE.search(correct)
    if base_match:
        raw = base_match.group(0).replace(" ", "").replace(",", ".")
        try:
            num = float(raw)
            extras = []
            for delta in [-2, -1, 1, 2, 5]:
                guess = num + delta
                if guess > 0:
                    suffix = correct.replace(base_match.group(0), "").strip()
                    if guess.is_integer():
                        val = str(int(guess))
                    else:
                        val = str(round(guess, 1)).replace(".", ",")
                    extras.append(f"{val} {suffix}".strip())
            matches.extend(extras)
        except Exception:
            pass
    return _dedupe_strings(matches, limit=4)


def _entity_pool(cards: list[KnowledgeCard], card: KnowledgeCard) -> list[str]:
    values = []
    exclude = card.correct_answer
    entity_class = _entity_class_for_card(card)
    for peer in cards:
        if peer.card_id == card.card_id:
            continue
        if peer.answer_type != "entity":
            continue
        if entity_class and not _same_entity_class(card, peer):
            continue
        if not entity_class and peer.area != card.area:
            continue
        candidate = peer.metadata.get("entity") or peer.correct_answer
        if candidate and candidate.casefold() != exclude.casefold():
            values.append(candidate)
    if entity_class in GENERIC_ENTITY_FALLBACKS:
        values.extend(v for v in GENERIC_ENTITY_FALLBACKS[entity_class] if v.casefold() != exclude.casefold())
    return _dedupe_strings(values)


def _build_distractors(card: KnowledgeCard, all_cards: list[KnowledgeCard]) -> list[str]:
    if card.answer_type == "numeric":
        pool = [c.correct_answer for c in all_cards if c.card_id != card.card_id and c.answer_type == "numeric"]
        options = _build_numeric_options(card.correct_answer, pool)
        return [opt for opt in options if opt.casefold() != card.correct_answer.casefold()][:3]

    pair_group = card.metadata.get("pair_group")
    polarity = card.metadata.get("polarity")
    if pair_group and polarity in {"positive", "negative"}:
        opposite = []
        for peer in all_cards:
            if peer.card_id == card.card_id:
                continue
            if peer.metadata.get("pair_group") != pair_group:
                continue
            if peer.metadata.get("polarity") == polarity:
                continue
            opposite.append(peer.correct_answer)
        if len(opposite) >= 3:
            return _dedupe_strings(opposite, limit=3)

    if card.card_type == "mistake":
        positives = []
        for peer in all_cards:
            if peer.card_id == card.card_id:
                continue
            if peer.area != card.area:
                continue
            if peer.card_type == "mistake":
                continue
            if peer.answer_type in {"action", "statement"} and _word_overlap_ratio(peer.correct_answer, card.correct_answer) < 0.6:
                positives.append(peer.correct_answer)
        positives.extend([
            "Сначала уточнить задачу клиента, а потом предлагать решение.",
            "Фиксировать договоренности в CRM в моменте и понятным языком.",
            "Завершать разговор понятным следующим шагом и датой продолжения.",
        ])
        return _dedupe_strings(positives, limit=3)

    if card.answer_type == "entity":
        distractors = _entity_pool(all_cards, card)
        return _dedupe_strings(distractors, limit=3)

    if card.answer_type == "action":
        distractors = list(card.common_errors or COMMON_ERRORS.get(card.area, COMMON_ERRORS["general"]))
        return _dedupe_strings(distractors, limit=3)

    distractors = list(card.common_errors or COMMON_ERRORS.get(card.area, COMMON_ERRORS["general"]))
    for peer in all_cards:
        if peer.card_id == card.card_id:
            continue
        if pair_group and peer.metadata.get("pair_group") == pair_group and peer.metadata.get("polarity") != polarity:
            distractors.append(peer.correct_answer)
            continue
        if peer.area == card.area and peer.answer_type == "statement" and _word_overlap_ratio(peer.correct_answer, card.correct_answer) < 0.5:
            distractors.append(peer.correct_answer)
    return _dedupe_strings(distractors, limit=3)


def _compact_situation(text: str, max_len: int = 180) -> str:
    t = _normalize_space(text)
    if len(t) <= max_len:
        return t
    first_sentence = _split_sentences(t)[0] if _split_sentences(t) else t
    return first_sentence[:max_len].rstrip(" ,;") + "…"


def _question_templates(card: KnowledgeCard) -> list[str]:
    situation = _compact_situation(card.situation or card.source_quote)
    heading = _normalize_space(card.heading or card.topic_title)
    low_quote = card.source_quote.casefold()
    if card.card_type == "tariff_selection":
        return [
            f"Какой тариф лучше подходит клиенту, если его потребности описаны так: {situation}?",
            f"Какой тариф менеджеру логичнее предложить в кейсе: {situation}?",
        ]
    if card.card_type in {"objection", "scenario"}:
        return [
            f"Как менеджеру лучше поступить в ситуации: {situation}?",
            f"Какое действие будет наиболее корректным, если {situation}?",
        ]
    if card.card_type == "crm_rule":
        if "каждый новый лид" in low_quote:
            return ["Что менеджер должен сделать с новым лидом в день его поступления?"]
        if "перестал выходить на связь" in low_quote:
            return ["Как менеджеру правильно отразить в CRM ситуацию, если клиент перестал выходить на связь?"]
        if "следующий шаг всегда" in low_quote:
            return ["Что менеджер обязан зафиксировать в CRM после разговора или встречи с клиентом?"]
        if "переносить сделки" in low_quote:
            return ["Что должно быть основанием для перевода сделки на следующий этап в CRM?"]
        return [
            f"Какое действие соответствует регламенту CRM в ситуации: {situation}?",
            f"Как менеджеру следует действовать по правилу CRM, если {situation}?",
        ]
    if card.card_type in {"rule_action", "next_step"}:
        if card.area == "discounts":
            return [
                f"Какой первый шаг менеджера наиболее корректен в ситуации: {situation}?",
                f"С чего менеджеру правильнее начать, если {situation}?",
            ]
        return [
            f"Какое действие будет наиболее корректным в ситуации: {situation}?",
            f"Как менеджеру следует действовать, если {situation}?",
        ]
    if card.card_type == "escalation_rule":
        return [
            f"Кого нужно подключить в ситуации: {situation}?",
            f"Какой участник должен быть вовлечен, если {situation}?",
        ]
    if card.card_type == "prohibition":
        return [
            f"Какое действие нарушает правило в ситуации: {situation}?",
            f"Что будет неверным действием, если {situation}?",
        ]
    if card.card_type == "numeric_limit":
        return [
            f"Какой норматив или показатель верно указан для следующего случая: {situation}?",
            f"Какое значение соответствует правилу или метрике: {situation}?",
        ]
    if card.card_type == "mistake":
        return [
            f"Какой вариант относится к типичной ошибке новичка?",
            f"Какое действие скорее всего приведет к типичной ошибке менеджера?",
        ]
    if card.card_type == "checklist":
        return [
            f"Какой пункт действительно относится к обязательным требованиям раздела «{heading}»?",
            f"Какой из вариантов соответствует обязательному правилу из раздела «{heading}»?",
        ]
    return [
        f"Какой из вариантов верно отражает правило или ориентир из раздела «{heading}»?",
    ]


def _deterministic_candidates(card: KnowledgeCard, all_cards: list[KnowledgeCard], rng: random.Random) -> list[QuestionCandidate]:
    distractors = _build_distractors(card, all_cards)
    if len(distractors) < 3:
        return []
    candidates: list[QuestionCandidate] = []
    for template in _question_templates(card):
        options = [card.correct_answer, *distractors[:3]]
        rng.shuffle(options)
        correct_index = options.index(card.correct_answer)
        candidate = QuestionCandidate(
            card=card,
            question_text=template,
            options=options,
            correct_option_index=correct_index,
            explanation=card.rationale,
            source="deterministic",
        )
        if _candidate_is_valid(candidate):
            candidates.append(candidate)
    return candidates


# ---------------------------
# Candidate validation and scoring
# ---------------------------

def _candidate_score(candidate: QuestionCandidate) -> tuple[int, int, int]:
    card = candidate.card
    options = candidate.options
    distinctiveness = len({opt.casefold() for opt in options})
    return (
        card.questionability,
        1 if card.area != "general" else 0,
        distinctiveness,
    )


def _question_option_type_matches(question_text: str, option: str, answer_type: str) -> bool:
    if answer_type == "numeric":
        return _contains_number(option)
    if answer_type == "action":
        return _looks_like_action(option)
    if answer_type == "entity":
        return not _looks_like_action(option) and not option.endswith("?")
    return True


def _is_rule_copy(candidate: QuestionCandidate) -> bool:
    q = candidate.question_text
    correct = candidate.options[candidate.correct_option_index]
    quote = candidate.card.source_quote
    if _looks_like_rule_copy(quote, q, correct):
        return True
    if GENERIC_ACTION_STEM_RE.search(q):
        return True
    return False


def _candidate_is_valid(candidate: QuestionCandidate) -> bool:
    q = _normalize_space(candidate.question_text)
    if not q or len(q) < 18:
        return False
    if not q.endswith("?"):
        return False
    if len(candidate.options) != 4:
        return False
    if not isinstance(candidate.correct_option_index, int) or not 0 <= candidate.correct_option_index < 4:
        return False
    if len({opt.casefold() for opt in candidate.options}) != 4:
        return False
    if any(not opt or opt.casefold() in BANNED_OPTIONS for opt in candidate.options):
        return False
    if any(_is_question_like(opt) for opt in candidate.options):
        return False
    if any(any(pat in opt.casefold() for pat in NONSENSE_DISTRACTOR_PATTERNS) for opt in candidate.options):
        return False
    if any(not _question_option_type_matches(q, opt, candidate.card.answer_type) for opt in candidate.options):
        return False
    if not _question_category_matches(candidate):
        return False
    if candidate.card.answer_type == "action" and not any(x in q.casefold() for x in ["как", "какое действие", "как менеджеру", "что менеджер должен"]):
        return False
    if candidate.card.answer_type == "entity" and any(_looks_like_action(opt) for opt in candidate.options):
        return False
    if not _question_has_context(candidate):
        return False
    if _is_rule_copy(candidate):
        return False
    correct = candidate.options[candidate.correct_option_index]
    for i, opt in enumerate(candidate.options):
        if i == candidate.correct_option_index:
            continue
        if _word_overlap_ratio(opt, correct) > 0.9:
            return False
    if _looks_like_low_value_context(q):
        return False
    if any(_looks_like_reference_field(opt) for opt in candidate.options) and candidate.card.area not in {"crm", "escalation"}:
        return False
    correct = candidate.options[candidate.correct_option_index]
    if _looks_like_case_description(correct) or correct.casefold().startswith(("кейс", "case", "ситуация")):
        return False
    q_low = q.casefold()
    if ("обязатель" in q_low or "required" in q_low) and not _explicit_required_signal(candidate.card.heading, candidate.card.topic_title, candidate.card.module_title, candidate.card.source_quote, candidate.card.rationale, candidate.card.situation):
        return False
    if candidate.card.card_type == "mistake":
        scope_hay = " ".join([candidate.card.module_title, candidate.card.topic_title, candidate.card.heading, candidate.card.source_quote]).casefold()
        if "ошиб" not in scope_hay and "red flag" not in scope_hay and "red_flag" not in scope_hay:
            return False
    return True


# ---------------------------
# Blueprint and selection
# ---------------------------

def _required_score(card: KnowledgeCard, required_questions: list[str]) -> int:
    haystack = " ".join([
        card.area,
        card.card_type,
        card.heading,
        card.topic_title,
        card.module_title,
        card.source_quote,
        card.correct_answer,
    ]).casefold()
    score = 0
    for item in required_questions:
        words = [w for w in _tokenize(item) if len(w) > 2]
        if words and all(w in haystack for w in words):
            score += 1
    return score


def _area_targets(cards: list[KnowledgeCard], question_count: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    available = {card.area for card in cards}
    remaining = question_count
    weighted = [(area, ratio) for area, ratio in AREA_TARGETS.items() if area in available]
    targets: dict[str, int] = {}
    for area, ratio in weighted:
        target = int(round(question_count * ratio))
        if target > 0:
            targets[area] = target
    for area in list(targets):
        available_count = sum(1 for c in cards if c.area == area)
        targets[area] = min(max(1, targets[area]), available_count)
    total = sum(targets.values())
    if total > question_count:
        for area in sorted(targets, key=targets.get, reverse=True):
            while total > question_count and targets[area] > 1:
                targets[area] -= 1
                total -= 1
    if total < question_count:
        ranked_areas = sorted(available, key=lambda a: sum(1 for c in cards if c.area == a), reverse=True)
        idx = 0
        while total < question_count and ranked_areas:
            area = ranked_areas[idx % len(ranked_areas)]
            if targets.get(area, 0) < sum(1 for c in cards if c.area == area):
                targets[area] = targets.get(area, 0) + 1
                total += 1
            idx += 1
            if idx > 1000:
                break
    return targets


def _select_cards(cards: list[KnowledgeCard], question_count: int, required_questions: list[str]) -> list[KnowledgeCard]:
    if not cards:
        return []
    scored = sorted(
        cards,
        key=lambda c: (
            _required_score(c, required_questions),
            c.questionability,
            1 if c.area != "general" else 0,
            1 if c.card_type not in {"entity_fact", "checklist"} else 0,
            1 if c.area in {"tariffs", "objections", "crm", "discounts", "escalation", "next_step", "qualification"} else 0,
        ),
        reverse=True,
    )
    targets = _area_targets(scored, question_count)
    selected: list[KnowledgeCard] = []
    per_area: dict[str, int] = {}
    # first satisfy required matches and area quotas
    for card in scored:
        target = targets.get(card.area, 0)
        if target and per_area.get(card.area, 0) < target:
            selected.append(card)
            per_area[card.area] = per_area.get(card.area, 0) + 1
        if len(selected) >= question_count:
            break
    # then fill with best remaining
    if len(selected) < question_count:
        selected_ids = {c.card_id for c in selected}
        for card in scored:
            if card.card_id in selected_ids:
                continue
            selected.append(card)
            selected_ids.add(card.card_id)
            if len(selected) >= question_count:
                break
    return selected


# ---------------------------
# Assembly
# ---------------------------

def _build_questions_from_cards(
    cards: list[KnowledgeCard],
    all_cards: list[KnowledgeCard],
    provider: Any | None,
    question_count: int,
    rng: random.Random,
    required_questions: list[str] | None = None,
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    selected = _select_cards(cards, question_count, required_questions or [])
    backlog = selected + [c for c in all_cards if c.card_id not in {x.card_id for x in selected}]

    def try_card(card: KnowledgeCard) -> bool:
        deterministic = _deterministic_candidates(card, all_cards, rng)
        ai = _generate_ai_candidates(card, provider)
        best = _critic_choose_best(ai + deterministic, provider)
        if not best:
            return False
        key = best.question_text.casefold()
        if key in seen:
            return False
        seen.add(key)
        questions.append({
            "question_text": best.question_text,
            "options": best.options,
            "correct_option_index": best.correct_option_index,
            "family": card.card_type,
            "topic_title": card.topic_title,
            "module_title": card.module_title,
            "process_area": card.area,
            "source_quote": card.source_quote,
            "explanation": best.explanation,
        })
        return True

    # pass 1: best cards
    for card in backlog:
        if len(questions) >= question_count:
            break
        try_card(card)

    # pass 2: allow second question forms from strong cards if still short
    if len(questions) < question_count:
        strong = [c for c in all_cards if c.questionability >= 4]
        for card in strong:
            if len(questions) >= question_count:
                break
            candidates = sorted(_deterministic_candidates(card, all_cards, rng) + _generate_ai_candidates(card, provider), key=_candidate_score, reverse=True)
            for cand in candidates:
                key = cand.question_text.casefold()
                if key in seen or not _candidate_is_valid(cand):
                    continue
                seen.add(key)
                questions.append({
                    "question_text": cand.question_text,
                    "options": cand.options,
                    "correct_option_index": cand.correct_option_index,
                    "family": card.card_type,
                    "topic_title": card.topic_title,
                    "module_title": card.module_title,
                    "process_area": card.area,
                    "source_quote": card.source_quote,
                    "explanation": cand.explanation,
                })
                break

    return questions[:question_count]


# ---------------------------
# Public API
# ---------------------------

def build_test_draft_from_course(
    *,
    course_title: str,
    modules: list[dict[str, Any]],
    question_count: int,
    required_questions: list[str],
    provider: Any | None = None,
) -> dict[str, Any]:
    rng = random.Random(f"ai-first:{course_title}:{question_count}:{'|'.join(required_questions)}")

    deterministic_cards = _extract_deterministic_cards(modules)
    ai_cards = _extract_ai_cards(modules, provider)
    all_cards = _dedupe_cards([*ai_cards, *deterministic_cards])

    # Rescue mode for diverse table-heavy documents: if strict extraction produced too few cards,
    # run a broader AI pass before we decide the course lacks testable material.
    if len(all_cards) < max(12, question_count * 2):
        rescue_cards = _extract_ai_cards_relaxed(modules, provider)
        all_cards = _dedupe_cards([*all_cards, *rescue_cards])

    if required_questions:
        sorted_cards = sorted(all_cards, key=lambda c: (_required_score(c, required_questions), c.questionability, 1 if c.card_type != 'entity_fact' else 0), reverse=True)
    else:
        sorted_cards = sorted(all_cards, key=lambda c: (c.questionability, 1 if c.card_type != 'entity_fact' else 0, 1 if c.area != 'general' else 0), reverse=True)

    if not sorted_cards:
        raise ValueError("Не удалось извлечь из курса достаточное количество полезных знаний для теста")

    questions = _build_questions_from_cards(sorted_cards, sorted_cards, provider, question_count, rng, required_questions)

    if len(questions) < question_count:
        # second cycle: focus on missing areas and weaker cards
        remaining_cards = [c for c in sorted_cards if c.card_id not in { _fingerprint(q['family'], q['process_area'], q['source_quote']) for q in questions }]
        extra = _build_questions_from_cards(remaining_cards, sorted_cards, provider, question_count - len(questions), rng, required_questions)
        existing = {q["question_text"].casefold() for q in questions}
        for q in extra:
            if q["question_text"].casefold() not in existing:
                questions.append(q)
                existing.add(q["question_text"].casefold())
                if len(questions) >= question_count:
                    break

    if len(questions) < question_count:
        # final rescue: retry with relaxed AI cards if a table-heavy or structurally diverse course was over-pruned.
        rescue_cards = [c for c in _extract_ai_cards_relaxed(modules, provider) if c.card_id not in {x.card_id for x in sorted_cards}]
        if rescue_cards:
            rescue_pool = _dedupe_cards([*sorted_cards, *rescue_cards])
            extra = _build_questions_from_cards(rescue_pool, rescue_pool, provider, question_count - len(questions), rng, required_questions)
            existing = {q["question_text"].casefold() for q in questions}
            for q in extra:
                if q["question_text"].casefold() not in existing:
                    questions.append(q)
                    existing.add(q["question_text"].casefold())
                    if len(questions) >= question_count:
                        break

    minimum = min(question_count, 6)
    if len(questions) < minimum:
        raise ValueError(
            f"Удалось собрать только {len(questions)} качественных вопрос(ов) из {question_count} запрошенных. "
            "Скорее всего, в курсе слишком мало извлекаемых правил/кейсов или модель не вернула достаточно качественные knowledge cards."
        )

    description = (
        f"Тест собран по курсу «{course_title}». "
        f"Генерация использует AI-first пайплайн: сначала из тем извлекаются knowledge cards, затем формируется покрытие теста, "
        f"после чего создаются и критикуются несколько кандидатов вопросов на каждую карточку знаний."
    )
    return {
        "title": f"Тест по курсу «{course_title}»",
        "description": description,
        "questions": questions[:question_count],
    }


def validate_generated_test(data: dict[str, Any], *, expected_count: int) -> dict[str, Any]:
    title = _normalize_option(str(data.get("title") or "Тест"))
    description = _normalize_option(str(data.get("description") or ""))
    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("Генератор не вернул вопросы")

    validated_questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_questions:
        question_text = _normalize_option(str(raw.get("question_text") or ""))
        options = [_normalize_option(str(x)) for x in (raw.get("options") or [])]
        correct_index = raw.get("correct_option_index")
        if not question_text or question_text.casefold() in seen:
            continue
        if len(options) != 4 or len({o.casefold() for o in options}) != 4:
            continue
        if not isinstance(correct_index, int) or not 0 <= correct_index < 4:
            continue
        inferred_answer_type = "numeric" if all(_contains_number(o) for o in options) else ("action" if all(_looks_like_action(o) for o in options) else "statement")
        card = _make_card(
            card_type=_normalize_option(str(raw.get("family") or "entity_fact")).casefold() or "entity_fact",
            area=_normalize_option(str(raw.get("process_area") or "general")).casefold() or "general",
            module_title=_normalize_option(str(raw.get("module_title") or "")),
            topic_title=_normalize_option(str(raw.get("topic_title") or "")),
            heading=_normalize_option(str(raw.get("topic_title") or "")),
            source_quote=_normalize_option(str(raw.get("source_quote") or question_text)),
            source_snippet=_normalize_option(str(raw.get("source_quote") or question_text)),
            questionability=4,
            answer_type=inferred_answer_type,
            situation=question_text,
            correct_answer=options[correct_index],
        )
        candidate = QuestionCandidate(card=card, question_text=question_text, options=options, correct_option_index=correct_index, explanation=_normalize_option(str(raw.get("explanation") or "")))
        if not _candidate_is_valid(candidate):
            continue
        seen.add(question_text.casefold())
        validated_questions.append({
            "question_text": question_text,
            "options": options,
            "correct_option_index": correct_index,
            "family": card.card_type,
            "topic_title": card.topic_title,
            "module_title": card.module_title,
            "process_area": card.area,
            "source_quote": card.source_quote,
            "explanation": candidate.explanation,
        })
        if len(validated_questions) >= expected_count:
            break

    if not validated_questions:
        raise ValueError("После валидации не осталось ни одного корректного вопроса")
    if len(validated_questions) < min(expected_count, 6):
        raise ValueError(
            f"После валидации осталось только {len(validated_questions)} качественных вопрос(ов) из {expected_count} ожидаемых"
        )

    return {
        "title": title or "Тест",
        "description": description,
        "questions": validated_questions[:expected_count],
    }
