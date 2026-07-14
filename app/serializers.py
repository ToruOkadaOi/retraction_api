from app.models import Retraction
from app.schemas import ArticleDetail


def _split(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(";") if part.strip()]


def build_article_detail(retraction: Retraction) -> ArticleDetail:
    return ArticleDetail(
        record_id=retraction.record_id,
        title=retraction.title,
        journal=retraction.journal,
        retraction_nature=retraction.retraction_nature,
        retraction_date=retraction.retraction_date,
        publisher=retraction.publisher,
        article_type=retraction.article_type,
        retraction_doi=retraction.retraction_doi,
        retraction_pubmed_id=retraction.retraction_pubmed_id,
        original_paper_date=retraction.original_paper_date,
        original_paper_doi=retraction.original_paper_doi,
        original_paper_pubmed_id=retraction.original_paper_pubmed_id,
        paywalled=retraction.paywalled,
        notes=retraction.notes,
        institution=retraction.institution,
        urls=_split(retraction.urls),
        authors=_split(retraction.authors_raw),
        countries=[country.country for country in retraction.countries],
        reasons=[reason.reason for reason in retraction.reasons],
        subjects=[subject.subject for subject in retraction.subjects],
    )
