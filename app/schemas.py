from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


class ArticleBase(BaseModel):
    title: str
    journal: str
    retraction_nature: str
    retraction_date: date | None = None


class ArticleCreate(ArticleBase):
    record_id: int


class ArticleListItem(ArticleBase):
    record_id: int
    publisher: str | None = None

    model_config = {"from_attributes": True}


class ArticleDetail(ArticleBase):
    record_id: int
    publisher: str | None = None
    article_type: str | None = None
    retraction_doi: str | None = None
    retraction_pubmed_id: int | None = None
    original_paper_date: date | None = None
    original_paper_doi: str | None = None
    original_paper_pubmed_id: int | None = None
    paywalled: str
    notes: str | None = None
    institution: str | None = None
    urls: list[str] = []
    authors: list[str] = []
    countries: list[str] = []
    reasons: list[str] = []
    subjects: list[str] = []

    model_config = {"from_attributes": True}
