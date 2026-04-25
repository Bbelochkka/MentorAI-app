from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
import logging
from typing import Any
from minio.error import S3Error
from .chatbot import router as chatbot_router

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from .course_generation import (
    build_course_draft_from_documents,
    prepare_documents_for_course_generation,
    validate_generated_course,
)
from .llm_provider import LLMProviderError, get_llm_provider
from .config import settings
from .document_processing import extract_text_by_file_type, split_text_into_chunks
from .infrastructure import (
    delete_object_from_minio,
    download_bytes_from_minio,
    ensure_bucket_exists,
    get_minio_client,
    get_postgres_connection,
    get_redis_client,
    upload_bytes_to_minio,
)
from .schemas import (
    DocumentListResponse,
    DocumentResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    CourseDraftResponse,
    CourseGenerateRequest,
    CourseModuleResponse,
    CourseTopicResponse,
    CourseListResponse,
    CourseSummaryResponse,
    CourseDraftUpdateRequest,
    CourseStatusUpdateRequest,
    TestGenerateRequest,
    TestOptionResponse,
    TestQuestionResponse,
    TestDraftResponse,
    TestSummaryResponse,
    TestListResponse,
    TestStatusUpdateRequest,
    TestDraftUpdateRequest,
    LearnerTestOptionResponse,
    LearnerTestQuestionResponse,
    TestAttemptStartResponse,
    AttemptAnswerRequest,
    TestAttemptFinishRequest,
    AttemptResultOptionResponse,
    AttemptResultQuestionResponse,
    TestAttemptResultResponse,
)
from .security import authenticate_user, create_access_token, get_current_user
from .test_generation import (
    build_test_draft_from_course,
    parse_desired_question_count,
    validate_generated_test,
)
logger = logging.getLogger(__name__)

ADMIN_ROLES = {"manager", "admin"}
LEARNER_ROLES = {"employer"}

def is_admin_user(user: dict) -> bool:
    return user.get("role") in ADMIN_ROLES

def is_learner_user(user: dict) -> bool:
    return user.get("role") in LEARNER_ROLES

def require_admin_user(user: dict) -> None:
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Недостаточно прав для выполнения действия")

def require_learner_user(user: dict) -> None:
    if not is_learner_user(user):
        raise HTTPException(status_code=403, detail="Действие доступно только стажёру")

ALLOWED_FILE_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
}


def row_to_document(row: tuple) -> DocumentResponse:
    return DocumentResponse(
        id=row[0],
        company_id=row[1],
        uploaded_by=row[2],
        title=row[3],
        file_name=row[4],
        file_type=row[5],
        file_path=row[6],
        raw_text=row[7],
        status=row[8],
        created_at=row[9],
    )


def build_course_draft_response(
    *,
    course_id: int,
    version_id: int,
    title: str,
    description: str,
    status_value: str,
    modules_data: list[dict],
) -> CourseDraftResponse:
    modules = [
        CourseModuleResponse(
            id=module["id"],
            title=module["title"],
            order_index=module["order_index"],
            topics=[
                CourseTopicResponse(
                    id=topic["id"],
                    title=topic["title"],
                    content=topic["content"],
                    order_index=topic["order_index"],
                )
                for topic in module["topics"]
            ],
        )
        for module in modules_data
    ]

    return CourseDraftResponse(
        course_id=course_id,
        version_id=version_id,
        title=title,
        description=description,
        status=status_value,
        modules=modules,
    )

