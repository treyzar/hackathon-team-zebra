from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    # .env is shared with docker compose, so it has keys the app does not use.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    db_url: str = "postgresql+asyncpg://postgres:admin@localhost:5432/app"
    # Password kept out of DB_URL: docker compose cannot URL-escape it, and
    # characters like @ : / % would break the URL.
    db_password: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_key: str
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
    # How long the language list of Judge0 is cached: it changes only when
    # Judge0 is upgraded.
    judge0_languages_ttl_seconds: int = 300
    judge_max_retries: int = 3
    # A submission stuck in "running" longer than this is requeued (worker crash).
    judge_stale_after_seconds: int = 600
    worker_concurrency: int = 2
    # Judge0 caps program output (max_file_size) at MAX_MAX_FILE_SIZE, 4096 KB
    # by default; expected outputs of tests must fit into it.
    judge_max_output_kb: int = 4096
    # Largest input file of a programming test.
    test_input_max_mb: int = 16
    # All test files of one step together: the worker holds them in memory.
    test_files_total_mb: int = 128
    # Upper bound of stdin + expected output sent to Judge0 in one batch.
    judge_batch_max_mb: int = 16
    # In-memory cache of test files in each worker process.
    worker_file_cache_mb: int = 64

    @property
    def database_url(self) -> URL:
        url = make_url(self.db_url)
        if self.db_password is not None:
            url = url.set(password=self.db_password)
        return url


settings = Settings()
