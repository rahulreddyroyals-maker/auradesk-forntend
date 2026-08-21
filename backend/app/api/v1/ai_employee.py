from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthedSession, get_current_session
from app.models import AIEmployee, ChannelType
from app.orchestrator.session import handle_message
from app.schemas.ai_employee import AIEmployeeOut, AIEmployeeUpdate
from app.schemas.chat import TestMessageRequest, TestMessageResponse

router = APIRouter(prefix="/ai-employee", tags=["ai_employee"])


def _get_or_404(session: AuthedSession) -> AIEmployee:
    ai_employee = (
        session.db.query(AIEmployee).filter(AIEmployee.clinic_id == session.claims.clinic_id).first()
    )
    if not ai_employee:
        # Shouldn't happen — onboarding always creates one — but fail clearly if it does.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI Employee configured for this clinic yet.",
        )
    return ai_employee


@router.get("", response_model=AIEmployeeOut)
def get_ai_employee(session: AuthedSession = Depends(get_current_session)) -> AIEmployee:
    return _get_or_404(session)


@router.patch("", response_model=AIEmployeeOut)
def update_ai_employee(
    payload: AIEmployeeUpdate, session: AuthedSession = Depends(get_current_session)
) -> AIEmployee:
    ai_employee = _get_or_404(session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ai_employee, field, value)
    session.db.commit()
    session.db.refresh(ai_employee)
    return ai_employee


@router.post("/test-message", response_model=TestMessageResponse)
def send_test_message(
    payload: TestMessageRequest, session: AuthedSession = Depends(get_current_session)
) -> TestMessageResponse:
    """
    Lets the clinic owner talk to their own AI Employee from the dashboard
    before any real channel (web chat widget, SMS, voice) is wired up.
    Runs through the exact same orchestrator every channel will use.
    """
    result = handle_message(
        db=session.db,
        clinic_id=session.claims.clinic_id,
        channel=ChannelType.web_chat,
        user_message=payload.message,
        conversation_id=str(payload.conversation_id) if payload.conversation_id else None,
    )
    return TestMessageResponse(**result)
