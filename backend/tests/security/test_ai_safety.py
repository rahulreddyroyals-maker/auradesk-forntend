"""AI safety: channel-specific PHI guardrails, and tool-authorization enforcement (the backend, never the LLM, decides whether a tool call is permitted)."""
from app.models import AIEmployee, ChannelType
from app.orchestrator.session import _build_system_prompt
from app.orchestrator.tools import execute_tool_call


def test_messenger_gets_phi_restriction_in_system_prompt():
    employee = AIEmployee(name="Aura", personality_prompt="")
    prompt = _build_system_prompt(employee, ChannelType.messenger)
    assert "Messenger or Instagram" in prompt
    assert "do NOT ask about or discuss specific symptoms" in prompt


def test_instagram_gets_phi_restriction_in_system_prompt():
    employee = AIEmployee(name="Aura", personality_prompt="")
    prompt = _build_system_prompt(employee, ChannelType.instagram)
    assert "Messenger or Instagram" in prompt


def test_sms_does_not_get_meta_specific_restriction():
    """SMS can carry PHI once Twilio's BAA is signed — it shouldn't inherit Meta's restriction."""
    employee = AIEmployee(name="Aura", personality_prompt="")
    prompt = _build_system_prompt(employee, ChannelType.sms)
    assert "Messenger or Instagram" not in prompt


def test_unknown_tool_name_returns_error_not_exception():
    """The LLM can request any string as a 'tool name' — the backend must never let an unrecognized one silently do nothing dangerous or crash the process."""
    from unittest.mock import MagicMock

    result = execute_tool_call(MagicMock(), "clinic-1", "conv-1", "delete_entire_database", {})
    assert "error" in result
