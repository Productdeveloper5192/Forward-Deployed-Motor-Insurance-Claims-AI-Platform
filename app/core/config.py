from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Moto Insurance Claims"
    environment: str = "development"

    database_url: str = f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"
    storage_dir: Path = BASE_DIR / "storage" / "uploads"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    claude_provider: str = "anthropic"  # "anthropic" or "foundry"
    anthropic_api_key: str | None = None
    foundry_api_key: str | None = None
    foundry_resource: str | None = None
    claude_model: str = "claude-opus-4-8"

    # Deterministic thresholds used by the rules engine
    fraud_review_threshold: int = 60
    fraud_deny_threshold: int = 85
    auto_approve_max_amount: float = 3000.0


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
