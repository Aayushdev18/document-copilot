from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./document_copilot.db"
    seed_on_startup: bool = True
    auth_mode: str = "local"
    local_auth_secret: str = "dev-only-change-me"
    token_ttl_seconds: int = 60 * 60 * 24 * 14
    allowed_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    openai_api_key: str | None = None

    @model_validator(mode="after")
    def require_mode_secrets(self) -> "Settings":
        if self.auth_mode not in {"local", "supabase"}:
            raise ValueError("AUTH_MODE must be 'local' or 'supabase'")
        if self.auth_mode == "local" and not self.local_auth_secret:
            raise ValueError("LOCAL_AUTH_SECRET is required when AUTH_MODE=local")
        if self.auth_mode == "supabase":
            missing = [
                name
                for name, value in {
                    "SUPABASE_URL": self.supabase_url,
                    "SUPABASE_ANON_KEY": self.supabase_anon_key,
                    "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(
                    "Missing required settings for AUTH_MODE=supabase: " + ", ".join(missing)
                )
        return self

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
