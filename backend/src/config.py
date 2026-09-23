from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    db_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    jwt_algorithm: str = "HS256"
    jwt_key: str = "bruh"
    access_token_expire_minutes: int = 10
    refresh_token_expire_minutes: int = 7 * 24 * 60
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
