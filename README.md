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

- List and filter articles by journal, publisher, retraction nature, reason, country, subject, institution, paywalled status, PubPeer presence, and date range
- Look up articles by DOI or PubMed ID (resolving **both** original publication identifiers and retraction notices)
- Screen entire bibliographies or citation lists in batch in a single call
- Full-text search across titles, journals, authors, narrative notes, and institutions
- Surface community whistleblower reports and post-publication peer review threads from **PubPeer** (over 9,300 linked articles)
- Search standardized scientific misconduct concepts (image manipulation, fake peer review, paper mills, data fabrication)
- Generate research integrity dossiers for authors or institutions with narrative notes
- Analyze retraction timelines and latency (time between publication and retraction)
- Detect anomalous retraction clusters by journal and year (identifying potential paper mill spikes)
- Access journal profiles and aggregate database metrics
- Return paginated responses with configurable `skip` and `limit` parameters, capped at 100 records per page
- Provide interactive OpenAPI documentation at `/docs`

## MCP tools

| Tool | Result |
|---|---|
| `health_check` | API and database status |
| `list_articles` | Multi-facet filtered, paginated article summaries (including `has_pubpeer` filter) |
| `get_article` | Full article details by record ID (including latency and `pubpeer_url`) |
| `lookup_article_by_doi` | Full article details by DOI (matches original paper DOI or retraction notice DOI) |
| `lookup_article_by_pubmed` | Full article details by PubMed ID (matches original paper PMID or retraction PMID) |
| `batch_check_citations` | Screen unique DOIs/PMIDs; return matching notice records, counts by notice type, and identifiers not found |
| `search_articles` | Ranked, paginated full-text search summaries |
| `search_investigation_notes` | Search full investigation narratives, institutional committee findings, and whistleblower accounts |
| `get_pubpeer_evidence` | Retrieve a PubPeer publication or search link from the record's notes |
| `get_misconduct_taxonomy` | Standardized misconduct taxonomy (image manipulation, fake peer review, paper mill, etc.) |
| `search_by_misconduct_concept` | Search articles mapped to a standardized scientific misconduct concept |
| `search_author_retractions` | Author-specific retraction records with top journals and reasons |
| `generate_integrity_dossier` | Investigative dossier for author or institution with timeline and narrative notes |
| `analyze_retraction_timeline` | Time-to-retraction delay analytics, averages, medians, and distribution brackets |
| `detect_retraction_clusters` | Anomalous volume surges by journal and year (paper mill detection) |
| `get_journal_profile` | Detailed journal track record, annual trend, top reasons, and latency |
| `get_database_summary` | Global database summary metrics, nature breakdown, and paywalled ratio |
| `get_top_journals` | Journals with the most retractions |
| `get_top_reasons` | Most frequently recorded retraction reasons |
| `get_top_countries` | Countries associated with the most retractions |

## MCP resources

| Resource URI | Description |
|---|---|
| `retraction://stats/summary` | Global database metrics and category breakdown |
| `retraction://stats/top-reasons` | Top 25 most frequent retraction reasons |
| `retraction://stats/top-journals` | Top 25 journals with the highest retraction counts |
| `retraction://stats/top-countries` | Top 25 countries associated with retractions |
| `retraction://stats/clusters` | Active journal-year retraction clusters |
| `retraction://taxonomy` | Controlled scientific misconduct taxonomy and reason mappings |

## MCP prompts

| Prompt | Description |
|---|---|
| `screen_bibliography` | Parses citations/DOIs, calls `batch_check_citations`, and generates an audit report |
| `author_integrity_audit` | Conducts a research integrity assessment on a named researcher |
| `journal_reliability_audit`| Audits a journal's track record, latency, and volume anomalies |
| `paper_mill_investigation` | Investigates high-volume clusters and coordinated paper-mill fraud |
| `investigate_scientific_misconduct` | Conducts a deep forensic investigation using misconduct taxonomy, narrative notes, and PubPeer links |



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
| `API_VERSION` | `0.2.0` | API version string |
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

The importer validates the CSV, builds a temporary SQLite database, rebuilds FTS indexes, verifies row counts, foreign keys, triggers, `PRAGMA integrity_check`, and FTS index/content consistency, then atomically replaces the configured database. CSV validation rejects missing or duplicate headers, malformed quoting, incorrect row widths, empty titles, and invalid or duplicate positive integer record IDs. UTF-8 files with or without a byte-order mark are accepted.

