from __future__ import annotations

import logging
import time

import psycopg

from app.config import settings
from app.generation_jobs import run_generation_job
from app.infrastructure import get_minio_client, get_redis_client
from app.job_queue import (
    dequeue_generation_job,
    mark_generation_job_completed,
    mark_generation_job_failed,
    mark_generation_job_running,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("content-worker")


def wait_for_dependencies() -> None:
    while True:
        try:
            with psycopg.connect(settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()

            redis_client = get_redis_client()
            redis_client.ping()

            minio_client = get_minio_client()
            minio_client.bucket_exists(settings.minio_bucket)

            logger.info("All worker dependencies are available.")
            return
        except Exception as exc:
            logger.warning("Dependencies are not ready yet: %s", exc)
            time.sleep(3)


def main() -> None:
    logger.info("Starting content-worker...")
    logger.info("Configured LLM provider: %s", settings.llm_provider)
    wait_for_dependencies()

    while True:
        job = dequeue_generation_job(block_timeout_seconds=5)
        if job is None:
            continue

        job_id = job["id"]
        job_type = job["type"]
        payload = job["payload"]

        logger.info("Started generation job id=%s type=%s", job_id, job_type)
        mark_generation_job_running(job_id)

        try:
            result = run_generation_job(job_type, payload)
            mark_generation_job_completed(job_id, result)
            logger.info("Completed generation job id=%s type=%s", job_id, job_type)
        except Exception as exc:
            logger.exception("Failed generation job id=%s type=%s", job_id, job_type)
            mark_generation_job_failed(job_id, str(exc))


if __name__ == "__main__":
    main()
