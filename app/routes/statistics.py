import statistics
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject
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


@router.get("/summary")
def get_database_summary(db: Session = Depends(get_db)) -> DatabaseSummary:
    total_retractions = db.query(func.count(Retraction.record_id)).scalar() or 0
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
    retraction_natures = {r[0]: r[1] for r in nature_rows if r[0]}

    paywall_rows = (
        db.query(Retraction.paywalled, func.count(Retraction.record_id))
        .group_by(Retraction.paywalled)
        .all()
    )
    paywalled_counts = {r[0]: r[1] for r in paywall_rows if r[0]}

    top_reasons_list = top_reasons(limit=10, db=db)
    top_countries_list = top_countries(limit=10, db=db)

    return DatabaseSummary(
        total_retractions=total_retractions,
        unique_journals=unique_journals,
        unique_publishers=unique_publishers,
        retraction_natures=retraction_natures,
        paywalled_counts=paywalled_counts,
        top_reasons=top_reasons_list,
        top_countries=top_countries_list,
    )


@router.get("/journal/{journal:path}")
def get_journal_profile(journal: str, db: Session = Depends(get_db)) -> JournalProfile:
    clean_journal = journal.strip().lower()
    records = (
        db.query(Retraction)
        .filter(func.lower(Retraction.journal) == clean_journal)
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail="Journal not found")

    total_count = len(records)
    canonical_name = records[0].journal

    latencies = [
        (r.retraction_date - r.original_paper_date).days
        for r in records
        if r.retraction_date and r.original_paper_date
    ]
    avg_latency = round(statistics.mean(latencies), 1) if latencies else None

    reason_counts = Counter()
    for r in records:
        for reason in r.reasons:
            reason_counts[reason.reason] += 1
    top_reasons_list = [
        ReasonStatistic(reason=reason, count=count)
        for reason, count in reason_counts.most_common(10)
    ]

    yearly_counts_raw = Counter(
        str(r.retraction_date.year) for r in records if r.retraction_date
    )
    yearly_counts = dict(sorted(yearly_counts_raw.items()))

    return JournalProfile(
        journal=canonical_name,
        total_retractions=total_count,
        average_latency_days=avg_latency,
        top_reasons=top_reasons_list,
        yearly_counts=yearly_counts,
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
    journal: str | None = Query(None),
    subject: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RetractionLatencyAnalysis:
    query = db.query(Retraction).filter(
        Retraction.retraction_date.isnot(None),
        Retraction.original_paper_date.isnot(None),
    )
    if journal:
        query = query.filter(func.lower(Retraction.journal) == journal.strip().lower())
    if subject:
        query = query.filter(
            Retraction.subjects.any(
                func.lower(RetractionSubject.subject).contains(subject.strip().lower())
            )
        )

    records = query.all()
    if not records:
        return RetractionLatencyAnalysis(
            total_records_analyzed=0,
            average_latency_days=0.0,
            median_latency_days=0.0,
            fastest_retractions=[],
            slowest_retractions=[],
            distribution=[],
        )

    scored = []
    for r in records:
        days = (r.retraction_date - r.original_paper_date).days
        if days >= 0:
            scored.append((days, r))

    if not scored:
        return RetractionLatencyAnalysis(
            total_records_analyzed=0,
            average_latency_days=0.0,
            median_latency_days=0.0,
            fastest_retractions=[],
            slowest_retractions=[],
            distribution=[],
        )

    scored.sort(key=lambda item: item[0])
    days_list = [days for days, _ in scored]
    avg_latency = round(statistics.mean(days_list), 1)
    median_latency = round(float(statistics.median(days_list)), 1)

    bracket_counts = {
        "< 1 year": 0,
        "1-3 years": 0,
        "3-5 years": 0,
        "> 5 years": 0,
    }
    for days in days_list:
        if days < 365:
            bracket_counts["< 1 year"] += 1
        elif days < 1095:
            bracket_counts["1-3 years"] += 1
        elif days < 1825:
            bracket_counts["3-5 years"] += 1
        else:
            bracket_counts["> 5 years"] += 1

    total_scored = len(scored)
    distribution = [
        LatencyDistributionBracket(
            bracket=bracket,
            count=count,
            percentage=round((count / total_scored) * 100, 1),
        )
        for bracket, count in bracket_counts.items()
    ]

    fastest = [_to_batch_item(r) for _, r in scored[:5]]
    slowest = [_to_batch_item(r) for _, r in scored[-5:][::-1]]

    return RetractionLatencyAnalysis(
        total_records_analyzed=total_scored,
        average_latency_days=avg_latency,
        median_latency_days=median_latency,
        fastest_retractions=fastest,
        slowest_retractions=slowest,
        distribution=distribution,
    )


@router.get("/clusters")
def detect_retraction_clusters(
    min_count: int = Query(10, ge=1, le=500),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[RetractionClusterItem]:
    year_col = func.strftime("%Y", Retraction.retraction_date)
    query = (
        db.query(
            Retraction.journal,
            year_col.label("year"),
            func.count(Retraction.record_id).label("count"),
        )
        .filter(Retraction.journal != "", Retraction.retraction_date.isnot(None))
    )
    if year:
        query = query.filter(year_col == str(year))

    cluster_rows = (
        query.group_by(Retraction.journal, year_col)
        .having(func.count(Retraction.record_id) >= min_count)
        .order_by(func.count(Retraction.record_id).desc())
        .limit(50)
        .all()
    )

    clusters: list[RetractionClusterItem] = []
    for journal_name, cluster_year, count in cluster_rows:
        records = (
            db.query(Retraction)
            .filter(
                Retraction.journal == journal_name,
                func.strftime("%Y", Retraction.retraction_date) == cluster_year,
            )
            .limit(100)
            .all()
        )
        reason_counts = Counter(
            reason.reason for r in records for reason in r.reasons
        )
        top_reasons_for_cluster = [r for r, _ in reason_counts.most_common(3)]
        sample_ids = [r.record_id for r in records[:5]]

        clusters.append(
            RetractionClusterItem(
                journal=journal_name,
                year=int(cluster_year),
                retraction_count=count,
                top_reasons=top_reasons_for_cluster,
                sample_record_ids=sample_ids,
            )
        )

    return clusters

