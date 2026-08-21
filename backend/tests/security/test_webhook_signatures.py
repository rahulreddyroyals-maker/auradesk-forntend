"""Webhook forgery: every public webhook must reject requests that don't carry a valid signature from the actual vendor."""
import hashlib
import hmac

from app.integrations.meta_client import verify_webhook_signature


def test_meta_webhook_rejects_missing_signature(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "META_APP_SECRET", "test-secret")
    assert verify_webhook_signature(b'{"object":"page"}', None) is False


def test_meta_webhook_rejects_tampered_body(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "META_APP_SECRET", "test-secret")

    original_body = b'{"object":"page","entry":[{"id":"real-page"}]}'
    tampered_body = b'{"object":"page","entry":[{"id":"attacker-page"}]}'
    valid_sig_for_original = "sha256=" + hmac.new(b"test-secret", original_body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(tampered_body, valid_sig_for_original) is False


def test_meta_webhook_accepts_correctly_signed_body(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "META_APP_SECRET", "test-secret")

    body = b'{"object":"page","entry":[{"id":"real-page"}]}'
    correct_sig = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, correct_sig) is True


def test_twilio_webhook_rejects_when_validation_enabled_and_signature_missing(monkeypatch):
    from app.api.v1.sms import _verify_twilio_signature
    from app.core import config
    from fastapi import HTTPException
    from unittest.mock import MagicMock
    import pytest

    monkeypatch.setattr(config.settings, "TWILIO_VALIDATE_SIGNATURE", True)
    with pytest.raises(HTTPException) as exc_info:
        _verify_twilio_signature(MagicMock(), {}, None)
    assert exc_info.value.status_code == 403