def fetch_course_draft_from_db(course_id: int, company_id: int) -> CourseDraftResponse:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, cv.id, c.title, COALESCE(c.description, ''), cv.status
                FROM courses c
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.id = %s AND c.company_id = %s
                """,
                (course_id, company_id),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Курс не найден")

            db_course_id, version_id, title, description, status_value = row

            cur.execute(
                """
                SELECT id, title, sort_order
                FROM course_modules
                WHERE course_version_id = %s
                ORDER BY sort_order
                """,
                (version_id,),
            )
            module_rows = cur.fetchall()

            modules_data: list[dict] = []

            for module_id, module_title, module_order in module_rows:
                cur.execute(
                    """
                    SELECT id, title, content, sort_order
                    FROM course_topics
                    WHERE module_id = %s
                    ORDER BY sort_order
                    """,
                    (module_id,),
                )
                topic_rows = cur.fetchall()

                topics_data = [
                    {
                        "id": topic_id,
                        "title": topic_title,
                        "content": topic_content,
                        "order_index": topic_order,
                    }
                    for topic_id, topic_title, topic_content, topic_order in topic_rows
                ]

                modules_data.append(
                    {
                        "id": module_id,
                        "title": module_title,
                        "order_index": module_order,
                        "topics": topics_data,
                    }
                )

    return build_course_draft_response(
        course_id=db_course_id,
        version_id=version_id,
        title=title,
        description=description,
        status_value=status_value,
        modules_data=modules_data,
    )


def _normalize_course_update_payload(payload: CourseDraftUpdateRequest) -> tuple[str, str, list[dict[str, Any]]]:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Название курса не может быть пустым")

    description = (payload.description or "").strip()
    normalized_modules: list[dict[str, Any]] = []

    for module_index, module in enumerate(payload.modules, start=1):
        module_title = module.title.strip()
        if not module_title:
            raise HTTPException(status_code=400, detail=f"У модуля #{module_index} нет названия")

        normalized_topics: list[dict[str, Any]] = []
        for topic_index, topic in enumerate(module.topics, start=1):
            topic_title = topic.title.strip()
            topic_content = (topic.content or "").strip()

            if not topic_title:
                raise HTTPException(
                    status_code=400,
                    detail=f"У темы #{topic_index} в модуле «{module_title}» нет названия",
                )
            if not topic_content:
                raise HTTPException(
                    status_code=400,
                    detail=f"У темы «{topic_title}» пустое содержимое",
                )

            normalized_topics.append(
                {
                    "title": topic_title,
                    "content": topic_content,
                    "order_index": topic_index,
                }
            )

        if not normalized_topics:
            raise HTTPException(
                status_code=400,
                detail=f"В модуле «{module_title}» должна остаться хотя бы одна тема",
            )

        normalized_modules.append(
            {
                "title": module_title,
                "order_index": module_index,
                "topics": normalized_topics,
            }
        )

    if not normalized_modules:
        raise HTTPException(status_code=400, detail="В курсе должен остаться хотя бы один модуль")

    return title, description, normalized_modules

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        ensure_bucket_exists()
    except Exception:
        pass
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chatbot_router)



@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    checks: dict[str, str] = {}
    has_errors = False

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc.__class__.__name__}"
        has_errors = True

    try:
        client = get_redis_client()
        client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"
        has_errors = True

    try:
        client = get_minio_client()
        client.bucket_exists(settings.minio_bucket)
        checks["minio"] = "ok"
    except Exception as exc:
        checks["minio"] = f"error: {exc.__class__.__name__}"
        has_errors = True

    status_text = "degraded" if has_errors else "ok"
    return HealthResponse(status=status_text, service="content-service", checks=checks)


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user_record = authenticate_user(payload.email, payload.password)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный e-mail или пароль",
        )

    access_token = create_access_token(user_record["id"])
    user = UserResponse(
        id=user_record["id"],
        email=user_record["email"],
        name=user_record["name"],
        role=user_record["role"],
        company_id=user_record["company_id"],
    )

    return LoginResponse(access_token=access_token, user=user)


@app.get("/api/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        company_id=current_user["company_id"],
    )


@app.post("/api/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> DocumentResponse:
    require_admin_user(current_user)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы PDF, DOCX и TXT",
        )

    file_type = ALLOWED_FILE_TYPES[ext]
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")

    object_name = f"company_{current_user['company_id']}/documents/{uuid4()}_{file.filename}"
    content_type = file.content_type or "application/octet-stream"

    upload_bytes_to_minio(
        object_name=object_name,
        content=file_bytes,
        content_type=content_type,
    )

    title = Path(file.filename).stem

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    company_id,
                    uploaded_by,
                    title,
                    file_name,
                    file_type,
                    file_path,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'uploaded')
                RETURNING id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at
                """,
                (
                    current_user["company_id"],
                    current_user["id"],
                    title,
                    file.filename,
                    file_type,
                    object_name,
                ),
            )
            row = cur.fetchone()
        conn.commit()

    return row_to_document(row)


@app.get("/api/documents", response_model=DocumentListResponse)
def list_documents(current_user: dict = Depends(get_current_user)) -> DocumentListResponse:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at
                FROM documents
                WHERE company_id = %s
                ORDER BY created_at DESC
                """,
                (current_user["company_id"],),
            )
            rows = cur.fetchall()

    return DocumentListResponse(items=[row_to_document(row) for row in rows])


@app.get("/api/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, current_user: dict = Depends(get_current_user)) -> DocumentResponse:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at
                FROM documents
                WHERE id = %s AND company_id = %s
                """,
                (document_id, current_user["company_id"]),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Документ не найден")

    return row_to_document(row)


@app.post("/api/documents/{document_id}/process", response_model=DocumentResponse)
def process_document(document_id: int, current_user: dict = Depends(get_current_user)) -> DocumentResponse:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at
                FROM documents
                WHERE id = %s AND company_id = %s
                """,
                (document_id, current_user["company_id"]),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Документ не найден")

            if row[8] == "processing":
                raise HTTPException(status_code=400, detail="Документ уже обрабатывается")

            cur.execute(
                """
                UPDATE documents
                SET status = 'processing'
                WHERE id = %s AND company_id = %s
                """,
                (document_id, current_user["company_id"]),
            )
        conn.commit()

    try:
        file_type = row[5]
        file_path = row[6]

        file_bytes = download_bytes_from_minio(object_name=file_path)
        extracted_text = extract_text_by_file_type(file_type, file_bytes)

        if not extracted_text.strip():
            raise ValueError("Не удалось извлечь текст из документа")

        chunks = split_text_into_chunks(extracted_text)

        if not chunks:
            raise ValueError("После обработки документа не удалось сформировать чанки")

        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s
                    """,
                    (document_id,),
                )

                for index, chunk_text in enumerate(chunks, start=1):
                    cur.execute(
                        """
                        INSERT INTO document_chunks (
                            document_id,
                            chunk_index,
                            chunk_text
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (document_id, index, chunk_text),
                    )

                cur.execute(
                    """
                    UPDATE documents
                    SET raw_text = %s,
                        status = 'processed'
                    WHERE id = %s AND company_id = %s
                    RETURNING id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at
                    """,
                    (
                        extracted_text,
                        document_id,
                        current_user["company_id"],
                    ),
                )
                updated_row = cur.fetchone()
            conn.commit()

        return row_to_document(updated_row)

    except Exception as exc:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = 'failed'
                    WHERE id = %s AND company_id = %s
                    """,
                    (document_id, current_user["company_id"]),
                )
            conn.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки документа: {str(exc)}",
        ) from exc

