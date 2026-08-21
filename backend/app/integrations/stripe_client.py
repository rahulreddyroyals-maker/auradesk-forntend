"""
Thin wrapper around Stripe's Python SDK for subscription billing.
Untested against a live Stripe account (no keys configured yet) — same
honest status as the other external integrations in this project until
you've set STRIPE_SECRET_KEY and run through a real checkout.
"""
import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

MONTHLY_PRICE_LOOKUP_KEY = "auradesk_monthly"  # configure this Price in the Stripe dashboard


def get_or_create_customer(clinic_id: str, clinic_name: str, email: str | None = None) -> str:
    customers = stripe.Customer.list(limit=1, email=email) if email else None
    if customers and customers.data:
        return customers.data[0].id
    customer = stripe.Customer.create(name=clinic_name, email=email, metadata={"clinic_id": clinic_id})
    return customer.id


def create_checkout_session(customer_id: str, clinic_id: str, success_url: str, cancel_url: str) -> str:
    prices = stripe.Price.list(lookup_keys=[MONTHLY_PRICE_LOOKUP_KEY], limit=1)
    if not prices.data:
        raise ValueError(
            f"No Stripe Price found with lookup_key='{MONTHLY_PRICE_LOOKUP_KEY}'. "
            "Create a recurring monthly Price in the Stripe dashboard with this lookup key first."
        )
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": prices.data[0].id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"clinic_id": clinic_id},
    )
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
