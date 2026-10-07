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

    # Demo / sales environment
    #
    # A standing, self-serve demo clinic that sales can point prospects
    # at (see app/api/v1/demo.py). DEMO_RESEED_TOKEN gates the one
    # destructive action (wiping and regenerating the demo clinic's
    # story data) — it is deliberately NOT a NEXT_PUBLIC_ value and
    # never reaches the frontend bundle; only you, calling the reseed
    # endpoint directly (curl/Postman) before a demo, need it. Leaving
    # it unset disables the reseed endpoint entirely (fails closed, not
    # open) while the read-only /demo/info endpoint still works.
    DEMO_RESEED_TOKEN: str = ""
    DEMO_LOGIN_EMAIL: str = "demo@auradesk.ai"
    DEMO_LOGIN_PASSWORD: str = "AuraDeskDemo2026!"
    DEMO_CLINIC_NAME: str = "Glow Aesthetic Studio"

    # Platform admin (you, managing every clinic — distinct from a clinic's
    # own owner/admin/front_desk staff roles, see app/api/v1/platform_admin.py)
    #
    # Deliberately an email allowlist, not a database table: there's no
    # migration to run, and granting yourself access is just adding your
    # own Supabase account's email here. Comma-separated for more than one
    # person. Checked against the verified JWT's own "email" claim — never
    # trust a client-supplied email instead. Leaving this unset disables
    # every /api/v1/admin/* route (fails closed, same pattern as
    # DEMO_RESEED_TOKEN above).
    PLATFORM_ADMIN_EMAILS: str = ""

    @property
    def platform_admin_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.PLATFORM_ADMIN_EMAILS.split(",") if e.strip()]

    # CORS
    #
    # Deliberately typed as a plain `str`, not `list[str]` — pydantic-
    # settings tries to JSON-decode any list-typed env var BEFORE our own
    # validation logic ever runs, and a value that isn't valid JSON
    # (which is exactly what a dashboard text box like Railway's
    # naturally produces if you don't remember the brackets/quotes)
    # crashes the whole app at startup with an opaque error, not a
    # helpful one. Keeping this as a raw string sidesteps that entirely;
    # frontend_origins_list below does our own forgiving parsing.
    #
    # Accepts EITHER a JSON array (e.g. '["https://app.example.com"]') OR
    # a plain comma-separated string (e.g. 'https://app.example.com' or
    # 'https://a.com,https://b.com'). Every value is trimmed and has any
    # trailing slash stripped, since a trailing slash on an Origin never
    # matches what the browser actually sends and silently breaks CORS
    # with no useful error.
    FRONTEND_ORIGINS: str = "http://localhost:3001"

    @property
    def frontend_origins_list(self) -> list[str]:
        raw = self.FRONTEND_ORIGINS.strip()
        if raw.startswith("["):
            import json

            try:
                parsed = json.loads(raw)
                return [str(v).strip().rstrip("/") for v in parsed]
            except json.JSONDecodeError:
                # Not valid JSON despite looking like it — fall back to
                # treating the whole thing as one origin rather than
                # crashing app startup over a formatting mistake.
                return [raw.strip().rstrip("/")]
        return [v.strip().rstrip("/") for v in raw.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
