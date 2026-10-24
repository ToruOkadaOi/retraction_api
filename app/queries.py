"""Bounded result queries and database-side notice summaries."""

from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session, load_only

from app.models import Retraction, RetractionReason
from app.notices import notice_type
from app.schemas import JournalStatistic, ReasonStatistic


def notice_counts(db: Session, *filters) -> dict[str, int]:
    rows = db.query(Retraction.retraction_nature, func.count(Retraction.record_id)).filter(
        *filters
    ).group_by(Retraction.retraction_nature).all()
    counts: Counter = Counter()
    for nature, count in rows:
        counts[notice_type(nature)] += count
    return dict(sorted(counts.items()))


def reason_counts(db: Session, *filters, limit: int) -> list[ReasonStatistic]:
    count = func.count(RetractionReason.id)
    rows = db.query(RetractionReason.reason, count).join(Retraction).filter(*filters).group_by(
        RetractionReason.reason
    ).order_by(count.desc(), RetractionReason.reason).limit(limit).all()
    return [ReasonStatistic(reason=reason, count=count) for reason, count in rows]


def journal_counts(db: Session, *filters, limit: int) -> list[JournalStatistic]:
    count = func.count(Retraction.record_id)
    rows = db.query(Retraction.journal, count).filter(*filters, Retraction.journal != "").group_by(
        Retraction.journal
    ).order_by(count.desc(), Retraction.journal).limit(limit).all()
    return [JournalStatistic(journal=journal, count=count) for journal, count in rows]


def article_summaries(db: Session):
    return db.query(Retraction).options(load_only(
        Retraction.record_id, Retraction.title, Retraction.journal,
        Retraction.retraction_nature, Retraction.retraction_date, Retraction.publisher,
    ))
