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
        "batch_check_citations",
        "search_articles",
        "search_investigation_notes",
        "get_pubpeer_evidence",
        "get_misconduct_taxonomy",
        "search_by_misconduct_concept",
        "search_author_retractions",
        "generate_integrity_dossier",
        "analyze_retraction_timeline",
        "detect_retraction_clusters",
        "get_journal_profile",
        "get_database_summary",
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
        ("batch_check_citations", {"dois": ["10.1000/test.doi"]}),
        ("search_articles", {"query": "test"}),
        ("search_investigation_notes", {"query": "test"}),
        ("get_pubpeer_evidence", {"record_id": 1}),
        ("get_misconduct_taxonomy", {}),
        ("search_by_misconduct_concept", {"concept": "image_manipulation"}),
        ("search_author_retractions", {"author_name": "Jane Smith"}),
        ("generate_integrity_dossier", {"target_type": "author", "target_name": "Jane Smith"}),
        ("analyze_retraction_timeline", {}),
        ("detect_retraction_clusters", {"min_count": 5}),
        ("get_journal_profile", {"journal": "Test Journal"}),
        ("get_database_summary", {}),
        ("get_top_journals", {"limit": 10}),
        ("get_top_reasons", {"limit": 10}),
        ("get_top_countries", {"limit": 10}),
    ],
)
async def test_mcp_tools_call_the_api(mcp_session: ClientSession, tool_name, arguments):
    result = await mcp_session.call_tool(tool_name, arguments)

    assert result.isError is not True


@pytest.mark.anyio
async def test_mcp_resources(mcp_session: ClientSession):
    resources = await mcp_session.list_resources()
    resource_uris = {str(r.uri) for r in resources.resources}
    assert "retraction://stats/summary" in resource_uris
    assert "retraction://stats/top-reasons" in resource_uris
    assert "retraction://taxonomy" in resource_uris

    content = await mcp_session.read_resource("retraction://stats/summary")
    assert len(content.contents) == 1
    assert "total_retractions" in content.contents[0].text


@pytest.mark.anyio
async def test_mcp_prompts(mcp_session: ClientSession):
    prompts = await mcp_session.list_prompts()
    prompt_names = {p.name for p in prompts.prompts}
    assert "screen_bibliography" in prompt_names
    assert "author_integrity_audit" in prompt_names
    assert "investigate_scientific_misconduct" in prompt_names

    prompt_res = await mcp_session.get_prompt("screen_bibliography", {"citations_text": "Sample text"})
    assert len(prompt_res.messages) == 1
    assert "Sample text" in prompt_res.messages[0].content.text




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
