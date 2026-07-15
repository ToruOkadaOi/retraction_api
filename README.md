# Retraction Watch API

A REST API for querying the [Retraction Watch](https://retractionwatch.com/) database, a curated repository of retractions, expressions of concern, and corrections to academic and scientific articles. Built with FastAPI and SQLite.

## What it does

- List and filter articles by journal, publisher, retraction nature, and year
- Look up a specific article by Retraction DOI or PubMed ID
- Full-text search across titles, journals, and authors
- Aggregate stats: top journals, retraction reasons, and countries by count
- Paginated responses (configurable skip/limit, capped at 100 per page)
- Interactive OpenAPI docs at `/docs`

## Live API

Deployed at - [https://retraction-api.onrender.com/docs](https://retraction-api.onrender.com/docs)

## Getting started

```bash
git clone <repo-url>
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

## Docker

```bash
docker compose up --build
```

The API runs on port `8000` and the MCP endpoint runs at `http://localhost:8001/mcp`. The API database is validated and built into the image; mounting a host `data/` directory would mask that database.

## Configuration

Environment variables, loaded from `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
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

## MCP server

The repo includes a read-only MCP server for use with MCP clients (Claude Desktop, OpenCode, VS Code). It connects to the deployed API by default.

| Tool | Result |
|------|--------|
| `health_check` | API and database status |
| `list_articles` | Filtered, paginated article summaries |
| `get_article` | Full article details by record ID |
| `lookup_article_by_doi` | Full article details by retraction DOI |
| `lookup_article_by_pubmed` | Full article details by retraction PubMed ID |
| `search_articles` | Ranked, paginated article summaries |
| `get_top_journals` | Journals with the most retractions |
| `get_top_reasons` | Most frequently recorded retraction reasons |
| `get_top_countries` | Countries associated with the most retractions |

```bash
pip install -e ".[dev]"
python -m mcp_server
```

Set `RETRACTION_API_URL` in `.env` to override.

Local clients use `stdio` by default. To deploy a remote MCP server, build `Dockerfile.mcp` and configure Streamable HTTP:

```bash
docker build -f Dockerfile.mcp -t retraction-watch-mcp .
docker run --rm -p 8001:8000 \
  -e RETRACTION_API_URL=https://retraction-api.onrender.com \
  -e RETRACTION_MCP_ALLOWED_HOSTS=localhost:8001 \
  -e RETRACTION_MCP_ALLOWED_ORIGINS=http://localhost:8001 \
  retraction-watch-mcp
```

The MCP endpoint is `/mcp`; `/health` is available for deployment health checks. For a public hostname, replace the local allowlists with the exact external host and permitted browser origins. Non-browser MCP clients normally do not send an `Origin` header.

## Data ingestion

```bash
python scripts/ingest_csv.py
```

The importer validates the CSV, builds a temporary SQLite database, rebuilds FTS, verifies row counts, foreign keys, triggers, and `PRAGMA integrity_check`, then atomically replaces the configured database. A failed import leaves the live database untouched. It parses dates, DOIs, PubMed IDs, and semicolon-delimited fields in batches of 500; sentinel values (`"unavailable"` for DOIs, `"0"` for PubMed IDs) become `NULL`.

Run ingestion while the API is stopped. Atomic file replacement protects the database on disk, but an already-running process may retain connections to the previous SQLite file. Container deployments should build and validate a new image, pass its health check, and then replace the old container.

<details>
<summary><strong>API reference</strong></summary>

## API reference

Base URL: [https://retraction-api.onrender.com](https://retraction-api.onrender.com)

### `GET /health`

```json
{"status": "ok", "database": "ok"}
```

### `GET /articles`

Parameters: `skip` (0), `limit` (20, ≤100), `journal`, `publisher`, `retraction_nature`, `year`.

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

### `GET /articles/{record_id}`

Full detail with authors, countries, reasons, subjects, DOIs, PubMed IDs, and more. Returns 404 if not found.

### `GET /lookup/doi/{doi}`

Look up by retraction DOI. Same response as `/articles/{record_id}`.

### `GET /lookup/pubmed/{pubmed_id}`

Look up by retraction PubMed ID. Same response as `/articles/{record_id}`.

### `GET /search`

Parameters: `q` (required), `skip`, `limit`. Uses SQLite FTS5 with prefix matching and AND logic.

### `GET /stats/top-journals`

Top N journals by retraction count. Parameter: `limit` (10, ≤100).

### `GET /stats/top-reasons`

Top N retraction reasons. Parameter: `limit` (10, ≤100).

### `GET /stats/top-countries`

Top N countries by retraction count. Parameter: `limit` (10, ≤100).

</details>

## Database model

| Table | Description |
|-------|-------------|
| `retractions` | Main table, one row per retracted article (17 columns) |
| `retraction_countries` | Many-to-many: countries associated with each retraction |
| `retraction_reasons` | Many-to-many: reasons for each retraction |
| `retraction_subjects` | Many-to-many: subject classifications |
| `retractions_fts` | FTS5 virtual table for full-text search over title, journal, and authors_raw |

## Project structure

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

## Testing

```bash
pytest tests/
```

## Linting

```bash
ruff check .
```
