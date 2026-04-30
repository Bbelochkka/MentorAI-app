from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .infrastructure import get_postgres_connection
from .security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ADMIN_ROLES = {"manager", "admin"}


class AnalyticsEmployeeCardResponse(BaseModel):
    employee_id: int
    full_name: str
    email: str
    hire_date: date
    role_label: str
    adaptation_index: float
    material_progress_percent: float
    tests_completed_percent: float
    correct_answers_percent: float
    dialog_score_percent: float


class AnalyticsEmployeeListResponse(BaseModel):
    items: list[AnalyticsEmployeeCardResponse]


class AnalyticsCourseResultResponse(BaseModel):
    course_id: int
    course_title: str
    correct_answers_percent: float


class AnalyticsTypicalErrorResponse(BaseModel):
    question_id: int
    question_text: str
    course_title: str
    wrong_answers: int
    total_answers: int
    error_rate: float


class AnalyticsEmployeeDetailResponse(BaseModel):
    employee: AnalyticsEmployeeCardResponse
    completed_tests_count: int
    completed_dialogs_count: int
    course_results: list[AnalyticsCourseResultResponse]
    typical_errors: list[AnalyticsTypicalErrorResponse]
class AnalyticsTestCardResponse(BaseModel):
    test_id: int
    title: str
    course_id: int
    course_title: str
    question_count: int
    attempts_count: int
    unique_employees_count: int
    avg_best_percent: float


class AnalyticsTestListResponse(BaseModel):
    items: list[AnalyticsTestCardResponse]


class AnalyticsTestParticipantResponse(BaseModel):
    employee_id: int
    full_name: str
    email: str
    best_percent: float
    attempts_count: int
    last_completed_at: str | None = None


class AnalyticsTestTopErrorResponse(BaseModel):
    question_id: int
    question_text: str
    wrong_answers: int
    total_answers: int
    error_rate: float


class AnalyticsTestDetailResponse(BaseModel):
    test_id: int
    title: str
    course_id: int
    course_title: str
    question_count: int
    attempts_count: int
    unique_employees_count: int
    avg_best_percent: float
    participants: list[AnalyticsTestParticipantResponse]
    top_errors: list[AnalyticsTestTopErrorResponse]

def require_manager_user(user: dict) -> None:
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Раздел аналитики доступен только руководителю")
    
def get_supervisor_scope(user: dict) -> int | None:
    if user.get("role") == "manager":
        return user["id"]
    return None


def role_label(role_code: str) -> str:
    mapping = {
        "employer": "Менеджер по продажам",
        "manager": "Руководитель",
        "admin": "Администратор",
    }
    return mapping.get(role_code, role_code)


def build_employee_card(row: tuple) -> AnalyticsEmployeeCardResponse:
    return AnalyticsEmployeeCardResponse(
        employee_id=row[0],
        full_name=row[1],
        email=row[2],
        hire_date=row[3],
        role_label=role_label(row[4]),
        material_progress_percent=float(row[5] or 0),
        tests_completed_percent=float(row[6] or 0),
        correct_answers_percent=float(row[7] or 0),
        dialog_score_percent=float(row[8] or 0),
        adaptation_index=float(row[9] or 0),
    )


SORT_SQL = {
    "hire_date": "COALESCE(u.hire_date, u.created_at::date) DESC, u.full_name ASC",
    "adaptation": "adaptation_index DESC, COALESCE(u.hire_date, u.created_at::date) DESC, u.full_name ASC",
    "correct_answers": "correct_answers_percent DESC, adaptation_index DESC, u.full_name ASC",
}

