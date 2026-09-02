from typing import Any, TypeVar
from urllib.parse import quote

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.schemas import (
    ArticleDetail,
    ArticleListItem,
    AuthorRetractionSummary,
    BatchLookupResponse,
    CountryStatistic,
    DatabaseSummary,
    IntegrityDossier,
    JournalProfile,
    JournalStatistic,
    PaginatedResponse,
    ReasonStatistic,
    RetractionClusterItem,
    RetractionLatencyAnalysis,
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class RetractionAPIError(RuntimeError):
    """Raised when the Retraction Watch API cannot fulfill a request."""


class RetractionAPINotFoundError(RetractionAPIError):
    """Raised when an article lookup has no matching record."""


class RetractionAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise RetractionAPIError(
                f"Retraction Watch API timed out after {self.timeout:g} seconds"
            ) from exc
        except httpx.RequestError as exc:
            raise RetractionAPIError(
                f"Could not connect to Retraction Watch API at {self.base_url}"
            ) from exc

        if response.status_code == 404:
            raise RetractionAPINotFoundError("Article not found")
        if response.is_error:
            raise RetractionAPIError(
                f"Retraction Watch API returned HTTP {response.status_code}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RetractionAPIError("Retraction Watch API returned invalid JSON") from exc

    async def _post(self, path: str, json: Any) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.post(path, json=json)
        except httpx.TimeoutException as exc:
            raise RetractionAPIError(
                f"Retraction Watch API timed out after {self.timeout:g} seconds"
            ) from exc
        except httpx.RequestError as exc:
            raise RetractionAPIError(
                f"Could not connect to Retraction Watch API at {self.base_url}"
            ) from exc

        if response.status_code == 404:
            raise RetractionAPINotFoundError("Resource not found")
        if response.is_error:
            raise RetractionAPIError(
                f"Retraction Watch API returned HTTP {response.status_code}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RetractionAPIError("Retraction Watch API returned invalid JSON") from exc

    @staticmethod
    def _model(model: type[ResponseModel], data: Any) -> ResponseModel:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise RetractionAPIError("Retraction Watch API returned an invalid response") from exc

    @staticmethod
    def _models(model: type[ResponseModel], data: Any) -> list[ResponseModel]:
        try:
            return TypeAdapter(list[model]).validate_python(data)
        except ValidationError as exc:
            raise RetractionAPIError("Retraction Watch API returned an invalid response") from exc

    async def health_check(self) -> dict[str, str]:
        data = await self._get("/health")
        if not isinstance(data, dict) or not all(
            isinstance(data.get(key), str) for key in ("status", "database")
        ):
            raise RetractionAPIError("Retraction Watch API returned an invalid response")
        return {"status": data["status"], "database": data["database"]}

    async def list_articles(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        journal: str | None = None,
        publisher: str | None = None,
        retraction_nature: str | None = None,
        year: int | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
        reason: str | None = None,
        country: str | None = None,
        subject: str | None = None,
        institution: str | None = None,
        paywalled: str | None = None,
    ) -> PaginatedResponse[ArticleListItem]:
        optional_params = {
            "journal": journal,
            "publisher": publisher,
            "retraction_nature": retraction_nature,
            "year": year,
            "from_year": from_year,
            "to_year": to_year,
            "reason": reason,
            "country": country,
            "subject": subject,
            "institution": institution,
            "paywalled": paywalled,
        }
        params = {
            "skip": skip,
            "limit": limit,
            **{key: value for key, value in optional_params.items() if value is not None},
        }
        data = await self._get("/articles", params=params)
        try:
            return PaginatedResponse[ArticleListItem].model_validate(data)
        except ValidationError as exc:
            raise RetractionAPIError("Retraction Watch API returned an invalid response") from exc

    async def get_article(self, record_id: int) -> ArticleDetail:
        return self._model(ArticleDetail, await self._get(f"/articles/{record_id}"))

    async def lookup_by_doi(self, doi: str) -> ArticleDetail:
        encoded_doi = quote(doi, safe="/")
        return self._model(ArticleDetail, await self._get(f"/lookup/doi/{encoded_doi}"))

    async def lookup_by_pubmed(self, pubmed_id: int) -> ArticleDetail:
        return self._model(
            ArticleDetail,
            await self._get(f"/lookup/pubmed/{pubmed_id}"),
        )

    async def batch_lookup(
        self,
        dois: list[str] | None = None,
        pubmed_ids: list[int] | None = None,
    ) -> BatchLookupResponse:
        data = await self._post(
            "/lookup/batch",
            json={"dois": dois or [], "pubmed_ids": pubmed_ids or []},
        )
        return self._model(BatchLookupResponse, data)

    async def search_articles(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[ArticleListItem]:
        data = await self._get(
            "/search",
            params={"q": query, "skip": skip, "limit": limit},
        )
        try:
            return PaginatedResponse[ArticleListItem].model_validate(data)
        except ValidationError as exc:
            raise RetractionAPIError("Retraction Watch API returned an invalid response") from exc

    async def search_author(
        self,
        author: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> AuthorRetractionSummary:
        data = await self._get(
            "/search/author",
            params={"author": author, "skip": skip, "limit": limit},
        )
        return self._model(AuthorRetractionSummary, data)

    async def generate_dossier(
        self,
        target_type: str,
        target_name: str,
    ) -> IntegrityDossier:
        data = await self._get(
            "/search/dossier",
            params={"target_type": target_type, "target_name": target_name},
        )
        return self._model(IntegrityDossier, data)

    async def analyze_retraction_latency(
        self,
        *,
        journal: str | None = None,
        subject: str | None = None,
    ) -> RetractionLatencyAnalysis:
        params = {}
        if journal is not None:
            params["journal"] = journal
        if subject is not None:
            params["subject"] = subject
        data = await self._get("/stats/latency", params=params or None)
        return self._model(RetractionLatencyAnalysis, data)

    async def detect_retraction_clusters(
        self,
        *,
        min_count: int = 10,
        year: int | None = None,
    ) -> list[RetractionClusterItem]:
        params: dict[str, Any] = {"min_count": min_count}
        if year is not None:
            params["year"] = year
        data = await self._get("/stats/clusters", params=params)
        return self._models(RetractionClusterItem, data)

    async def get_journal_profile(self, journal: str) -> JournalProfile:
        encoded = quote(journal, safe="")
        data = await self._get(f"/stats/journal/{encoded}")
        return self._model(JournalProfile, data)

    async def get_database_summary(self) -> DatabaseSummary:
        data = await self._get("/stats/summary")
        return self._model(DatabaseSummary, data)

    async def top_journals(self, limit: int = 10) -> list[JournalStatistic]:
        return self._models(
            JournalStatistic,
            await self._get("/stats/top-journals", params={"limit": limit}),
        )

    async def top_reasons(self, limit: int = 10) -> list[ReasonStatistic]:
        return self._models(
            ReasonStatistic,
            await self._get("/stats/top-reasons", params={"limit": limit}),
        )

    async def top_countries(self, limit: int = 10) -> list[CountryStatistic]:
        return self._models(
            CountryStatistic,
            await self._get("/stats/top-countries", params={"limit": limit}),
        )

