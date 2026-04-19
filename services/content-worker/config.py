from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    postgres_db: str = Field(alias='POSTGRES_DB')
    postgres_user: str = Field(alias='POSTGRES_USER')
    postgres_password: str = Field(alias='POSTGRES_PASSWORD')
    postgres_host: str = Field(alias='POSTGRES_HOST')
    postgres_port: int = Field(alias='POSTGRES_PORT')

    redis_host: str = Field(alias='REDIS_HOST')
    redis_port: int = Field(alias='REDIS_PORT')

    minio_endpoint: str = Field(alias='MINIO_ENDPOINT')
    minio_access_key: str = Field(alias='MINIO_ACCESS_KEY')
    minio_secret_key: str = Field(alias='MINIO_SECRET_KEY')
    minio_bucket: str = Field(alias='MINIO_BUCKET')
    minio_secure: bool = Field(alias='MINIO_SECURE', default=False)

    llm_provider: str = Field(alias='LLM_PROVIDER', default='ollama')
    llm_base_url: str = Field(alias='LLM_BASE_URL', default='http://host.docker.internal:11434')
    llm_model: str = Field(alias='LLM_MODEL', default='gemma3:4b')
    llm_timeout_seconds: int = Field(alias='LLM_TIMEOUT_SECONDS', default=180)

    @property
    def postgres_dsn(self) -> str:
        return (
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password} host={self.postgres_host} port={self.postgres_port}"
        )


settings = Settings()
