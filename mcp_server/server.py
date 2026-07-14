from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from mcp_server.api_client import RetractionAPIClient
from mcp_server.config import settings

mcp = FastMCP("Retraction Watch API", json_response=True)
api_client = RetractionAPIClient(settings.base_url, settings.api_timeout)

Skip = Annotated[int, Field(ge=0, description="Number of results to skip")]
PageLimit = Annotated[int, Field(ge=1, le=100, description="Maximum results to return")]
StatsLimit = Annotated[int, Field(ge=1, le=100, description="Maximum statistics to return")]


def _dump(value: Any) -> Any:
    if isinstance(value, list):
        return [item.model_dump(mode="json") for item in value]
    return value.model_dump(mode="json")


@mcp.tool()
async def health_check() -> dict[str, str]:
    """Check whether the Retraction Watch API and its database are available."""
    return await api_client.health_check()


@mcp.tool()
async def list_articles(
    skip: Skip = 0,
    limit: PageLimit = 20,
    journal: str | None = None,
    publisher: str | None = None,
    retraction_nature: str | None = None,
    year: Annotated[int | None, Field(ge=1000, le=9999)] = None,
) -> dict[str, Any]:
    """List article summaries with optional exact-match filters and pagination."""
    result = await api_client.list_articles(
        skip=skip,
        limit=limit,
        journal=journal,
        publisher=publisher,
        retraction_nature=retraction_nature,
        year=year,
    )
    return _dump(result)


@mcp.tool()
async def get_article(record_id: Annotated[int, Field(gt=0)]) -> dict[str, Any]:
    """Get full details for an article by its Retraction Watch record ID."""
    return _dump(await api_client.get_article(record_id))


@mcp.tool()
async def lookup_article_by_doi(
    doi: Annotated[str, Field(min_length=1)],
) -> dict[str, Any]:
    """Get full article details by retraction DOI."""
    return _dump(await api_client.lookup_by_doi(doi))


@mcp.tool()
async def lookup_article_by_pubmed(
    pubmed_id: Annotated[int, Field(gt=0)],
) -> dict[str, Any]:
    """Get full article details by retraction PubMed ID."""
    return _dump(await api_client.lookup_by_pubmed(pubmed_id))


@mcp.tool()
async def search_articles(
    query: Annotated[str, Field(min_length=1)],
    skip: Skip = 0,
    limit: PageLimit = 20,
) -> dict[str, Any]:
    """Search title, journal, and author text and return ranked article summaries."""
    return _dump(
        await api_client.search_articles(
            query,
            skip=skip,
            limit=limit,
        )
    )


@mcp.tool()
async def get_top_journals(limit: StatsLimit = 10) -> list[dict[str, Any]]:
    """Get journals with the highest number of retraction records."""
    return _dump(await api_client.top_journals(limit))


@mcp.tool()
async def get_top_reasons(limit: StatsLimit = 10) -> list[dict[str, Any]]:
    """Get the most frequently recorded retraction reasons."""
    return _dump(await api_client.top_reasons(limit))


@mcp.tool()
async def get_top_countries(limit: StatsLimit = 10) -> list[dict[str, Any]]:
    """Get countries associated with the highest number of retraction records."""
    return _dump(await api_client.top_countries(limit))


def main() -> None:
    mcp.run(transport="stdio")
