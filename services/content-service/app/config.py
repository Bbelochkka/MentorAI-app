from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MentorAI content-service"
    app_version: str = "0.1.0"

    postgres_dsn: str = Field(
        default="postgresql://mentorai:mentorai@postgres:5432/mentorai"
    )

    redis_host: str = "redis"
    redis_port: int = 6379

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"
    minio_secure: bool = False

    jwt_secret_key: str = "dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    fake_user_email: str = "aoanuchina@hse.edu.ru"
    fake_user_password: str = "password123"
    fake_user_name: str = "Alena"
    fake_user_role: str = "manager"
    fake_user_company_id: int = 1
    fake_user_id: int = 1

    llm_provider: str = "gigachat"   # gigachat | ollama
    llm_timeout_seconds: int = 300

    llm_base_url: str = "http://host.docker.internal:11434"
    llm_model: str = "gemma3:4b"

    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    gigachat_model: str = "GigaChat-2"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()