@app.get("/api/courses", response_model=CourseListResponse)
def list_courses(current_user: dict = Depends(get_current_user)) -> CourseListResponse:
    published_filter = "AND cv.status = 'published'" if is_learner_user(current_user) else ""

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT c.id, c.title, COALESCE(c.description, ''), cv.status
                FROM courses c
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.company_id = %s
                {published_filter}
                ORDER BY c.id DESC
                """,
                (current_user["company_id"],),
            )
            rows = cur.fetchall()

            course_ids = [row[0] for row in rows]
            doc_titles_by_course: dict[int, list[str]] = {course_id: [] for course_id in course_ids}

            if course_ids and is_admin_user(current_user):
                cur.execute(
                    """
                    SELECT l.course_id, d.title
                    FROM course_document_links l
                    JOIN documents d ON d.id = l.document_id
                    WHERE l.course_id = ANY(%s)
                    ORDER BY l.course_id, d.id
                    """,
                    (course_ids,),
                )
                link_rows = cur.fetchall()

                for linked_course_id, doc_title in link_rows:
                    doc_titles_by_course.setdefault(linked_course_id, []).append(doc_title)

    return CourseListResponse(
        items=[
            CourseSummaryResponse(
                course_id=course_id,
                title=title,
                description=description,
                status=status_value,
                source_documents=doc_titles_by_course.get(course_id, []),
            )
            for course_id, title, description, status_value in rows
        ]
    )

@app.get("/api/courses/{course_id}", response_model=CourseDraftResponse)
def get_course(course_id: int, current_user: dict = Depends(get_current_user)) -> CourseDraftResponse:
    draft = fetch_course_draft_from_db(course_id, current_user["company_id"])
    if is_learner_user(current_user) and draft.status != "published":
        raise HTTPException(status_code=404, detail="Курс не найден")
    return draft

@app.put("/api/courses/{course_id}", response_model=CourseDraftResponse)
def update_course(
    course_id: int,
    payload: CourseDraftUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> CourseDraftResponse:
    require_admin_user(current_user)
    title, description, normalized_modules = _normalize_course_update_payload(payload)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, cv.id
                FROM courses c
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.id = %s AND c.company_id = %s
                """,
                (course_id, current_user["company_id"]),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Курс не найден")

            _course_id, version_id = row

            cur.execute(
                """
                UPDATE courses
                SET title = %s,
                    description = %s,
                    status = 'draft'
                WHERE id = %s AND company_id = %s
                """,
                (title, description, course_id, current_user["company_id"]),
            )

            cur.execute(
                """
                UPDATE course_versions
                SET status = 'draft',
                    notes = %s
                WHERE id = %s
                """,
                ("Черновик курса был обновлён вручную", version_id),
            )

            cur.execute(
                """
                DELETE FROM course_topics
                WHERE module_id IN (
                    SELECT id
                    FROM course_modules
                    WHERE course_version_id = %s
                )
                """,
                (version_id,),
            )

            cur.execute(
                """
                DELETE FROM course_modules
                WHERE course_version_id = %s
                """,
                (version_id,),
            )

            for module in normalized_modules:
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
                    (version_id, module["title"], module["order_index"]),
                )
                module_id = cur.fetchone()[0]

                for topic in module["topics"]:
                    cur.execute(
                        """
                        INSERT INTO course_topics (
                            module_id,
                            title,
                            content,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (module_id, topic["title"], topic["content"], topic["order_index"]),
                    )

        conn.commit()

    return fetch_course_draft_from_db(course_id, current_user["company_id"])


@app.post("/api/courses/{course_id}/status", response_model=CourseDraftResponse)
def update_course_status(
    course_id: int,
    payload: CourseStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> CourseDraftResponse:
    require_admin_user(current_user)
    notes_by_status = {
        "draft": "Статус курса переведен в черновик",
        "published": "Курс опубликован",
    }

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, cv.id
                FROM courses c
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.id = %s AND c.company_id = %s
                """,
                (course_id, current_user["company_id"]),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Курс не найден")

            _course_id, version_id = row

            cur.execute(
                """
                UPDATE courses
                SET status = %s
                WHERE id = %s AND company_id = %s
                """,
                (payload.status, course_id, current_user["company_id"]),
            )

            cur.execute(
                """
                UPDATE course_versions
                SET status = %s,
                    notes = %s
                WHERE id = %s
                """,
                (payload.status, notes_by_status[payload.status], version_id),
            )

        conn.commit()

    return fetch_course_draft_from_db(course_id, current_user["company_id"])


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int, current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM courses
                WHERE id = %s AND company_id = %s
                """,
                (course_id, current_user["company_id"]),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Курс не найден")

            cur.execute(
                """
                DELETE FROM course_topics
                WHERE module_id IN (
                    SELECT cm.id
                    FROM course_modules cm
                    JOIN course_versions cv ON cv.id = cm.course_version_id
                    WHERE cv.course_id = %s
                )
                """,
                (course_id,),
            )

            cur.execute(
                """
                DELETE FROM course_modules
                WHERE course_version_id IN (
                    SELECT id
                    FROM course_versions
                    WHERE course_id = %s
                )
                """,
                (course_id,),
            )

            cur.execute(
                """
                DELETE FROM course_document_links
                WHERE course_id = %s
                """,
                (course_id,),
            )

            cur.execute(
                """
                DELETE FROM course_versions
                WHERE course_id = %s
                """,
                (course_id,),
            )

            cur.execute(
                """
                DELETE FROM courses
                WHERE id = %s AND company_id = %s
                """,
                (course_id, current_user["company_id"]),
            )

        conn.commit()

    return {"message": "Курс удалён"}

@app.post("/api/courses/generate-draft", response_model=CourseDraftResponse)
def generate_course_draft(
    payload: CourseGenerateRequest,
    current_user: dict = Depends(get_current_user),
) -> CourseDraftResponse:
    require_admin_user(current_user)

    title = payload.title.strip()
    document_ids = payload.document_ids

    if not title:
        raise HTTPException(status_code=400, detail="Название курса обязательно")

    if not document_ids:
        raise HTTPException(status_code=400, detail="Нужно выбрать хотя бы один документ")

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, title, raw_text, status
                FROM documents
                WHERE company_id = %s
                  AND id = ANY(%s)
                ORDER BY created_at DESC
                """,
                (current_user["company_id"], document_ids),
            )
            rows = cur.fetchall()

            if len(rows) != len(document_ids):
                raise HTTPException(status_code=404, detail="Часть документов не найдена")

            not_processed = [row[1] for row in rows if row[3] != "processed" or not (row[2] or "").strip()]
            if not_processed:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Перед созданием курса нужно обработать все выбранные документы. "
                        f"Не обработаны: {', '.join(not_processed)}"
                    ),
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
    desired_structure_text = (payload.desired_structure or "").strip()
    if desired_structure_text:
        try:
            llm_provider = get_llm_provider()
        except LLMProviderError:
            llm_provider = None

    try:
        generated = build_course_draft_from_documents(
            course_title=title,
            structured_documents=structured_documents,
            additional_requirements=payload.additional_requirements,
            desired_structure=payload.desired_structure,
            llm_provider=llm_provider,
        )
        validated = validate_generated_course(generated)
    except ValueError as exc:
        logger.exception("Ошибка генерации курса")
        raise HTTPException(status_code=500, detail=f"Не удалось сгенерировать курс: {exc}") from exc

    modules_data: list[dict] = []

    try:
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
                        current_user["company_id"],
                        validated["title"],
                        validated["description"],
                        current_user["id"],
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
                        current_user["id"],
                        "Черновик курса собран строго по структуре документов; optional-поля применены как исключения и настройки блока Важно запомнить",
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
                        (
                            version_id,
                            module["title"],
                            module_index,
                        ),
                    )
                    module_id = cur.fetchone()[0]

                    topics_data: list[dict] = []
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
                            (
                                module_id,
                                topic["title"],
                                topic["content"],
                                topic_index,
                            ),
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
    except Exception as exc:
        logger.exception("Ошибка сохранения курса в БД")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения курса в БД: {exc}") from exc

    return build_course_draft_response(
        course_id=course_id,
        version_id=version_id,
        title=validated["title"],
        description=validated["description"],
        status_value="draft",
        modules_data=modules_data,
    )

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    require_admin_user(current_user)
    file_path: str | None = None

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.title, cv.status
                FROM courses c
                LEFT JOIN course_document_links l ON l.course_id = c.id
                LEFT JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE c.company_id = %s
                  AND (l.document_id = %s OR cv.generated_from_document_id = %s)
                LIMIT 1
                """,
                (current_user["company_id"], document_id, document_id),
            )
            linked_course = cur.fetchone()

            if linked_course:
                _, course_title, course_status = linked_course
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Документ нельзя удалить, потому что на его основе уже есть курс "
                        f"«{course_title}» (статус: {course_status}). "
                        f"Сначала удалите курс."
                    ),
                )

            cur.execute(
                """
                SELECT id, file_path, status
                FROM documents
                WHERE id = %s AND company_id = %s
                """,
                (document_id, current_user["company_id"]),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Документ не найден")

            _, file_path, status_value = row

            if status_value == "processing":
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя удалить документ во время обработки",
                )

            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s
                """,
                (document_id,),
            )

            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s AND company_id = %s
                """,
                (document_id, current_user["company_id"]),
            )

        conn.commit()

    if file_path:
        try:
            delete_object_from_minio(object_name=file_path)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                # не ломаем удаление документа, даже если проблема только в хранилище
                pass

    return {"message": "Документ удалён"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "MentorAI content-service bootstrap is running",
        "health": "/health",
        "docs": "/docs",
    }


def build_test_draft_response(
    *,
    test_id: int,
    version_id: int,
    title: str,
    status_value: str,
    course_id: int,
    course_title: str,
    questions_data: list[dict],
) -> TestDraftResponse:
    questions = [
        TestQuestionResponse(
            id=question["id"],
            question_text=question["question_text"],
            order_index=question["order_index"],
            options=[
                TestOptionResponse(
                    id=option["id"],
                    text=option["text"],
                    is_correct=option["is_correct"],
                    order_index=option["order_index"],
                )
                for option in question["options"]
            ],
        )
        for question in questions_data
    ]

    return TestDraftResponse(
        test_id=test_id,
        version_id=version_id,
        title=title,
        status=status_value,
        course_id=course_id,
        course_title=course_title,
        question_count=len(questions),
        questions=questions,
    )


def fetch_test_draft_from_db(test_id: int, company_id: int) -> TestDraftResponse:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, tv.id, t.title, tv.status, c.id, c.title
                FROM tests t
                JOIN test_versions tv
                  ON tv.test_id = t.id
                 AND tv.version_number = t.current_version_no
                JOIN courses c ON c.id = t.course_id
                WHERE t.id = %s AND t.company_id = %s
                """,
                (test_id, company_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Тест не найден")

            db_test_id, version_id, title, status_value, course_id, course_title = row

            cur.execute(
                """
                SELECT id, question_text, sort_order
                FROM questions
                WHERE test_version_id = %s
                ORDER BY sort_order
                """,
                (version_id,),
            )
            question_rows = cur.fetchall()

            questions_data: list[dict] = []
            for question_id, question_text, order_index in question_rows:
                cur.execute(
                    """
                    SELECT id, option_text, is_correct, sort_order
                    FROM question_options
                    WHERE question_id = %s
                    ORDER BY sort_order
                    """,
                    (question_id,),
                )
                option_rows = cur.fetchall()
                questions_data.append(
                    {
                        "id": question_id,
                        "question_text": question_text,
                        "order_index": order_index,
                        "options": [
                            {
                                "id": option_id,
                                "text": option_text,
                                "is_correct": is_correct,
                                "order_index": option_order,
                            }
                            for option_id, option_text, is_correct, option_order in option_rows
                        ],
                    }
                )

    return build_test_draft_response(
        test_id=db_test_id,
        version_id=version_id,
        title=title,
        status_value=status_value,
        course_id=course_id,
        course_title=course_title,
        questions_data=questions_data,
    )


def _normalize_test_title(title: str) -> str:
    value = title.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Название теста не может быть пустым")
    return value


def _normalize_test_question_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Текст вопроса не может быть пустым")
    return value


def _normalize_test_option_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Текст варианта ответа не может быть пустым")
    return value


def _validate_test_update_payload(payload: TestDraftUpdateRequest) -> None:
    _normalize_test_title(payload.title)
    if not payload.questions:
        raise HTTPException(status_code=400, detail="В тесте должен быть хотя бы один вопрос")
    for index, question in enumerate(payload.questions, start=1):
        _normalize_test_question_text(question.question_text)
        if len(question.options) < 2:
            raise HTTPException(status_code=400, detail=f"Вопрос {index} должен содержать минимум два варианта ответа")
        correct_count = 0
        for option in question.options:
            _normalize_test_option_text(option.text)
            if option.is_correct:
                correct_count += 1
        if correct_count != 1:
            raise HTTPException(status_code=400, detail=f"Вопрос {index} должен содержать ровно один правильный ответ")


@app.get("/api/tests", response_model=TestListResponse)
def list_tests(current_user: dict = Depends(get_current_user)) -> TestListResponse:
    published_filter = "AND tv.status = 'published' AND c.status = 'published'" if is_learner_user(current_user) else ""

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT t.id,
                       t.title,
                       tv.status,
                       c.id,
                       c.title,
                       COUNT(DISTINCT q.id),
                       MAX(ta.percent)
                FROM tests t
                JOIN test_versions tv
                  ON tv.test_id = t.id
                 AND tv.version_number = t.current_version_no
                JOIN courses c ON c.id = t.course_id
                LEFT JOIN questions q ON q.test_version_id = tv.id
                LEFT JOIN test_attempts ta
                  ON ta.test_id = t.id
                 AND ta.user_id = %s
                 AND ta.status = 'completed'
                WHERE t.company_id = %s
                {published_filter}
                GROUP BY t.id, t.title, tv.status, c.id, c.title
                ORDER BY t.updated_at DESC, t.id DESC
                """,
                (current_user["id"], current_user["company_id"]),
            )
            rows = cur.fetchall()

    items = [
        TestSummaryResponse(
            test_id=row[0],
            title=row[1],
            status=row[2],
            course_id=row[3],
            course_title=row[4],
            question_count=row[5],
            best_attempt_percent=float(row[6]) if row[6] is not None else None,
        )
        for row in rows
    ]
    return TestListResponse(items=items)


@app.get("/api/tests/{test_id}", response_model=TestDraftResponse)
def get_test(test_id: int, current_user: dict = Depends(get_current_user)) -> TestDraftResponse:
    draft = fetch_test_draft_from_db(test_id, current_user["company_id"])
    if is_learner_user(current_user):
        if draft.status != "published":
            raise HTTPException(status_code=404, detail="Тест не найден")
        course = fetch_course_draft_from_db(draft.course_id, current_user["company_id"])
        if course.status != "published":
            raise HTTPException(status_code=404, detail="Тест не найден")
        for question in draft.questions:
            for option in question.options:
                option.is_correct = False
    return draft




def _fetch_published_test_context_for_attempt(test_id: int, company_id: int) -> tuple[int, int, str, int, str]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, tv.id, t.title, c.id, c.title
                FROM tests t
                JOIN test_versions tv
                  ON tv.test_id = t.id
                 AND tv.version_number = t.current_version_no
                JOIN courses c ON c.id = t.course_id
                JOIN course_versions cv
                  ON cv.course_id = c.id
                 AND cv.version_number = c.current_version_no
                WHERE t.id = %s
                  AND t.company_id = %s
                  AND t.status = 'published'
                  AND tv.status = 'published'
                  AND c.status = 'published'
                  AND cv.status = 'published'
                LIMIT 1
                """,
                (test_id, company_id),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Опубликованный тест не найден")

    return row[0], row[1], row[2], row[3], row[4]


def _fetch_attempt_questions_for_version(test_version_id: int) -> list[dict]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT q.id, q.question_text, q.sort_order, q.weight
                FROM questions q
                WHERE q.test_version_id = %s
                ORDER BY q.sort_order
                """,
                (test_version_id,),
            )
            question_rows = cur.fetchall()

            questions: list[dict] = []
            for question_id, question_text, order_index, weight in question_rows:
                cur.execute(
                    """
                    SELECT id, option_text, is_correct, sort_order
                    FROM question_options
                    WHERE question_id = %s
                    ORDER BY sort_order
                    """,
                    (question_id,),
                )
                option_rows = cur.fetchall()
                questions.append(
                    {
                        "id": question_id,
                        "question_text": question_text,
                        "order_index": order_index,
                        "weight": float(weight),
                        "options": [
                            {
                                "id": option_id,
                                "text": option_text,
                                "is_correct": is_correct,
                                "order_index": option_order,
                            }
                            for option_id, option_text, is_correct, option_order in option_rows
                        ],
                    }
                )
    return questions


def _build_attempt_start_response(*, attempt_id: int, attempt_no: int, test_id: int, version_id: int, title: str, course_id: int, course_title: str):
    questions_data = _fetch_attempt_questions_for_version(version_id)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT started_at FROM test_attempts WHERE id = %s", (attempt_id,))
            started_at = cur.fetchone()[0]

    return TestAttemptStartResponse(
        attempt_id=attempt_id,
        attempt_no=attempt_no,
        test_id=test_id,
        title=title,
        course_id=course_id,
        course_title=course_title,
        question_count=len(questions_data),
        started_at=started_at,
        questions=[
            LearnerTestQuestionResponse(
                id=question["id"],
                question_text=question["question_text"],
                order_index=question["order_index"],
                options=[
                    LearnerTestOptionResponse(
                        id=option["id"],
                        text=option["text"],
                        order_index=option["order_index"],
                    )
                    for option in question["options"]
                ],
            )
            for question in questions_data
        ],
    )


def _fetch_attempt_result_from_db(attempt_id: int, user_id: int, company_id: int) -> TestAttemptResultResponse:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id,
                       a.attempt_no,
                       a.started_at,
                       a.completed_at,
                       a.score,
                       a.percent,
                       a.status,
                       t.id,
                       t.title,
                       c.id,
                       c.title,
                       tv.id
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                JOIN test_versions tv ON tv.id = a.test_version_id
                JOIN courses c ON c.id = t.course_id
                WHERE a.id = %s
                  AND a.user_id = %s
                  AND t.company_id = %s
                LIMIT 1
                """,
                (attempt_id, user_id, company_id),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Попытка не найдена")

            db_attempt_id, attempt_no, started_at, completed_at, score, percent, status_value, test_id, title, course_id, course_title, version_id = row
            questions_data = _fetch_attempt_questions_for_version(version_id)

            correct_answers = 0
            result_questions: list[AttemptResultQuestionResponse] = []

            for question in questions_data:
                cur.execute(
                    """
                    SELECT selected_option_id, COALESCE(is_correct, FALSE)
                    FROM question_responses
                    WHERE attempt_id = %s AND question_id = %s
                    LIMIT 1
                    """,
                    (attempt_id, question["id"]),
                )
                response_row = cur.fetchone()
                selected_option_id = response_row[0] if response_row else None
                is_correct = bool(response_row[1]) if response_row else False
                if is_correct:
                    correct_answers += 1

                result_questions.append(
                    AttemptResultQuestionResponse(
                        id=question["id"],
                        question_text=question["question_text"],
                        order_index=question["order_index"],
                        selected_option_id=selected_option_id,
                        is_correct=is_correct,
                        options=[
                            AttemptResultOptionResponse(
                                id=option["id"],
                                text=option["text"],
                                order_index=option["order_index"],
                                is_selected=(option["id"] == selected_option_id),
                                is_correct=option["is_correct"],
                            )
                            for option in question["options"]
                        ],
                    )
                )

    return TestAttemptResultResponse(
        attempt_id=db_attempt_id,
        attempt_no=attempt_no,
        test_id=test_id,
        title=title,
        course_id=course_id,
        course_title=course_title,
        question_count=len(result_questions),
        correct_answers=correct_answers,
        score=float(score),
        percent=float(percent),
        status=status_value,
        started_at=started_at,
        completed_at=completed_at,
        questions=result_questions,
    )


@app.post("/api/tests/{test_id}/attempts", response_model=TestAttemptStartResponse)
def start_test_attempt(test_id: int, current_user: dict = Depends(get_current_user)) -> TestAttemptStartResponse:
    require_learner_user(current_user)
    test_id, version_id, title, course_id, course_title = _fetch_published_test_context_for_attempt(
        test_id,
        current_user["company_id"],
    )

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE test_attempts
                SET status = 'abandoned', completed_at = NOW()
                WHERE user_id = %s AND test_id = %s AND status = 'started'
                """,
                (current_user["id"], test_id),
            )
            cur.execute(
                """
                SELECT COALESCE(MAX(attempt_no), 0) + 1
                FROM test_attempts
                WHERE user_id = %s AND test_id = %s
                """,
                (current_user["id"], test_id),
            )
            attempt_no = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO test_attempts (user_id, test_id, test_version_id, attempt_no, status)
                VALUES (%s, %s, %s, %s, 'started')
                RETURNING id
                """,
                (current_user["id"], test_id, version_id, attempt_no),
            )
            attempt_id = cur.fetchone()[0]
        conn.commit()

    return _build_attempt_start_response(
        attempt_id=attempt_id,
        attempt_no=attempt_no,
        test_id=test_id,
        version_id=version_id,
        title=title,
        course_id=course_id,
        course_title=course_title,
    )