def fetch_employee_metric_rows(
    *,
    company_id: int,
    search: str | None,
    sort: Literal["hire_date", "adaptation", "correct_answers"],
    employee_id: int | None = None,
    supervisor_scope_id: int | None = None,
) -> list[tuple]:
    search_pattern = f"%{(search or '').strip()}%" if (search or "").strip() else "%"
    sort_sql = SORT_SQL[sort]

    scope_filter_sql = ""
    employee_filter_sql = ""

    params: list[object] = [
        company_id,
        company_id,
        company_id,
        company_id,
        search_pattern,
    ]

    if supervisor_scope_id is not None:
        scope_filter_sql = "AND u.supervisor_id = %s"
        params.append(supervisor_scope_id)

    if employee_id is not None:
        employee_filter_sql = "AND u.id = %s"
        params.append(employee_id)

    query = f"""
    WITH published_courses AS (
        SELECT c.id
        FROM courses c
        WHERE c.company_id = %s
          AND c.status = 'published'
    ),
    published_tests AS (
        SELECT t.id, t.course_id
        FROM tests t
        WHERE t.company_id = %s
          AND t.status = 'published'
    ),
    best_tests AS (
        SELECT
            ta.user_id,
            ta.test_id,
            MAX(ta.percent) AS best_percent
        FROM test_attempts ta
        JOIN published_tests pt ON pt.id = ta.test_id
        WHERE ta.status = 'completed'
        GROUP BY ta.user_id, ta.test_id
    ),
    test_metrics AS (
        SELECT
            bt.user_id,
            ROUND(COALESCE(AVG(bt.best_percent), 0)::numeric, 2) AS correct_answers_percent,
            ROUND(
                COALESCE(
                    COUNT(DISTINCT bt.test_id) * 100.0
                    / NULLIF((SELECT COUNT(*) FROM published_tests), 0),
                    0
                )::numeric,
                2
            ) AS tests_completed_percent,
            COUNT(DISTINCT bt.test_id) AS completed_tests_count,
            COUNT(DISTINCT pt.course_id) AS completed_courses_count
        FROM best_tests bt
        JOIN published_tests pt ON pt.id = bt.test_id
        GROUP BY bt.user_id
    ),
    material_metrics AS (
        SELECT
            tm.user_id,
            ROUND(
                COALESCE(
                    tm.completed_courses_count * 100.0
                    / NULLIF((SELECT COUNT(*) FROM published_courses), 0),
                    0
                )::numeric,
                2
            ) AS material_progress_percent
        FROM test_metrics tm
    ),
    dialog_metrics AS (
        SELECT
            s.user_id,
            ROUND(COALESCE(AVG(COALESCE(r.total_score, s.total_score, 0)), 0)::numeric, 2) AS dialog_score_percent,
            COUNT(*) AS completed_dialogs_count
        FROM dialog_trainer_sessions s
        LEFT JOIN dialog_trainer_results r ON r.session_id = s.id
        WHERE s.company_id = %s
          AND s.status = 'completed'
        GROUP BY s.user_id
    )
    SELECT
        u.id,
        u.full_name,
        u.email,
        COALESCE(u.hire_date, u.created_at::date) AS hire_date,
        rl.code AS role_code,
        COALESCE(mm.material_progress_percent, 0) AS material_progress_percent,
        COALESCE(tm.tests_completed_percent, 0) AS tests_completed_percent,
        COALESCE(tm.correct_answers_percent, 0) AS correct_answers_percent,
        COALESCE(dm.dialog_score_percent, 0) AS dialog_score_percent,
        ROUND((
            COALESCE(mm.material_progress_percent, 0) * 0.3 +
            COALESCE(tm.correct_answers_percent, 0) * 0.3 +
            COALESCE(dm.dialog_score_percent, 0) * 0.4
        )::numeric, 2) AS adaptation_index,
        COALESCE(tm.completed_tests_count, 0) AS completed_tests_count,
        COALESCE(dm.completed_dialogs_count, 0) AS completed_dialogs_count
    FROM users u
    JOIN roles rl ON rl.id = u.role_id
    LEFT JOIN test_metrics tm ON tm.user_id = u.id
    LEFT JOIN material_metrics mm ON mm.user_id = u.id
    LEFT JOIN dialog_metrics dm ON dm.user_id = u.id
    WHERE u.company_id = %s
      AND u.is_active = TRUE
      AND rl.code = 'employer'
      AND LOWER(u.full_name) LIKE LOWER(%s)
      {scope_filter_sql}
      {employee_filter_sql}
    ORDER BY {sort_sql}
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()  

def fetch_test_participants(company_id: int, test_id: int) -> list[AnalyticsTestParticipantResponse]:
    query = """
    WITH completed_attempts AS (
        SELECT
            ta.user_id,
            ta.test_id,
            ta.percent,
            ta.completed_at
        FROM test_attempts ta
        JOIN users u ON u.id = ta.user_id
        JOIN roles r ON r.id = u.role_id
        JOIN tests t ON t.id = ta.test_id
        WHERE ta.test_id = %s
          AND ta.status = 'completed'
          AND t.company_id = %s
          AND r.code = 'employer'
    ),
    ranked_attempts AS (
        SELECT
            ca.user_id,
            ca.test_id,
            ca.percent,
            ca.completed_at,
            ROW_NUMBER() OVER (
                PARTITION BY ca.user_id
                ORDER BY ca.percent DESC, ca.completed_at DESC NULLS LAST
            ) AS rn
        FROM completed_attempts ca
    ),
    attempts_stats AS (
        SELECT
            ca.user_id,
            COUNT(*) AS attempts_count,
            MAX(ca.completed_at) AS last_completed_at
        FROM completed_attempts ca
        GROUP BY ca.user_id
    )
    SELECT
        u.id,
        u.full_name,
        u.email,
        ra.percent AS best_percent,
        ast.attempts_count,
        ast.last_completed_at
    FROM ranked_attempts ra
    JOIN users u ON u.id = ra.user_id
    JOIN attempts_stats ast ON ast.user_id = ra.user_id
    WHERE ra.rn = 1
    ORDER BY ra.percent DESC, ast.last_completed_at DESC NULLS LAST, u.full_name ASC
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (test_id, company_id))
            rows = cur.fetchall()

    return [
        AnalyticsTestParticipantResponse(
            employee_id=row[0],
            full_name=row[1],
            email=row[2],
            best_percent=float(row[3] or 0),
            attempts_count=int(row[4] or 0),
            last_completed_at=row[5].isoformat() if row[5] else None,
        )
        for row in rows
    ]


