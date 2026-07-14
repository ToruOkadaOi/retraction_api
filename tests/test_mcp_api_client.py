import httpx
import pytest

from mcp_server.api_client import (
    RetractionAPIClient,
    RetractionAPIError,
    RetractionAPINotFoundError,
)

ARTICLE_SUMMARY = {
    "record_id": 1,
    "title": "Test Article",
    "journal": "Test Journal",
    "retraction_nature": "Retraction",
    "retraction_date": "2020-06-15",
    "publisher": "Test Publisher",
}

ARTICLE_DETAIL = {
    **ARTICLE_SUMMARY,
    "article_type": "Research Article",
    "retraction_doi": "10.1000/test.doi",
    "retraction_pubmed_id": 12345678,
    "original_paper_date": None,
    "original_paper_doi": None,
    "original_paper_pubmed_id": None,
    "paywalled": "No",
    "notes": None,
    "institution": None,
    "urls": [],
    "authors": ["Jane Smith"],
    "countries": ["USA"],
    "reasons": ["Fake Data"],
    "subjects": [],
}


def api_response(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/health":
        return httpx.Response(200, json={"status": "ok", "database": "ok"})
    if path == "/articles":
        return httpx.Response(
            200,
            json={"items": [ARTICLE_SUMMARY], "total": 1, "skip": 0, "limit": 20},
        )
    if path == "/search":
        return httpx.Response(
            200,
            json={"items": [ARTICLE_SUMMARY], "total": 1, "skip": 0, "limit": 20},
        )
    if path.startswith(("/articles/", "/lookup/doi/", "/lookup/pubmed/")):
        return httpx.Response(200, json=ARTICLE_DETAIL)
    if path == "/stats/top-journals":
        return httpx.Response(200, json=[{"journal": "Test Journal", "count": 2}])
    if path == "/stats/top-reasons":
        return httpx.Response(200, json=[{"reason": "Fake Data", "count": 2}])
    if path == "/stats/top-countries":
        return httpx.Response(200, json=[{"country": "USA", "count": 2}])
    return httpx.Response(404, json={"detail": "Article not found"})


@pytest.fixture
def mcp_api_client() -> RetractionAPIClient:
    return RetractionAPIClient(
        "http://api.test",
        transport=httpx.MockTransport(api_response),
    )


@pytest.mark.anyio
async def test_api_client_supports_all_read_endpoints(mcp_api_client):
    assert await mcp_api_client.health_check() == {"status": "ok", "database": "ok"}
    assert (await mcp_api_client.list_articles()).total == 1
    assert (await mcp_api_client.get_article(1)).authors == ["Jane Smith"]
    assert (await mcp_api_client.lookup_by_doi("10.1000/test.doi")).record_id == 1
    assert (await mcp_api_client.lookup_by_pubmed(12345678)).record_id == 1
    assert (await mcp_api_client.search_articles("test")).items[0].record_id == 1
    assert (await mcp_api_client.top_journals())[0].journal == "Test Journal"
    assert (await mcp_api_client.top_reasons())[0].reason == "Fake Data"
    assert (await mcp_api_client.top_countries())[0].country == "USA"


@pytest.mark.anyio
async def test_api_client_passes_filters_and_pagination():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "skip": 5, "limit": 10},
        )

    client = RetractionAPIClient(
        "http://api.test/",
        transport=httpx.MockTransport(handler),
    )
    await client.list_articles(
        skip=5,
        limit=10,
        journal="Test Journal",
        publisher="Publisher",
        retraction_nature="Retraction",
        year=2020,
    )

    params = requests[0].url.params
    assert params["skip"] == "5"
    assert params["limit"] == "10"
    assert params["journal"] == "Test Journal"
    assert params["year"] == "2020"


@pytest.mark.anyio
async def test_api_client_omits_unused_filters():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"items": [], "total": 0, "skip": 0, "limit": 20},
        )

    client = RetractionAPIClient(
        "http://api.test",
        transport=httpx.MockTransport(handler),
    )
    await client.list_articles()

    assert set(requests[0].url.params) == {"skip", "limit"}


@pytest.mark.anyio
async def test_api_client_reports_not_found():
    client = RetractionAPIClient(
        "http://api.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(404, request=request)),
    )

    with pytest.raises(RetractionAPINotFoundError, match="Article not found"):
        await client.get_article(999)


@pytest.mark.anyio
async def test_api_client_reports_connection_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = RetractionAPIClient(
        "http://api.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RetractionAPIError, match="Could not connect"):
        await client.health_check()


@pytest.mark.anyio
async def test_api_client_rejects_invalid_response():
    client = RetractionAPIClient(
        "http://api.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"unexpected": True}, request=request)
        ),
    )

    with pytest.raises(RetractionAPIError, match="invalid response"):
        await client.get_article(1)
