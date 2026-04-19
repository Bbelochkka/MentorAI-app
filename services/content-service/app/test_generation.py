from __future__ import annotations

import random
import re
from collections import defaultdict
from typing import Any, Iterable

BANNED_OPTIONS = {"все вышеперечисленное", "ничего из вышеперечисленного"}
STOPWORDS = {
    "модуль", "тема", "курс", "для", "про", "это", "как", "что", "при", "или", "если",
    "нужно", "нужен", "нужна", "нужны", "только", "также", "этот", "этого", "эта", "эти",
}
SERVICE_LINE_PATTERNS = (
    r"^кому:\s*",
    r"^от:\s*",
    r"^тема:\s*",
    r"^ответ:\s*",
    r"^подсказка:\s*",
    r"^назначение$",
    r"^что проверяет$",
    r"^внутренний пакет",
    r"^внутренний документ",
    r"^актуально для",
    r"^версия документа",
    r"^содержание$",
    r"^колонка\s*\d+",
)
RULE_KEYWORDS = (
    "обязательно", "нельзя", "не позднее", "не менее", "не ниже", "только", "должен", "должны",
    "запрещено", "требуется", "следующий шаг", "фикси", "соглас", "эскал", "пилот", "скидк",
    "kpi", "sla", "crm", "лпр", "внедр", "договор", "оплата", "срок", "ответить клиенту",
)
HEADER_NOISE = {"да / нет", "комментарий менеджера", "что это", "что важно озвучить клиенту"}
PRIORITY = {
    "time_rule": 120,
    "action_rule": 118,
    "restriction_rule": 116,
    "approval_rule": 114,
    "escalation_rule": 112,
    "faq_fact": 108,
    "table_action": 104,
    "table_role": 102,
    "table_price": 100,
    "table_fit": 96,
    "table_definition": 94,
    "table_lookup": 70,
}
LOW_VALUE_TYPES = {"table_lookup"}
MAX_LOOKUP_SHARE = 0.25


def parse_desired_question_count(raw: str | None, default: int = 10) -> int:
    if not raw:
        return default
    match = re.search(r"(\d+)", raw)
    if not match:
        return default
    value = int(match.group(1))
    return max(1, min(30, value))



