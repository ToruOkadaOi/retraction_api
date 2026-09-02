import json
import logging
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.api_client import RetractionAPIClient
from mcp_server.config import settings

logger = logging.getLogger(__name__)


def _build_transport_security() -> TransportSecuritySettings | None:
    if settings.mcp_transport != "streamable-http":
        return None
    if settings.allowed_hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=settings.allowed_origins,
        )
    logger.warning(
        "RETRACTION_MCP_ALLOWED_HOSTS is not set; accepting any Host header. "
        "Set it to your public hostname to enable DNS rebinding protection."
    )
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


mcp = FastMCP(
    "Retraction Watch API",
    host=settings.mcp_host,
    port=settings.server_port,
    stateless_http=True,
    json_response=True,
    transport_security=_build_transport_security(),
)
api_client = RetractionAPIClient(settings.base_url, settings.api_timeout)

Skip = Annotated[int, Field(ge=0, description="Number of results to skip")]
PageLimit = Annotated[int, Field(ge=1, le=100, description="Maximum results to return")]
StatsLimit = Annotated[int, Field(ge=1, le=100, description="Maximum statistics to return")]


@mcp.custom_route("/health", methods=["GET"])
async def http_health_check(_request: Request) -> JSONResponse:
    """Health endpoint for hosted HTTP deployments (e.g. Render health checks)."""
    return JSONResponse({"status": "ok"})


def _dump(value: Any) -> Any:
    if isinstance(value, list):
        return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


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
    year: Annotated[int | None, Field(ge=1000, le=9999, description="Retraction year")] = None,
    from_year: Annotated[int | None, Field(ge=1000, le=9999, description="Start retraction year")] = None,
    to_year: Annotated[int | None, Field(ge=1000, le=9999, description="End retraction year")] = None,
    reason: Annotated[str | None, Field(description="Filter by retraction reason keyword")] = None,
    country: Annotated[str | None, Field(description="Filter by author country")] = None,
    subject: Annotated[str | None, Field(description="Filter by subject discipline")] = None,
    institution: Annotated[str | None, Field(description="Filter by author institution")] = None,
    paywalled: Annotated[str | None, Field(description="'Yes', 'No', or 'Unknown'")] = None,
) -> dict[str, Any]:
    """List article summaries with rich multi-facet filters and pagination."""
    result = await api_client.list_articles(
        skip=skip,
        limit=limit,
        journal=journal,
        publisher=publisher,
        retraction_nature=retraction_nature,
        year=year,
        from_year=from_year,
        to_year=to_year,
        reason=reason,
        country=country,
        subject=subject,
        institution=institution,
        paywalled=paywalled,
    )
    return _dump(result)


@mcp.tool()
async def get_article(record_id: Annotated[int, Field(gt=0)]) -> dict[str, Any]:
    """Get full details for an article by its Retraction Watch record ID."""
    return _dump(await api_client.get_article(record_id))


@mcp.tool()
async def lookup_article_by_doi(
    doi: Annotated[str, Field(min_length=1, description="Publication or retraction DOI")],
) -> dict[str, Any]:
    """Get full article details by DOI. Matches either the original paper DOI or the retraction notice DOI."""
    return _dump(await api_client.lookup_by_doi(doi))


@mcp.tool()
async def lookup_article_by_pubmed(
    pubmed_id: Annotated[int, Field(gt=0, description="Publication or retraction PubMed ID")],
) -> dict[str, Any]:
    """Get full article details by PubMed ID. Matches either the original paper PMID or the retraction notice PMID."""
    return _dump(await api_client.lookup_by_pubmed(pubmed_id))


@mcp.tool()
async def batch_check_citations(
    dois: list[str] = [],
    pubmed_ids: list[int] = [],
) -> dict[str, Any]:
    """Screen a list of DOIs and/or PubMed IDs in a single call.

    Returns an objective classification: which papers are retracted (with dates, reasons,
    and matched identifier) and which have no retraction records found in the database.
    """
    return _dump(await api_client.batch_lookup(dois=dois, pubmed_ids=pubmed_ids))


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
async def search_author_retractions(
    author_name: Annotated[str, Field(min_length=2, description="Author name to search")],
    skip: Skip = 0,
    limit: PageLimit = 20,
) -> dict[str, Any]:
    """Search an author's retraction record, returning total retractions, top reasons, journals, and articles."""
    return _dump(await api_client.search_author(author_name, skip=skip, limit=limit))


@mcp.tool()
async def generate_integrity_dossier(
    target_type: Annotated[str, Field(description="Must be 'author' or 'institution'")],
    target_name: Annotated[str, Field(min_length=2, description="Name of the author or institution")],
) -> dict[str, Any]:
    """Generate an investigative research integrity dossier synthesizing retraction count, timeline, and narrative notes."""
    return _dump(await api_client.generate_dossier(target_type=target_type, target_name=target_name))


@mcp.tool()
async def analyze_retraction_timeline(
    journal: Annotated[str | None, Field(description="Optional journal filter")] = None,
    subject: Annotated[str | None, Field(description="Optional subject discipline filter")] = None,
) -> dict[str, Any]:
    """Analyze time-to-retraction latency, average/median delay, bracket distributions, and outliers."""
    return _dump(await api_client.analyze_retraction_latency(journal=journal, subject=subject))