@app.post("/api/attempts/{attempt_id}/finish", response_model=TestAttemptResultResponse)
def finish_test_attempt(
    attempt_id: int,
    payload: TestAttemptFinishRequest,
    current_user: dict = Depends(get_current_user),
) -> TestAttemptResultResponse:
    require_learner_user(current_user)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.test_id, a.test_version_id, a.status, t.company_id
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE a.id = %s AND a.user_id = %s
                LIMIT 1
                """,
                (attempt_id, current_user["id"]),
            )
            attempt_row = cur.fetchone()

            if not attempt_row:
                raise HTTPException(status_code=404, detail="Попытка не найдена")

            _, test_id, test_version_id, attempt_status, company_id = attempt_row
            if company_id != current_user["company_id"]:
                raise HTTPException(status_code=404, detail="Попытка не найдена")
            if attempt_status != "started":
                raise HTTPException(status_code=400, detail="Попытка уже завершена")

            questions_data = _fetch_attempt_questions_for_version(test_version_id)
            if not questions_data:
                raise HTTPException(status_code=400, detail="В тесте нет вопросов")

            answers_by_question_id = {answer.question_id: answer.selected_option_id for answer in payload.answers}
            valid_question_ids = {question["id"] for question in questions_data}

            invalid_question_ids = [question_id for question_id in answers_by_question_id if question_id not in valid_question_ids]
            if invalid_question_ids:
                raise HTTPException(status_code=400, detail="Обнаружены ответы на вопросы, которых нет в тесте")

            total_weight = 0.0
            earned_score = 0.0
            correct_answers = 0

            cur.execute("DELETE FROM question_responses WHERE attempt_id = %s", (attempt_id,))

            for question in questions_data:
                question_id = question["id"]
                selected_option_id = answers_by_question_id.get(question_id)
                valid_option_ids = {option["id"] for option in question["options"]}
                if selected_option_id is not None and selected_option_id not in valid_option_ids:
                    raise HTTPException(status_code=400, detail="Обнаружен вариант ответа, не принадлежащий вопросу")

                correct_option = next((option for option in question["options"] if option["is_correct"]), None)
                is_correct = selected_option_id is not None and correct_option is not None and selected_option_id == correct_option["id"]
                question_weight = float(question["weight"])
                total_weight += question_weight
                current_score = question_weight if is_correct else 0.0
                earned_score += current_score
                if is_correct:
                    correct_answers += 1

                cur.execute(
                    """
                    INSERT INTO question_responses (
                        attempt_id,
                        question_id,
                        selected_option_id,
                        answer_text,
                        is_correct,
                        earned_score
                    )
                    VALUES (%s, %s, %s, NULL, %s, %s)
                    """,
                    (attempt_id, question_id, selected_option_id, is_correct, current_score),
                )

            percent = round((earned_score / total_weight) * 100, 2) if total_weight else 0.0

            cur.execute(
                """
                UPDATE test_attempts
                SET completed_at = NOW(),
                    score = %s,
                    percent = %s,
                    status = 'completed'
                WHERE id = %s
                """,
                (earned_score, percent, attempt_id),
            )
        conn.commit()

    return _fetch_attempt_result_from_db(attempt_id, current_user["id"], current_user["company_id"])


@app.get("/api/attempts/{attempt_id}/result", response_model=TestAttemptResultResponse)
def get_attempt_result(attempt_id: int, current_user: dict = Depends(get_current_user)) -> TestAttemptResultResponse:
    require_learner_user(current_user)
    return _fetch_attempt_result_from_db(attempt_id, current_user["id"], current_user["company_id"])


@app.put("/api/tests/{test_id}", response_model=TestDraftResponse)
def update_test_draft(test_id: int, payload: TestDraftUpdateRequest, current_user: dict = Depends(get_current_user)) -> TestDraftResponse:
    require_admin_user(current_user)
    _validate_test_update_payload(payload)
    title = _normalize_test_title(payload.title)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, tv.id
                FROM tests t
                JOIN test_versions tv
                  ON tv.test_id = t.id
                 AND tv.version_number = t.current_version_no
                WHERE t.id = %s AND t.company_id = %s
                """,
                (test_id, current_user["company_id"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Тест не найден")
            _, version_id = row

            cur.execute("UPDATE tests SET title = %s, updated_at = now() WHERE id = %s", (title, test_id))
            cur.execute("SELECT id FROM questions WHERE test_version_id = %s", (version_id,))
            question_ids = [r[0] for r in cur.fetchall()]
            if question_ids:
                cur.execute("DELETE FROM question_options WHERE question_id = ANY(%s)", (question_ids,))
            cur.execute("DELETE FROM questions WHERE test_version_id = %s", (version_id,))

            for question_index, question in enumerate(payload.questions, start=1):
                cur.execute(
                    """
                    INSERT INTO questions (test_version_id, topic_id, question_text, question_type, weight, sort_order)
                    VALUES (%s, NULL, %s, 'single_choice', 1.0, %s)
                    RETURNING id
                    """,
                    (version_id, _normalize_test_question_text(question.question_text), question_index),
                )
                question_id = cur.fetchone()[0]
                for option_index, option in enumerate(question.options, start=1):
                    cur.execute(
                        """
                        INSERT INTO question_options (question_id, option_text, is_correct, sort_order)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (question_id, _normalize_test_option_text(option.text), option.is_correct, option_index),
                    )
        conn.commit()

    return fetch_test_draft_from_db(test_id, current_user["company_id"])


@app.post("/api/tests/{test_id}/status", response_model=TestDraftResponse)
def update_test_status(test_id: int, payload: TestStatusUpdateRequest, current_user: dict = Depends(get_current_user)) -> TestDraftResponse:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, tv.id
                FROM tests t
                JOIN test_versions tv
                  ON tv.test_id = t.id
                 AND tv.version_number = t.current_version_no
                WHERE t.id = %s AND t.company_id = %s
                """,
                (test_id, current_user["company_id"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Тест не найден")

            _, version_id = row

            cur.execute("UPDATE tests SET status = %s, updated_at = now() WHERE id = %s", (payload.status, test_id))
            cur.execute("UPDATE test_versions SET status = %s WHERE id = %s", (payload.status, version_id))
        conn.commit()

    return fetch_test_draft_from_db(test_id, current_user["company_id"])


@app.delete("/api/tests/{test_id}")
def delete_test(test_id: int, current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    require_admin_user(current_user)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tests WHERE id = %s AND company_id = %s", (test_id, current_user["company_id"]))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Тест не найден")
        conn.commit()
    return {"message": "Тест удалён"}


@app.post("/api/tests/generate-draft", response_model=TestDraftResponse)
def generate_test_draft(payload: TestGenerateRequest, current_user: dict = Depends(get_current_user)) -> TestDraftResponse:
    require_admin_user(current_user)
    title = _normalize_test_title(payload.title)
    question_count = parse_desired_question_count(payload.desired_question_count)

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
                (payload.course_id, current_user["company_id"]),
            )
            course_row = cur.fetchone()
            if not course_row:
                raise HTTPException(status_code=400, detail="Можно выбрать только курс вашей компании, созданный на основе документов")

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
        raise HTTPException(status_code=400, detail="В выбранном курсе нет тем для генерации теста")

    modules_map: dict[str, dict[str, Any]] = {}
    for module_title, topic_id, topic_title, topic_content, module_order, topic_order in topic_rows:
        key = f"{module_order}:{module_title}"
        modules_map.setdefault(key, {"title": module_title, "order_index": module_order, "topics": []})
        modules_map[key]["topics"].append({
            "id": topic_id,
            "title": topic_title,
            "content": topic_content,
            "order_index": topic_order,
        })

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
        raise HTTPException(status_code=400, detail=f"Не удалось сгенерировать тест: {exc}") from exc

    questions_data: list[dict] = []
    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tests (company_id, course_id, title, test_type, status, current_version_no, created_by)
                    VALUES (%s, %s, %s, 'course', 'draft', 1, %s)
                    RETURNING id
                    """,
                    (current_user["company_id"], course_id, title, current_user["id"]),
                )
                test_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO test_versions (test_id, version_number, created_by, status)
                    VALUES (%s, 1, %s, 'draft')
                    RETURNING id
                    """,
                    (test_id, current_user["id"]),
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

                    options_data = []
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
                        options_data.append({
                            "id": option_id,
                            "text": option_text,
                            "is_correct": is_correct,
                            "order_index": option_index,
                        })

                    questions_data.append({
                        "id": question_id,
                        "question_text": question["question_text"],
                        "order_index": question_index,
                        "options": options_data,
                    })
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения теста в БД: {exc}") from exc

    return build_test_draft_response(
        test_id=test_id,
        version_id=version_id,
        title=title,
        status_value='draft',
        course_id=course_id,
        course_title=course_title,
        questions_data=questions_data,
    )
