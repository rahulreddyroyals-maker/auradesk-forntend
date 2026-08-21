from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    calls_today: int
    texts_today: int
    chats_today: int
    booked_today: int
    missed_leads_today: int
    revenue_today_cents: int
    upcoming_appointments: int
    conversion_rate_7d: float  # 0.0-1.0
    avg_response_seconds: float | None
    total_conversations_7d: int
