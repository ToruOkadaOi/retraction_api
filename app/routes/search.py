from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction
from app.schemas import (
    ArticleListItem,
    AuthorRetractionSummary,
    IntegrityDossier,
    JournalStatistic,
    PaginatedResponse,
    ReasonStatistic,
)

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


@router.get("/author")
def search_author(
    author: str = Query(..., min_length=2),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AuthorRetractionSummary:
    clean_author = author.strip().lower()
    author_filter = func.lower(Retraction.authors_raw).contains(clean_author)

    total = db.query(func.count(Retraction.record_id)).filter(author_filter).scalar() or 0
    all_matched = db.query(Retraction).filter(author_filter).all()

    reason_counter = Counter(
        reason.reason for r in all_matched for reason in r.reasons
    )
    journal_counter = Counter(r.journal for r in all_matched if r.journal)

    top_reasons = [
        ReasonStatistic(reason=reason, count=count)
        for reason, count in reason_counter.most_common(5)
    ]
    top_journals = [
        JournalStatistic(journal=journal, count=count)
        for journal, count in journal_counter.most_common(5)
    ]

    paged_rows = (
        db.query(Retraction)
        .filter(author_filter)
        .order_by(Retraction.record_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    articles = [
        ArticleListItem(
            record_id=r.record_id,
            title=r.title,
            journal=r.journal,
            retraction_nature=r.retraction_nature,
            retraction_date=r.retraction_date,
            publisher=r.publisher,
        )
        for r in paged_rows
    ]

    return AuthorRetractionSummary(
        author=author.strip(),
        total_retractions=total,
        top_reasons=top_reasons,
        top_journals=top_journals,
        articles=articles,
    )


@router.get("/dossier")
def get_integrity_dossier(
    target_type: str = Query("author", pattern="^(author|institution)$"),
    target_name: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
) -> IntegrityDossier:
    clean_target = target_name.strip().lower()
    if target_type == "author":
        target_filter = func.lower(Retraction.authors_raw).contains(clean_target)
    else:
        target_filter = func.lower(Retraction.institution).contains(clean_target)

    records = (
        db.query(Retraction)
        .filter(target_filter)
        .order_by(Retraction.retraction_date.desc().nullslast())
        .all()
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No records found for {target_type} '{target_name}'",
        )

    retraction_dates = [r.retraction_date for r in records if r.retraction_date]
    first_date = min(retraction_dates) if retraction_dates else None
    latest_date = max(retraction_dates) if retraction_dates else None

    reason_counter = Counter(
        reason.reason for r in records for reason in r.reasons
    )
    journal_counter = Counter(r.journal for r in records if r.journal)

    top_reasons = [
        ReasonStatistic(reason=reason, count=count)
        for reason, count in reason_counter.most_common(10)
    ]
    top_journals = [
        JournalStatistic(journal=journal, count=count)
        for journal, count in journal_counter.most_common(10)
    ]

    seen_notes = set()
    narrative_notes: list[str] = []
    for r in records:
        if r.notes and r.notes.strip() and r.notes.strip() not in seen_notes:
            seen_notes.add(r.notes.strip())
            narrative_notes.append(r.notes.strip())
            if len(narrative_notes) >= 10:
                break

    articles = [
        ArticleListItem(
            record_id=r.record_id,
            title=r.title,
            journal=r.journal,
            retraction_nature=r.retraction_nature,
            retraction_date=r.retraction_date,
            publisher=r.publisher,
        )
        for r in records[:20]
    ]

    return IntegrityDossier(
        target_type=target_type,
        target_name=target_name.strip(),
        total_retractions=len(records),
        first_retraction_date=first_date,
        latest_retraction_date=latest_date,
        top_reasons=top_reasons,
        top_journals=top_journals,
        narrative_notes=narrative_notes,
        articles=articles,
    )

