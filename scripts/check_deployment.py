"""Read-only smoke checks for a deployed API and its connected MCP server."""

import argparse
import asyncio
import json

import httpx


async def check_deployment(api_url: str, mcp_url: str, expected_version: str) -> None:
    async with httpx.AsyncClient(timeout=90) as client:
        async def get(path):
            response = await client.get(f"{api_url.rstrip('/')}{path}")
            response.raise_for_status()
            return response.json()

        schema = await get("/openapi.json")
        if schema["info"]["version"] != expected_version:
            raise RuntimeError(f"Expected API {expected_version}, got {schema['info']['version']}")
        ready = await get("/ready")
        if ready["status"] != "ok":
            raise RuntimeError("API is not ready")
        dataset = await get("/dataset")
        if not dataset["record_count"] or len(dataset["source_sha256"]) != 64:
            raise RuntimeError("Dataset provenance is incomplete")
        summary = await get("/stats/summary")
        if summary["total_records"] != dataset["record_count"]:
            raise RuntimeError("Dataset metadata and API counts disagree")

        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        next_id = 0

        async def rpc(method, params):
            nonlocal next_id
            next_id += 1
            response = await client.post(mcp_url, headers=headers, json={
                "jsonrpc": "2.0", "id": next_id, "method": method, "params": params,
            })
            response.raise_for_status()
            if response.headers.get("mcp-session-id"):
                headers["Mcp-Session-Id"] = response.headers["mcp-session-id"]
            body = response.json()
            if "error" in body:
                raise RuntimeError(f"MCP {method} failed: {body['error']}")
            return body["result"]

        initialized = await rpc("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "retraction-deployment-check", "version": "1.0"},
        })
        headers["MCP-Protocol-Version"] = initialized["protocolVersion"]
        response = await client.post(mcp_url, headers=headers, json={
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })
        response.raise_for_status()

        async def call(name, arguments):
            result = await rpc("tools/call", {"name": name, "arguments": arguments})
            if result.get("isError"):
                raise RuntimeError(f"MCP tool {name} failed: {result.get('content')}")
            return result.get("structuredContent") or json.loads(result["content"][0]["text"])

        mcp_dataset = await call("get_dataset_info", {})
        if mcp_dataset["source_sha256"] != dataset["source_sha256"]:
            raise RuntimeError("MCP and API are serving different dataset snapshots")
        screened = await call("batch_check_citations", {"dois": []})
        if screened.get("screened_count") != 0 or "records" not in screened or "not_found_count" not in screened:
            raise RuntimeError("MCP screening response contract is out of date")
        print(f"API {expected_version} and MCP verified: {dataset['record_count']} records, snapshot {dataset['source_sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="https://retraction-api.onrender.com")
    parser.add_argument("--mcp-url", default="https://retraction-watch-mcp.onrender.com/mcp")
    parser.add_argument("--expected-version", default="0.2.1")
    args = parser.parse_args()
    asyncio.run(check_deployment(args.api_url, args.mcp_url, args.expected_version))


if __name__ == "__main__":
    main()