def fetch_test_top_errors(company_id: int, test_id: int) -> list[AnalyticsTestTopErrorResponse]:
    query = """
    SELECT
        q.id,
        q.question_text,
        COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) AS wrong_answers,
        COUNT(*) AS total_answers,
        ROUND(
            (
                COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) * 100.0
                / NULLIF(COUNT(*), 0)
            )::numeric,
            2
        ) AS error_rate
    FROM question_responses qr
    JOIN test_attempts ta ON ta.id = qr.attempt_id
    JOIN questions q ON q.id = qr.question_id
    JOIN tests t ON t.id = ta.test_id
    JOIN users u ON u.id = ta.user_id
    JOIN roles r ON r.id = u.role_id
    WHERE ta.test_id = %s
      AND ta.status = 'completed'
      AND t.company_id = %s
      AND r.code = 'employer'
    GROUP BY q.id, q.question_text
    HAVING COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) > 0
    ORDER BY error_rate DESC, wrong_answers DESC, q.id DESC
    LIMIT 5
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (test_id, company_id))
            rows = cur.fetchall()

    return [
        AnalyticsTestTopErrorResponse(
            question_id=row[0],
            question_text=row[1],
            wrong_answers=int(row[2] or 0),
            total_answers=int(row[3] or 0),
            error_rate=float(row[4] or 0),
        )
        for row in rows
    ]


def fetch_test_detail(company_id: int, test_id: int) -> AnalyticsTestDetailResponse:
    query = """
    WITH current_test_version AS (
        SELECT
            t.id AS test_id,
            t.title,
            t.course_id,
            c.title AS course_title,
            tv.id AS test_version_id
        FROM tests t
        JOIN courses c ON c.id = t.course_id
        LEFT JOIN test_versions tv
          ON tv.test_id = t.id
         AND tv.version_number = t.current_version_no
        WHERE t.company_id = %s
          AND t.id = %s
          AND t.status <> 'archived'
    ),
    question_count AS (
        SELECT
            ctv.test_id,
            COUNT(q.id) AS question_count
        FROM current_test_version ctv
        LEFT JOIN questions q ON q.test_version_id = ctv.test_version_id
        GROUP BY ctv.test_id
    ),
    attempts_agg AS (
        SELECT
            ta.test_id,
            COUNT(*) AS attempts_count,
            COUNT(DISTINCT ta.user_id) AS unique_employees_count
        FROM test_attempts ta
        JOIN current_test_version ctv ON ctv.test_id = ta.test_id
        WHERE ta.status = 'completed'
        GROUP BY ta.test_id
    ),
    best_attempts AS (
        SELECT
            ta.user_id,
            MAX(ta.percent) AS best_percent
        FROM test_attempts ta
        JOIN current_test_version ctv ON ctv.test_id = ta.test_id
        JOIN users u ON u.id = ta.user_id
        JOIN roles r ON r.id = u.role_id
        WHERE ta.status = 'completed'
          AND r.code = 'employer'
        GROUP BY ta.user_id
    ),
    avg_best AS (
        SELECT ROUND(COALESCE(AVG(best_percent), 0)::numeric, 2) AS avg_best_percent
        FROM best_attempts
    )
    SELECT
        ctv.test_id,
        ctv.title,
        ctv.course_id,
        ctv.course_title,
        COALESCE(qc.question_count, 0) AS question_count,
        COALESCE(aa.attempts_count, 0) AS attempts_count,
        COALESCE(aa.unique_employees_count, 0) AS unique_employees_count,
        COALESCE(ab.avg_best_percent, 0) AS avg_best_percent
    FROM current_test_version ctv
    LEFT JOIN question_count qc ON qc.test_id = ctv.test_id
    LEFT JOIN attempts_agg aa ON aa.test_id = ctv.test_id
    CROSS JOIN avg_best ab
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (company_id, test_id))
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Тест не найден")

    return AnalyticsTestDetailResponse(
        test_id=row[0],
        title=row[1],
        course_id=row[2],
        course_title=row[3],
        question_count=int(row[4] or 0),
        attempts_count=int(row[5] or 0),
        unique_employees_count=int(row[6] or 0),
        avg_best_percent=float(row[7] or 0),
        participants=fetch_test_participants(company_id, test_id),
        top_errors=fetch_test_top_errors(company_id, test_id),
    )
