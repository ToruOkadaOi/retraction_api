from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db
from app.models import Retraction, RetractionReason
from app.notices import retraction_filter
from app.queries import article_summaries, journal_counts, notice_counts, reason_counts
from app.schemas import (
    ArticleListItem,
    AuthorRetractionSummary,
    IntegrityDossier,
    InvestigationSearchItem,
    PaginatedResponse,
    TaxonomyConcept,
)
from app.taxonomy import (
    extract_pubpeer_url,
    get_taxonomy_concepts,
    map_concept_to_tags,
)
from app.validation import FilterText, NameText, SearchText

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
    q: Annotated[SearchText, Query()],
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
                "ORDER BY rank, rowid LIMIT :limit OFFSET :skip"
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
    author: Annotated[NameText, Query()],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AuthorRetractionSummary:
    clean_author = author.strip().lower()
    author_filter = func.lower(Retraction.authors_raw).contains(clean_author, autoescape=True)

    counts_by_nature = notice_counts(db, author_filter)
    total = sum(counts_by_nature.values())
    top_reasons = reason_counts(db, author_filter, limit=5)
    top_journals = journal_counts(db, author_filter, limit=5)

    paged_rows = (
        article_summaries(db)
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
        total_records=total,
        total_retractions=counts_by_nature.get("Retraction", 0),
        counts_by_nature=counts_by_nature,
        top_reasons=top_reasons,
        top_journals=top_journals,
        articles=articles,
    )


@router.get("/dossier")
def get_integrity_dossier(
    target_name: Annotated[NameText, Query()],
    target_type: str = Query("author", pattern="^(author|institution)$"),
    db: Session = Depends(get_db),
) -> IntegrityDossier:
    clean_target = target_name.strip().lower()
    if target_type == "author":
        target_filter = func.lower(Retraction.authors_raw).contains(clean_target, autoescape=True)
    else:
        target_filter = func.lower(Retraction.institution).contains(clean_target, autoescape=True)

    counts_by_nature = notice_counts(db, target_filter)
    total = sum(counts_by_nature.values())
    if not total:
        raise HTTPException(status_code=404, detail=f"No records found for {target_type} '{target_name}'")

    first_date, latest_date = db.query(
        func.min(Retraction.retraction_date), func.max(Retraction.retraction_date)
    ).filter(target_filter, retraction_filter()).one()
    top_reasons = reason_counts(db, target_filter, limit=10)
    top_journals = journal_counts(db, target_filter, limit=10)
    trimmed_note = func.trim(Retraction.notes)
    narrative_notes = [row[0] for row in db.query(trimmed_note).filter(
        target_filter, Retraction.notes.isnot(None), trimmed_note != ""
    ).group_by(trimmed_note).order_by(
        func.max(Retraction.retraction_date).desc().nullslast(), func.min(Retraction.record_id)
    ).limit(10).all()]
    records = article_summaries(db).filter(target_filter).order_by(
        Retraction.retraction_date.desc().nullslast(), Retraction.record_id
    ).limit(20).all()

    articles = [
        ArticleListItem(
            record_id=r.record_id,
            title=r.title,
            journal=r.journal,
            retraction_nature=r.retraction_nature,
            retraction_date=r.retraction_date,
            publisher=r.publisher,
        )
        for r in records
    ]

    return IntegrityDossier(
        target_type=target_type,
        target_name=target_name.strip(),
        total_records=total,
        total_retractions=counts_by_nature.get("Retraction", 0),
        counts_by_nature=counts_by_nature,
        first_retraction_date=first_date,
        latest_retraction_date=latest_date,
        top_reasons=top_reasons,
        top_journals=top_journals,
        narrative_notes=narrative_notes,
        articles=articles,
    )


@router.get("/investigation")
def search_investigation_notes(
    q: Annotated[SearchText, Query()],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InvestigationSearchItem]:
    query = _fts_query(q)
    if not query:
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit)

    total = db.execute(
        text("SELECT COUNT(*) FROM retractions_fts WHERE retractions_fts MATCH :q"),
        {"q": query},
    ).scalar()

    rows = db.execute(
        text(
            "SELECT rowid FROM retractions_fts "
            "WHERE retractions_fts MATCH :q "
            "ORDER BY rank, rowid LIMIT :limit OFFSET :skip"
        ),
        {"q": query, "limit": limit, "skip": skip},
    ).all()

    record_ids = [r[0] for r in rows]
    if not record_ids:
        return PaginatedResponse(items=[], total=total or 0, skip=skip, limit=limit)

    records = (
        db.query(Retraction)
        .options(selectinload(Retraction.reasons))
        .filter(Retraction.record_id.in_(record_ids))
        .all()
    )
    records_by_id = {r.record_id: r for r in records}

    items = []
    for rid in record_ids:
        if rid in records_by_id:
            r = records_by_id[rid]
            notes_str = r.notes.strip() if r.notes else None
            snippet = notes_str[:300] + ("..." if notes_str and len(notes_str) > 300 else "") if notes_str else None
            items.append(
                InvestigationSearchItem(
                    record_id=r.record_id,
                    title=r.title,
                    journal=r.journal,
                    retraction_nature=r.retraction_nature,
                    retraction_date=r.retraction_date,
                    publisher=r.publisher,
                    notes_snippet=snippet,
                    pubpeer_url=extract_pubpeer_url(r.notes),
                    reasons=[reason.reason for reason in r.reasons],
                    institution=r.institution,
                )
            )

    return PaginatedResponse(
        items=items,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/taxonomy")
def get_taxonomy() -> list[TaxonomyConcept]:
    return [TaxonomyConcept(**item) for item in get_taxonomy_concepts()]


@router.get("/concept/{concept}")
def search_by_concept(
    concept: FilterText,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ArticleListItem]:
    tags = map_concept_to_tags(concept)
    if not tags:
        available = ", ".join(item["concept"] for item in get_taxonomy_concepts())
        raise HTTPException(
            status_code=404,
            detail=f"Unknown concept '{concept}'. Available concepts: {available}",
        )

    tag_filters = [
        Retraction.reasons.any(func.lower(RetractionReason.reason).contains(t.lower()))
        for t in tags
    ]
    filter_expr = tag_filters[0]
    for expr in tag_filters[1:]:
        filter_expr = filter_expr | expr

    total = db.query(func.count(Retraction.record_id)).filter(filter_expr).scalar() or 0
    records = (
        db.query(Retraction)
        .filter(filter_expr)
        .order_by(Retraction.retraction_date.desc().nullslast(), Retraction.record_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = [
        ArticleListItem(
            record_id=r.record_id,
            title=r.title,
            journal=r.journal,
            retraction_nature=r.retraction_nature,
            retraction_date=r.retraction_date,
            publisher=r.publisher,
        )
        for r in records
    ]

    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


