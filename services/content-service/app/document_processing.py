from __future__ import annotations

from io import BytesIO
import re
from typing import Any, Iterator

from docx import Document as DocxDocument
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

INLINE_BREAK = " / "
DOCX_H1_MARKER = "[[DOCX_H1]]"



def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x0b", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_docx_heading1_style(style_name: str | None) -> bool:
    if not style_name:
        return False
    normalized = style_name.strip().lower()
    return (
        normalized in {"heading 1", "заголовок 1"}
        or normalized.startswith("heading 1")
        or normalized.startswith("заголовок 1")
    )


def _encode_docx_heading1(text: str) -> str:
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    return f"{DOCX_H1_MARKER} {cleaned}"


def strip_docx_heading_markers(text: str) -> str:
    text = re.sub(rf"^\s*{re.escape(DOCX_H1_MARKER)}\s*", "", text)
    return text.strip()

def extract_text_from_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def iter_block_items(parent: _Document | _Cell) -> Iterator[Paragraph | Table]:
    parent_element = parent.element.body if isinstance(parent, _Document) else parent._tc

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _paragraph_text(paragraph: Paragraph) -> str:
    return normalize_text(paragraph.text)


def _cell_text(cell: _Cell) -> str:
    parts: list[str] = []
    for paragraph in cell.paragraphs:
        text = _paragraph_text(paragraph)
        if text:
            parts.append(text)
    return INLINE_BREAK.join(parts).strip()


