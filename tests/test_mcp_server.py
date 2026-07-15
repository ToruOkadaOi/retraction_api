from collections.abc import AsyncGenerator

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

import mcp_server.server as server
from mcp_server.api_client import RetractionAPIClient
from tests.test_mcp_api_client import api_response


@pytest.fixture
async def mcp_session(monkeypatch) -> AsyncGenerator[ClientSession, None]:
    monkeypatch.setattr(
        server,
        "api_client",
        RetractionAPIClient(
            "http://api.test",
            transport=httpx.MockTransport(api_response),
        ),
    )
    async with create_connected_server_and_client_session(
        server.mcp,
        raise_exceptions=True,
    ) as session:
        yield session


@pytest.mark.anyio
async def test_mcp_exposes_only_expected_read_tools(mcp_session: ClientSession):
    result = await mcp_session.list_tools()

    assert {tool.name for tool in result.tools} == {
        "health_check",
        "list_articles",
        "get_article",
        "lookup_article_by_doi",
        "lookup_article_by_pubmed",
        "search_articles",
        "get_top_journals",
        "get_top_reasons",
        "get_top_countries",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("health_check", {}),
        ("list_articles", {"limit": 20}),
        ("get_article", {"record_id": 1}),
        ("lookup_article_by_doi", {"doi": "10.1000/test.doi"}),
        ("lookup_article_by_pubmed", {"pubmed_id": 12345678}),
        ("search_articles", {"query": "test"}),
        ("get_top_journals", {"limit": 10}),
        ("get_top_reasons", {"limit": 10}),
        ("get_top_countries", {"limit": 10}),
    ],
)
async def test_mcp_tools_call_the_api(mcp_session: ClientSession, tool_name, arguments):
    result = await mcp_session.call_tool(tool_name, arguments)

    assert result.isError is not True


@pytest.mark.anyio
async def test_mcp_validates_tool_arguments(mcp_session: ClientSession):
    result = await mcp_session.call_tool("list_articles", {"limit": 101})

    assert result.isError is True


def test_main_uses_configured_transport(monkeypatch):
    calls = []
    monkeypatch.setattr(server.settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.append(transport))

    server.main()

    assert calls == ["streamable-http"]
