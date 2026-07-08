from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Retraction
from app.routes.articles import _build_detail
from app.schemas import ArticleDetail

router = APIRouter(prefix="/lookup", tags=["lookup"])


@router.get("/doi/{doi:path}")
def lookup_by_doi(doi: str, db: Session = Depends(get_db)) -> ArticleDetail:
    r = db.query(Retraction).filter(Retraction.retraction_doi == doi).first()
    if not r:
        raise HTTPException(status_code=404, detail="Article not found")
    return _build_detail(r)


@router.get("/pubmed/{pubmed_id}")
def lookup_by_pubmed(pubmed_id: int, db: Session = Depends(get_db)) -> ArticleDetail:
    r = (
        db.query(Retraction)
        .filter(Retraction.retraction_pubmed_id == pubmed_id)
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="Article not found")
    return _build_detail(r)
