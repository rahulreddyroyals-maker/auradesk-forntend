from fastapi import APIRouter, Depends

from app.api.deps import AuthedSession, get_current_session
from app.models import Conversation, Message, MessageRole
from app.schemas.logs import LogEntry

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[LogEntry])
def list_logs(session: AuthedSession = Depends(get_current_session)) -> list[LogEntry]:
    clinic_conv_ids = [
        c.id
        for c in session.db.query(Conversation.id)
        .filter(Conversation.clinic_id == session.claims.clinic_id)
        .all()
    ]
    if not clinic_conv_ids:
        return []

    messages = (
        session.db.query(Message)
        .filter(
            Message.conversation_id.in_(clinic_conv_ids),
            Message.role == MessageRole.ai,
        )
        .order_by(Message.created_at.desc())
        .limit(100)
        .all()
    )

    entries: list[LogEntry] = []
    for m in messages:
        for call in m.tool_calls_json or []:
            entries.append(
                LogEntry(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    channel=m.channel.value,
                    created_at=m.created_at,
                    tool=call.get("tool", "unknown"),
                    arguments=call.get("arguments", {}),
                    result=call.get("result", {}),
                )
            )
    return entries[:100]
