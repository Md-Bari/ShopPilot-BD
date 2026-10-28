"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "dev-insecure-secret-change-me-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ShopPilot BD"
    environment: Literal["development", "test", "production"] = "development"
    secret_key: str = Field(default=INSECURE_DEFAULT_SECRET, min_length=32)
    database_url: str = "postgresql+psycopg://shoppilot:shoppilot@localhost:5432/shoppilot"
    log_level: str = "INFO"

    # Auth / sessions
    access_token_ttl_minutes: int = 720
    password_reset_ttl_minutes: int = 60
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"

    # Uploads and request limits
    media_dir: str = "media"
    media_url_prefix: str = "/media"
    max_request_bytes: int = 6 * 1024 * 1024
    max_webhook_bytes: int = 1024 * 1024
    max_image_bytes: int = 3 * 1024 * 1024
    max_csv_bytes: int = 2 * 1024 * 1024

    # Subscriptions
    enforce_subscription_limits: bool = True

    # Meta WhatsApp Cloud API (development: one shared test number from env)
    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_waba_id: str = ""
    meta_app_secret: str = ""
    meta_verify_token: str = ""
    meta_graph_api_version: str = "v21.0"
    meta_graph_base_url: str = "https://graph.facebook.com"
    meta_mode: Literal["test", "production"] = "test"
    meta_http_timeout_seconds: float = 10.0

    # Approved template names. Leave empty when a template is not approved yet:
    # the notification then falls back to free-form text inside the 24h window only.
    wa_template_language: str = "en"
    wa_template_order_confirmed: str = "order_confirmation"
    wa_template_order_shipped: str = "order_shipped"
    wa_template_order_delivered: str = "order_delivered"

    webhook_event_retention_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def meta_env_credentials_present(self) -> bool:
        return bool(self.meta_access_token and self.meta_phone_number_id)

    def production_problems(self) -> list[str]:
        problems: list[str] = []
        if self.secret_key == INSECURE_DEFAULT_SECRET:
            problems.append("SECRET_KEY must be set to a strong random value")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true behind HTTPS")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
