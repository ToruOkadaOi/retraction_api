from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from app.validation import MAX_BATCH_IDENTIFIERS, BatchDOIs, BatchPMIDs

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
    urls: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    latency_days: int | None = None
    pubpeer_url: str | None = None

    model_config = {"from_attributes": True}


class JournalStatistic(BaseModel):
    journal: str
    count: int


class ReasonStatistic(BaseModel):
    reason: str
    count: int


class CountryStatistic(BaseModel):
    country: str
    count: int


class BatchLookupRequest(BaseModel):
    dois: BatchDOIs = Field(default_factory=list)
    pubmed_ids: BatchPMIDs = Field(default_factory=list)

    @model_validator(mode="after")
    def limit_total_identifiers(self):
        if len(self.dois) + len(self.pubmed_ids) > MAX_BATCH_IDENTIFIERS:
            raise ValueError(f"At most {MAX_BATCH_IDENTIFIERS} identifiers may be submitted per batch")
        return self


class BatchRetractionItem(BaseModel):
    record_id: int
    title: str
    journal: str
    retraction_nature: str
    retraction_date: date | None = None
    original_paper_date: date | None = None
    latency_days: int | None = None
    pubpeer_url: str | None = None
    original_paper_doi: str | None = None
    retraction_doi: str | None = None
    original_paper_pubmed_id: int | None = None
    retraction_pubmed_id: int | None = None
    matched_by: str
    reasons: list[str] = Field(default_factory=list)


class PubPeerEvidence(BaseModel):
    record_id: int
    title: str
    journal: str
    doi: str | None = None
    pubpeer_url: str
    notes: str | None = None


class TaxonomyConcept(BaseModel):
    concept: str
    description: str
    tags: list[str]


class InvestigationSearchItem(ArticleListItem):
    notes_snippet: str | None = None
    pubpeer_url: str | None = None
    reasons: list[str] = Field(default_factory=list)
    institution: str | None = None



class BatchLookupResponse(BaseModel):
    screened_count: int = Field(description="Unique nonempty DOIs plus unique positive PubMed IDs screened")
    matched_identifier_count: int
    not_found_count: int = Field(description="Screened identifiers with no matching database record; not a safety assessment")
    matched_record_count: int
    retracted_count: int = Field(description="Matched records whose notice type is Retraction; not a current-status determination")
    counts_by_nature: dict[str, int]
    records: list[BatchRetractionItem]
    unmatched_dois: list[str]
    unmatched_pubmed_ids: list[int]


class LatencyDistributionBracket(BaseModel):
    bracket: str
    count: int
    percentage: float


class RetractionLatencyAnalysis(BaseModel):
    total_records_analyzed: int
    average_latency_days: float
    median_latency_days: float
    fastest_retractions: list[BatchRetractionItem]
    slowest_retractions: list[BatchRetractionItem]
    distribution: list[LatencyDistributionBracket]


class RetractionClusterItem(BaseModel):
    journal: str
    year: int
    retraction_count: int
    top_reasons: list[str]
    sample_record_ids: list[int]
    baseline_yearly_counts: dict[str, int] = Field(default_factory=dict)
    baseline_average: float = 0.0
    ratio_to_baseline: float | None = None
    is_partial_year: bool = False


class AuthorRetractionSummary(BaseModel):
    author: str
    total_records: int
    total_retractions: int
    counts_by_nature: dict[str, int]
    top_reasons: list[ReasonStatistic]
    top_journals: list[JournalStatistic]
    articles: list[ArticleListItem]


class IntegrityDossier(BaseModel):
    target_type: str
    target_name: str
    total_records: int
    total_retractions: int
    counts_by_nature: dict[str, int]
    first_retraction_date: date | None = None
    latest_retraction_date: date | None = None
    top_reasons: list[ReasonStatistic]
    top_journals: list[JournalStatistic]
    narrative_notes: list[str] = Field(default_factory=list)
    articles: list[ArticleListItem]


class JournalProfile(BaseModel):
    journal: str
    total_records: int
    total_retractions: int
    counts_by_nature: dict[str, int]
    average_latency_days: float | None = None
    top_reasons: list[ReasonStatistic]
    yearly_counts: dict[str, int]


class DatabaseSummary(BaseModel):
    total_records: int
    total_retractions: int
    unique_journals: int
    unique_publishers: int
    retraction_natures: dict[str, int]
    paywalled_counts: dict[str, int]
    top_reasons: list[ReasonStatistic]
    top_countries: list[CountryStatistic]


class DatasetMetadata(BaseModel):
    source_filename: str
    source_sha256: str
    imported_at: datetime
    record_count: int
    api_version: str

    model_config = {"from_attributes": True}


class ReadinessResponse(BaseModel):
    status: str
    database: str
    detail: str | None = None
    dataset: DatasetMetadata | None = None

