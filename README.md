# Retraction Watch API

A REST API and MCP server for searching the [Retraction Watch database](https://gitlab.com/crossref/retraction-watch-data) of retractions, corrections, expressions of concern, and reinstatements. Built with FastAPI and SQLite.

## Hosted services

### API

- Interactive documentation: [retraction-api.onrender.com/docs](https://retraction-api.onrender.com/docs)
- Base URL: [retraction-api.onrender.com](https://retraction-api.onrender.com)
- Health check: [retraction-api.onrender.com/health](https://retraction-api.onrender.com/health)

P.S - A knowledge graph based [**dashboard**](https://toruokadaoi.github.io/retraction_watch_data/) is also present!

### MCP server

- Streamable HTTP endpoint: `https://retraction-watch-mcp.onrender.com/mcp`
- Health check: [retraction-watch-mcp.onrender.com/health](https://retraction-watch-mcp.onrender.com/health)

Hosted services may take a moment to wake up after being idle.

<details>
<summary><strong>Optional research skill</strong></summary>

The [Retraction Watch research skill](skills/retraction-watch-research/SKILL.md) guides agents through citation screening and notice interpretation, including batching, source attribution, and ambiguous matches.

To install, copy the `skills/retraction-watch-research/` folder from this repository into your agent's supported skills directory. Keep the folder name and `SKILL.md` intact, then reload skills as required by your client. Connect the MCP server below, or give the agent HTTP access to the API. Installing the skill supplies instructions; it does not configure a connection.

Try: “Use the Retraction Watch research skill to screen these citations and report matching notice types and dataset provenance.”

</details>

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

- Look up papers and notices by DOI or PubMed ID, or screen up to 200 identifiers at once.
- Search titles, authors, institutions, investigation notes, and recorded misconduct reasons.
- Filter articles by journal, publisher, notice type, country, subject, and year.
- Find PubPeer links and build author or institution summaries.
- Explore journal profiles, retraction timelines, and journal/year counts with historical comparisons.
- Check the dataset's source hash, import time, and record count.

Results distinguish retractions from other notice types. A missing match does not establish that a paper is reliable. Journal/year comparisons describe recorded counts; they do not establish misconduct.

<details>
<summary><strong>MCP tools, resources, and prompts</strong></summary>

| Tool | Result |
|---|---|
| `health_check` | Basic API and database connectivity |
| `get_dataset_info` | Served snapshot SHA-256, source filename, import time, row count, and importer version |
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
| `detect_retraction_clusters` | High-volume journal/year groups with full-group reasons and descriptive historical comparisons |
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
| `retraction://stats/clusters` | High-volume journal/year groups with historical comparisons |
| `retraction://dataset` | Provenance of the currently served dataset |
| `retraction://taxonomy` | Controlled scientific misconduct taxonomy and reason mappings |

## MCP prompts

| Prompt | Description |
|---|---|
| `screen_bibliography` | Parses citations/DOIs, calls `batch_check_citations`, and generates an audit report |
| `author_integrity_audit` | Conducts a research integrity assessment on a named researcher |
| `journal_reliability_audit`| Audits a journal's track record, latency, and volume anomalies |
| `paper_mill_investigation` | Investigates high-volume clusters and coordinated paper-mill fraud |
| `investigate_scientific_misconduct` | Conducts a deep forensic investigation using misconduct taxonomy, narrative notes, and PubPeer links |

</details>

<details>
<summary><strong>Run locally</strong></summary>

Requires Python 3.10 or later.

```bash
git clone https://github.com/ToruOkadaOi/retraction_api.git
cd retraction_api
python -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements-dev.lock
pip install --no-deps --no-build-isolation -e .
cp .env.example .env
python scripts/ingest_csv.py
uvicorn app.main:app --reload
```

Open [localhost:8000/docs](http://localhost:8000/docs) for the complete API reference and request examples. The importer uses the included `retraction_watch.csv`; run it while the API is stopped.

To run the MCP server against the local API in another terminal:

```bash
source .venv/bin/activate
RETRACTION_API_URL=http://localhost:8000 python -m mcp_server
```

This starts the MCP server over stdio. For HTTP transport, also set `RETRACTION_MCP_TRANSPORT=streamable-http` and `RETRACTION_MCP_PORT=8001`.

</details>

<details>
<summary><strong>Docker</strong></summary>

After creating `.env`, start both services:

```bash
docker compose up --build
```

API documentation: `http://localhost:8000/docs` · MCP endpoint: `http://localhost:8001/mcp`

The API image includes a validated database built from the CSV. Rebuild the image to update it.

</details>

## API at a glance

| Endpoint | Purpose |
|---|---|
| `GET /articles` | Filter and paginate article summaries |
| `GET /articles/{record_id}` | Full record details |
| `GET /lookup/doi/{doi}` | Look up an original paper or notice DOI |
| `GET /lookup/pubmed/{pubmed_id}` | Look up an original paper or notice PubMed ID |
| `POST /lookup/batch` | Screen up to 200 combined DOIs and PubMed IDs |
| `GET /lookup/pubpeer` | Find a PubPeer publication or search link |
| `GET /search?q=...` | Full-text search |
| `GET /search/author` · `GET /search/dossier` | Author and institution summaries |
| `GET /search/investigation` · `GET /search/taxonomy` · `GET /search/concept/{concept}` | Investigation notes and misconduct categories |
| `GET /stats/summary` · `GET /stats/top-journals` · `GET /stats/top-reasons` · `GET /stats/top-countries` | Database statistics |
| `GET /stats/journal/{journal}` · `GET /stats/latency` · `GET /stats/clusters` | Journal profiles, timelines, and historical comparisons |
| `GET /dataset` | Source snapshot and import details |
| `GET /health` · `GET /ready` | Connectivity and dataset readiness |

Paginated endpoints accept `skip` and `limit`, with at most 100 records per page. Batch results contain `records`, `counts_by_nature`, and `not_found_count`; `retracted_count` counts only retraction notices.

## Development

```bash
python -m ruff check app mcp_server scripts tests
python -m pytest -q
```

See [maintenance and deployment](docs/maintenance.md) for configuration and deployment details.
