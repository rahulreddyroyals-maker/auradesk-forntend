import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class KnowledgeBaseArticle(UUIDPKMixin, Base):
    """
    Source of truth the AI Employee retrieves from (RAG) before answering
    any pricing/policy/FAQ question — this is the mechanism that keeps it
    from hallucinating. embedding is generated on write via a worker
    (app/workers/kb_embedder.py) and searched with pgvector cosine distance.
    """

    __tablename__ = "knowledge_base_articles"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # pricing|policy|hours|service|general
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str] = mapped_column(String(5000), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual|imported
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