# The above code is using the FastAPI framework in Python to define a route for handling GET requests
# to "/tests". It specifies that the response should be formatted according to the
# `AnalyticsTestListResponse` model. This means that the response data will be validated against the
# specified model before being returned to the client.
@router.get("/tests", response_model=AnalyticsTestListResponse)

def fetch_course_results(company_id: int, employee_id: int) -> list[AnalyticsCourseResultResponse]:
    query = """
    WITH published_tests AS (
        SELECT
            t.id AS test_id,
            t.course_id,
            c.title AS course_title
        FROM tests t
        JOIN courses c ON c.id = t.course_id
        WHERE t.company_id = %s
          AND t.status = 'published'
    ),
    best_attempts AS (
        SELECT
            ta.test_id,
            MAX(ta.percent) AS best_percent
        FROM test_attempts ta
        JOIN published_tests pt ON pt.test_id = ta.test_id
        WHERE ta.user_id = %s
          AND ta.status = 'completed'
        GROUP BY ta.test_id
    )
    SELECT
        pt.course_id,
        pt.course_title,
        ROUND(COALESCE(AVG(ba.best_percent), 0)::numeric, 2) AS correct_answers_percent
    FROM published_tests pt
    LEFT JOIN best_attempts ba ON ba.test_id = pt.test_id
    GROUP BY pt.course_id, pt.course_title
    ORDER BY pt.course_title ASC
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (company_id, employee_id))
            rows = cur.fetchall()

    return [
        AnalyticsCourseResultResponse(
            course_id=row[0],
            course_title=row[1],
            correct_answers_percent=float(row[2] or 0),
        )
        for row in rows
    ]


def fetch_typical_errors(company_id: int, employee_id: int) -> list[AnalyticsTypicalErrorResponse]:
    query = """
    SELECT
        q.id,
        q.question_text,
        c.title AS course_title,
        COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) AS wrong_answers,
        COUNT(*) AS total_answers,
        ROUND(
            (
                COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) * 100.0
                / NULLIF(COUNT(*), 0)
            )::numeric,
            2
        ) AS error_rate
    FROM question_responses qr
    JOIN test_attempts ta ON ta.id = qr.attempt_id
    JOIN questions q ON q.id = qr.question_id
    JOIN tests t ON t.id = ta.test_id
    JOIN courses c ON c.id = t.course_id
    WHERE ta.user_id = %s
      AND ta.status = 'completed'
      AND t.company_id = %s
    GROUP BY q.id, q.question_text, c.title
    HAVING COUNT(*) FILTER (WHERE COALESCE(qr.is_correct, FALSE) = FALSE) > 0
    ORDER BY error_rate DESC, wrong_answers DESC, q.id DESC
    LIMIT 5
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (employee_id, company_id))
            rows = cur.fetchall()

    return [
        AnalyticsTypicalErrorResponse(
            question_id=row[0],
            question_text=row[1],
            course_title=row[2],
            wrong_answers=int(row[3] or 0),
            total_answers=int(row[4] or 0),
            error_rate=float(row[5] or 0),
        )
        for row in rows
    ]


