from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any

from .document_processing import extract_document_blocks_from_text, normalize_text, strip_docx_heading_markers

SERVICE_PATTERNS = [
    r"^внутренний документ компании$",
    r"^учебный кейс",
    r"^актуально для",
    r"^версия документа",
    r"^назначение документа$",
    r"^что проверяет$",
    r"^содержание$",
    r"^внутренний пакет для адаптации$",
    r"^редакция\b",
    r"^[а-яё\- ]+,\s*20\d{2}$",
]

POLICY_KEYWORDS = [
    "обязательно",
    "запрещ",
    "нельзя",
    "только",
    "не позднее",
    "должен",
    "должны",
    "правило",
    "согласует",
    "согласование",
    "red flags",
]
PROCESS_KEYWORDS = [
    "этап",
    "процесс",
    "квалификац",
    "демо",
    "пилот",
    "кп",
    "встреч",
    "воронк",
    "следующий шаг",
]
OPERATIONS_KEYWORDS = [
    "crm",
    "kpi",
    "sla",
    "коммуникац",
    "этик",
    "отдел",
    "поддержк",
    "presale",
    "маркетинг",
    "финансы",
    "юрист",
]

RUSSIAN_STEM_ENDINGS = (
    "иями", "ями", "ами", "иях", "иях", "его", "ого", "ему", "ому", "ыми", "ими",
    "ией", "ией", "иям", "ием", "иях", "иях", "ать", "ять", "ить", "еть",
    "ый", "ий", "ой", "ая", "яя", "ое", "ее", "ые", "ие", "ых", "их",
    "ам", "ям", "ах", "ях", "ов", "ев", "ей", "ом", "ем", "ую", "юю",
    "а", "я", "ы", "и", "е", "о", "у", "ю"
)
COMMON_STOPWORDS = {
    "модуль", "модуля", "модуле", "модулю", "модули",
    "тема", "темы", "теме", "тем", "теме",
    "раздел", "раздела", "разделе",
    "блок", "блока", "блоке",
    "нужен", "нужна", "нужно", "нужны",
    "добавить", "добавь", "добавьте", "сделать", "сделай", "сделайте",
    "для", "в", "по", "про", "о",
}


def _normalize_for_fingerprint(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\sа-яё]", "", text, flags=re.IGNORECASE)
    return text.strip()


def _fingerprint(text: str) -> str:
    return hashlib.md5(_normalize_for_fingerprint(text).encode("utf-8")).hexdigest()


def _stem_token(word: str) -> str:
    word = word.lower().strip()
    if len(word) <= 4:
        return word
    for ending in RUSSIAN_STEM_ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", text.lower())
    result: set[str] = set()
    for word in words:
        if len(word) >= 3 and word not in COMMON_STOPWORDS:
            result.add(word)
            result.add(_stem_token(word))
    return {word for word in result if word and len(word) >= 3}


