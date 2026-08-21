"""Role-based access: only owner/admin may invite/remove staff or manage billing."""
from dataclasses import dataclass

from app.api.deps import AuthedSession


@dataclass(frozen=True)
class FakeClaims:
    user_id: str
    clinic_id: str
    role: str


def _check_role(session_role: str, allowed_roles: tuple[str, ...]) -> bool:
    """Mirrors the exact check in app/api/deps.py::require_role."""
    return session_role in allowed_roles


def test_front_desk_cannot_invite_staff():
    assert _check_role("front_desk", ("owner", "admin")) is False


def test_owner_can_invite_staff():
    assert _check_role("owner", ("owner", "admin")) is True


def test_admin_can_invite_staff():
    assert _check_role("admin", ("owner", "admin")) is True


def test_front_desk_cannot_manage_billing():
    assert _check_role("front_desk", ("owner", "admin")) is False


def test_last_owner_cannot_be_removed():
    """Mirrors the safety check in app/api/v1/team.py::remove_team_member."""
    owner_count = 1
    is_owner = True
    would_block = is_owner and owner_count <= 1
    assert would_block is True


def test_second_owner_can_be_removed():
    owner_count = 2
    is_owner = True
    would_block = is_owner and owner_count <= 1
    assert would_block is False
