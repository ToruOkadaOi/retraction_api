from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction, RetractionCountry, RetractionReason
from app.schemas import CountryStatistic, JournalStatistic, ReasonStatistic

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/top-journals")
def top_journals(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[JournalStatistic]:
    rows = (
        db.query(Retraction.journal, func.count(Retraction.record_id).label("count"))
        .filter(Retraction.journal != "")
        .group_by(Retraction.journal)
        .order_by(func.count(Retraction.record_id).desc())
        .limit(limit)
        .all()
    )
    return [JournalStatistic(journal=r.journal, count=r.count) for r in rows]


@router.get("/top-reasons")
def top_reasons(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ReasonStatistic]:
    rows = (
        db.query(RetractionReason.reason, func.count(RetractionReason.id).label("count"))
        .group_by(RetractionReason.reason)
        .order_by(func.count(RetractionReason.id).desc())
        .limit(limit)
        .all()
    )
    return [ReasonStatistic(reason=r.reason, count=r.count) for r in rows]


@router.get("/top-countries")
def top_countries(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CountryStatistic]:
    rows = (
        db.query(RetractionCountry.country, func.count(RetractionCountry.id).label("count"))
        .group_by(RetractionCountry.country)
        .order_by(func.count(RetractionCountry.id).desc())
        .limit(limit)
        .all()
    )
    return [CountryStatistic(country=r.country, count=r.count) for r in rows]
