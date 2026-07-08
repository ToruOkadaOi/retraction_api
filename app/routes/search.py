from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction
from app.schemas import ArticleListItem, PaginatedResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search_articles(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    pattern = f"%{q}%"
    text_filter = or_(
        Retraction.title.ilike(pattern),
        Retraction.authors_raw.ilike(pattern),
        Retraction.journal.ilike(pattern),
    )

    total = (
        db.query(func.count(Retraction.record_id))
        .filter(text_filter)
        .scalar()
    )
    rows = (
        db.query(Retraction)
        .filter(text_filter)
        .order_by(Retraction.record_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(
        items=[
            ArticleListItem(
                record_id=r.record_id,
                title=r.title,
                journal=r.journal,
                retraction_nature=r.retraction_nature,
                retraction_date=r.retraction_date,
                publisher=r.publisher,
            )
            for r in rows
        ],
        total=total,
        skip=skip,
        limit=limit,
    )