FTS startup builds an index for existing articles when needed and checks existing indexes against their content table using [FTS5 integrity-check with rank=1](https://www.sqlite.org/fts5.html#the_integrity_check_command). A stale index is rebuilt and checked again; an unrecoverable error fails startup instead of silently returning incomplete search results.

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
| `GET /articles/{record_id}` | Full article details (including latency); returns 404 if the record does not exist |
| `GET /lookup/doi/{doi}` | Look up a record by original publication DOI or retraction notice DOI |
| `GET /lookup/pubmed/{pubmed_id}` | Look up a record by original publication PubMed ID or retraction notice PubMed ID |
| `POST /lookup/batch` | Screen DOIs and PubMed IDs; returns matching notice records, notice-type counts, and identifiers not found |
| `GET /lookup/pubpeer` | Retrieve a PubPeer publication or search URL and the source notes |
| `GET /search?q=...` | FTS5 search over titles, journals, authors, notes, and institutions |
| `GET /search/investigation?q=...` | Narrative FTS5 search returning institutional findings, committee notes, and PubPeer links |
| `GET /search/taxonomy` | Retrieve the standardized scientific misconduct taxonomy and concept mappings |
| `GET /search/concept/{concept}` | Search articles mapped to a standardized misconduct concept (e.g. `image_manipulation`) |
| `GET /search/author?author=...` | Author retraction search with aggregated top reasons and journals |
| `GET /search/dossier?target_type=...&target_name=...` | Investigative research integrity dossier with timeline and narrative notes |
| `GET /stats/summary` | Global summary metrics (totals, unique journals/publishers, nature breakdown) |
| `GET /stats/journal/{journal}` | Comprehensive journal profile (annual trend, top reasons, average latency) |
| `GET /stats/latency` | Time-to-retraction delay analytics, averages, medians, and distribution brackets |
| `GET /stats/clusters` | Statistical surge detector for journal-year clusters (paper mill anomaly detection) |
| `GET /stats/top-journals` | Top journals by retraction count |
| `GET /stats/top-reasons` | Most frequently recorded retraction reasons |
| `GET /stats/top-countries` | Countries associated with the most retractions |

The statistics endpoints accept `limit`, defaulting to `10` and capped at `100`.

</details>

## Version 0.2 response changes

Database matches are notice records. A correction, expression of concern, or reinstatement is not counted as a retraction. A missing database match does not establish that an article is reliable. Historical records also do not, by themselves, resolve a paper's current status; review related notices and reinstatements together.

For `POST /lookup/batch` and the MCP `batch_check_citations` tool:

| Field | Meaning |
|---|---|
| `screened_count` | Unique nonempty DOIs plus unique positive PubMed IDs submitted |
| `matched_identifier_count` | Screened identifiers matching at least one record |
| `not_found_count` | Screened identifiers with no matching record |
| `matched_record_count` | Distinct database records matched by any identifier |
| `retracted_count` | Matched records whose notice type is `Retraction` |
| `counts_by_nature` | Matched record counts by notice type |
| `records` | All matched notice records, including their original `retraction_nature` |
| `unmatched_dois`, `unmatched_pubmed_ids` | Unique identifiers not found |

DOIs are trimmed and compared case-insensitively; the first submitted spelling is retained for display. Blank DOIs and nonpositive PubMed IDs are omitted. `screened_count = matched_identifier_count + not_found_count`. A DOI and PMID pointing to one record count as two matched identifiers and one matched record; one identifier can also match several notice records.

**Client migration:** replace `clean_count` with `not_found_count` and `retractions` with `records`. Those old batch fields have been removed. `retracted_count` now counts only retraction notices, rather than all matches. Deploy the API and MCP server together and update API consumers for this response contract.

Summary, journal, author, and dossier responses now distinguish `total_records` from `total_retractions`. Notice breakdowns use `counts_by_nature` (or the existing `retraction_natures` field in the database summary), with canonical names `Retraction`, `Correction`, `Expression of concern`, and `Reinstatement`; other labels are retained.

Top journals/reasons/countries, latency statistics, and cluster counts cover retraction notices only. Journal yearly counts, top reasons, and latency also cover retractions only. Journal profiles retain counts for all notice types. Author and dossier article lists, top reasons, and top journals cover all matching notices; dossier first/latest retraction dates cover only retractions. Database-wide unique journal/publisher and paywall counts cover all notices.

PubPeer search links are preserved as search links. A publication link is preferred when both are present in the notes; a search link alone does not establish the existence of a discussion thread.

## Continuous integration

`Code CI` runs on pushes, pull requests, and manual dispatch. It runs Ruff, pytest, and full-snapshot ingestion into a temporary database on Python 3.10 and 3.13.

`Sync Retraction Data` runs on its daily schedule or manual dispatch. It runs lint and tests, downloads the source CSV, validates its structure, and ingests it into a temporary database before committing the CSV. Validation or ingestion failures stop publication. Sync runs for the same branch are serialized. The sync performs its own checks because commits made with GitHub's workflow token do not trigger a separate push workflow.

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
