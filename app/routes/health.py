from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import DatasetImport
from app.schemas import DatasetMetadata, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.rollback()
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "error"}
    return {"status": "ok", "database": "ok"}


@router.get("/dataset")
def dataset_metadata(db: Session = Depends(get_db)) -> DatasetMetadata:
    try:
        metadata = db.get(DatasetImport, 1)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Dataset metadata unavailable; run ingestion") from exc
    if metadata is None:
        raise HTTPException(status_code=503, detail="Dataset metadata unavailable; run ingestion")
    return DatasetMetadata.model_validate(metadata)


@router.get("/ready")
def readiness(response: Response, db: Session = Depends(get_db)) -> ReadinessResponse:
    try:
        metadata = dataset_metadata(db)
        records = db.execute(text("SELECT COUNT(*) FROM retractions")).scalar_one()
        # Unlike the external-content table, docsize counts actual indexed documents.
        indexed = db.execute(text("SELECT COUNT(*) FROM retractions_fts_docsize")).scalar_one()
        if not records or records != metadata.record_count or indexed != records:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(status="error", database="not_ready", detail="Dataset or search index is incomplete")
    except (SQLAlchemyError, HTTPException):
        db.rollback()
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="error", database="not_ready", detail="Dataset unavailable; run ingestion")
    return ReadinessResponse(status="ok", database="ok", dataset=metadata)
