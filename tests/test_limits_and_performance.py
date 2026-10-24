from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import event, text

from app.models import Retraction, RetractionReason
from tests.conftest import TestingSessionLocal, engine


@contextmanager
def sql_queries():
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.mark.parametrize(("path", "params"), [
    ("/search", {"q": "   "}),
    ("/search/investigation", {"q": "   "}),
    ("/search", {"q": "x" * 501}),
    ("/search/author", {"author": "   "}),
    ("/search/author", {"author": "x" * 301}),
    ("/search/dossier", {"target_name": "   "}),
    ("/articles", {"institution": "   "}),
    ("/stats/latency", {"journal": "   "}),
    ("/articles", {"from_year": 2023, "to_year": 2020}),
    ("/articles", {"year": 2010, "from_year": 2020}),
    ("/stats/clusters", {"year": 99999}),
])
def test_invalid_filters_fail_before_querying(client, path, params):
    with sql_queries() as statements:
        response = client.get(path, params=params)
    assert response.status_code == 422
    assert statements == []


@pytest.mark.parametrize("body", [
    {"dois": ["10.1000/example"] * 201},
    {"pubmed_ids": [1] * 201},
    {"dois": ["10.1000/example"] * 100, "pubmed_ids": [1] * 101},
    {"dois": ["x" * 2049]},
    {"pubmed_ids": [2**63]},
])
def test_batch_limits_apply_before_database_work(client, body):
    with sql_queries() as statements:
        response = client.post("/lookup/batch", json=body)
    assert response.status_code == 422
    assert statements == []


def test_batch_accepts_boundary_size(client):
    assert client.post("/lookup/batch", json={"dois": ["10.1000/example"] * 200}).status_code == 200


def test_percent_and_underscore_are_literal_search_characters(client):
    assert client.get("/search/author", params={"author": "%%"}).json()["total_records"] == 0
    assert client.get("/articles", params={"institution": "%"}).json()["total"] == 0
    assert client.get("/articles", params={"reason": "_"}).json()["total"] == 0


def test_case_insensitive_doi_lookup_uses_indexes(client):
    with engine.connect() as connection:
        plan = connection.execute(text(
            "EXPLAIN QUERY PLAN SELECT record_id FROM retractions WHERE "
            "lower(trim(original_paper_doi))=:doi OR lower(trim(retraction_doi))=:doi"
        ), {"doi": "10.1000/original.doi"}).all()
    details = " ".join(row[-1] for row in plan)
    assert "ix_retractions_original_doi_normalized" in details
    assert "ix_retractions_retraction_doi_normalized" in details
    assert client.get("/lookup/doi/10.1000/ORIGINAL.DOI").json()["record_id"] == 1


def test_summaries_and_batch_queries_do_not_grow_per_record(client):
    with TestingSessionLocal() as db:
        for i in range(100, 300):
            article = Retraction(
                record_id=i, title=f"Benchmark {i}", journal="Benchmark Journal",
                authors_raw="Benchmark Author", retraction_nature="Retraction", paywalled="No",
                original_paper_doi=f"10.1000/{i}", notes=f"Finding {i}",
                retraction_date=date(2020, 1, 1), original_paper_date=date(2019, 1, 1),
            )
            article.reasons.append(RetractionReason(reason="Benchmark Reason"))
            db.add(article)
        db.commit()
    for path, params, budget in [
        ("/search/author", {"author": "Benchmark Author", "limit": 1}, 4),
        ("/search/dossier", {"target_name": "Benchmark Author"}, 6),
        ("/stats/journal/Benchmark Journal", {}, 5),
        ("/stats/latency", {"journal": "Benchmark Journal"}, 7),
    ]:
        with sql_queries() as statements:
            response = client.get(path, params=params)
        assert response.status_code == 200, response.text
        assert len(statements) <= budget, statements
        data = response.json()
        if "total_records" in data:
            assert data["total_records"] == 200
    with sql_queries() as statements:
        data = client.post("/lookup/batch", json={"dois": [f"10.1000/{i}" for i in range(100, 300)]}).json()
    assert data["matched_record_count"] == 200
    assert len(statements) <= 2


def test_clusters_use_all_records_and_a_three_year_baseline(client):
    with TestingSessionLocal() as db:
        for i in range(250):
            article = Retraction(record_id=1000 + i, title="Cluster", journal="Cluster Journal",
                                 retraction_nature="Retraction", paywalled="No", retraction_date=date(2020, 1, 1))
            article.reasons.append(RetractionReason(reason="Early reason" if i < 100 else "Majority reason"))
            db.add(article)
        for i in range(9):
            db.add(Retraction(record_id=2000 + i, title="Baseline", journal="Cluster Journal",
                              retraction_nature="Retraction", paywalled="No",
                              retraction_date=date(2017 if i < 3 else 2018, 1, 1)))
        db.commit()
    with sql_queries() as statements:
        response = client.get("/stats/clusters", params={"min_count": 200, "year": 2020})
    assert response.status_code == 200, response.text
    cluster = response.json()[0]
    assert cluster["retraction_count"] == 250
    assert cluster["top_reasons"] == ["Majority reason", "Early reason"]
    assert cluster["sample_record_ids"] == [1000, 1001, 1002, 1003, 1004]
    assert cluster["baseline_yearly_counts"] == {"2017": 3, "2018": 6, "2019": 0}
    assert cluster["baseline_average"] == 3
    assert cluster["ratio_to_baseline"] == 83.33
    assert cluster["is_partial_year"] is False
    assert len(statements) == 4


def test_cluster_zero_baseline_has_no_infinite_ratio(client):
    cluster = client.get("/stats/clusters", params={"min_count": 1}).json()[0]
    assert cluster["baseline_average"] == 0
    assert cluster["ratio_to_baseline"] is None


@pytest.mark.parametrize("days", [[0, 364, 365, 1095, 1825], [10, 30]])
def test_latency_aggregates_and_median_use_all_valid_retractions(client, days):
    from datetime import timedelta
    from statistics import median

    with TestingSessionLocal() as db:
        for i, delay in enumerate([*days, -1]):
            db.add(Retraction(record_id=3000 + i, title="Latency", journal="Latency Journal",
                              retraction_nature="Retraction", paywalled="No", original_paper_date=date(2000, 1, 1),
                              retraction_date=date(2000, 1, 1) + timedelta(days=delay)))
        db.commit()
    response = client.get("/stats/latency", params={"journal": "Latency Journal"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_records_analyzed"] == len(days)
    assert data["average_latency_days"] == round(sum(days) / len(days), 1)
    assert data["median_latency_days"] == median(days)
    assert sum(b["count"] for b in data["distribution"]) == len(days)
    assert data["fastest_retractions"][0]["latency_days"] == min(days)
    assert data["slowest_retractions"][0]["latency_days"] == max(days)
