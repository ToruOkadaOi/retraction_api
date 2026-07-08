from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction
from app.schemas import ArticleListItem, PaginatedResponse

router = APIRouter(prefix="/search", tags=["search"])

_FTS_CHARS = set('"()+-*^')


def _fts_query(raw: str) -> str:
    words = raw.strip().split()
    cleaned = []
    for w in words:
        w = "".join(c for c in w if c not in _FTS_CHARS).strip()
        if w:
            cleaned.append(w)
    return ' AND '.join(f'"{w}"*' for w in cleaned)


@router.get("")
def search_articles(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    query = _fts_query(q)
    if not query:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit)

    total = (
        db.execute(
            text("SELECT COUNT(*) FROM retractions_fts WHERE retractions_fts MATCH :q"),
            {"q": query},
        ).scalar()
    )

    rows = (
        db.execute(
            text(
                "SELECT rowid FROM retractions_fts "
                "WHERE retractions_fts MATCH :q "
                "ORDER BY rank LIMIT :limit OFFSET :skip"
            ),
            {"q": query, "limit": limit, "skip": skip},
        ).all()
    )
    matching_ids = [r[0] for r in rows]

    if not matching_ids:
        return PaginatedResponse(items=[], total=total, skip=skip, limit=limit)

    articles = (
        db.query(Retraction)
        .filter(Retraction.record_id.in_(matching_ids))
        .all()
    )
    id_map = {a.record_id: a for a in articles}
    ordered = [id_map[rid] for rid in matching_ids if rid in id_map]

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
            for r in ordered
        ],
        total=total,
        skip=skip,
        limit=limit,
    )