@mcp.tool()
async def detect_retraction_clusters(
    min_count: Annotated[int, Field(ge=1, le=500, description="Minimum retractions in a journal-year cluster")] = 10,
    year: Annotated[int | None, Field(ge=1000, le=9999, description="Optional retraction year filter")] = None,
) -> list[dict[str, Any]]:
    """Detect statistical surges in retractions by journal and year (identifying paper mill episodes or compromised special issues)."""
    return _dump(await api_client.detect_retraction_clusters(min_count=min_count, year=year))


@mcp.tool()
async def get_journal_profile(
    journal: Annotated[str, Field(min_length=1, description="Journal name")],
) -> dict[str, Any]:
    """Get a journal's complete retraction track record, annual trend, top reasons, and average latency."""
    return _dump(await api_client.get_journal_profile(journal))


@mcp.tool()
async def get_database_summary() -> dict[str, Any]:
    """Get overall Retraction Watch database metrics, counts, nature distribution, and paywalled ratio."""
    return _dump(await api_client.get_database_summary())


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


# ---------------------------------------------------------------------------
# FastMCP Resources: Browsable knowledge context
# ---------------------------------------------------------------------------


@mcp.resource("retraction://stats/summary")
async def resource_database_summary() -> str:
    """High-level summary snapshot of the Retraction Watch database."""
    data = await api_client.get_database_summary()
    return json.dumps(_dump(data), indent=2)


@mcp.resource("retraction://stats/top-reasons")
async def resource_top_reasons() -> str:
    """Top 25 most frequent retraction reasons."""
    data = await api_client.top_reasons(limit=25)
    return json.dumps(_dump(data), indent=2)


@mcp.resource("retraction://stats/top-journals")
async def resource_top_journals() -> str:
    """Top 25 journals with the highest retraction counts."""
    data = await api_client.top_journals(limit=25)
    return json.dumps(_dump(data), indent=2)


@mcp.resource("retraction://stats/top-countries")
async def resource_top_countries() -> str:
    """Top 25 countries associated with the highest retraction counts."""
    data = await api_client.top_countries(limit=25)
    return json.dumps(_dump(data), indent=2)


@mcp.resource("retraction://stats/clusters")
async def resource_retraction_clusters() -> str:
    """Active journal-year retraction clusters (potential paper mill or special issue surges)."""
    data = await api_client.detect_retraction_clusters(min_count=10)
    return json.dumps(_dump(data), indent=2)


# ---------------------------------------------------------------------------
# FastMCP Prompts: Guided workflows for AI agents
# ---------------------------------------------------------------------------


@mcp.prompt()
def screen_bibliography(citations_text: str) -> str:
    """Screen citations or a bibliography against the Retraction Watch database."""
    return (
        "Please screen the following bibliography for retracted articles, expressions of concern, "
        "or corrections. Extract all DOIs and PubMed IDs from the text, call the `batch_check_citations` "
        "tool with the extracted identifiers, and present a structured audit report with:\n"
        "1. Summary: Total screened, total retracted, and total clean citations.\n"
        "2. Flagged Works: Detail for any flagged paper (Title, Journal, Retraction Date, Reasons).\n"
        "3. Advice: Recommended actions for the authors (e.g. replacing retracted citations).\n\n"
        f"Bibliography Text:\n{citations_text}"
    )


@mcp.prompt()
def author_integrity_audit(author_name: str) -> str:
    """Conduct a research integrity assessment for an author."""
    return (
        f"Conduct a comprehensive academic integrity audit on researcher '{author_name}' using "
        "the Retraction Watch database.\n"
        "1. Call `generate_integrity_dossier` and `search_author_retractions` for the author.\n"
        "2. Summarize their total retractions, timeline (first vs latest), top journals, and recurring reasons.\n"
        "3. Review the narrative investigative notes for details from institutional committees or whistleblower investigations.\n"
        "4. Provide a factual assessment of their retraction record."
    )


@mcp.prompt()
def journal_reliability_audit(journal_name: str) -> str:
    """Audit the retraction history and integrity record of an academic journal."""
    return (
        f"Perform an integrity and reliability audit on the journal '{journal_name}'.\n"
        "1. Call `get_journal_profile` to review total retractions, annual trajectories, and top reasons.\n"
        "2. Call `analyze_retraction_timeline` with the journal name to inspect time-to-retraction velocity.\n"
        "3. Call `detect_retraction_clusters` to check if this journal has any sudden volume spikes.\n"
        "4. Summarize whether retractions appear to be rigorous post-publication self-policing or systemic vulnerability."
    )


@mcp.prompt()
def paper_mill_investigation(target: str = "") -> str:
    """Investigate coordinated fraud, paper mills, or hijacked special issues."""
    target_clause = f" focusing on '{target}'" if target else ""
    return (
        f"Investigate high-volume retraction clusters and coordinated paper-mill activity{target_clause}.\n"
        "1. Call `detect_retraction_clusters` to identify journals and years with large retraction spikes.\n"
        "2. Call `list_articles` filtering by reasons such as 'Paper Mill', 'Fake Peer Review', or 'Unreliable Data'.\n"
        "3. Synthesize the findings, identifying affected publishers, journals, and common patterns."
    )


def main() -> None:
    mcp.run(transport=settings.mcp_transport)

