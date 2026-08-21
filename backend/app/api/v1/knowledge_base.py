import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthedSession, get_current_session
from app.models import KnowledgeBaseArticle
from app.schemas.knowledge_base import KBArticleCreate, KBArticleOut, KBArticleUpdate

router = APIRouter(prefix="/knowledge-base", tags=["knowledge_base"])


def _to_out(article: KnowledgeBaseArticle) -> KBArticleOut:
    return KBArticleOut(
        id=article.id,
        category=article.category,
        question=article.question,
        answer=article.answer,
        source=article.source,
        updated_at=article.updated_at,
        embedded=article.embedding is not None,
    )


@router.get("", response_model=list[KBArticleOut])
def list_articles(session: AuthedSession = Depends(get_current_session)) -> list[KBArticleOut]:
    articles = (
        session.db.query(KnowledgeBaseArticle)
        .filter(KnowledgeBaseArticle.clinic_id == session.claims.clinic_id)
        .order_by(KnowledgeBaseArticle.category, KnowledgeBaseArticle.question)
        .all()
    )
    return [_to_out(a) for a in articles]


@router.post("", response_model=KBArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: KBArticleCreate, session: AuthedSession = Depends(get_current_session)
) -> KBArticleOut:
    article = KnowledgeBaseArticle(
        clinic_id=session.claims.clinic_id,
        updated_at=datetime.now(timezone.utc),
        source="manual",
        **payload.model_dump(),
    )
    session.db.add(article)
    session.db.commit()
    session.db.refresh(article)
    # NOTE: embedding generation (app/workers/kb_embedder.py) lands in Phase 2
    # alongside the RAG retrieval tool — until then, embedded stays false and
    # the AI Employee has nothing to search yet.
    return _to_out(article)


def _get_owned_article(session: AuthedSession, article_id: uuid.UUID) -> KnowledgeBaseArticle:
    article = (
        session.db.query(KnowledgeBaseArticle)
        .filter(
            KnowledgeBaseArticle.id == article_id,
            KnowledgeBaseArticle.clinic_id == session.claims.clinic_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@router.patch("/{article_id}", response_model=KBArticleOut)
def update_article(
    article_id: uuid.UUID,
    payload: KBArticleUpdate,
    session: AuthedSession = Depends(get_current_session),
) -> KBArticleOut:
    article = _get_owned_article(session, article_id)
    changed = payload.model_dump(exclude_unset=True)
    for field, value in changed.items():
        setattr(article, field, value)
    if changed:
        article.updated_at = datetime.now(timezone.utc)
        article.embedding = None  # content changed — stale embedding, needs re-generation
    session.db.commit()
    session.db.refresh(article)
    return _to_out(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: uuid.UUID, session: AuthedSession = Depends(get_current_session)
) -> None:
    article = _get_owned_article(session, article_id)
    session.db.delete(article)
    session.db.commit()
