from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from .infrastructure import get_postgres_connection
from .security import get_current_user, hash_password

router = APIRouter(prefix="/api/users", tags=["users-admin"])


class UserListItemResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    role_label: str
    hire_date: date | None = None
    job_title: str | None = None
    department: str | None = None
    supervisor_id: int | None = None
    supervisor_name: str | None = None


class UserListResponse(BaseModel):
    items: list[UserListItemResponse]


class SupervisorOptionResponse(BaseModel):
    id: int
    full_name: str
    department: str | None = None


class SupervisorOptionsResponse(BaseModel):
    items: list[SupervisorOptionResponse]


class UserCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Literal["employer", "manager"]
    hire_date: date
    job_title: str
    department: str
    supervisor_id: int | None = None


class UserUpdateRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str | None = None
    role: Literal["employer", "manager"]
    hire_date: date
    job_title: str
    department: str
    supervisor_id: int | None = None


def require_admin_user(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Раздел сотрудников доступен только администратору")


def role_label(role_code: str) -> str:
    mapping = {
        "admin": "Администратор",
        "manager": "Менеджер",
        "employer": "Сотрудник",
    }
    return mapping.get(role_code, role_code)


def _ensure_user_management_schema() -> None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS hire_date DATE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title VARCHAR(255)")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(255)")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS supervisor_id BIGINT")

            cur.execute(
                """
                UPDATE users
                SET hire_date = created_at::date
                WHERE hire_date IS NULL
                """
            )

            cur.execute(
                """
                UPDATE users
                SET department = COALESCE(department, 'Отдел продаж')
                WHERE department IS NULL
                """
            )

        conn.commit()


def _get_role_id(role_code: str) -> int:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM roles
                WHERE code = %s
                LIMIT 1
                """,
                (role_code,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Роль не найдена")

    return row[0]


def _get_company_admin_id(company_id: int) -> int:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.company_id = %s
                  AND u.is_active = TRUE
                  AND r.code = 'admin'
                ORDER BY u.id ASC
                LIMIT 1
                """,
                (company_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=400,
            detail="В компании не найден администратор, которого можно назначить супервизором менеджера",
        )

    return row[0]


def _validate_supervisor(company_id: int, supervisor_id: int) -> None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = %s
                  AND u.company_id = %s
                  AND u.is_active = TRUE
                  AND r.code = 'manager'
                LIMIT 1
                """,
                (supervisor_id, company_id),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=400,
            detail="Указанный супервизор не найден или не является менеджером",
        )


def _ensure_email_available(email: str, company_id: int, exclude_user_id: int | None = None) -> None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            if exclude_user_id is None:
                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE lower(email) = lower(%s)
                      AND company_id = %s
                    LIMIT 1
                    """,
                    (email, company_id),
                )
            else:
                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE lower(email) = lower(%s)
                      AND company_id = %s
                      AND id <> %s
                    LIMIT 1
                    """,
                    (email, company_id, exclude_user_id),
                )

            row = cur.fetchone()

    if row:
        raise HTTPException(status_code=400, detail="Пользователь с таким e-mail уже существует")


def _fetch_user_list(company_id: int) -> list[UserListItemResponse]:
    query = """
    SELECT
        u.id,
        u.full_name,
        u.email,
        r.code,
        COALESCE(u.hire_date, u.created_at::date) AS hire_date,
        u.job_title,
        u.department,
        u.supervisor_id,
        s.full_name AS supervisor_name
    FROM users u
    JOIN roles r ON r.id = u.role_id
    LEFT JOIN users s ON s.id = u.supervisor_id
    WHERE u.company_id = %s
      AND u.is_active = TRUE
    ORDER BY
        CASE r.code
            WHEN 'admin' THEN 1
            WHEN 'manager' THEN 2
            WHEN 'employer' THEN 3
            ELSE 4
        END,
        u.full_name ASC
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (company_id,))
            rows = cur.fetchall()

    return [
        UserListItemResponse(
            id=row[0],
            full_name=row[1],
            email=row[2],
            role=row[3],
            role_label=role_label(row[3]),
            hire_date=row[4],
            job_title=row[5],
            department=row[6],
            supervisor_id=row[7],
            supervisor_name=row[8],
        )
        for row in rows
    ]


def _fetch_single_user(company_id: int, user_id: int) -> UserListItemResponse:
    users = _fetch_user_list(company_id)
    for user in users:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="Пользователь не найден")


def _fetch_supervisor_options(company_id: int) -> list[SupervisorOptionResponse]:
    query = """
    SELECT
        u.id,
        u.full_name,
        u.department
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE u.company_id = %s
      AND u.is_active = TRUE
      AND r.code = 'manager'
    ORDER BY u.full_name ASC
    """

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (company_id,))
            rows = cur.fetchall()

    return [
        SupervisorOptionResponse(
            id=row[0],
            full_name=row[1],
            department=row[2],
        )
        for row in rows
    ]


