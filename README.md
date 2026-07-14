# Retraction Watch API

A REST API for querying the [Retraction Watch](https://retractionwatch.com/) database, a curated repository of retractions, expressions of concern, and corrections to academic and scientific articles. Built with FastAPI and SQLite.

**Live API** — [https://retraction-api.onrender.com/docs](https://retraction-api.onrender.com/docs)

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
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs).

## Docker

```bash
docker compose up --build
```

Runs on port `8000`. The `data/` directory and `.env` file get mounted into the container.

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

## Data ingestion

```bash
python scripts/ingest_csv.py
```

Parses dates, DOIs, PubMed IDs, and semicolon-delimited fields, inserts in batches of 500. Sentinel values (`"unavailable"` for DOIs, `"0"` for PubMed IDs) get converted to `NULL`.

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
