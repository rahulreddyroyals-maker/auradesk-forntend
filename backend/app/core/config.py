"""
Centralized application configuration.

All environment-dependent values live here, loaded once at startup.
Never read os.environ directly elsewhere in the app — import `settings`.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    ENVIRONMENT: str = "development"  # development | staging | production
    APP_NAME: str = "AuraDesk API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database (Supabase Postgres)
    DATABASE_URL: str  # postgresql+psycopg2://... — the RESTRICTED app role (see sql/restrict_app_role.sql). RLS actually applies to this connection.
    DATABASE_URL_ADMIN: str | None = None  # postgresql+psycopg2://... — the `postgres` table-owner role. Bypasses RLS. Used ONLY for migrations and onboarding's clinic-creation step, where no clinic_id claim can exist yet. Falls back to DATABASE_URL if unset (dev convenience before you've split the roles).
    DATABASE_URL_ASYNC: str | None = None  # postgresql+asyncpg://... (for future async use)

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    # Twilio signs each webhook request against the exact URL it called.
    # Behind a dev tunnel (ngrok) or a proxy that doesn't forward the
    # original host/proto, reconstructing that exact URL is easy to get
    # subtly wrong — so signature validation defaults OFF for local dev.
    # Set to true in production, behind HTTPS with correctly forwarded
    # headers (see app/api/v1/sms.py for what "correctly" requires).
    TWILIO_VALIDATE_SIGNATURE: bool = False

    # AI providers
    GROQ_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # Meta (Messenger / Instagram)
    META_APP_SECRET: str = ""
    META_PAGE_ACCESS_TOKEN: str = ""
    META_VERIFY_TOKEN: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Observability
    SENTRY_DSN: str = ""
    POSTHOG_API_KEY: str = ""

    # CORS
    FRONTEND_ORIGINS: list[str] = ["http://localhost:3001"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