def _get_target_user(company_id: int, user_id: int) -> tuple[int, str]:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, r.code
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = %s
                  AND u.company_id = %s
                  AND u.is_active = TRUE
                LIMIT 1
                """,
                (user_id, company_id),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return row[0], row[1]


def _normalize_user_payload(
    *,
    full_name: str,
    email: str,
    password: str | None,
    role: Literal["employer", "manager"],
    hire_date: date,
    job_title: str,
    department: str,
    supervisor_id: int | None,
    company_id: int,
) -> dict:
    normalized_full_name = full_name.strip()
    normalized_email = email.strip().lower()
    normalized_job_title = job_title.strip()
    normalized_department = department.strip()
    normalized_password = (password or "").strip()

    if not normalized_full_name:
        raise HTTPException(status_code=400, detail="Введите ФИО")
    if not normalized_job_title:
        raise HTTPException(status_code=400, detail="Введите должность")
    if not normalized_department:
        raise HTTPException(status_code=400, detail="Введите отдел")

    if role == "manager":
        resolved_supervisor_id = _get_company_admin_id(company_id)
    else:
        if supervisor_id is None:
            raise HTTPException(status_code=400, detail="Для сотрудника нужно выбрать супервизора")
        _validate_supervisor(company_id, supervisor_id)
        resolved_supervisor_id = supervisor_id

    return {
        "full_name": normalized_full_name,
        "email": normalized_email,
        "password": normalized_password,
        "role": role,
        "hire_date": hire_date,
        "job_title": normalized_job_title,
        "department": normalized_department,
        "supervisor_id": resolved_supervisor_id,
    }


@router.get("", response_model=UserListResponse)
def list_users(current_user: dict = Depends(get_current_user)) -> UserListResponse:
    _ensure_user_management_schema()
    require_admin_user(current_user)
    return UserListResponse(items=_fetch_user_list(current_user["company_id"]))


@router.get("/supervisors", response_model=SupervisorOptionsResponse)
def list_supervisors(current_user: dict = Depends(get_current_user)) -> SupervisorOptionsResponse:
    _ensure_user_management_schema()
    require_admin_user(current_user)
    return SupervisorOptionsResponse(items=_fetch_supervisor_options(current_user["company_id"]))


@router.post("", response_model=UserListItemResponse)
def create_user(
    payload: UserCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserListItemResponse:
    _ensure_user_management_schema()
    require_admin_user(current_user)

    normalized = _normalize_user_payload(
        full_name=payload.full_name,
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
        hire_date=payload.hire_date,
        job_title=payload.job_title,
        department=payload.department,
        supervisor_id=payload.supervisor_id,
        company_id=current_user["company_id"],
    )

    if len(normalized["password"]) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

    _ensure_email_available(normalized["email"], current_user["company_id"])
    role_id = _get_role_id(normalized["role"])

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    company_id,
                    role_id,
                    full_name,
                    email,
                    password_hash,
                    is_active,
                    hire_date,
                    job_title,
                    department,
                    supervisor_id
                )
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    current_user["company_id"],
                    role_id,
                    normalized["full_name"],
                    normalized["email"],
                    hash_password(normalized["password"]),
                    normalized["hire_date"],
                    normalized["job_title"],
                    normalized["department"],
                    normalized["supervisor_id"],
                ),
            )
            new_user_id = cur.fetchone()[0]

        conn.commit()

    return _fetch_single_user(current_user["company_id"], new_user_id)


@router.put("/{user_id}", response_model=UserListItemResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserListItemResponse:
    _ensure_user_management_schema()
    require_admin_user(current_user)

    target_user_id, target_role = _get_target_user(current_user["company_id"], user_id)

    if target_role == "admin":
        raise HTTPException(status_code=400, detail="Администратора нельзя редактировать через этот экран")

    normalized = _normalize_user_payload(
        full_name=payload.full_name,
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
        hire_date=payload.hire_date,
        job_title=payload.job_title,
        department=payload.department,
        supervisor_id=payload.supervisor_id,
        company_id=current_user["company_id"],
    )

    if normalized["password"] and len(normalized["password"]) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

    _ensure_email_available(normalized["email"], current_user["company_id"], exclude_user_id=target_user_id)
    role_id = _get_role_id(normalized["role"])

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET role_id = %s,
                    full_name = %s,
                    email = %s,
                    hire_date = %s,
                    job_title = %s,
                    department = %s,
                    supervisor_id = %s
                WHERE id = %s
                  AND company_id = %s
                """,
                (
                    role_id,
                    normalized["full_name"],
                    normalized["email"],
                    normalized["hire_date"],
                    normalized["job_title"],
                    normalized["department"],
                    normalized["supervisor_id"],
                    target_user_id,
                    current_user["company_id"],
                ),
            )

            if normalized["password"]:
                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE id = %s
                      AND company_id = %s
                    """,
                    (
                        hash_password(normalized["password"]),
                        target_user_id,
                        current_user["company_id"],
                    ),
                )

        conn.commit()

    return _fetch_single_user(current_user["company_id"], target_user_id)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    _ensure_user_management_schema()
    require_admin_user(current_user)

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    target_user_id, target_role = _get_target_user(current_user["company_id"], user_id)

    if target_role == "admin":
        raise HTTPException(status_code=400, detail="Администратора нельзя удалить через этот экран")

    if target_role == "manager":
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM users subordinate
                    JOIN roles subordinate_role ON subordinate_role.id = subordinate.role_id
                    WHERE subordinate.company_id = %s
                      AND subordinate.is_active = TRUE
                      AND subordinate.supervisor_id = %s
                      AND subordinate_role.code = 'employer'
                    """,
                    (current_user["company_id"], target_user_id),
                )
                subordinate_count = cur.fetchone()[0]

        if subordinate_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Нельзя удалить менеджера, пока к нему прикреплены сотрудники",
            )

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET is_active = FALSE
                WHERE id = %s
                  AND company_id = %s
                """,
                (target_user_id, current_user["company_id"]),
            )
        conn.commit()

    return {"message": "Пользователь удалён"}