from __future__ import annotations

from io import BytesIO

import psycopg
from minio import Minio
from redis import Redis

from .config import settings


def get_postgres_connection() -> psycopg.Connection:
    return psycopg.connect(settings.postgres_dsn)


def get_redis_client() -> Redis:
    return Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def upload_bytes_to_minio(
    *,
    object_name: str,
    content: bytes,
    content_type: str,
) -> None:
    client = get_minio_client()
    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )


def download_bytes_from_minio(*, object_name: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object_from_minio(*, object_name: str) -> None:
    client = get_minio_client()
    client.remove_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
    )