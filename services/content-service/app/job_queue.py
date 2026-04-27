from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from .infrastructure import get_postgres_connection, get_redis_client

GENERATION_QUEUE_KEY = "mentorai:generation:queue"
GENERATION_JOB_KEY_PREFIX = "mentorai:generation:job:"
GENERATION_JOB_TTL_SECONDS = 60 * 60


class JobFailedError(RuntimeError):
    pass


class JobTimeoutError(TimeoutError):
    pass


def _job_key(job_id: str) -> str:
    return f"{GENERATION_JOB_KEY_PREFIX}{job_id}"

def _extract_user_and_company(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    current_user = payload.get("current_user") or {}
    user_id = current_user.get("id")
    company_id = current_user.get("company_id")

    if user_id is None or company_id is None:
        return None, None

    return int(user_id), int(company_id)


def _detect_entity_from_result(
    job_type: str,
    result: dict[str, Any],
) -> tuple[str | None, int | None]:
    if job_type == "test_generate_draft" and result.get("test_id") is not None:
        return "test", int(result["test_id"])

    if job_type == "course_generate_draft" and result.get("course_id") is not None:
        return "course", int(result["course_id"])

    if result.get("test_id") is not None:
        return "test", int(result["test_id"])

    if result.get("course_id") is not None:
        return "course", int(result["course_id"])

    return None, None


def _create_generation_job_db_record(
    *,
    job_id: str,
    job_type: str,
    payload: dict[str, Any],
) -> None:
    user_id, company_id = _extract_user_and_company(payload)

    if user_id is None or company_id is None:
        return

    request_payload = payload.get("request_payload") or {}

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO generation_jobs (
                    id,
                    company_id,
                    user_id,
                    job_type,
                    status,
                    request_payload,
                    created_at
                )
                VALUES (%s, %s, %s, %s, 'queued', %s::jsonb, NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    job_id,
                    company_id,
                    user_id,
                    job_type,
                    json.dumps(request_payload, ensure_ascii=False, default=str),
                ),
            )
        conn.commit()


def _mark_generation_job_db_running(job_id: str) -> None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE generation_jobs
                SET status = 'running',
                    started_at = COALESCE(started_at, NOW())
                WHERE id = %s
                """,
                (job_id,),
            )
        conn.commit()


def _mark_generation_job_db_completed(
    job_id: str,
    job_type: str,
    result: dict[str, Any],
) -> None:
    entity_type, entity_id = _detect_entity_from_result(job_type, result)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE generation_jobs
                SET status = 'completed',
                    entity_type = %s,
                    entity_id = %s,
                    result_payload = %s::jsonb,
                    completed_at = NOW()
                WHERE id = %s
                """,
                (
                    entity_type,
                    entity_id,
                    json.dumps(result, ensure_ascii=False, default=str),
                    job_id,
                ),
            )
        conn.commit()


def _mark_generation_job_db_failed(job_id: str, error: str) -> None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE generation_jobs
                SET status = 'failed',
                    error_message = %s,
                    completed_at = NOW()
                WHERE id = %s
                """,
                (error, job_id),
            )
        conn.commit()

def create_generation_job(job_type: str, payload: dict[str, Any]) -> str:
    redis_client = get_redis_client()
    job_id = str(uuid4())
    now = str(time.time())

    _create_generation_job_db_record(
        job_id=job_id,
        job_type=job_type,
        payload=payload,
    )

    redis_client.hset(
        _job_key(job_id),
        mapping={
            "id": job_id,
            "type": job_type,
            "status": "queued",
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
            "created_at": now,
            "updated_at": now,
        },
    )
    redis_client.expire(_job_key(job_id), GENERATION_JOB_TTL_SECONDS)
    redis_client.rpush(GENERATION_QUEUE_KEY, job_id)
    return job_id


def wait_for_generation_job(
    job_id: str,
    *,
    timeout_seconds: int = 600,
    poll_interval_seconds: float = 0.5,
) -> dict[str, Any]:
    redis_client = get_redis_client()
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        data = redis_client.hgetall(_job_key(job_id))
        if not data:
            raise JobFailedError("Задача генерации не найдена или была удалена из Redis")

        status = data.get("status")
        if status == "completed":
            raw_result = data.get("result") or "{}"
            result = json.loads(raw_result)
            if not isinstance(result, dict):
                raise JobFailedError("Фоновый обработчик вернул результат в неверном формате")
            return result

        if status == "failed":
            raise JobFailedError(data.get("error") or "Фоновая генерация завершилась ошибкой")

        time.sleep(poll_interval_seconds)

    raise JobTimeoutError("Фоновая генерация выполняется слишком долго. Попробуйте повторить запрос позже")


def run_generation_job_sync(
    job_type: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    job_id = create_generation_job(job_type, payload)
    return wait_for_generation_job(job_id, timeout_seconds=timeout_seconds)


def dequeue_generation_job(*, block_timeout_seconds: int = 5) -> dict[str, Any] | None:
    redis_client = get_redis_client()
    item = redis_client.blpop(GENERATION_QUEUE_KEY, timeout=block_timeout_seconds)
    if item is None:
        return None

    _queue_name, job_id = item
    data = redis_client.hgetall(_job_key(job_id))
    if not data:
        return None

    raw_payload = data.get("payload") or "{}"
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        payload = {}

    return {
        "id": job_id,
        "type": data.get("type") or "",
        "payload": payload,
    }


def mark_generation_job_running(job_id: str) -> None:
    redis_client = get_redis_client()
    redis_client.hset(
        _job_key(job_id),
        mapping={
            "status": "running",
            "updated_at": str(time.time()),
        },
    )
    redis_client.expire(_job_key(job_id), GENERATION_JOB_TTL_SECONDS)

    _mark_generation_job_db_running(job_id)


def mark_generation_job_completed(job_id: str, result: dict[str, Any]) -> None:
    redis_client = get_redis_client()
    job = redis_client.hgetall(_job_key(job_id))
    job_type = job.get("type", "")

    redis_client.hset(
        _job_key(job_id),
        mapping={
            "status": "completed",
            "result": json.dumps(result, ensure_ascii=False, default=str),
            "updated_at": str(time.time()),
        },
    )
    redis_client.expire(_job_key(job_id), GENERATION_JOB_TTL_SECONDS)

    _mark_generation_job_db_completed(job_id, job_type, result)


def mark_generation_job_failed(job_id: str, error: str) -> None:
    redis_client = get_redis_client()
    redis_client.hset(
        _job_key(job_id),
        mapping={
            "status": "failed",
            "error": error,
            "updated_at": str(time.time()),
        },
    )
    redis_client.expire(_job_key(job_id), GENERATION_JOB_TTL_SECONDS)

    _mark_generation_job_db_failed(job_id, error)
