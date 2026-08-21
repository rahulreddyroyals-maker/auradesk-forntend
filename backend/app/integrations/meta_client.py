"""
Meta (Messenger + Page-linked Instagram) client.

Assumes the common small-business setup: an Instagram Business account
connected to a Facebook Page. Both channels then share the same webhook
payload shape and the same Send API
(graph.facebook.com/.../me/messages, using the Page Access Token) — this
is Meta's long-established, broadly-documented integration path. The
newer standalone "Instagram API with Instagram Login" (graph.instagram.com,
no Page required) targets creators without a linked Page, which isn't
the common case for a med spa and isn't implemented here.
"""
import hashlib
import hmac

import httpx

from app.core.config import settings

GRAPH_API_VERSION = "v21.0"
SEND_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages"


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Verifies X-Hub-Signature-256. Unlike Twilio's signature (which is
    tied to the exact request URL and is fiddly behind a tunnel/proxy),
    Meta's is computed purely over the raw body + app secret — reliable
    to check even in local dev, so this is on whenever META_APP_SECRET is
    configured, no separate toggle needed.
    """
    if not settings.META_APP_SECRET:
        return True  # no secret configured yet — allow through in early dev, matches other integrations' pattern
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


def send_message(page_access_token: str, recipient_id: str, text: str) -> str:
    """Returns the Meta-assigned message id."""
    resp = httpx.post(
        SEND_API_URL,
        params={"access_token": page_access_token},
        json={"recipient": {"id": recipient_id}, "message": {"text": text}},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json().get("message_id", "")