def _escape_table_cell(text: str) -> str:
    text = normalize_text(text)
    text = text.replace("|", "\\|")
    # Переносы внутри markdown-таблиц ломают распознавание строк на фронте.
    # Поэтому сохраняем многострочные значения как inline-текст внутри одной ячейки.
    text = text.replace(INLINE_BREAK, " / ")
    text = text.replace("\n", " / ")
    text = re.sub(r"\s*/\s*/+", " / ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" /")


def _table_rows(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    max_cols = 0

    for row in table.rows:
        values = [_cell_text(cell) for cell in row.cells]
        if any(value.strip() for value in values):
            rows.append(values)
            max_cols = max(max_cols, len(values))

    if max_cols == 0:
        return []

    return [row + [""] * (max_cols - len(row)) for row in rows]


def _is_placeholder_row(row: list[str]) -> bool:
    if not row:
        return True
    combined = " ".join(normalize_text(cell) for cell in row).strip(" _")
    return combined == ""


def _split_callout(text: str) -> tuple[str | None, str]:
    value = normalize_text(text)
    if not value:
        return None, ""

    if INLINE_BREAK in value:
        left, right = value.split(INLINE_BREAK, 1)
        left = normalize_text(left)
        right = normalize_text(right)
        if left and right:
            return left, right

    return None, value


def _render_single_column_table(rows: list[list[str]]) -> str:
    values = [normalize_text(row[0]) for row in rows if row and normalize_text(row[0])]
    if not values:
        return ""

    rendered_blocks: list[str] = []
    for value in values:
        title, body = _split_callout(value)
        if title and body:
            rendered_blocks.append(f"{title}\n{body}")
        else:
            rendered_blocks.append(value)

    return "\n\n".join(rendered_blocks).strip()


def table_to_markdown(table: Table) -> str:
    rows = _table_rows(table)
    rows = [row for row in rows if not _is_placeholder_row(row)]
    if not rows:
        return ""

    col_count = max(len(row) for row in rows)

    # Одноколоночные таблицы в учебных docx часто являются не таблицами данных,
    # а callout-блоками вроде “Red flags / …” или “Tone of voice / …”.
    # Не создаем synthetic header “Колонка 1”, а сохраняем как текстовый блок.
    if col_count == 1:
        return _render_single_column_table(rows)

    # Если таблица фактически состоит из одного ряда, безопаснее отдать её как текст,
    # а не создавать искусственный заголовок.
    if len(rows) == 1:
        return "\n".join(cell for cell in rows[0] if normalize_text(cell)).strip()

    header = [normalize_text(cell) for cell in rows[0]]
    body_rows = [[normalize_text(cell) for cell in row] for row in rows[1:]]

    if not any(header):
        header = [f"Поле {idx}" for idx in range(1, len(header) + 1)]

    header = [_escape_table_cell(cell) for cell in header]
    separator = ["---"] * len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]

    for row in body_rows:
        escaped = [_escape_table_cell(cell) for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")

    return "\n".join(lines)


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = DocxDocument(BytesIO(file_bytes))
    blocks: list[str] = []

    for block in iter_block_items(document):
        if isinstance(block, Paragraph):
            text = _paragraph_text(block)
            if not text:
                continue
            style_name = getattr(getattr(block, "style", None), "name", None)
            if _is_docx_heading1_style(style_name):
                encoded = _encode_docx_heading1(text)
                if encoded:
                    blocks.append(encoded)
            else:
                blocks.append(text)
        elif isinstance(block, Table):
            table_text = table_to_markdown(block)
            if table_text:
                blocks.append(table_text)

    return "\n\n".join(blocks)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if page_text:
            pages.append(page_text)

    return "\n\n".join(pages)


def extract_text_by_file_type(file_type: str, file_bytes: bytes) -> str:
    if file_type == "txt":
        return normalize_text(extract_text_from_txt(file_bytes))

    if file_type == "docx":
        return normalize_text(extract_text_from_docx(file_bytes))

    if file_type == "pdf":
        return normalize_text(extract_text_from_pdf(file_bytes))

    raise ValueError(f"Неподдерживаемый тип файла: {file_type}")


def _heading_level(text: str) -> int | None:
    line = text.strip()
    if not line:
        return None

    if line.startswith(DOCX_H1_MARKER):
        return 1

    match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(\S+)", strip_docx_heading_markers(line))
    if match:
        first_token = match.group(2)
        first_char = first_token[0]
        if first_char.isupper() or first_char in {'«', '"', '('}:
            return match.group(1).count(".") + 1

    if len(line) <= 90 and len(line.split()) <= 10 and not line.endswith((".", "!", "?", ";")):
        if line and strip_docx_heading_markers(line)[0].isupper():
            return 1

    return None


def _block_type(text: str) -> tuple[str, int | None, str | None]:
    block = text.strip()
    if not block:
        return "empty", None, None

    if block.startswith(DOCX_H1_MARKER):
        return "heading", 1, "docx_h1"

    heading_level = _heading_level(block)
    if heading_level is not None and "\n" not in block:
        heading_source = "numbered" if re.match(r"^(\d+(?:\.\d+)*)\.?\s+\S+", strip_docx_heading_markers(block)) else "heuristic"
        return "heading", heading_level, heading_source

    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) >= 2 and sum(1 for line in lines if line.count("|") >= 2) >= 2:
        return "table", None, None

    if any(line.startswith("Q:") for line in lines) or any(line.startswith("A:") for line in lines):
        return "qa_block", None, None

    if any("☐" in line or "☑" in line for line in lines):
        return "checklist", None, None

    if lines and all(re.match(r"^(?:[-*•]|\d+[.)])\s+", line) for line in lines if line):
        return "bullet_list", None, None

    return "paragraph", None, None

def extract_document_blocks_from_text(text: str) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    raw_blocks = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    blocks: list[dict[str, Any]] = []

    for index, raw_block in enumerate(raw_blocks, start=1):
        block_type, heading_level, heading_source = _block_type(raw_block)
        block_text = strip_docx_heading_markers(raw_block) if heading_source == "docx_h1" else raw_block
        blocks.append(
            {
                "index": index,
                "type": block_type,
                "heading_level": heading_level,
                "heading_source": heading_source,
                "text": block_text,
            }
        )

    return blocks


def split_text_into_chunks(
    text: str,
    *,
    target_chunk_size: int = 1200,
    max_chunk_size: int = 1600,
) -> list[str]:
    if not text.strip():
        return []

    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current_chunk else f"{current_chunk}\n\n{paragraph}"

        if len(candidate) <= target_chunk_size:
            current_chunk = candidate
            continue

        if current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph
            continue

        parts = re.split(r"(?<=[.!?])\s+", paragraph)
        temp = ""

        for part in parts:
            candidate_part = part if not temp else f"{temp} {part}"

            if len(candidate_part) <= max_chunk_size:
                temp = candidate_part
            else:
                if temp:
                    chunks.append(temp.strip())
                temp = part

        if temp:
            current_chunk = temp.strip()

    if current_chunk:
        chunks.append(current_chunk)

    return [chunk.strip() for chunk in chunks if chunk.strip()]
