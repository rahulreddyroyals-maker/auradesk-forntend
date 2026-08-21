import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.rate_limit import WebhookRateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

from app.api.v1 import auth as auth_router
from app.api.v1 import onboarding as onboarding_router
from app.api.v1 import services as services_router
from app.api.v1 import patients as patients_router
from app.api.v1 import knowledge_base as kb_router
from app.api.v1 import ai_employee as ai_employee_router
from app.api.v1 import conversations as conversations_router
from app.api.v1 import sms as sms_router
from app.api.v1 import calls as calls_router
from app.api.v1 import clinic as clinic_router
from app.api.v1 import social as social_router
from app.api.v1 import escalations as escalations_router
from app.api.v1 import integrations as integrations_router
from app.api.v1 import billing as billing_router
from app.api.v1 import analytics as analytics_router
from app.api.v1 import appointments as appointments_router
from app.api.v1 import team as team_router
from app.api.v1 import logs as logs_router
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
        # Never send patient content to Sentry — scrub bodies, keep only metadata.
        send_default_pii=False,
    )

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(WebhookRateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(auth_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(onboarding_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(services_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(patients_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(kb_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_employee_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(sms_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(calls_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(clinic_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(social_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(escalations_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(appointments_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(team_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(logs_router.router, prefix=settings.API_V1_PREFIX)

# This completes the Phase 0-6 roadmap. Remaining known simplifications
# (see README): keyword-based KB search instead of pgvector similarity,
# per-turn batch voice STT/TTS instead of continuous streaming, and
# RLS as a defense-in-depth layer rather than the primary tenant
# isolation boundary (the backend connects as table owner, which
# Postgres exempts from RLS — see Phase 0 notes).

# Phase 5+ still to come: swapping knowledge-base lookup from keyword
# search to pgvector similarity once an embedding provider is set, and
# analytics/billing/polish for Phase 6.

# Phase 4+ still to come: Messenger/Instagram adapters, and swapping
# knowledge-base lookup from keyword search to pgvector similarity once
# an embedding provider is set. Voice pipeline is per-turn batch STT/TTS
# (see app/orchestrator/voice_pipeline.py) — Cartesia's WebSocket
# streaming API is a natural lower-latency upgrade once this is proven.
