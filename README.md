# Retraction Watch API

A REST API for querying the [Retraction Watch](https://retractionwatch.com/) database, a curated repository of retractions, expressions of concern, and corrections to academic and scientific articles. Built with FastAPI and SQLite.

## Hosted services

### API

- Interactive documentation: [retraction-api.onrender.com/docs](https://retraction-api.onrender.com/docs)
- Base URL: [retraction-api.onrender.com](https://retraction-api.onrender.com)
- Health check: [retraction-api.onrender.com/health](https://retraction-api.onrender.com/health)

### MCP server

- Streamable HTTP endpoint: `https://retraction-watch-mcp.onrender.com/mcp`
- Health check: [retraction-watch-mcp.onrender.com/health](https://retraction-watch-mcp.onrender.com/health)

The free Render instance may sleep while idle, so the first request can take roughly 30–60 seconds.

#### VS Code

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "retraction-watch": {
      "type": "http",
      "url": "https://retraction-watch-mcp.onrender.com/mcp"
    }
  }
}
```

#### OpenCode

Add this to `opencode.json`:

```json
{
  "mcp": {
    "retraction-watch": {
      "type": "remote",
      "url": "https://retraction-watch-mcp.onrender.com/mcp"
    }
  }
}
```

#### Claude Desktop

Open **Settings → Connectors** and add:

```text
https://retraction-watch-mcp.onrender.com/mcp
```

## What it does

- List and filter articles by journal, publisher, retraction nature, and year
- Look up a specific article by Retraction DOI or PubMed ID
- Full-text search across titles, journals, and authors
- Aggregate statistics for journals, retraction reasons, and countries
- Return paginated responses with configurable `skip` and `limit` parameters, capped at 100 records per page
- Provide interactive OpenAPI documentation at `/docs`

## MCP tools

| Tool | Result |
|---|---|
| `health_check` | API and database status |
| `list_articles` | Filtered, paginated article summaries |
| `get_article` | Full article details by record ID |
| `lookup_article_by_doi` | Full article details by retraction DOI |
| `lookup_article_by_pubmed` | Full article details by retraction PubMed ID |
| `search_articles` | Ranked, paginated article summaries |
| `get_top_journals` | Journals with the most retractions |
| `get_top_reasons` | Most frequently recorded retraction reasons |
| `get_top_countries` | Countries associated with the most retractions |

<details>
<summary><strong>Getting started locally</strong></summary>

```bash
git clone https://github.com/ToruOkadaOi/retraction_api.git
cd retraction_api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
cp .env.example .env
python scripts/ingest_csv.py
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs).

</details>

<details>
<summary><strong>Docker</strong></summary>

Start the API locally:

```bash
docker compose up --build
```

The API runs on port `8000`; the MCP endpoint runs at `http://localhost:8001/mcp`.

The API database is validated and built into the image. Do not mount a host `data/` directory, as it would mask the database included in the image.

Run the MCP server independently:

```bash
docker build -f Dockerfile.mcp -t retraction-watch-mcp .
docker run --rm -p 8001:8000 \
  -e RETRACTION_MCP_HOST=0.0.0.0 \
  retraction-watch-mcp
```

</details>

<details>
<summary><strong>Configuration</strong></summary>

Environment variables are loaded from `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/retraction_watch.db` | SQLAlchemy database URL |
| `CSV_PATH` | `data/retraction_watch.csv` | Path to source CSV for ingestion |
| `DEBUG` | `false` | Enable debug mode |
| `API_TITLE` | `Retraction Watch API` | OpenAPI title |
| `API_VERSION` | `0.1.0` | API version string |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Comma-separated allowed browser origins |
| `RETRACTION_API_URL` | `https://retraction-api.onrender.com` | Base URL used by the MCP server |
| `RETRACTION_API_TIMEOUT` | `10` | MCP-to-API request timeout in seconds |
| `RETRACTION_MCP_TRANSPORT` | `stdio` | MCP transport: `stdio` or `streamable-http` |
| `RETRACTION_MCP_HOST` | `127.0.0.1` | MCP HTTP bind host; use `0.0.0.0` in a container |
| `RETRACTION_MCP_PORT` | `8000` | MCP HTTP port; hosting platforms may override it with `PORT` |
| `RETRACTION_MCP_ALLOWED_HOSTS` | empty | Comma-separated HTTP Host allowlist for deployed MCP servers |
| `RETRACTION_MCP_ALLOWED_ORIGINS` | empty | Comma-separated browser Origin allowlist for deployed MCP servers |

For public MCP deployments, set `RETRACTION_MCP_ALLOWED_HOSTS` to the public hostname, such as `retraction-watch-mcp.onrender.com`, to enable DNS rebinding protection.

</details>

<details>
<summary><strong>Data ingestion</strong></summary>

```bash
python scripts/ingest_csv.py
```

The importer validates the CSV, builds a temporary SQLite database, rebuilds FTS indexes, verifies row counts, foreign keys, triggers, and `PRAGMA integrity_check`, then atomically replaces the configured database.

A failed import leaves the existing database untouched. Sentinel values (`"unavailable"` for DOIs and `"0"` for PubMed IDs) are stored as `NULL`.

Run ingestion while the API is stopped. Although atomic replacement protects the database file, a running process can retain connections to the old SQLite database. For containers, build and validate a new image, pass its health check, then replace the old container.

</details>

<details>
<summary><strong>API reference</strong></summary>

Base URL: [https://retraction-api.onrender.com](https://retraction-api.onrender.com)

### `GET /health`

```json
{"status": "ok", "database": "ok"}
```

### `GET /articles`

Parameters: `skip` (default `0`), `limit` (default `20`, maximum `100`), `journal`, `publisher`, `retraction_nature`, and `year`.

```json
{
  "items": [
    {
      "record_id": 123,
      "title": "Article Title",
      "journal": "Journal Name",
      "retraction_nature": "Retraction",
      "retraction_date": "2023-01-15",
      "publisher": "Publisher Name"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### Other endpoints

| Endpoint | Description |
|---|---|
| `GET /articles/{record_id}` | Full article details; returns 404 if the record does not exist |
| `GET /lookup/doi/{doi}` | Look up a record by retraction DOI |
| `GET /lookup/pubmed/{pubmed_id}` | Look up a record by retraction PubMed ID |
| `GET /search?q=...` | FTS5 search over titles, journals, and authors using prefix matching and AND logic |
| `GET /stats/top-journals` | Top journals by retraction count |
| `GET /stats/top-reasons` | Most frequently recorded retraction reasons |
| `GET /stats/top-countries` | Countries associated with the most retractions |

The statistics endpoints accept `limit`, defaulting to `10` and capped at `100`.

</details>

<details>
<summary><strong>Project structure</strong></summary>

```text
app/
  main.py, config.py, database.py, models.py, schemas.py, serializers.py, dependencies.py
  routes/ -- health.py, articles.py, lookup.py, search.py, statistics.py
mcp_server/
  api_client.py, config.py, server.py, __main__.py
scripts/
  ingest_csv.py, explore_csv.py, validate_csv.py
tests/
  conftest.py + test_*.py files
```

</details>
