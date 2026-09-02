from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject
from app.schemas import ArticleDetail, ArticleListItem, PaginatedResponse
from app.serializers import build_article_detail

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("")
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    journal: str | None = Query(None),
    publisher: str | None = Query(None),
    retraction_nature: str | None = Query(None),
    year: int | None = Query(None),
    from_year: int | None = Query(None),
    to_year: int | None = Query(None),
    reason: str | None = Query(None),
    country: str | None = Query(None),
    subject: str | None = Query(None),
    institution: str | None = Query(None),
    paywalled: str | None = Query(None),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    filters = []
    if journal:
        filters.append(func.lower(Retraction.journal) == journal.strip().lower())
    if publisher:
        filters.append(func.lower(Retraction.publisher) == publisher.strip().lower())
    if retraction_nature:
        filters.append(func.lower(Retraction.retraction_nature) == retraction_nature.strip().lower())
    if year:
        filters.append(func.strftime("%Y", Retraction.retraction_date) == str(year))
    if from_year:
        filters.append(func.strftime("%Y", Retraction.retraction_date) >= str(from_year))
    if to_year:
        filters.append(func.strftime("%Y", Retraction.retraction_date) <= str(to_year))
    if reason:
        filters.append(
            Retraction.reasons.any(
                func.lower(RetractionReason.reason).contains(reason.strip().lower())
            )
        )
    if country:
        filters.append(
            Retraction.countries.any(
                func.lower(RetractionCountry.country) == country.strip().lower()
            )
        )
    if subject:
        filters.append(
            Retraction.subjects.any(
                func.lower(RetractionSubject.subject).contains(subject.strip().lower())
            )
        )
    if institution:
        filters.append(func.lower(Retraction.institution).contains(institution.strip().lower()))
    if paywalled:
        filters.append(func.lower(Retraction.paywalled) == paywalled.strip().lower())

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
    return build_article_detail(r)
