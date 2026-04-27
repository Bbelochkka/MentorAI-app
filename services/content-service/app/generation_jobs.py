from __future__ import annotations

import logging
from typing import Any

from .course_generation import (
    build_course_draft_from_documents,
    prepare_documents_for_course_generation,
    validate_generated_course,
)
from .infrastructure import get_postgres_connection
from .llm_provider import LLMProviderError, get_llm_provider
from .test_generation import (
    build_test_draft_from_course,
    parse_desired_question_count,
    validate_generated_test,
)

logger = logging.getLogger(__name__)

COURSE_GENERATE_DRAFT_JOB = "course_generate_draft"
TEST_GENERATE_DRAFT_JOB = "test_generate_draft"


def _require_user_ids(current_user: dict[str, Any]) -> tuple[int, int]:
    user_id = current_user.get("id")
    company_id = current_user.get("company_id")
    if user_id is None or company_id is None:
        raise ValueError("Не удалось определить пользователя или компанию для фоновой генерации")
    return int(user_id), int(company_id)


def _normalize_test_title(title: str) -> str:
    value = (title or "").strip()
    if not value:
        raise ValueError("Название теста не может быть пустым")
    return value


def generate_course_draft_job(job_payload: dict[str, Any]) -> dict[str, Any]:
    request_payload = job_payload.get("request_payload") or {}
    current_user = job_payload.get("current_user") or {}
    user_id, company_id = _require_user_ids(current_user)

    title = (request_payload.get("title") or "").strip()
    document_ids = request_payload.get("document_ids") or []
    additional_requirements = request_payload.get("additional_requirements")
    desired_structure = request_payload.get("desired_structure")

    if not title:
        raise ValueError("Название курса обязательно")
    if not document_ids:
        raise ValueError("Нужно выбрать хотя бы один документ")

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, raw_text, status
                FROM documents
                WHERE company_id = %s
                  AND id = ANY(%s)
                ORDER BY created_at DESC
                """,
                (company_id, document_ids),
            )
            rows = cur.fetchall()

            if len(rows) != len(document_ids):
                raise ValueError("Часть документов не найдена")

            not_processed = [row[1] for row in rows if row[3] != "processed" or not (row[2] or "").strip()]
            if not_processed:
                raise ValueError(
                    "Перед созданием курса нужно обработать все выбранные документы. "
                    f"Не обработаны: {', '.join(not_processed)}"
                )

            chunks_by_document_id: dict[int, list[str]] = {row[0]: [] for row in rows}
            cur.execute(
                """
                SELECT document_id, chunk_text
                FROM document_chunks
                WHERE document_id = ANY(%s)
                ORDER BY document_id, chunk_index
                """,
                (document_ids,),
            )
            for doc_id, chunk_text in cur.fetchall():
                chunks_by_document_id.setdefault(doc_id, []).append(chunk_text)

    documents_for_generation: list[dict[str, Any]] = []
    for doc_id, doc_title, raw_text, _status in rows:
        documents_for_generation.append(
            {
                "id": doc_id,
                "title": doc_title,
                "raw_text": raw_text,
                "chunks": chunks_by_document_id.get(doc_id, []),
            }
        )

    structured_documents = prepare_documents_for_course_generation(documents_for_generation)

    llm_provider = None
    desired_structure_text = (desired_structure or "").strip()
    if desired_structure_text:
        try:
            llm_provider = get_llm_provider()
        except LLMProviderError:
            llm_provider = None

    try:
        generated = build_course_draft_from_documents(
            course_title=title,
            structured_documents=structured_documents,
            additional_requirements=additional_requirements,
            desired_structure=desired_structure,
            llm_provider=llm_provider,
        )
        validated = validate_generated_course(generated)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Ошибка фоновой генерации курса")
        raise ValueError(f"Не удалось сгенерировать курс: {exc}") from exc

    modules_data: list[dict[str, Any]] = []

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO courses (
                    company_id,
                    title,
                    description,
                    created_by,
                    status,
                    current_version_no
                )
                VALUES (%s, %s, %s, %s, 'draft', 1)
                RETURNING id
                """,
                (
                    company_id,
                    validated["title"],
                    validated["description"],
                    user_id,
                ),
            )
            course_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO course_versions (
                    course_id,
                    version_number,
                    generated_from_document_id,
                    created_by,
                    status,
                    notes
                )
                VALUES (%s, 1, %s, %s, 'draft', %s)
                RETURNING id
                """,
                (
                    course_id,
                    document_ids[0] if document_ids else None,
                    user_id,
                    "Черновик курса собран фоновым обработчиком на основе выбранных документов",
                ),
            )
            version_id = cur.fetchone()[0]

            for document_id in document_ids:
                cur.execute(
                    """
                    INSERT INTO course_document_links (
                        course_id,
                        document_id
                    )
                    VALUES (%s, %s)
                    """,
                    (course_id, document_id),
                )

            for module_index, module in enumerate(validated["modules"], start=1):
                cur.execute(
                    """
                    INSERT INTO course_modules (
                        course_version_id,
                        title,
                        sort_order
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (version_id, module["title"], module_index),
                )
                module_id = cur.fetchone()[0]

                topics_data: list[dict[str, Any]] = []
                for topic_index, topic in enumerate(module["topics"], start=1):
                    cur.execute(
                        """
                        INSERT INTO course_topics (
                            module_id,
                            title,
                            content,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (module_id, topic["title"], topic["content"], topic_index),
                    )
                    topic_id = cur.fetchone()[0]
                    topics_data.append(
                        {
                            "id": topic_id,
                            "title": topic["title"],
                            "content": topic["content"],
                            "order_index": topic_index,
                        }
                    )

                modules_data.append(
                    {
                        "id": module_id,
                        "title": module["title"],
                        "order_index": module_index,
                        "topics": topics_data,
                    }
                )

        conn.commit()

    return {
        "course_id": course_id,
        "version_id": version_id,
        "title": validated["title"],
        "description": validated["description"],
        "status": "draft",
        "modules": modules_data,
    }


def generate_test_draft_job(job_payload: dict[str, Any]) -> dict[str, Any]:
    request_payload = job_payload.get("request_payload") or {}
    current_user = job_payload.get("current_user") or {}
    user_id, company_id = _require_user_ids(current_user)

    title = _normalize_test_title(request_payload.get("title") or "")
    course_id_payload = request_payload.get("course_id")
    question_count = parse_desired_question_count(request_payload.get("desired_question_count"))

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.title
                FROM courses c
                WHERE c.id = %s
                  AND c.company_id = %s
                  AND EXISTS (
                    SELECT 1
                    FROM course_document_links l
                    JOIN documents d ON d.id = l.document_id
                    WHERE l.course_id = c.id AND d.company_id = c.company_id
                  )
                """,
                (course_id_payload, company_id),
            )
            course_row = cur.fetchone()
            if not course_row:
                raise ValueError("Можно выбрать только курс вашей компании, созданный на основе документов")

            course_id, course_title = course_row

            cur.execute(
                """
                SELECT cm.title, ct.id, ct.title, ct.content, cm.sort_order, ct.sort_order
                FROM course_versions cv
                JOIN course_modules cm ON cm.course_version_id = cv.id
                JOIN course_topics ct ON ct.module_id = cm.id
                WHERE cv.course_id = %s
                  AND cv.version_number = (SELECT current_version_no FROM courses WHERE id = %s)
                ORDER BY cm.sort_order, ct.sort_order
                """,
                (course_id, course_id),
            )
            topic_rows = cur.fetchall()

    if not topic_rows:
        raise ValueError("В выбранном курсе нет тем для генерации теста")

    modules_map: dict[str, dict[str, Any]] = {}
    for module_title, topic_id, topic_title, topic_content, module_order, topic_order in topic_rows:
        key = f"{module_order}:{module_title}"
        modules_map.setdefault(key, {"title": module_title, "order_index": module_order, "topics": []})
        modules_map[key]["topics"].append(
            {
                "id": topic_id,
                "title": topic_title,
                "content": topic_content,
                "order_index": topic_order,
            }
        )

    modules = [item for _, item in sorted(modules_map.items(), key=lambda pair: pair[1]["order_index"])]

    provider = None
    try:
        provider = get_llm_provider()
    except Exception:
        provider = None

    try:
        generated = build_test_draft_from_course(
            course_title=course_title,
            modules=modules,
            question_count=question_count,
            required_questions=[],
            provider=provider,
        )
        validated = validate_generated_test(generated, expected_count=question_count)
    except Exception as exc:
        raise ValueError(f"Не удалось сгенерировать тест: {exc}") from exc

    questions_data: list[dict[str, Any]] = []
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tests (company_id, course_id, title, test_type, status, current_version_no, created_by)
                VALUES (%s, %s, %s, 'course', 'draft', 1, %s)
                RETURNING id
                """,
                (company_id, course_id, title, user_id),
            )
            test_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO test_versions (test_id, version_number, created_by, status)
                VALUES (%s, 1, %s, 'draft')
                RETURNING id
                """,
                (test_id, user_id),
            )
            version_id = cur.fetchone()[0]

            for question_index, question in enumerate(validated["questions"], start=1):
                cur.execute(
                    """
                    INSERT INTO questions (test_version_id, topic_id, question_text, question_type, weight, sort_order)
                    VALUES (%s, NULL, %s, 'single_choice', 1.0, %s)
                    RETURNING id
                    """,
                    (version_id, question["question_text"], question_index),
                )
                question_id = cur.fetchone()[0]

                options_data: list[dict[str, Any]] = []
                for option_index, option_text in enumerate(question["options"], start=1):
                    is_correct = option_index - 1 == question["correct_option_index"]
                    cur.execute(
                        """
                        INSERT INTO question_options (question_id, option_text, is_correct, sort_order)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (question_id, option_text, is_correct, option_index),
                    )
                    option_id = cur.fetchone()[0]
                    options_data.append(
                        {
                            "id": option_id,
                            "text": option_text,
                            "is_correct": is_correct,
                            "order_index": option_index,
                        }
                    )

                questions_data.append(
                    {
                        "id": question_id,
                        "question_text": question["question_text"],
                        "order_index": question_index,
                        "options": options_data,
                    }
                )

        conn.commit()

    return {
        "test_id": test_id,
        "version_id": version_id,
        "title": title,
        "status": "draft",
        "course_id": course_id,
        "course_title": course_title,
        "question_count": len(questions_data),
        "questions": questions_data,
    }


def run_generation_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if job_type == COURSE_GENERATE_DRAFT_JOB:
        return generate_course_draft_job(payload)
    if job_type == TEST_GENERATE_DRAFT_JOB:
        return generate_test_draft_job(payload)
    raise ValueError(f"Неизвестный тип фоновой задачи: {job_type}")
