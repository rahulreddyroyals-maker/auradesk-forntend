from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import AuthedSession, get_current_session
from app.core.audit import record_audit_event
from app.models import Integration
from app.schemas.integrations import IntegrationOut, IntegrationUpsert

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationOut])
def list_integrations(session: AuthedSession = Depends(get_current_session)) -> list[Integration]:
    return (
        session.db.query(Integration)
        .filter(Integration.clinic_id == session.claims.clinic_id)
        .all()
    )


@router.put("", response_model=IntegrationOut)
def upsert_integration(
    payload: IntegrationUpsert, session: AuthedSession = Depends(get_current_session)
) -> Integration:
    integration = (
        session.db.query(Integration)
        .filter(Integration.clinic_id == session.claims.clinic_id, Integration.type == payload.type)
        .first()
    )
    config = {"page_id": payload.page_id, "page_access_token": payload.page_access_token}
    if integration:
        integration.config_json = config
        integration.status = "connected"
        integration.connected_at = datetime.now(timezone.utc)
    else:
        integration = Integration(
            clinic_id=session.claims.clinic_id,
            type=payload.type,
            status="connected",
            config_json=config,
            connected_at=datetime.now(timezone.utc),
        )
        session.db.add(integration)
    # Audit the credential save — but never log the token value itself,
    # only that a credential of this type was saved.
    record_audit_event(
        session.db,
        clinic_id=session.claims.clinic_id,
        event_type="integration_credentials_saved",
        actor_user_id=session.claims.user_id,
        resource_type="integration",
        integration_type=payload.type,
    )
    session.db.commit()
    session.db.refresh(integration)
    return integration
