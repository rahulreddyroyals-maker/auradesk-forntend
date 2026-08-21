"""
Two entry points for phone calls:

  POST /calls/incoming — Twilio hits this first, on every inbound call.
  We look up the clinic by the receiving number (same pattern as SMS) and
  respond with TwiML telling Twilio to open a Media Stream back to us.

  WS /calls/media-stream — Twilio connects here for the actual call
  audio, bidirectionally, for the lifetime of the call.
"""
import base64
import json

from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.db.session import AdminSessionLocal
from app.models import Clinic
from app.orchestrator.voice_pipeline import CallSession

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/incoming")
async def incoming_call(request: Request, From: str = Form(...), To: str = Form(...), CallSid: str = Form(...)) -> Response:
    # Same reasoning as sms.py: we don't know the clinic_id until this
    # lookup resolves it, so it can't be RLS-scoped — admin connection,
    # kept to exactly this one query.
    db = AdminSessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.phone_number == To).first()
    finally:
        db.close()

    if not clinic:
        twiml = "<Response><Say>Sorry, this number isn't set up yet.</Say></Response>"
        return Response(content=twiml, media_type="application/xml")

    host = request.headers.get("host")
    stream_url = f"wss://{host}/api/v1/calls/media-stream"
    twiml = (
        "<Response><Connect><Stream url=\"" + stream_url + "\">"
        f'<Parameter name="clinic_id" value="{clinic.id}" />'
        "</Stream></Connect></Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    session: CallSession | None = None

    async def send_audio(mulaw_chunk: bytes) -> None:
        if not session:
            return
        payload = base64.b64encode(mulaw_chunk).decode("ascii")
        await websocket.send_text(
            json.dumps({"event": "media", "streamSid": session.stream_sid, "media": {"payload": payload}})
        )

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            event = data.get("event")

            if event == "start":
                start = data["start"]
                params = start.get("customParameters", {})
                session = CallSession(
                    clinic_id=params.get("clinic_id"),
                    call_sid=start.get("callSid", ""),
                    stream_sid=start.get("streamSid", ""),
                )
                session.start()

            elif event == "media" and session:
                payload = data["media"]["payload"]
                mulaw_chunk = base64.b64decode(payload)
                await session.handle_frame(mulaw_chunk, send_audio)

            elif event == "stop":
                if session:
                    session.end()
                break

    except WebSocketDisconnect:
        if session:
            session.end()
