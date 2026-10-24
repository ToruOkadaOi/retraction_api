from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject
from app.schemas import ArticleDetail, ArticleListItem, PaginatedResponse
from app.serializers import build_article_detail
from app.validation import FilterText

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("")
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    journal: Annotated[FilterText | None, Query()] = None,
    publisher: Annotated[FilterText | None, Query()] = None,
    retraction_nature: Annotated[FilterText | None, Query()] = None,
    year: int | None = Query(None, ge=1000, le=9999),
    from_year: int | None = Query(None, ge=1000, le=9999),
    to_year: int | None = Query(None, ge=1000, le=9999),
    reason: Annotated[FilterText | None, Query()] = None,
    country: Annotated[FilterText | None, Query()] = None,
    subject: Annotated[FilterText | None, Query()] = None,
    institution: Annotated[FilterText | None, Query()] = None,
    paywalled: Annotated[FilterText | None, Query()] = None,
    has_pubpeer: bool | None = Query(None, description="Filter for articles with/without PubPeer discussion threads"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    filters = []
    if journal:
        filters.append(func.lower(Retraction.journal) == journal.strip().lower())
    if publisher:
        filters.append(func.lower(Retraction.publisher) == publisher.strip().lower())
    if retraction_nature:
        filters.append(func.lower(Retraction.retraction_nature) == retraction_nature.strip().lower())
    if from_year and to_year and from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year must not exceed to_year")
    if year and ((from_year and year < from_year) or (to_year and year > to_year)):
        raise HTTPException(status_code=422, detail="year must be within the requested year range")
    lower_year, upper_year = year or from_year, year or to_year
    if lower_year:
        filters.append(Retraction.retraction_date >= date(lower_year, 1, 1))
    if upper_year and upper_year < 9999:
        filters.append(Retraction.retraction_date < date(upper_year + 1, 1, 1))
    if reason:
        filters.append(
            Retraction.reasons.any(
                func.lower(RetractionReason.reason).contains(reason.strip().lower(), autoescape=True)
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
                func.lower(RetractionSubject.subject).contains(subject.strip().lower(), autoescape=True)
            )
        )
    if institution:
        filters.append(func.lower(Retraction.institution).contains(institution.strip().lower(), autoescape=True))
    if paywalled:
        filters.append(func.lower(Retraction.paywalled) == paywalled.strip().lower())
    if has_pubpeer is True:
        filters.append(func.lower(Retraction.notes).contains("pubpeer.com"))
    elif has_pubpeer is False:
        filters.append(
            (Retraction.notes.is_(None)) | (~func.lower(Retraction.notes).contains("pubpeer.com"))
        )

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
