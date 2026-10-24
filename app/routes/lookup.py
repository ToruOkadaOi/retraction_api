from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db
from app.models import Retraction
from app.notices import count_notice_types
from app.schemas import (
    ArticleDetail,
    BatchLookupRequest,
    BatchLookupResponse,
    BatchRetractionItem,
    PubPeerEvidence,
)
from app.serializers import build_article_detail, compute_latency_days
from app.taxonomy import extract_pubpeer_url
from app.validation import DOIText

router = APIRouter(prefix="/lookup", tags=["lookup"])


@router.get("/doi/{doi:path}")
def lookup_by_doi(doi: DOIText, db: Session = Depends(get_db)) -> ArticleDetail:
    clean_doi = doi.strip().lower()
    r = (
        db.query(Retraction)
        .filter(
            (func.lower(func.trim(Retraction.retraction_doi)) == clean_doi)
            | (func.lower(func.trim(Retraction.original_paper_doi)) == clean_doi)
        )
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="Article not found")
    return build_article_detail(r)


@router.get("/pubmed/{pubmed_id}")
def lookup_by_pubmed(pubmed_id: int, db: Session = Depends(get_db)) -> ArticleDetail:
    r = (
        db.query(Retraction)
        .filter(
            (Retraction.retraction_pubmed_id == pubmed_id)
            | (Retraction.original_paper_pubmed_id == pubmed_id)
        )
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="Article not found")
    return build_article_detail(r)


@router.post("/batch")
def batch_lookup(
    request: BatchLookupRequest,
    db: Session = Depends(get_db),
) -> BatchLookupResponse:
    # Match and count canonical identifiers; keep the first spelling for display.
    doi_lookup_map: dict[str, str] = {}
    for doi in request.dois:
        if doi.strip():
            doi_lookup_map.setdefault(doi.strip().lower(), doi.strip())
    clean_pmids = list(dict.fromkeys(p for p in request.pubmed_ids if p > 0))

    matched_records: dict[int, tuple[Retraction, list[str]]] = {}
    matched_dois: set[str] = set()
    matched_pmids: set[int] = set()

    if doi_lookup_map:
        lower_dois = list(doi_lookup_map.keys())
        doi_records = (
            db.query(Retraction)
            .options(selectinload(Retraction.reasons))
            .filter(
                (func.lower(func.trim(Retraction.retraction_doi)).in_(lower_dois))
                | (func.lower(func.trim(Retraction.original_paper_doi)).in_(lower_dois))
            )
            .all()
        )
        for r in doi_records:
            matches = []
            orig_lower = r.original_paper_doi.strip().lower() if r.original_paper_doi else None
            ret_lower = r.retraction_doi.strip().lower() if r.retraction_doi else None
            if orig_lower in doi_lookup_map:
                orig_input = doi_lookup_map[orig_lower]
                matches.append(f"original_paper_doi: {orig_input}")
                matched_dois.add(orig_lower)
            if ret_lower in doi_lookup_map:
                ret_input = doi_lookup_map[ret_lower]
                matches.append(f"retraction_doi: {ret_input}")
                matched_dois.add(ret_lower)

            if r.record_id in matched_records:
                matched_records[r.record_id][1].extend(matches)
            else:
                matched_records[r.record_id] = (r, matches)

    if clean_pmids:
        pmid_records = (
            db.query(Retraction)
            .options(selectinload(Retraction.reasons))
            .filter(
                (Retraction.retraction_pubmed_id.in_(clean_pmids))
                | (Retraction.original_paper_pubmed_id.in_(clean_pmids))
            )
            .all()
        )
        for r in pmid_records:
            matches = []
            if r.original_paper_pubmed_id in clean_pmids:
                matches.append(f"original_paper_pmid: {r.original_paper_pubmed_id}")
                matched_pmids.add(r.original_paper_pubmed_id)
            if r.retraction_pubmed_id in clean_pmids:
                matches.append(f"retraction_pmid: {r.retraction_pubmed_id}")
                matched_pmids.add(r.retraction_pubmed_id)

            if r.record_id in matched_records:
                matched_records[r.record_id][1].extend(matches)
            else:
                matched_records[r.record_id] = (r, matches)

    retraction_items = [
        BatchRetractionItem(
            record_id=r.record_id,
            title=r.title,
            journal=r.journal,
            retraction_nature=r.retraction_nature,
            retraction_date=r.retraction_date,
            original_paper_date=r.original_paper_date,
            latency_days=compute_latency_days(r.retraction_date, r.original_paper_date),
            pubpeer_url=extract_pubpeer_url(r.notes),
            original_paper_doi=r.original_paper_doi,
            retraction_doi=r.retraction_doi,
            original_paper_pubmed_id=r.original_paper_pubmed_id,
            retraction_pubmed_id=r.retraction_pubmed_id,
            matched_by="; ".join(sorted(set(matches))),
            reasons=[reason.reason for reason in r.reasons],
        )
        for _, (r, matches) in sorted(matched_records.items())
    ]

    unmatched_dois = [display for key, display in doi_lookup_map.items() if key not in matched_dois]
    unmatched_pmids = [p for p in clean_pmids if p not in matched_pmids]

    total_screened = len(doi_lookup_map) + len(clean_pmids)
    counts_by_nature = count_notice_types(item.retraction_nature for item in retraction_items)

    return BatchLookupResponse(
        screened_count=total_screened,
        matched_identifier_count=len(matched_dois) + len(matched_pmids),
        not_found_count=len(unmatched_dois) + len(unmatched_pmids),
        matched_record_count=len(retraction_items),
        retracted_count=counts_by_nature.get("Retraction", 0),
        counts_by_nature=counts_by_nature,
        records=retraction_items,
        unmatched_dois=unmatched_dois,
        unmatched_pubmed_ids=unmatched_pmids,
    )


@router.get("/pubpeer")
def get_pubpeer_evidence(
    record_id: int | None = Query(None),
    doi: Annotated[DOIText | None, Query()] = None,
    db: Session = Depends(get_db),
) -> PubPeerEvidence:
    if not record_id and not doi:
        raise HTTPException(
            status_code=400,
            detail="Must provide either record_id or doi",
        )

    query = db.query(Retraction)
    if record_id:
        article = query.filter(Retraction.record_id == record_id).first()
    else:
        clean_doi = doi.strip().lower()
        article = query.filter(
            (func.lower(func.trim(Retraction.retraction_doi)) == clean_doi)
            | (func.lower(func.trim(Retraction.original_paper_doi)) == clean_doi)
        ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    pubpeer_url = extract_pubpeer_url(article.notes)
    if not pubpeer_url:
        raise HTTPException(
            status_code=404,
            detail="No PubPeer publication or search link found for this article",
        )

    return PubPeerEvidence(
        record_id=article.record_id,
        title=article.title,
        journal=article.journal,
        doi=article.original_paper_doi or article.retraction_doi,
        pubpeer_url=pubpeer_url,
        notes=article.notes,
    )


