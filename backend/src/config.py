from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env is shared with docker compose, so it has keys the app does not use.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    db_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    jwt_algorithm: str = "HS256"
    jwt_key: str = "bruh"
    access_token_expire_minutes: int = 10
    refresh_token_expire_minutes: int = 7 * 24 * 60
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # S3-compatible storage (SeaweedFS in docker compose). Presigned URLs are signed for
    # s3_public_endpoint, since the browser uploads/downloads directly.
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "dev-access-key"
    s3_secret_key: str = "dev-secret-key"
    s3_bucket: str = "zebra"
    s3_region: str = "us-east-1"
    max_upload_mb: int = 20
    presigned_url_ttl_seconds: int = 15 * 60

    judge0_url: str = "http://localhost:2358"
    judge0_auth_token: str | None = None
    # Language id of Python 3 in the deployed Judge0 (71 in Judge0 CE 1.13).
    judge0_python_language_id: int = 71
    judge_max_retries: int = 3
    # A submission stuck in "running" longer than this is requeued (worker crash).
    judge_stale_after_seconds: int = 600
    worker_concurrency: int = 2


settings = Settings()
