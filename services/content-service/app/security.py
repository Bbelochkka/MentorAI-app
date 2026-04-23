from __future__ import annotations

import binascii
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings
from .infrastructure import get_postgres_connection


security_scheme = HTTPBearer()

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 260000
SALT_BYTES_HEX_LEN = 32
HASH_PREFIX = "pbkdf2_sha256"


def _pbkdf2_digest(password: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return binascii.hexlify(digest).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES_HEX_LEN // 2)
    digest = _pbkdf2_digest(password, salt, PBKDF2_ITERATIONS)
    return f"{HASH_PREFIX}${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    if not stored_password_hash:
        return False

    parts = stored_password_hash.split("$")
    if len(parts) == 4 and parts[0] == HASH_PREFIX:
        _, iterations_raw, salt, expected_digest = parts
        try:
            iterations = int(iterations_raw)
        except ValueError:
            return False
        actual_digest = _pbkdf2_digest(password, salt, iterations)
        return hmac.compare_digest(actual_digest, expected_digest)

    # Legacy bootstrap mode: plain text in DB.
    return hmac.compare_digest(password, stored_password_hash)


def is_password_hash_legacy(stored_password_hash: str) -> bool:
    return not stored_password_hash.startswith(f"{HASH_PREFIX}$")


def get_user_by_email(email: str) -> dict | None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id,
                       u.email,
                       u.full_name,
                       r.code,
                       u.company_id,
                       u.password_hash,
                       u.is_active
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE lower(u.email) = lower(%s)
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "company_id": row[4],
        "password_hash": row[5],
        "is_active": row[6],
    }


def get_user_by_id(user_id: int) -> dict | None:
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id,
                       u.email,
                       u.full_name,
                       r.code,
                       u.company_id,
                       u.password_hash,
                       u.is_active
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "name": row[2],
        "role": row[3],
        "company_id": row[4],
        "password_hash": row[5],
        "is_active": row[6],
    }


def upgrade_legacy_password_hash(user_id: int, password: str) -> None:
    new_hash = hash_password(password)
    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
            )
        conn.commit()


def authenticate_user(email: str, password: str) -> dict | None:
    user = get_user_by_email(email)
    if not user or not user.get("is_active"):
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    if is_password_hash_legacy(user["password_hash"]):
        upgrade_legacy_password_hash(user["id"], password)
        user = get_user_by_id(user["id"])

    return user


def create_access_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(subject),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        user_id = int(subject)
    except (JWTError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        ) from exc

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user