def fetch_test_cards(company_id: int) -> list[AnalyticsTestCardResponse]:
    query = """
    WITH current_test_versions AS (
        SELECT
            t.id AS test_id,
            t.title,
            t.course_id,
            c.title AS course_title,
            tv.id AS test_version_id
        FROM tests t
        JOIN courses c ON c.id = t.course_id
        LEFT JOIN test_versions tv
          ON tv.test_id = t.id
         AND tv.version_number = t.current_version_no
        WHERE t.company_id = %s
          AND t.status <> 'archived'
    ),
    question_counts AS (
        SELECT
            ctv.test_id,
            COUNT(q.id) AS question_count
        FROM current_test_versions ctv
        LEFT JOIN questions q ON q.test_version_id = ctv.test_version_id
        GROUP BY ctv.test_id
    ),
    attempts_agg AS (
        SELECT
            ta.test_id,
            COUNT(*) AS attempts_count,
            COUNT(DISTINCT ta.user_id) AS unique_employees_count
        FROM test_attempts ta
        JOIN current_test_versions ctv ON ctv.test_id = ta.test_id
        WHERE ta.status = 'completed'
        GROUP BY ta.test_id
    ),
    best_attempts AS (
        SELECT
            ta.test_id,
            ta.user_id,
            MAX(ta.percent) AS best_percent
        FROM test_attempts ta
        JOIN current_test_versions ctv ON ctv.test_id = ta.test_id
        JOIN users u ON u.id = ta.user_id
        JOIN roles r ON r.id = u.role_id
        WHERE ta.status = 'completed'
          AND r.code = 'employer'
        GROUP BY ta.test_id, ta.user_id
    ),
    avg_best AS (
        SELECT
            test_id,
            ROUND(COALESCE(AVG(best_percent), 0)::numeric, 2) AS avg_best_percent
        FROM best_attempts
        GROUP BY test_id
    )
    SELECT
        ctv.test_id,
        ctv.title,
        ctv.course_id,
        ctv.course_title,
        COALESCE(qc.question_count, 0) AS question_count,
        COALESCE(aa.attempts_count, 0) AS attempts_count,
        COALESCE(aa.unique_employees_count, 0) AS unique_employees_count,
        COALESCE(ab.avg_best_percent, 0) AS avg_best_percent
    FROM current_test_versions ctv
    LEFT JOIN question_counts qc ON qc.test_id = ctv.test_id
    LEFT JOIN attempts_agg aa ON aa.test_id = ctv.test_id
    LEFT JOIN avg_best ab ON ab.test_id = ctv.test_id
    ORDER BY ctv.test_id DESC
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (company_id,))
            rows = cur.fetchall()

    return [
        AnalyticsTestCardResponse(
            test_id=row[0],
            title=row[1],
            course_id=row[2],
            course_title=row[3],
            question_count=int(row[4] or 0),
            attempts_count=int(row[5] or 0),
            unique_employees_count=int(row[6] or 0),
            avg_best_percent=float(row[7] or 0),
        )
        for row in rows
    ]

def list_test_analytics(
    current_user: dict = Depends(get_current_user),
) -> AnalyticsTestListResponse:
    require_manager_user(current_user)

    return AnalyticsTestListResponse(
        items=fetch_test_cards(current_user["company_id"])
    )


@router.get("/tests/{test_id}", response_model=AnalyticsTestDetailResponse)
def get_test_analytics_detail(
    test_id: int,
    current_user: dict = Depends(get_current_user),
) -> AnalyticsTestDetailResponse:
    require_manager_user(current_user)
    return fetch_test_detail(current_user["company_id"], test_id)


@router.get("/employees", response_model=AnalyticsEmployeeListResponse)
def list_employee_analytics(
    search: str | None = Query(default=None),
    sort: Literal["hire_date", "adaptation", "correct_answers"] = Query(default="hire_date"),
    current_user: dict = Depends(get_current_user),
) -> AnalyticsEmployeeListResponse:
    require_manager_user(current_user)

    rows = fetch_employee_metric_rows(
    company_id=current_user["company_id"],
    search=search,
    sort=sort,
    supervisor_scope_id=get_supervisor_scope(current_user),
)

    return AnalyticsEmployeeListResponse(items=[build_employee_card(row) for row in rows])


@router.get("/employees/{employee_id}", response_model=AnalyticsEmployeeDetailResponse)
def get_employee_analytics_detail(
    employee_id: int,
    current_user: dict = Depends(get_current_user),
) -> AnalyticsEmployeeDetailResponse:
    require_manager_user(current_user)

    rows = fetch_employee_metric_rows(
    company_id=current_user["company_id"],
    search=None,
    sort="hire_date",
    employee_id=employee_id,
    supervisor_scope_id=get_supervisor_scope(current_user),
)

    if not rows:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    row = rows[0]
    employee = build_employee_card(row)

    return AnalyticsEmployeeDetailResponse(
        employee=employee,
        completed_tests_count=int(row[10] or 0),
        completed_dialogs_count=int(row[11] or 0),
        course_results=fetch_course_results(current_user["company_id"], employee_id),
        typical_errors=fetch_typical_errors(current_user["company_id"], employee_id),
    )
    