def parse_required_questions(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[\n;]+", raw)
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        cleaned = re.sub(r"^[-•\s]+", "", part).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result



def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", (text or "").casefold()) if t not in STOPWORDS]



def _is_service_line(text: str) -> bool:
    stripped = (text or "").strip().casefold()
    if not stripped:
        return True
    return any(re.search(pattern, stripped) for pattern in SERVICE_LINE_PATTERNS)



def _clean_cell_value(text: str) -> str:
    value = text or ""
    value = value.replace("<br/>", " / ").replace("<br>", " / ")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip(" ;")
    return value



def _normalize_option(text: str) -> str:
    value = _clean_cell_value(text)
    return re.sub(r"\s+", " ", value).strip(" ;")



def _strip_markdown(text: str) -> str:
    value = text or ""
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"^#{1,6}\s*", "", value, flags=re.M)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("<br/>", "; ").replace("<br>", "; ")

    lines = []
    for raw_line in value.splitlines():
        stripped = raw_line.strip()
        if not stripped or _is_service_line(stripped):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        stripped = re.sub(r"^[-*+□☐]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        stripped = re.sub(r"^(Ответ|Подсказка|Вопрос|Q|A):\s*", "", stripped, flags=re.I)
        if stripped and not _is_service_line(stripped):
            lines.append(stripped)
    plain = " ".join(lines)
    return re.sub(r"\s+", " ", plain).strip()



def _split_sentences(text: str) -> list[str]:
    plain = _strip_markdown(text)
    parts = re.split(r"(?<=[.!?])\s+", plain)
    result = []
    for part in parts:
        s = part.strip(" ;")
        if len(s) < 18:
            continue
        if _is_service_line(s):
            continue
        result.append(s)
    return result



def _parse_markdown_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not (line.startswith("|") and line.endswith("|")):
            i += 1
            continue
        if i + 1 >= len(lines):
            i += 1
            continue
        sep = lines[i + 1].strip()
        if not (sep.startswith("|") and sep.endswith("|")):
            i += 1
            continue
        sep_cells = [cell.strip() for cell in sep.strip("|").split("|")]
        if not sep_cells or not all(re.fullmatch(r"[:\- ]+", cell or "") for cell in sep_cells):
            i += 1
            continue
        headers = [_clean_cell_value(cell) for cell in line.strip("|").split("|")]
        rows: list[list[str]] = []
        j = i + 2
        while j < len(lines):
            candidate = lines[j].strip()
            if not (candidate.startswith("|") and candidate.endswith("|")):
                break
            cells = [_clean_cell_value(cell) for cell in candidate.strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(cells)
            j += 1
        if rows and all(not _is_service_line(h) for h in headers):
            tables.append({"headers": headers, "rows": rows})
            i = j
        else:
            i += 1
    return tables



def _parse_faq_pairs(text: str) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(("Q:", "Вопрос:", "В:")):
            question = re.sub(r"^(Q:|Вопрос:|В:)\s*", "", line).strip()
            if _is_service_line(question):
                i += 1
                continue
            answer_parts = []
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if candidate.startswith(("Q:", "Вопрос:", "В:")):
                    break
                candidate = re.sub(r"^(A:|Ответ:|О:)\s*", "", candidate).strip()
                if candidate and not _is_service_line(candidate):
                    answer_parts.append(candidate)
                j += 1
            answer = _strip_markdown(" ".join(answer_parts))
            if question and answer and not _is_service_line(answer):
                pairs.append({"question": question.rstrip("?"), "answer": answer})
            i = j
        else:
            i += 1
    return pairs



def _is_good_answer_value(value: str) -> bool:
    value = _normalize_option(value)
    if not value or len(value) < 2:
        return False
    if len(value) > 180:
        return False
    if value.casefold() in BANNED_OPTIONS:
        return False
    if _is_service_line(value):
        return False
    if re.match(r"^(Q|A|Вопрос|Ответ|Подсказка):", value, flags=re.I):
        return False
    return True



def _distinct(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        norm = _normalize_option(value)
        key = norm.casefold()
        if not _is_good_answer_value(norm) or key in seen:
            continue
        seen.add(key)
        result.append(norm)
    return result



def _same_type_synthetic_distractors(answer: str) -> list[str]:
    value = _normalize_option(answer)
    result: list[str] = []
    money = re.search(r"(\d[\d\s]*)\s*₽", value)
    if money:
        digits = int(re.sub(r"\s+", "", money.group(1)))
        suffix = value[value.find("₽"):]
        for delta in (0.85, 1.15, 1.35):
            variant = f"{int(digits * delta):,}".replace(",", " ") + f" {suffix}".strip()
            if variant != value:
                result.append(variant)
    percent = re.search(r"(\d+)\s*%", value)
    if percent:
        digits = int(percent.group(1))
        for delta in (-5, 5, 10):
            v = max(1, digits + delta)
            result.append(f"{v}%")
    duration = re.search(r"от\s*(\d+)\s*до\s*(\d+)\s*(рабочих|календарных)?\s*дн", value.casefold())
    if duration:
        start, end = int(duration.group(1)), int(duration.group(2))
        unit = duration.group(3) or "календарных"
        result.extend([
            f"от {max(1, start - 3)} до {max(start, end - 3)} {unit} дней",
            f"от {start + 3} до {end + 7} {unit} дней",
            f"до {end + 14} {unit} дней",
        ])
    time = re.fullmatch(r"до\s*\d{1,2}:\d{2}", value.casefold())
    if time:
        m = re.search(r"(\d{1,2}):(\d{2})", value)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            result.extend([f"До {max(0, hh - 2):02d}:{mm:02d}", f"До {min(23, hh + 2):02d}:{mm:02d}", "До конца рабочего дня"])
    number = re.fullmatch(r"\d+", value)
    if number:
        n = int(value)
        result.extend([str(max(1, n - 2)), str(n + 2), str(n + 5)])
    return _distinct(result)



def _balanced_options(correct: str, distractor_pool: list[str], rng: random.Random) -> tuple[list[str], int] | None:
    correct_norm = _normalize_option(correct)
    if not _is_good_answer_value(correct_norm):
        return None
    distractors = [d for d in _distinct(distractor_pool) if d.casefold() != correct_norm.casefold()]
    if len(distractors) < 3:
        distractors.extend(_same_type_synthetic_distractors(correct_norm))
        distractors = [d for d in _distinct(distractors) if d.casefold() != correct_norm.casefold()]
    if len(distractors) < 3:
        return None
    distractors.sort(key=lambda item: (abs(len(item) - len(correct_norm)), item))
    selected = distractors[:3]
    options = selected + [correct_norm]
    rng.shuffle(options)
    return options, options.index(correct_norm)



def _make_candidate(question_text: str, correct: str, distractors: list[str], *, unit_type: str, topic_title: str, module_title: str, fingerprint: str, match_text: str, rng: random.Random) -> dict[str, Any] | None:
    question_text = re.sub(r"\s+", " ", question_text).strip()
    if not question_text or question_text.casefold().startswith("какое утверждение соответствует"):
        return None
    options_pack = _balanced_options(correct, distractors, rng)
    if not options_pack:
        return None
    options, correct_index = options_pack
    candidate = {
        "question_text": question_text,
        "options": options,
        "correct_option_index": correct_index,
        "score": PRIORITY.get(unit_type, 50),
        "match_text": match_text,
        "fingerprint": fingerprint,
        "topic_title": topic_title,
        "module_title": module_title,
        "unit_type": unit_type,
    }
    return candidate if _candidate_quality(candidate) else None



def _header_semantic(header: str) -> str:
    text = header.casefold().strip()
    if text in HEADER_NOISE:
        return "noise"
    if "определен" in text:
        return "definition"
    if "цена" in text or "стоим" in text:
        return "price"
    if text == "тип" or "тип" in text:
        return "role"
    if "кому" in text and "подходит" in text:
        return "fit"
    if "подходит" in text:
        return "fit"
    if "кому эскалировать" in text:
        return "escalate_to"
    if text == "когда":
        return "when"
    if "как действовать" in text or "рекомендуемый ответ" in text:
        return "action"
    if "что включено" in text or "функц" in text:
        return "features"
    if "пример" in text:
        return "example"
    if "комментар" in text:
        return "comment"
    return "generic"



def _table_candidates(module_title: str, topic_title: str, content: str, rng: random.Random) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for table in _parse_markdown_tables(content):
        headers = table["headers"]
        rows = table["rows"]
        if len(headers) < 2 or not rows:
            continue
        entity_header = headers[0].casefold()
        columns: dict[int, list[str]] = defaultdict(list)
        for row in rows:
            for idx in range(1, min(len(row), len(headers))):
                columns[idx].append(row[idx])

        for row in rows:
            entity = _normalize_option(row[0])
            if not entity or _is_service_line(entity):
                continue
            for idx in range(1, min(len(row), len(headers))):
                attribute = headers[idx]
                semantic = _header_semantic(attribute)
                if semantic in {"noise", "comment", "features", "example", "generic"}:
                    continue
                answer = row[idx]
                if not _is_good_answer_value(answer):
                    continue

                if "тариф" in entity_header and semantic == "price":
                    q = f"Сколько стоит тариф «{entity}»?"
                    unit_type = "table_price"
                elif ("тариф" in entity_header or "для кого подходит" in headers[idx].casefold()) and semantic == "fit":
                    q = f"Для какого сегмента подходит тариф «{entity}»?"
                    unit_type = "table_fit"
                elif ("поле" in entity_header or "crm-пол" in topic_title.casefold()) and semantic == "role":
                    q = f"Какой тип данных используется для поля «{entity}»?"
                    unit_type = "table_role"
                elif ("термин" in entity_header or "глоссар" in topic_title.casefold()) and semantic == "definition":
                    q = f"Что означает термин «{entity}»?"
                    unit_type = "table_definition"
                elif semantic == "escalate_to":
                    q = f"К кому следует эскалировать вопрос о «{entity}»?"
                    unit_type = "escalation_rule"
                elif semantic == "action" and ("ситуац" in entity_header or "возраж" in entity_header):
                    if entity_header.startswith("возраж"):
                        q = f"Какой ответ соответствует возражению «{entity}»?"
                    else:
                        q = f"Как следует действовать в ситуации: «{entity}»?"
                    unit_type = "table_action"
                elif semantic == "when" and "тип вопроса" in entity_header:
                    q = f"В каком случае нужно эскалировать вопрос о «{entity}»?"
                    unit_type = "table_action"
                else:
                    # very low-value lookup kept only as fallback for stable courses
                    if semantic != "role":
                        continue
                    q = f"Какой тип значения установлен для «{entity}»?"
                    unit_type = "table_lookup"

                candidate = _make_candidate(
                    q,
                    answer,
                    columns[idx],
                    unit_type=unit_type,
                    topic_title=topic_title,
                    module_title=module_title,
                    fingerprint=f"table::{topic_title}::{entity}::{attribute}",
                    match_text=f"{module_title} {topic_title} {entity} {attribute} {answer}",
                    rng=rng,
                )
                if candidate:
                    candidates.append(candidate)
    return candidates



def _faq_question_stem(question: str) -> str | None:
    q = question.strip().rstrip("?")
    lowered = q.casefold()
    if _is_service_line(q) or lowered in {"что проверяет", "назначение"}:
        return None
    if lowered.startswith("сколько") or lowered.startswith("можно ли") or lowered.startswith("где") or lowered.startswith("когда") or lowered.startswith("есть ли"):
        return q + "?"
    if "внедрение" in lowered:
        return q + "?"
    return None



def _faq_candidates(module_title: str, topic_title: str, content: str, rng: random.Random) -> list[dict[str, Any]]:
    pairs = _parse_faq_pairs(content)
    if not pairs:
        return []
    answer_pool = [pair["answer"] for pair in pairs]
    candidates = []
    for pair in pairs:
        q = _faq_question_stem(pair["question"])
        if not q:
            continue
        candidate = _make_candidate(
            q,
            pair["answer"],
            answer_pool,
            unit_type="faq_fact",
            topic_title=topic_title,
            module_title=module_title,
            fingerprint=f"faq::{topic_title}::{pair['question']}",
            match_text=f"{module_title} {topic_title} {pair['question']} {pair['answer']}",
            rng=rng,
        )
        if candidate:
            candidates.append(candidate)
    return candidates



def _extract_rule_units(module_title: str, topic_title: str, content: str) -> list[dict[str, str]]:
    text = _strip_markdown(content)
    sentences = _split_sentences(text)
    units: list[dict[str, str]] = []
    for sentence in sentences:
        lowered = sentence.casefold()
        if not any(keyword in lowered for keyword in RULE_KEYWORDS) and not re.search(r"\d", lowered):
            continue
        if re.search(r"\b(northpeak|leadflow ai \u2022|внутренний учебный материал|новые менеджеры по продажам)\b", lowered):
            continue
        units.append({
            "module_title": module_title,
            "topic_title": topic_title,
            "fact": sentence,
            "match_text": f"{module_title} {topic_title} {sentence}",
        })
    return units



def _mutate_statement(correct: str) -> list[str]:
    text = correct
    variants: list[str] = []
    for pattern, repls in [
        (r"не позднее\s+(\d{1,2}:\d{2})", lambda m: [f"не позднее {max(0, int(m.group(1).split(':')[0]) - 2):02d}:{m.group(1).split(':')[1]}", f"не позднее {min(23, int(m.group(1).split(':')[0]) + 2):02d}:{m.group(1).split(':')[1]}"]),
        (r"не менее\s+(\d+)", lambda m: [f"не менее {int(m.group(1)) + 2}", f"не менее {max(1, int(m.group(1)) - 2)}"]),
        (r"(\d+)\s*календарных\s+дней", lambda m: [f"{int(m.group(1)) + 7} календарных дней", f"{max(1, int(m.group(1)) - 7)} календарных дней"]),
        (r"(\d+)\s*рабочих\s+дней", lambda m: [f"{int(m.group(1)) + 5} рабочих дней", f"{max(1, int(m.group(1)) - 5)} рабочих дней"]),
        (r"(\d+)\s*%", lambda m: [f"{int(m.group(1)) + 5}%", f"{max(1, int(m.group(1)) - 5)}%"]),
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            for repl in repls(match):
                variants.append(re.sub(pattern, repl, text, count=1, flags=re.I))
    swaps = [("нельзя", "можно"), ("обязательно", "необязательно"), ("только", "в том числе"), ("после", "до")]
    for left, right in swaps:
        if left in text.casefold():
            variants.append(re.sub(left, right, text, count=1, flags=re.I))
    return _distinct(variants)



def _rule_candidate(fact: dict[str, str], action_pool: list[str], restriction_pool: list[str], rng: random.Random) -> dict[str, Any] | None:
    sentence = fact["fact"].strip()
    lowered = sentence.casefold()
    topic_title = fact["topic_title"]
    module_title = fact["module_title"]

    # Time rules at line start.
    m = re.match(r"^(До\s*\d{1,2}:\d{2})\s+(.+)$", sentence, flags=re.I)
    if m:
        deadline, action = m.group(1), m.group(2).rstrip(".")
        q = f"До какого времени менеджер должен {action[0].lower() + action[1:]}?"
        return _make_candidate(q, deadline, _same_type_synthetic_distractors(deadline), unit_type="time_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"time::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^(Не позднее[^—–-]*?)\s+(.+)$", sentence, flags=re.I)
    if m:
        deadline, action = m.group(1).rstrip(" ,.;"), m.group(2).rstrip(".")
        q = f"В какой срок менеджер должен {action[0].lower() + action[1:]}?"
        return _make_candidate(q, deadline, _same_type_synthetic_distractors(deadline), unit_type="time_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"time::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^После каждого\s+([^,.]+?)\s+(.+)$", sentence, flags=re.I)
    if m:
        trigger, action = m.group(1).strip(), m.group(2).rstrip(".")
        q = f"Что менеджер должен сделать после каждого {trigger}?"
        return _make_candidate(q, action, action_pool, unit_type="action_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"action::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^Если клиент\s+(.+?),\s*(?:менеджер\s+)?(.+)$", sentence, flags=re.I)
    if m:
        condition, action = m.group(1).strip(), m.group(2).rstrip(".")
        q = f"Как следует действовать, если клиент {condition}?"
        return _make_candidate(q, action, action_pool, unit_type="action_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"action::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.search(r"(\d+)\s*календарных\s+дней", sentence, flags=re.I)
    if m and ("пилот" in lowered or "без активности" in lowered):
        number = m.group(0)
        if "пилот" in lowered:
            q = "Какова максимальная длительность пилотного периода?"
        else:
            q = "Через какой срок без активности сделки попадают в отчёт «требуют внимания»?"
        return _make_candidate(q, number, _same_type_synthetic_distractors(number), unit_type="time_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"time::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.search(r"(\d+)\s*рабочих\s+дней", sentence, flags=re.I)
    if m and ("следующего шага" in lowered or "без активности" in lowered or "ответ" in lowered):
        number = m.group(0)
        if "следующего шага" in lowered:
            q = "Через какой срок без следующего шага сделка считается рискованной?"
        else:
            q = "Какой срок указан в регламенте?"
        return _make_candidate(q, number, _same_type_synthetic_distractors(number), unit_type="time_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"time::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^(Нельзя\s+.+)$", sentence, flags=re.I)
    if m:
        q = "Что запрещено делать менеджеру согласно регламенту?"
        return _make_candidate(q, m.group(1).rstrip("."), restriction_pool + _mutate_statement(sentence), unit_type="restriction_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"restrict::{topic_title}::{sentence[:50]}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^(Запрещено\s+.+)$", sentence, flags=re.I)
    if m:
        q = "Какое ограничение прямо установлено регламентом?"
        return _make_candidate(q, m.group(1).rstrip("."), restriction_pool + _mutate_statement(sentence), unit_type="restriction_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"restrict::{topic_title}::{sentence[:50]}", match_text=fact["match_text"], rng=rng)

    m = re.match(r"^Менеджер отвечает клиенту.*?(не позднее\s+\d+\s+час[ао]в?).*$", sentence, flags=re.I)
    if m:
        q = "В какой срок менеджер должен ответить клиенту в рабочее время?"
        return _make_candidate(q, m.group(1), _same_type_synthetic_distractors(m.group(1)), unit_type="time_rule", topic_title=topic_title, module_title=module_title, fingerprint=f"time::{topic_title}::{q}", match_text=fact["match_text"], rng=rng)

    return None



def _policy_candidates(modules: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    facts = []
    for module in modules:
        for topic in module.get("topics", []):
            facts.extend(_extract_rule_units(module["title"], topic["title"], topic.get("content", "")))
    action_pool = []
    restriction_pool = []
    for fact in facts:
        s = fact["fact"]
        low = s.casefold()
        if low.startswith("нельзя") or low.startswith("запрещено"):
            restriction_pool.append(s)
        if re.match(r"^(После каждого|Если клиент)", s, flags=re.I):
            action_pool.append(re.sub(r"^(После каждого\s+[^,.]+?\s+|Если клиент\s+.+?,\s*(?:менеджер\s+)?)", "", s, flags=re.I).rstrip("."))
    candidates = []
    for fact in facts:
        candidate = _rule_candidate(fact, _distinct(action_pool), _distinct(restriction_pool), rng)
        if candidate:
            candidates.append(candidate)
    return candidates



def _candidate_quality(candidate: dict[str, Any]) -> bool:
    q = candidate["question_text"].strip()
    if not q or len(q) < 12:
        return False
    q_low = q.casefold()
    banned_phrases = (
        "какое утверждение соответствует материалам курса",
        "какое действие менеджер обязан выполнить по теме",
        "какое правило согласования действует по теме",
        "какое правило по срокам или нормативам установлено в теме",
        "в колонке",
        "кому:", "от:", "подсказка", "ответ:",
    )
    if any(bad in q_low for bad in banned_phrases):
        return False
    if q_low.startswith("что указано"):
        return False
    options = candidate["options"]
    if len(options) != 4:
        return False
    option_keys = {o.casefold() for o in options}
    if len(option_keys) != 4:
        return False
    if any(re.match(r"^(Q|A|Вопрос|Ответ|Подсказка):", o, flags=re.I) for o in options):
        return False
    if sum(1 for o in options if o.casefold().startswith("вопрос:")):
        return False
    lengths = [len(o) for o in options]
    if max(lengths) - min(lengths) > 140:
        return False
    return True



def _score_required_match(candidate: dict[str, Any], prompt: str) -> int:
    tokens = set(_tokenize(prompt))
    if not tokens:
        return 0
    haystack = candidate["match_text"].casefold()
    overlap = sum(1 for token in tokens if token in haystack)
    if prompt.casefold() in haystack:
        overlap += 4
    return overlap



def _assemble_candidates(course_title: str, modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(42)
    candidates: list[dict[str, Any]] = []
    for module in modules:
        for topic in module.get("topics", []):
            content = topic.get("content", "")
            candidates.extend(_table_candidates(module["title"], topic["title"], content, rng))
            candidates.extend(_faq_candidates(module["title"], topic["title"], content, rng))
    candidates.extend(_policy_candidates(modules, rng))

    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not _candidate_quality(candidate):
            continue
        current = deduped.get(candidate["fingerprint"])
        if current is None or candidate["score"] > current["score"]:
            deduped[candidate["fingerprint"]] = candidate
    return list(deduped.values())



def _select_candidates(candidates: list[dict[str, Any]], question_count: int, required_questions: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    max_lookup = max(1, int(question_count * MAX_LOOKUP_SHARE))
    lookup_count = 0

    def can_take(candidate: dict[str, Any]) -> bool:
        nonlocal lookup_count
        if candidate["fingerprint"] in used:
            return False
        if candidate.get("unit_type") in LOW_VALUE_TYPES and lookup_count >= max_lookup:
            return False
        return True

    def add(candidate: dict[str, Any]) -> None:
        nonlocal lookup_count
        selected.append(candidate)
        used.add(candidate["fingerprint"])
        if candidate.get("unit_type") in LOW_VALUE_TYPES:
            lookup_count += 1

    for prompt in required_questions:
        ranked = sorted(candidates, key=lambda c: (_score_required_match(c, prompt), c["score"]), reverse=True)
        for candidate in ranked:
            if _score_required_match(candidate, prompt) <= 0:
                break
            if not can_take(candidate):
                continue
            add(candidate)
            break

    remaining = [c for c in candidates if c["fingerprint"] not in used]
    remaining.sort(key=lambda c: (c["score"], PRIORITY.get(c.get("unit_type", "table_lookup"), 0)), reverse=True)

    topic_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in remaining:
        key = f"{candidate.get('module_title','')}::{candidate.get('topic_title','')}"
        topic_buckets[key].append(candidate)

    bucket_keys = list(topic_buckets.keys())
    while len(selected) < question_count and bucket_keys:
        next_keys = []
        for key in bucket_keys:
            bucket = topic_buckets[key]
            while bucket and not can_take(bucket[0]):
                bucket.pop(0)
            if not bucket:
                continue
            add(bucket.pop(0))
            if len(selected) >= question_count:
                break
            if bucket:
                next_keys.append(key)
        bucket_keys = next_keys

    if len(selected) < question_count:
        for candidate in remaining:
            if not can_take(candidate):
                continue
            add(candidate)
            if len(selected) >= question_count:
                break

    return selected[:question_count]



def _sanitize_question(item: dict[str, Any]) -> dict[str, Any] | None:
    question_text = str(item.get("question_text", "")).strip()
    options = item.get("options")
    correct_option_index = item.get("correct_option_index")
    if not question_text or not isinstance(options, list) or len(options) != 4:
        return None
    try:
        correct_option_index = int(correct_option_index)
    except Exception:
        return None
    if correct_option_index < 0 or correct_option_index > 3:
        return None
    normalized_options = []
    seen: set[str] = set()
    for option in options:
        value = _normalize_option(str(option))
        if not _is_good_answer_value(value):
            return None
        key = value.casefold()
        if key in seen or key in BANNED_OPTIONS:
            return None
        if re.match(r"^(Q|A|Вопрос|Ответ|Подсказка):", value, flags=re.I):
            return None
        seen.add(key)
        normalized_options.append(value)
    cleaned = {"question_text": re.sub(r"\s+", " ", question_text).strip(), "options": normalized_options, "correct_option_index": correct_option_index}
    fake_candidate = {**cleaned, "score": 100, "match_text": cleaned["question_text"], "fingerprint": cleaned["question_text"]}
    return cleaned if _candidate_quality(fake_candidate) else None



def build_test_fallback(course_title: str, modules: list[dict[str, Any]], question_count: int, required_questions: list[str]) -> dict[str, Any]:
    candidates = _assemble_candidates(course_title, modules)
    if not candidates:
        raise ValueError("Недостаточно качественного материала курса для генерации теста")
    selected = _select_candidates(candidates, question_count, required_questions)
    if len(selected) < question_count:
        raise ValueError(f"Удалось подготовить только {len(selected)} качественных вопросов из {question_count}")
    return {"questions": [{"question_text": c["question_text"], "options": c["options"], "correct_option_index": c["correct_option_index"]} for c in selected]}



def build_test_draft_from_course(*, course_title: str, modules: list[dict[str, Any]], question_count: int, required_questions: list[str], provider: Any | None = None) -> dict[str, Any]:
    # Deterministic generation is intentionally preferred over broad LLM synthesis
    # to keep questions tied to explicit business rules and facts from the course.
    return build_test_fallback(course_title, modules, question_count, required_questions)



def validate_generated_test(data: dict[str, Any], *, expected_count: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Генерация теста вернула некорректную структуру")
    raw_questions = data.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("В тесте нет вопросов")
    questions = []
    seen: set[str] = set()
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        sanitized = _sanitize_question(item)
        if not sanitized:
            continue
        key = sanitized["question_text"].casefold()
        if key in seen:
            continue
        seen.add(key)
        questions.append(sanitized)
    if len(questions) < expected_count:
        raise ValueError(f"Удалось подготовить только {len(questions)} валидных вопросов из {expected_count}")
    return {"questions": questions[:expected_count]}
