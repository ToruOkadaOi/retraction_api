import pytest
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

import mcp_server.server as server
from mcp_server.config import MCPSettings


@pytest.fixture(scope="module")
def http_client():
    server.mcp.settings.stateless_http = True
    server.mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    app = server.mcp.streamable_http_app()
    with TestClient(app) as client:
        yield client


def test_health_route(http_client):
    resp = http_client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_initialize_over_http(http_client):
    resp = http_client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert data["result"]["serverInfo"]["name"] == "Retraction Watch API"


def test_tools_list_over_http(http_client):
    resp = http_client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
    )

    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    assert len(tools) == 16
    assert "get_article" in {tool["name"] for tool in tools}
    assert "batch_check_citations" in {tool["name"] for tool in tools}


def test_port_env_override(monkeypatch):
    monkeypatch.setenv("PORT", "9999")
    assert MCPSettings().server_port == 9999


def test_mcp_port_env(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("RETRACTION_MCP_PORT", "1234")
    assert MCPSettings().server_port == 1234


def test_default_http_settings(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("RETRACTION_MCP_PORT", raising=False)
    settings = MCPSettings()
    assert settings.mcp_host == "127.0.0.1"
    assert settings.server_port == 8000
    assert settings.mcp_transport == "stdio"
    assert settings.allowed_hosts == []
