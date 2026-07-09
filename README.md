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

Deployed at - https://retraction-api.onrender.com/docs

## Getting started

Clone and install:

```bash
git clone <repo-url>
cd retraction_api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Configure the environment (optional, defaults work fine since the repo ships with a pre-built `retractions.db`):

```bash
cp .env.example .env
```

Run it:

```bash
uvicorn app.main:app --reload
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive docs.

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
| `API_VERSION` | `0.0.1` | API version string |

## Data ingestion

The database can be rebuilt from the raw CSV at any time:

```bash
python scripts/ingest_csv.py
```

This reads `retraction_watch.csv`, parses dates, DOIs, PubMed IDs, and semicolon-delimited fields (countries, reasons, subjects, authors), and inserts records in batches of 500. Sentinel values (`"unavailable"` for DOIs, `"0"` for PubMed IDs) get converted to `NULL`.

The CSV bundled here is a static snapshot and won't update itself. For a more current copy, check out [retraction_watch_data](https://github.com/ToruOkadaOi/retraction_watch_data), swap it in at `data/retraction_watch.csv`, and re-run the ingestion script.

## API reference

Base URL: `http://localhost:8000`

---

### `GET /health`

Health check, verifies database connectivity.

```json
{
  "status": "ok",
  "database": "ok"
}
```

---

### `GET /articles`

List articles with optional filters and pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Number of records to skip |
| `limit` | int | 20 | Max records to return (<= 100) |
| `journal` | str | none | Filter by exact journal name |
| `publisher` | str | none | Filter by exact publisher name |
| `retraction_nature` | str | none | Filter by retraction nature (e.g. `Retraction`, `Expression of Concern`) |
| `year` | int | none | Filter by retraction year (4-digit) |

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

---

### `GET /articles/{record_id}`

Full detail for a single article by its record ID.

**Path parameter:** `record_id` (int)

```json
{
  "record_id": 123,
  "title": "Article Title",
  "journal": "Journal Name",
  "retraction_nature": "Retraction",
  "retraction_date": "2023-01-15",
  "publisher": "Publisher Name",
  "article_type": "Research Article",
  "retraction_doi": "10.1000/retraction-doi",
  "retraction_pubmed_id": 12345678,
  "original_paper_date": "2022-06-01",
  "original_paper_doi": "10.1000/original-doi",
  "original_paper_pubmed_id": 87654321,
  "paywalled": "No",
  "notes": "Some notes about the retraction",
  "institution": "University Name",
  "urls": ["https://example.com"],
  "authors": ["Author One", "Author Two"],
  "countries": ["United States"],
  "reasons": ["Fake Data"],
  "subjects": ["Biology"]
}
```

Returns 404 if the record ID doesn't exist.

---

### `GET /lookup/doi/{doi}`

Look up an article by its Retraction DOI.

**Path parameter:** `doi` (str, catch-all path)

Response is the same `ArticleDetail` shape as `GET /articles/{record_id}`. Returns 404 if the DOI isn't found.

---

### `GET /lookup/pubmed/{pubmed_id}`

Look up an article by its Retraction PubMed ID.

**Path parameter:** `pubmed_id` (int)

Response is the same `ArticleDetail` shape as `GET /articles/{record_id}`. Returns 404 if the PubMed ID isn't found.

---

### `GET /search`

Full-text search across article titles, journals, and authors.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | str | required | Search query (min 1 character) |
| `skip` | int | 0 | Number of results to skip |
| `limit` | int | 20 | Max results to return (<= 100) |

Uses SQLite FTS5 with prefix matching and AND logic. Special FTS characters (`"`, `(`, `)`, `+`, `-`, `*`, `^`) are sanitized automatically.

```
GET /search?q=cancer research
```

This searches for articles matching both `cancer*` and `research*`. Response format matches `GET /articles`, with `ArticleListItem` entries.

---

### `GET /stats/top-journals`

Top N journals with the most retractions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of results (<= 100) |

```json
[
  {"journal": "Journal of Fake Research", "count": 42},
  {"journal": "Another Journal", "count": 18}
]
```

---

### `GET /stats/top-reasons`

Top N retraction reasons.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of results (<= 100) |

```json
[
  {"reason": "Fake Data", "count": 150},
  {"reason": "Compromised Peer Review", "count": 87}
]
```

---

### `GET /stats/top-countries`

Top N countries by retraction count.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of results (<= 100) |

```json
[
  {"country": "United States", "count": 200},
  {"country": "China", "count": 175}
]
```

## Database model

Four tables:

| Table | Description |
|-------|-------------|
| `retractions` | Main table, one row per retracted article (17 columns) |
| `retraction_countries` | Many-to-many: countries associated with each retraction |
| `retraction_reasons` | Many-to-many: reasons for each retraction |
| `retraction_subjects` | Many-to-many: subject classifications |
| `retractions_fts` | FTS5 virtual table for full-text search over title, journal, and authors_raw |

Semicolon-delimited CSV fields (authors, URLs, institutions) are stored as text in `retractions` and split into lists when serialized in API responses.

## Project structure

```
app/
  main.py          -- FastAPI app entry point, CORS, lifespan, router registration
  config.py        -- Pydantic settings (DATABASE_URL, CSV_PATH, DEBUG, etc.)
  database.py      -- SQLAlchemy engine, session factory, table creation, FTS5 setup
  models.py        -- ORM models (Retraction, RetractionCountry, RetractionReason, RetractionSubject)
  schemas.py       -- Pydantic request/response schemas (ArticleListItem, ArticleDetail, PaginatedResponse)
  dependencies.py  -- get_db() dependency yielding a SQLAlchemy session
  routes/
    health.py      -- GET /health
    articles.py    -- GET /articles, GET /articles/{record_id}
    lookup.py      -- GET /lookup/doi/{doi}, /lookup/pubmed/{pubmed_id}
    search.py      -- GET /search?q=...
    statistics.py  -- GET /stats/top-journals, /stats/top-reasons, /stats/top-countries
scripts/
  ingest_csv.py    -- CSV to SQLite ingestion pipeline
  explore_csv.py   -- Exploratory CSV analysis
tests/
  conftest.py      -- In-memory SQLite fixtures, seed data, TestClient with dependency override
  test_health.py
  test_articles.py
  test_lookup.py
  test_search.py
  test_statistics.py
```

## Testing

```bash
pytest tests/
```

Tests run against an in-memory SQLite database with seed data, overriding the database dependency through FastAPI's dependency injection.

## Linting

```bash
ruff check .
```

Config lives in `pyproject.toml`.