def _strip_numbering(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", title).strip()


def _matches_any(text: str, patterns: list[str]) -> bool:
    lowered = text.lower().strip()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _clean_service_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []

    for line in lines:
        stripped = line.strip()
        stripped = strip_docx_heading_markers(stripped)
        if not stripped:
            cleaned.append("")
            continue

        lowered = stripped.lower()
        if _matches_any(lowered, SERVICE_PATTERNS):
            continue
        if lowered.startswith("из документа можно формировать"):
            continue
        if lowered.startswith("материал предназначен для обучения"):
            continue
        if lowered.startswith("актуально для адаптации"):
            continue
        cleaned.append(stripped)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _heading_level_from_title(text: str) -> int | None:
    match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+", text.strip())
    if not match:
        return None
    return match.group(1).count(".") + 1


def _classify_section_kind(title: str, body: str, block_types: list[str]) -> str:
    title_l = title.lower()
    body_l = body.lower()
    haystack = f"{title_l}\n{body_l}"
    has_table = any(bt == "table" for bt in block_types)
    has_qa = any(bt == "qa_block" for bt in block_types)
    has_checklist = any(bt == "checklist" for bt in block_types)

    if any(keyword in title_l for keyword in ["глоссар", "словар", "термин"]):
        return "glossary"
    if "faq" in title_l or has_qa:
        return "faq"
    if any(keyword in title_l for keyword in ["чек-лист", "чеклист"]) or has_checklist:
        return "checklist"
    if any(keyword in title_l for keyword in ["кейс", "ситуац"]):
        return "case"
    if "письмо" in title_l or "добро пожаловать" in haystack:
        return "intro_message"
    if has_table:
        return "reference_table"
    if any(keyword in haystack for keyword in POLICY_KEYWORDS):
        return "policy"
    if any(keyword in haystack for keyword in PROCESS_KEYWORDS):
        return "procedure"
    return "concept"


def _section_family(section: dict[str, Any]) -> str:
    title_l = section["title"].lower()
    body_l = section["body"].lower()
    haystack = f"{title_l}\n{body_l}"

    if section["kind"] in {"faq", "checklist", "case", "glossary"}:
        return "reference"
    if any(keyword in haystack for keyword in OPERATIONS_KEYWORDS):
        return "operations"
    if any(keyword in haystack for keyword in PROCESS_KEYWORDS):
        return "process"
    if any(keyword in haystack for keyword in ["компан", "продукт", "аудитор", "клиент", "тариф", "услуг"]):
        return "overview"
    return "general"


def _is_service_section(title: str, body: str) -> bool:
    title_l = _strip_numbering(title).lower()
    body_l = body.lower()

    if _matches_any(title_l, SERVICE_PATTERNS):
        return True
    if title_l in {"содержание", "назначение", "что проверяет"}:
        return True

    service_hits = 0
    for marker in [
        "актуально для адаптации",
        "версия документа",
        "учебный кейс",
        "материал предназначен",
        "из документа можно формировать",
    ]:
        if marker in body_l:
            service_hits += 1
    return service_hits >= 2


def _split_field_into_items(text: str | None) -> list[str]:
    if not text or not text.strip():
        return []
    prepared = text.replace("\n", ";")
    parts = [part.strip(" •-\t") for part in re.split(r"[;,]+", prepared) if part.strip()]
    return parts


def _parse_scoped_item(raw: str) -> tuple[str, str]:
    cleaned = raw.strip().strip('"«»').strip()
    match = re.match(r"^(модуль|тема|module|topic)\s*:\s*(.+)$", cleaned, flags=re.IGNORECASE)
    if not match:
        return "auto", cleaned

    scope_raw = match.group(1).lower()
    value = match.group(2).strip()
    scope = "module" if scope_raw in {"модуль", "module"} else "topic"
    return scope, value


def _build_match_spec(raw: str, scope: str = "auto") -> dict[str, Any]:
    cleaned = raw.strip().strip('"«»')
    cleaned = re.sub(r"\b(?:раздел\s+)?важно\s+запомнить\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(?:добавить|добавь|добавьте|нужен|нужна|нужно|нужны|сделать|сделай|сделайте|для|в|во|по|про|о|об|обо|касается|курс|курса|курсе)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
    effective = cleaned or raw.strip()
    return {
        "raw": effective,
        "scope": scope,
        "tokens": _tokenize(effective),
        "stems": {_stem_token(token) for token in _tokenize(effective)},
    }


def _extract_generation_controls(
    additional_requirements: str | None,
    desired_structure: str | None,
) -> dict[str, list[dict[str, Any]]]:
    exclude_specs: list[dict[str, Any]] = []
    remember_specs: list[dict[str, Any]] = []

    for item in _split_field_into_items(additional_requirements):
        lowered = item.lower()
        match = re.search(
            r"(?:не\s+нужн\w*|не\s+включать|исключить|убрать|без)\s+(.+)",
            lowered,
            flags=re.IGNORECASE,
        )
        target = match.group(1).strip() if match else item.strip()
        if not target:
            continue
        scope, value = _parse_scoped_item(target)
        if value:
            exclude_specs.append(_build_match_spec(value, scope=scope))

    for item in _split_field_into_items(desired_structure):
        cleaned = re.sub(r"['\"«»]", "", item).strip()
        if not cleaned:
            continue
        scope, value = _parse_scoped_item(cleaned)
        if value:
            remember_specs.append(_build_match_spec(value, scope=scope))

    return {"exclude_specs": exclude_specs, "remember_specs": remember_specs}

def _significant_words(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", text.lower())
        if word not in COMMON_STOPWORDS
    ]


def _spec_matches_title(spec: dict[str, Any], title: str) -> bool:
    if not title.strip():
        return False

    raw = (spec.get("raw") or "").strip()
    if not raw:
        return False

    raw_norm = _normalize_for_fingerprint(raw)
    title_norm = _normalize_for_fingerprint(_strip_numbering(title))
    if not raw_norm or not title_norm:
        return False

    if raw_norm == title_norm:
        return True

    raw_words = _significant_words(raw)
    raw_stems = {_stem_token(word) for word in raw_words}
    title_words = _significant_words(_strip_numbering(title))
    title_stems = {_stem_token(word) for word in title_words}

    if raw_norm in title_norm or title_norm in raw_norm:
        if len(raw_words) >= 2 or len(raw_norm) >= 8:
            return True

    if raw_stems and title_stems:
        stem_overlap = len(raw_stems & title_stems)
        if len(raw_stems) >= 2 and stem_overlap == len(raw_stems):
            return True
        if len(raw_stems) >= 3 and stem_overlap >= len(raw_stems) - 1:
            return True

    ratio = SequenceMatcher(None, raw_norm, title_norm).ratio()
    if len(raw_words) >= 2 and ratio >= 0.82:
        return True

    return False


def _render_list(block_text: str) -> str:
    result: list[str] = []
    for line in block_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^(?:[-*•]|\d+[.)]|☐|☑)\s+", "", stripped).strip()
        if stripped:
            result.append(f"- {stripped}")
    return "\n".join(result)


def _render_qa(block_text: str) -> str:
    lines = [line.strip() for line in block_text.splitlines() if line.strip()]
    rendered: list[str] = []
    for line in lines:
        if line.startswith("Q:"):
            rendered.append(f"**Вопрос:** {line[2:].strip()}")
        elif line.startswith("A:"):
            rendered.append(f"**Ответ:** {line[2:].strip()}")
        else:
            rendered.append(line)
    return "\n\n".join(rendered)


def _convert_fake_single_column_tables(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if re.match(r"^\|\s*колонка\s*1\s*\|$", stripped, flags=re.IGNORECASE) and re.match(r"^\|\s*[-:]+\s*\|$", next_line):
            i += 2
            values: list[str] = []
            while i < len(lines):
                row = lines[i].strip()
                if not re.match(r"^\|.*\|$", row):
                    break
                cell = row.strip("|").strip()
                if cell:
                    values.append(cell)
                i += 1
            if values:
                result.extend(values)
            continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def _cleanup_rendered_text(text: str) -> str:
    text = strip_docx_heading_markers(text)
    text = text.replace("<br/>", "\n").replace("<br>", "\n")
    text = _convert_fake_single_column_tables(text)
    text = re.sub(r"\[\s*конкретная дата\s*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Колонка\s+1\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*\|\s*Колонка\s*1\s*\|\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*\|\s*[-:]+\s*\|\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return normalize_text(text)


def _extract_key_points(section: dict[str, Any], limit: int = 4) -> list[str]:
    points: list[str] = []

    for block in section["blocks"]:
        if block["type"] == "table":
            continue
        if block["type"] in {"bullet_list", "checklist"}:
            for line in block["text"].splitlines():
                stripped = re.sub(r"^(?:[-*•]|\d+[.)]|☐|☑)\s*", "", line).strip()
                if stripped:
                    points.append(stripped)
            continue

        block_text = _clean_service_lines(block["text"])
        sentences = re.split(r"(?<=[.!?])\s+", block_text)
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            lowered = s.lower()
            if any(keyword in lowered for keyword in POLICY_KEYWORDS) or re.search(r"\d", s):
                points.append(s)

    compressed: list[str] = []
    seen: set[str] = set()
    for point in points:
        point = _cleanup_rendered_text(point)
        if not point:
            continue
        key = _fingerprint(point)
        if key in seen:
            continue
        seen.add(key)
        compressed.append(point)
        if len(compressed) >= limit:
            break

    return compressed


def _remember_points_from_llm(section: dict[str, Any], provider: Any) -> list[str]:
    prompt = f"""
Ты анализируешь фрагмент внутреннего документа для онбординга менеджеров по продажам.

Твоя задача: выделить 2-4 самых важных пункта, которые менеджер должен запомнить по теме.

Правила:
1. Используй только информацию из фрагмента ниже.
2. Ничего не придумывай и не обобщай сверх текста.
3. Если в тексте есть цифры, сроки, роли, ограничения, условия согласования, обязательные поля или запреты — включай их в приоритетном порядке.
4. Пиши коротко и конкретно.
5. Верни только валидный JSON.

Формат ответа:
{{
  "points": ["пункт 1", "пункт 2"]
}}

Тема: {_strip_numbering(section['title'])}
Фрагмент:
{section['body'][:6000]}
""".strip()

    data = provider.generate_json(prompt)
    points = data.get("points")
    if not isinstance(points, list):
        return []

    cleaned: list[str] = []
    for point in points:
        if not isinstance(point, str):
            continue
        normalized = _cleanup_rendered_text(point)
        if normalized:
            cleaned.append(normalized)
    return cleaned[:4]


def _build_remember_block(section: dict[str, Any], provider: Any | None = None) -> str:
    points: list[str] = []
    if provider is not None:
        try:
            points = _remember_points_from_llm(section, provider)
        except Exception:
            points = []

    if not points:
        points = _extract_key_points(section, limit=3)

    cleaned_points: list[str] = []
    seen: set[str] = set()
    section_fp = _fingerprint(section.get("body") or "")
    for point in points:
        point = _cleanup_rendered_text(point)
        if not point:
            continue
        point = re.split(r"(?<=[.!?])\s+", point.strip())[0].strip()
        if len(point) > 220:
            point = point[:220].rsplit(" ", 1)[0].rstrip(" ,;:-") + "."
        fp = _fingerprint(point)
        if fp in seen or fp == section_fp:
            continue
        seen.add(fp)
        cleaned_points.append(point)
        if len(cleaned_points) >= 3:
            break

    if not cleaned_points:
        return ""

    bullets = "\n".join(f"- {point}" for point in cleaned_points)
    return f"### Важно запомнить\n{bullets}".strip()


def _render_section_content(
    section: dict[str, Any],
    *,
    include_remember: bool = False,
    llm_provider: Any | None = None,
) -> str:
    title = strip_docx_heading_markers(_strip_numbering(section["title"]))
    parts: list[str] = []
    body_paragraphs: list[str] = []

    for block in section["blocks"]:
        text = _clean_service_lines(block["text"])
        if not text:
            continue

        if block["type"] == "table":
            if body_paragraphs:
                parts.append("\n\n".join(body_paragraphs).strip())
                body_paragraphs = []
            parts.append(text)
        elif block["type"] in {"bullet_list", "checklist"}:
            if body_paragraphs:
                parts.append("\n\n".join(body_paragraphs).strip())
                body_paragraphs = []
            parts.append(_render_list(text))
        elif block["type"] == "qa_block":
            if body_paragraphs:
                parts.append("\n\n".join(body_paragraphs).strip())
                body_paragraphs = []
            parts.append(_render_qa(text))
        else:
            if text != section["title"]:
                body_paragraphs.append(text)

    if body_paragraphs:
        parts.append("\n\n".join(body_paragraphs).strip())

    content_parts: list[str] = []
    if parts:
        content_parts.append("\n\n".join(parts))

    if include_remember:
        remember_block = _build_remember_block(section, provider=llm_provider)
        if remember_block:
            content_parts.append(remember_block)

    content = "\n\n".join(part.strip() for part in content_parts if part and part.strip())
    content = _cleanup_rendered_text(content)
    return content.strip()


def _build_sections_from_blocks(blocks: list[dict[str, Any]], document_title: str) -> list[dict[str, Any]]:
    if not blocks:
        return []

    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    untitled_index = 1
    has_heading = any(block["type"] == "heading" for block in blocks)

    if not has_heading:
        sections = [{"title": document_title, "blocks": blocks, "heading_level": 1, "heading_source": None}]
    else:
        for block in blocks:
            if block["type"] == "heading":
                if current and (current["blocks"] or current.get("heading_source") == "docx_h1"):
                    sections.append(current)
                current = {
                    "title": strip_docx_heading_markers(block["text"]),
                    "blocks": [],
                    "heading_level": block.get("heading_level") or _heading_level_from_title(block["text"]) or 1,
                    "heading_source": block.get("heading_source"),
                }
            else:
                if current is None:
                    current = {
                        "title": f"Раздел {untitled_index}",
                        "blocks": [],
                        "heading_level": 1,
                        "heading_source": None,
                    }
                    untitled_index += 1
                current["blocks"].append(block)
        if current and (current["blocks"] or current.get("heading_source") == "docx_h1"):
            sections.append(current)

    prepared: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        body = normalize_text("\n\n".join(block["text"] for block in section["blocks"] if block["text"].strip()))
        title = normalize_text(strip_docx_heading_markers(section["title"]))
        heading_source = section.get("heading_source")
        if not body.strip() and heading_source != "docx_h1":
            continue
        if _is_service_section(title, body):
            continue
        block_types = [block["type"] for block in section["blocks"]]
        prepared.append(
            {
                "id": f"{_fingerprint(document_title)}_{index}",
                "title": title,
                "body": body,
                "kind": _classify_section_kind(title, body, block_types) if body.strip() else "container",
                "heading_level": section.get("heading_level") or 1,
                "heading_source": heading_source,
                "blocks": section["blocks"],
                "source_documents": [document_title],
                "family": "",
                "document_title": document_title,
                "document_order": index,
            }
        )
    for section in prepared:
        section["family"] = _section_family(section)

    return prepared

def prepare_documents_for_course_generation(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []

    for document in documents:
        raw_text = normalize_text(document.get("raw_text") or "")
        if not raw_text:
            continue
        blocks = extract_document_blocks_from_text(raw_text)
        sections = _build_sections_from_blocks(blocks, document["title"])
        prepared.append(
            {
                "id": document["id"],
                "title": document["title"],
                "raw_text": raw_text,
                "blocks": blocks,
                "sections": sections,
            }
        )

    return prepared


def _dedupe_section_list(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for section in sections:
        key = _fingerprint(f"{_strip_numbering(section['title'])}\n{section['body']}")
        if key in seen:
            continue
        seen.add(key)
        result.append(section)
    return result


def _module_title_from_section(section: dict[str, Any], index: int) -> str:
    title = strip_docx_heading_markers(_strip_numbering(section["title"]))
    title = re.sub(r"^модуль\s+\d+\.?\s*", "", title, flags=re.IGNORECASE).strip()
    if not title or re.fullmatch(r"модуль\s*\d*", title, flags=re.IGNORECASE):
        mapping = {
            "overview": "Обзор и продукт",
            "process": "Процесс продажи",
            "operations": "Операционные правила",
            "reference": "Справочные материалы",
            "general": f"Модуль {index}",
        }
        return mapping.get(section["family"], f"Модуль {index}")
    return title


def _build_topics_and_modules(
    structured_documents: list[dict[str, Any]],
    controls: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []

    for document in structured_documents:
        sections = _dedupe_section_list([dict(section) for section in document["sections"]])
        if not sections:
            continue

        explicit_h1_sections = [section for section in sections if section.get("heading_source") == "docx_h1"]
        document_modules: list[dict[str, Any]] = []

        if explicit_h1_sections:
            intro_topics: list[dict[str, Any]] = []
            current_module: dict[str, Any] | None = None

            for section in sections:
                if section.get("heading_source") == "docx_h1":
                    if current_module:
                        document_modules.append(current_module)
                    current_module = {
                        "title": _module_title_from_section(section, len(modules) + len(document_modules) + 1),
                        "topics": [section] if (section.get("body") or "").strip() else [],
                    }
                else:
                    if current_module is None:
                        intro_topics.append(section)
                    else:
                        current_module["topics"].append(section)

            if intro_topics:
                document_modules.insert(0, {
                    "title": "Введение",
                    "topics": intro_topics,
                })
            if current_module:
                document_modules.append(current_module)
        else:
            has_top_level = any(section.get("heading_level", 1) == 1 for section in sections)

            if not has_top_level:
                document_modules.append({
                    "title": document["title"],
                    "topics": sections,
                })
            else:
                current_module = None
                for section in sections:
                    level = section.get("heading_level", 1)
                    if level == 1:
                        if current_module:
                            document_modules.append(current_module)
                        current_module = {
                            "title": _module_title_from_section(section, len(modules) + len(document_modules) + 1),
                            "topics": [section],
                        }
                    else:
                        if current_module is None:
                            current_module = {
                                "title": document["title"],
                                "topics": [section],
                            }
                        else:
                            current_module["topics"].append(section)

                if current_module:
                    document_modules.append(current_module)

        for module in document_modules:
            module_title = module["title"]
            if any(_module_matches_spec(spec, module_title) for spec in controls["exclude_specs"]):
                continue

            filtered_topics = [
                topic
                for topic in module["topics"]
                if not any(_topic_matches_spec(spec, module_title, topic) for spec in controls["exclude_specs"])
            ]
            filtered_topics = _dedupe_section_list(filtered_topics)
            if not filtered_topics:
                continue

            modules.append(
                {
                    "title": module_title,
                    "topics": filtered_topics,
                }
            )

    return modules

def _module_matches_spec(spec: dict[str, Any], module_title: str) -> bool:
    scope = spec.get("scope", "auto")
    if scope not in {"auto", "module"}:
        return False
    return _spec_matches_title(spec, module_title)


def _topic_matches_spec(spec: dict[str, Any], module_title: str, topic: dict[str, Any]) -> bool:
    scope = spec.get("scope", "auto")
    topic_title = _strip_numbering(topic.get("title") or "")

    if scope == "module":
        return _spec_matches_title(spec, module_title)
    if scope == "topic":
        return _spec_matches_title(spec, topic_title)
    return _spec_matches_title(spec, topic_title)

def _build_description(course_title: str, modules: list[dict[str, Any]]) -> str:
    modules_count = len(modules)
    topics_count = sum(len(module["topics"]) for module in modules)
    return (
        f"Курс «{course_title}» собран строго по выбранным документам. "
        f"Он включает {modules_count} модулей и {topics_count} тем. "
        f"По умолчанию материал следует логике исходных документов без добавления лишних тем."
    )


def build_course_draft_from_documents(
    *,
    course_title: str,
    structured_documents: list[dict[str, Any]],
    additional_requirements: str | None = None,
    desired_structure: str | None = None,
    llm_provider: Any | None = None,
) -> dict[str, Any]:
    controls = _extract_generation_controls(additional_requirements, desired_structure)
    modules = _build_topics_and_modules(structured_documents, controls)

    if not modules:
        raise ValueError("После применения фильтров не осталось ни одного содержательного раздела")

    rendered_modules: list[dict[str, Any]] = []
    remember_specs = controls["remember_specs"]

    for module in modules:
        module_title = module["title"]
        module_remember = any(_module_matches_spec(spec, module_title) for spec in remember_specs)
        rendered_topics: list[dict[str, str]] = []

        for topic in module["topics"]:
            topic_title = strip_docx_heading_markers(_strip_numbering(topic["title"]))
            topic_remember = module_remember or any(
                _topic_matches_spec(spec, module_title, topic)
                for spec in remember_specs
            )
            rendered_topics.append(
                {
                    "title": topic_title,
                    "content": _render_section_content(
                        topic,
                        include_remember=topic_remember,
                        llm_provider=llm_provider if topic_remember else None,
                    ),
                }
            )

        rendered_modules.append({"title": module_title, "topics": rendered_topics})

    return {
        "title": course_title,
        "description": _build_description(course_title, modules),
        "modules": rendered_modules,
    }


def validate_generated_course(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("В курсе отсутствует корректное поле title")
    if not isinstance(data.get("description"), str) or not data["description"].strip():
        raise ValueError("В курсе отсутствует корректное поле description")

    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("В курсе отсутствуют модули")

    for module in modules:
        if not isinstance(module.get("title"), str) or not module["title"].strip():
            raise ValueError("У модуля отсутствует title")
        topics = module.get("topics")
        if not isinstance(topics, list) or not topics:
            raise ValueError("У модуля отсутствуют темы")
        for topic in topics:
            if not isinstance(topic.get("title"), str) or not topic["title"].strip():
                raise ValueError("У темы отсутствует title")
            if not isinstance(topic.get("content"), str) or not topic["content"].strip():
                raise ValueError("У темы отсутствует content")

    return data
