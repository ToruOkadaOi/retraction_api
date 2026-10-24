from collections import Counter, defaultdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, and_, case, cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject
from app.notices import notice_type, retraction_filter
from app.queries import notice_counts, reason_counts
from app.schemas import (
    BatchRetractionItem,
    CountryStatistic,
    DatabaseSummary,
    JournalProfile,
    JournalStatistic,
    LatencyDistributionBracket,
    ReasonStatistic,
    RetractionClusterItem,
    RetractionLatencyAnalysis,
)
from app.serializers import compute_latency_days
from app.validation import FilterText

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/top-journals")
def top_journals(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[JournalStatistic]:
    rows = (
        db.query(Retraction.journal, func.count(Retraction.record_id).label("count"))
        .filter(Retraction.journal != "", retraction_filter())
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
        .join(Retraction)
        .filter(retraction_filter())
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
        .join(Retraction)
        .filter(retraction_filter())
        .group_by(RetractionCountry.country)
        .order_by(func.count(RetractionCountry.id).desc())
        .limit(limit)
        .all()
    )
    return [CountryStatistic(country=r.country, count=r.count) for r in rows]


@router.get("/summary")
def get_database_summary(db: Session = Depends(get_db)) -> DatabaseSummary:
    total_records = db.query(func.count(Retraction.record_id)).scalar() or 0
    unique_journals = (
        db.query(func.count(func.distinct(Retraction.journal)))
        .filter(Retraction.journal != "")
        .scalar()
        or 0
    )
    unique_publishers = (
        db.query(func.count(func.distinct(Retraction.publisher)))
        .filter(Retraction.publisher.isnot(None))
        .scalar()
        or 0
    )

    nature_rows = (
        db.query(Retraction.retraction_nature, func.count(Retraction.record_id))
        .group_by(Retraction.retraction_nature)
        .all()
    )
    retraction_natures: Counter = Counter()
    for nature, count in nature_rows:
        retraction_natures[notice_type(nature)] += count

    paywall_rows = (
        db.query(Retraction.paywalled, func.count(Retraction.record_id))
        .group_by(Retraction.paywalled)
        .all()
    )
    paywalled_counts = {r[0]: r[1] for r in paywall_rows if r[0]}

    top_reasons_list = top_reasons(limit=10, db=db)
    top_countries_list = top_countries(limit=10, db=db)

    return DatabaseSummary(
        total_records=total_records,
        total_retractions=retraction_natures.get("Retraction", 0),
        unique_journals=unique_journals,
        unique_publishers=unique_publishers,
        retraction_natures=retraction_natures,
        paywalled_counts=paywalled_counts,
        top_reasons=top_reasons_list,
        top_countries=top_countries_list,
    )


@router.get("/journal/{journal:path}")
def get_journal_profile(journal: FilterText, db: Session = Depends(get_db)) -> JournalProfile:
    journal_filter = func.lower(Retraction.journal) == journal.strip().lower()
    counts = notice_counts(db, journal_filter)
    if not counts:
        raise HTTPException(status_code=404, detail="Journal not found")
    canonical_name = db.query(Retraction.journal).filter(journal_filter).order_by(
        Retraction.record_id
    ).first()[0]
    days = func.julianday(Retraction.retraction_date) - func.julianday(Retraction.original_paper_date)
    avg = db.query(func.avg(days)).filter(journal_filter, retraction_filter(), days >= 0).scalar()
    year_col = func.strftime("%Y", Retraction.retraction_date)
    yearly = db.query(year_col, func.count(Retraction.record_id)).filter(
        journal_filter, retraction_filter(), Retraction.retraction_date.isnot(None)
    ).group_by(year_col).order_by(year_col).all()
    return JournalProfile(
        journal=canonical_name, total_records=sum(counts.values()),
        total_retractions=counts.get("Retraction", 0), counts_by_nature=counts,
        average_latency_days=round(avg, 1) if avg is not None else None,
        top_reasons=reason_counts(db, journal_filter, retraction_filter(), limit=10),
        yearly_counts=dict(yearly),
    )


def _to_batch_item(r: Retraction) -> BatchRetractionItem:
    return BatchRetractionItem(
        record_id=r.record_id,
        title=r.title,
        journal=r.journal,
        retraction_nature=r.retraction_nature,
        retraction_date=r.retraction_date,
        original_paper_date=r.original_paper_date,
        latency_days=compute_latency_days(r.retraction_date, r.original_paper_date),
        original_paper_doi=r.original_paper_doi,
        retraction_doi=r.retraction_doi,
        original_paper_pubmed_id=r.original_paper_pubmed_id,
        retraction_pubmed_id=r.retraction_pubmed_id,
        matched_by="latency_query",
        reasons=[reason.reason for reason in r.reasons],
    )


@router.get("/latency")
def analyze_retraction_latency(
    journal: Annotated[FilterText | None, Query()] = None,
    subject: Annotated[FilterText | None, Query()] = None,
    db: Session = Depends(get_db),
) -> RetractionLatencyAnalysis:
    days = cast(func.julianday(Retraction.retraction_date) - func.julianday(Retraction.original_paper_date), Integer)
    query = db.query(Retraction).filter(retraction_filter(), days >= 0)
    if journal:
        query = query.filter(func.lower(Retraction.journal) == journal.strip().lower())
    if subject:
        query = query.filter(Retraction.subjects.any(
            func.lower(RetractionSubject.subject).contains(subject.strip().lower(), autoescape=True)
        ))
    total, average = query.with_entities(func.count(Retraction.record_id), func.avg(days)).one()
    if not total:
        return RetractionLatencyAnalysis(
            total_records_analyzed=0, average_latency_days=0.0, median_latency_days=0.0,
            fastest_retractions=[], slowest_retractions=[], distribution=[],
        )
    middle = query.with_entities(days).order_by(days).offset((total - 1) // 2).limit(
        2 if total % 2 == 0 else 1
    ).all()
    median = sum(row[0] for row in middle) / len(middle)
    bracket = case(
        (days < 365, "< 1 year"), (days < 1095, "1-3 years"),
        (days < 1825, "3-5 years"), else_="> 5 years",
    )
    counts = dict(query.with_entities(bracket, func.count(Retraction.record_id)).group_by(bracket).all())
    distribution = [LatencyDistributionBracket(
        bracket=label, count=counts.get(label, 0), percentage=round(counts.get(label, 0) / total * 100, 1)
    ) for label in ["< 1 year", "1-3 years", "3-5 years", "> 5 years"]]
    extremes = query.options(selectinload(Retraction.reasons))
    fastest = extremes.order_by(days, Retraction.record_id).limit(5).all()
    slowest = extremes.order_by(days.desc(), Retraction.record_id).limit(5).all()
    return RetractionLatencyAnalysis(
        total_records_analyzed=total, average_latency_days=round(average, 1),
        median_latency_days=round(median, 1),
        fastest_retractions=[_to_batch_item(r) for r in fastest],
        slowest_retractions=[_to_batch_item(r) for r in slowest], distribution=distribution,
    )


@router.get("/clusters")
def detect_retraction_clusters(
    min_count: int = Query(10, ge=1, le=500),
    year: int | None = Query(None, ge=1000, le=9999),
    db: Session = Depends(get_db),
) -> list[RetractionClusterItem]:
    year_col = func.strftime("%Y", Retraction.retraction_date)
    count = func.count(Retraction.record_id)
    query = db.query(Retraction.journal.label("journal"), year_col.label("year"), count.label("count")).filter(
        Retraction.journal != "", Retraction.retraction_date.isnot(None), retraction_filter()
    )
    if year:
        query = query.filter(Retraction.retraction_date >= date(year, 1, 1))
        if year < 9999:
            query = query.filter(Retraction.retraction_date < date(year + 1, 1, 1))
    selected = query.group_by(Retraction.journal, year_col).having(count >= min_count).order_by(
        count.desc(), Retraction.journal, year_col
    ).limit(50).subquery()
    clusters = db.execute(select(selected)).all()
    if not clusters:
        return []
    membership = and_(Retraction.journal == selected.c.journal, year_col == selected.c.year)
    # Rank reasons across every record in each selected group, not a sample.
    reason_count = func.count(RetractionReason.id)
    ranked_reasons = db.query(
        Retraction.journal.label("journal"), year_col.label("year"), RetractionReason.reason,
        func.row_number().over(partition_by=(Retraction.journal, year_col),
                               order_by=(reason_count.desc(), RetractionReason.reason)).label("position"),
    ).join(RetractionReason).join(selected, membership).filter(retraction_filter()).group_by(
        Retraction.journal, year_col, RetractionReason.reason
    ).subquery()
    reasons = defaultdict(list)
    for row in db.execute(select(ranked_reasons).where(ranked_reasons.c.position <= 3).order_by(
        ranked_reasons.c.journal, ranked_reasons.c.year, ranked_reasons.c.position
    )):
        reasons[row.journal, row.year].append(row.reason)
    ranked_samples = db.query(
        Retraction.journal.label("journal"), year_col.label("year"), Retraction.record_id,
        func.row_number().over(partition_by=(Retraction.journal, year_col),
                               order_by=Retraction.record_id).label("position"),
    ).join(selected, membership).filter(retraction_filter()).subquery()
    samples = defaultdict(list)
    for row in db.execute(select(ranked_samples).where(ranked_samples.c.position <= 5).order_by(
        ranked_samples.c.journal, ranked_samples.c.year, ranked_samples.c.position
    )):
        samples[row.journal, row.year].append(row.record_id)
    years = [int(row.year) for row in clusters]
    baseline_rows = db.query(Retraction.journal, year_col, count).filter(
        retraction_filter(), Retraction.journal.in_({row.journal for row in clusters}),
        year_col >= f"{min(years) - 3:04d}", year_col <= f"{max(years) - 1:04d}",
    ).group_by(Retraction.journal, year_col).all()
    historical = {(journal, y): n for journal, y, n in baseline_rows}
    result = []
    for row in clusters:
        cluster_year = int(row.year)
        baseline = {str(y): historical.get((row.journal, f"{y:04d}"), 0)
                    for y in range(cluster_year - 3, cluster_year)}
        mean = sum(baseline.values()) / 3
        result.append(RetractionClusterItem(
            journal=row.journal, year=cluster_year, retraction_count=row.count,
            top_reasons=reasons[row.journal, row.year], sample_record_ids=samples[row.journal, row.year],
            baseline_yearly_counts=baseline, baseline_average=round(mean, 2),
            ratio_to_baseline=round(row.count / mean, 2) if mean else None,
            is_partial_year=cluster_year >= date.today().year,
        ))
    return result
