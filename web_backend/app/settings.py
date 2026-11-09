from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://topjobs:topjobs_dev_only@localhost:5432/topjobs"
    redis_url: str = "redis://localhost:6379/0"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    app_credentials_encryption_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    ai_provider_order: str = "groq,gemini"
    ai_enable_features: bool = True
    ai_per_feature_toggles: str = "resume_analysis=true,job_tuning=true,application_drafts=true"
    web_allowed_origins: str = "http://localhost:3000"
    search_queue_backend: Literal["local", "vercel"] = "local"
    vercel_queue_region: str = "iad1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.web_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
