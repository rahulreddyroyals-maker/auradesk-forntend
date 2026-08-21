from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import AuthedSession, get_current_session, require_role
from app.core.config import settings
from app.db.session import AdminSessionLocal
from app.integrations import stripe_client
from app.models import Clinic, Subscription
from app.schemas.billing import CheckoutResponse, PortalResponse, SubscriptionOut

router = APIRouter(prefix="/billing", tags=["billing"])


def _get_or_create_subscription_row(db, clinic_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.clinic_id == clinic_id).first()
    if not sub:
        sub = Subscription(clinic_id=clinic_id, status="none")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(session: AuthedSession = Depends(get_current_session)) -> Subscription:
    return _get_or_create_subscription_row(session.db, session.claims.clinic_id)


@router.post("/checkout", response_model=CheckoutResponse)
def start_checkout(session: AuthedSession = Depends(require_role("owner", "admin"))) -> CheckoutResponse:
    clinic = session.db.get(Clinic, session.claims.clinic_id)
    sub = _get_or_create_subscription_row(session.db, session.claims.clinic_id)

    if not sub.stripe_customer_id:
        sub.stripe_customer_id = stripe_client.get_or_create_customer(
            str(clinic.id), clinic.name, session.claims.email
        )
        session.db.commit()

    frontend_origin = settings.FRONTEND_ORIGINS[0] if settings.FRONTEND_ORIGINS else "http://localhost:3001"
    checkout_url = stripe_client.create_checkout_session(
        customer_id=sub.stripe_customer_id,
        clinic_id=str(clinic.id),
        success_url=f"{frontend_origin}/billing?checkout=success",
        cancel_url=f"{frontend_origin}/billing?checkout=canceled",
    )
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/portal", response_model=PortalResponse)
def open_billing_portal(session: AuthedSession = Depends(require_role("owner", "admin"))) -> PortalResponse:
    sub = _get_or_create_subscription_row(session.db, session.claims.clinic_id)
    if not sub.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No billing account yet — start checkout first.")

    frontend_origin = settings.FRONTEND_ORIGINS[0] if settings.FRONTEND_ORIGINS else "http://localhost:3001"
    portal_url = stripe_client.create_billing_portal_session(sub.stripe_customer_id, f"{frontend_origin}/billing")
    return PortalResponse(portal_url=portal_url)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.construct_webhook_event(payload, sig_header)
    except Exception as exc:  # noqa: BLE001 — invalid signature or payload, reject either way
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook: {exc}") from exc

    # Same reasoning as the other webhooks: no clinic_id claim exists yet
    # (we're looking up the row BY an external identifier). Unlike the
    # SMS/social webhooks, this touches exactly one row with no loop
    # afterward, so the admin connection for the whole handler is the
    # simplest correct choice here rather than adding a handoff.
    db = AdminSessionLocal()
    try:
        obj = event["data"]["object"]
        event_type = event["type"]

        customer_id = obj.get("customer")
        if not customer_id:
            return {"status": "ignored"}

        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
        if not sub:
            return {"status": "ignored"}

        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            sub.stripe_subscription_id = obj.get("id")
            sub.status = obj.get("status", sub.status)
            period_end = obj.get("current_period_end")
            if period_end:
                sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
            items = obj.get("items", {}).get("data", [])
            if items:
                sub.plan = items[0].get("price", {}).get("lookup_key")
        elif event_type == "customer.subscription.deleted":
            sub.status = "canceled"

        db.commit()
        return {"status": "ok"}
    finally:
        db.close()
