from __future__ import annotations

import logging
import time

import psycopg
from minio import Minio
from redis import Redis

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
)
logger = logging.getLogger('content-worker')


def wait_for_dependencies() -> None:
    while True:
        try:
            with psycopg.connect(settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1;')
                    cur.fetchone()

            redis_client = Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
            redis_client.ping()

            minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            minio_client.bucket_exists(settings.minio_bucket)

            logger.info('All worker dependencies are available.')
            return
        except Exception as exc:
            logger.warning('Dependencies are not ready yet: %s', exc)
            time.sleep(3)


def main() -> None:
    logger.info('Starting content-worker bootstrap...')
    logger.info('Configured LLM provider: %s (%s)', settings.llm_provider, settings.llm_model)
    wait_for_dependencies()

    while True:
        logger.info('Worker heartbeat: ready for document processing and LLM jobs.')
        time.sleep(30)


if __name__ == '__main__':
    main()
