# Maintenance and deployment

Setup and usage are in the [README](../README.md).

Data source: [Crossref's Retraction Watch dataset](https://gitlab.com/crossref/retraction-watch-data). See the [dataset field definitions](https://retractionwatch.com/retraction-watch-database-user-guide/retraction-watch-database-user-guide-appendix-a-fields/) for the meaning of each source field.

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

## Request limits and query behavior

Batch screening accepts at most **200 combined DOIs and PubMed IDs**, counting input entries before deduplication. DOI strings are limited to 2,048 characters and PubMed IDs to signed 64-bit integers. Split larger requests into batches; both HTTP and MCP reject oversized inputs before issuing database queries.

Full-text queries are trimmed, must contain non-whitespace text, and are limited to 500 characters. Author and dossier names require 2–300 trimmed characters; other text filters accept 1–300. `%` and `_` are literal characters in substring filters. Article year filters are validated and use date ranges. Case-insensitive DOI lookups use expression indexes; startup creates those indexes for existing databases as well as new imports.

Author, dossier, and journal summaries aggregate in SQL and load bounded result pages. Latency counts, means, medians, and brackets are computed with database queries; only the ten extreme records and their reasons are loaded for the response.

Cluster top reasons cover every retraction in each journal/year group. Sample IDs are ordered deterministically. `baseline_yearly_counts` contains the preceding three calendar years, including zeros for years with no recorded notices; `baseline_average` is their mean and `ratio_to_baseline` is null when the mean is zero. `is_partial_year` flags the current year or a future-dated group. These are descriptive comparisons within the dataset, not estimates of retraction rates, tests of statistical significance, or proof of paper-mill activity. Coverage changes and partial years affect comparisons.

## Data quality, readiness, and deployment

Ingestion supports the source's month/day/year dates with 24-hour times or AM/PM times including seconds, date-only values, and ISO dates. Blank dates remain null. An unrecognized populated date fails the import with its Record ID, field name, and value; the previous database remains in place. The source hash is checked before and after processing to detect changes during import.

Each imported database contains its source filename, SHA-256 snapshot identifier, UTC import time, record count, and importer API version. `/dataset`, the MCP `get_dataset_info` tool, and `retraction://dataset` expose this provenance. The hash identifies the exact CSV bytes, including formatting; import time is not the upstream publication time.

`/health` checks basic connectivity. **Use `/ready` for hosting readiness checks**: it requires import metadata, a nonempty database, and matching metadata, article, and indexed-document counts. Startup separately performs the complete FTS index/content integrity check. The MCP server also has `/ready`, which checks the upstream API's readiness. Existing databases without metadata need to be reingested; metadata is not fabricated from an old database.

For this release, rebuild the API image to import the snapshot and metadata, deploy the matching MCP image, and configure both hosting health-check paths as `/ready`. Verify a deployment with:

```bash
python scripts/check_deployment.py --expected-version 0.2.1
```

The script checks the API version, readiness, dataset counts, matching API/MCP snapshot hashes, and the screening response contract. `--api-url` and `--mcp-url` allow the same checks against local containers.

Both Docker images and CI install exact runtime versions from `requirements.lock`; tests and local development use `requirements-dev.lock`, constrained to those same runtime versions. These files include package hashes and platform/Python markers. The local `uv.lock` is not used by this workflow. Docker copies only the source and data each service needs; virtual environments and caches are excluded.

To intentionally refresh dependencies, regenerate both locks, then run the test suite and both container smoke tests:

```bash
uv pip compile pyproject.toml --universal --python-version 3.10 --generate-hashes --output-file requirements.lock --no-annotate --upgrade
uv pip compile pyproject.toml --extra dev --universal --python-version 3.10 --generate-hashes --constraint requirements.lock --output-file requirements-dev.lock --no-annotate --upgrade
```

## Continuous integration

`Code CI` runs on pushes, pull requests, and manual dispatch. It installs hash-pinned dependencies, runs Ruff, pytest, and full-snapshot ingestion into a temporary database on Python 3.10 and 3.13. A separate job builds both Docker images and tests API readiness, dataset provenance, and MCP responses together.

`Sync Retraction Data` runs on its daily schedule or manual dispatch. It runs lint and tests, downloads the source CSV, validates its structure, and ingests it into a temporary database before committing the CSV. Validation or ingestion failures stop publication. Sync runs for the same branch are serialized. The sync performs its own checks because commits made with GitHub's workflow token do not trigger a separate push workflow.

## Configuration

Environment variables are loaded from `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/retraction_watch.db` | SQLAlchemy database URL |
| `CSV_PATH` | `retraction_watch.csv` | Path to source CSV for ingestion |
| `DEBUG` | `false` | Enable debug mode |
| `API_TITLE` | `Retraction Watch API` | OpenAPI title |
| `API_VERSION` | `0.2.1` | API version string |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Comma-separated allowed browser origins |
| `RETRACTION_API_URL` | `https://retraction-api.onrender.com` | Base URL used by the MCP server |
| `RETRACTION_API_TIMEOUT` | `10` | MCP-to-API request timeout in seconds |
| `RETRACTION_MCP_TRANSPORT` | `stdio` | MCP transport: `stdio` or `streamable-http` |
| `RETRACTION_MCP_HOST` | `127.0.0.1` | MCP HTTP bind host; use `0.0.0.0` in a container |
| `RETRACTION_MCP_PORT` | `8000` | MCP HTTP port; hosting platforms may override it with `PORT` |
| `RETRACTION_MCP_ALLOWED_HOSTS` | empty | Comma-separated HTTP Host allowlist for deployed MCP servers |
| `RETRACTION_MCP_ALLOWED_ORIGINS` | empty | Comma-separated browser Origin allowlist for deployed MCP servers |

For public MCP deployments, set `RETRACTION_MCP_ALLOWED_HOSTS` to the public hostname, such as `retraction-watch-mcp.onrender.com`, to enable DNS rebinding protection.

## Data ingestion

```bash
python scripts/ingest_csv.py
```

The importer validates the CSV, builds a temporary SQLite database, rebuilds FTS indexes, verifies row counts, foreign keys, triggers, `PRAGMA integrity_check`, and FTS index/content consistency, then atomically replaces the configured database. CSV validation rejects missing or duplicate headers, malformed quoting, incorrect row widths, empty titles, and invalid or duplicate positive integer record IDs. UTF-8 files with or without a byte-order mark are accepted.

FTS startup builds an index for existing articles when needed and checks existing indexes against their content table using [FTS5 integrity-check with rank=1](https://www.sqlite.org/fts5.html#the_integrity_check_command). A stale index is rebuilt and checked again; an unrecoverable error fails startup instead of silently returning incomplete search results.

A failed import leaves the existing database untouched. Sentinel values (`"unavailable"` for DOIs and `"0"` for PubMed IDs) are stored as `NULL`.

Run ingestion while the API is stopped. Although atomic replacement protects the database file, a running process can retain connections to the old SQLite database. For containers, build and validate a new image, pass its health check, then replace the old container.
