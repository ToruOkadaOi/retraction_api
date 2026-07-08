from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction
from app.schemas import ArticleDetail, ArticleListItem, PaginatedResponse

router = APIRouter(prefix="/articles", tags=["articles"])


def _split(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(";") if p.strip()]


def _build_detail(r: Retraction) -> ArticleDetail:
    return ArticleDetail(
        record_id=r.record_id,
        title=r.title,
        journal=r.journal,
        retraction_nature=r.retraction_nature,
        retraction_date=r.retraction_date,
        publisher=r.publisher,
        article_type=r.article_type,
        retraction_doi=r.retraction_doi,
        retraction_pubmed_id=r.retraction_pubmed_id,
        original_paper_date=r.original_paper_date,
        original_paper_doi=r.original_paper_doi,
        original_paper_pubmed_id=r.original_paper_pubmed_id,
        paywalled=r.paywalled,
        notes=r.notes,
        institution=r.institution,
        urls=_split(r.urls),
        authors=_split(r.authors_raw),
        countries=[c.country for c in r.countries],
        reasons=[c.reason for c in r.reasons],
        subjects=[c.subject for c in r.subjects],
    )


@router.get("")
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    journal: str | None = Query(None),
    publisher: str | None = Query(None),
    retraction_nature: str | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    filters = []
    if journal:
        filters.append(Retraction.journal == journal)
    if publisher:
        filters.append(Retraction.publisher == publisher)
    if retraction_nature:
        filters.append(Retraction.retraction_nature == retraction_nature)
    if year:
        filters.append(func.strftime("%Y", Retraction.retraction_date) == str(year))

    total = (
        db.query(func.count(Retraction.record_id))
        .filter(*filters)
        .scalar()
    )
    rows = (
        db.query(Retraction)
        .filter(*filters)
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


@router.get("/{record_id}")
def get_article(
    record_id: int,
    db: Session = Depends(get_db),
) -> ArticleDetail:
    r = db.query(Retraction).filter(Retraction.record_id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Article not found")
    return _build_detail(r)
