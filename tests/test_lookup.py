from fastapi.testclient import TestClient

from app.models import Retraction
from tests.conftest import TestingSessionLocal


class TestLookup:
    def test_lookup_by_doi_found(self, client: TestClient):
        resp = client.get("/lookup/doi/10.1000/test.doi")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 1

    def test_lookup_by_doi_not_found(self, client: TestClient):
        resp = client.get("/lookup/doi/10.9999/missing")
        assert resp.status_code == 404

    def test_lookup_by_doi_is_case_insensitive(self, client: TestClient):
        resp = client.get("/lookup/doi/10.1000/TEST.DOI")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 1

    def test_lookup_by_pubmed_found(self, client: TestClient):
        resp = client.get("/lookup/pubmed/12345678")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 1

    def test_lookup_by_pubmed_not_found(self, client: TestClient):
        resp = client.get("/lookup/pubmed/99999999")
        assert resp.status_code == 404

    def test_lookup_by_original_paper_doi(self, client: TestClient):
        resp = client.get("/lookup/doi/10.1000/original.doi")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 1
        assert resp.json()["latency_days"] == 896

    def test_lookup_by_original_paper_pubmed(self, client: TestClient):
        resp = client.get("/lookup/pubmed/87654321")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 1

    def test_batch_lookup(self, client: TestClient):
        resp = client.post(
            "/lookup/batch",
            json={
                "dois": ["10.1000/original.doi", "10.9999/clean.doi"],
                "pubmed_ids": [12345678, 99999999],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["screened_count"] == 4
        assert data["matched_identifier_count"] == 2
        assert data["matched_record_count"] == 1
        assert data["counts_by_nature"] == {"Retraction": 1}
        assert data["retracted_count"] == 1
        assert data["not_found_count"] == 2
        assert len(data["records"]) == 1
        assert data["records"][0]["record_id"] == 1
        assert "original_paper_doi: 10.1000/original.doi" in data["records"][0]["matched_by"]
        assert data["unmatched_dois"] == ["10.9999/clean.doi"]
        assert data["unmatched_pubmed_ids"] == [99999999]
        assert data["records"][0]["pubpeer_url"] == "https://pubpeer.com/publications/ABC12345"

    def test_lookup_pubpeer_by_record_id(self, client: TestClient):
        resp = client.get("/lookup/pubpeer?record_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == 1
        assert data["pubpeer_url"] == "https://pubpeer.com/publications/ABC12345"

    def test_lookup_pubpeer_by_doi(self, client: TestClient):
        resp = client.get("/lookup/pubpeer?doi=10.1000/original.doi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pubpeer_url"] == "https://pubpeer.com/publications/ABC12345"

    def test_lookup_pubpeer_not_found(self, client: TestClient):
        resp = client.get("/lookup/pubpeer?record_id=2")
        assert resp.status_code == 404

    def test_lookup_pubpeer_missing_params(self, client: TestClient):
        resp = client.get("/lookup/pubpeer")
        assert resp.status_code == 400

    def test_batch_deduplicates_identifiers_before_matching_and_counting(self, client):
        response = client.post("/lookup/batch", json={
            "dois": [" 10.1000/ORIGINAL.DOI ", "10.1000/original.doi",
                     "10.9999/MISSING", "10.9999/missing", "", "  "],
            "pubmed_ids": [87654321, 87654321, 99999999, 99999999, 0, -1],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["screened_count"] == 4
        assert data["matched_identifier_count"] == 2
        assert data["not_found_count"] == 2
        assert data["matched_record_count"] == 1
        assert data["unmatched_dois"] == ["10.9999/MISSING"]
        assert data["unmatched_pubmed_ids"] == [99999999]
        assert "10.1000/ORIGINAL.DOI" in data["records"][0]["matched_by"]
        assert "clean_count" not in data
        assert "retractions" not in data

    def test_batch_distinguishes_notice_types_and_counts_records_separately(self, client):
        with TestingSessionLocal() as db:
            for record_id, nature in enumerate(
                ["Correction", "Expression of Concern", "Reinstatement", " Retraction "], start=3
            ):
                db.add(Retraction(record_id=record_id, title="Shared DOI", journal="Journal",
                                  retraction_nature=nature, paywalled="No",
                                  original_paper_doi="10.1000/shared"))
            db.commit()
        data = client.post("/lookup/batch", json={"dois": ["10.1000/shared"]}).json()
        assert data["screened_count"] == data["matched_identifier_count"] == 1
        assert data["not_found_count"] == 0
        assert data["matched_record_count"] == 4
        assert data["retracted_count"] == 1
        assert data["counts_by_nature"] == {
            "Correction": 1, "Expression of concern": 1, "Reinstatement": 1, "Retraction": 1,
        }
        assert [r["record_id"] for r in data["records"]] == [3, 4, 5, 6]

    def test_batch_empty_input(self, client):
        data = client.post("/lookup/batch", json={}).json()
        assert data["screened_count"] == data["matched_identifier_count"] == data["not_found_count"] == 0
        assert data["matched_record_count"] == data["retracted_count"] == 0
        assert data["records"] == []
        assert data["counts_by_nature"] == {}

    def test_pubpeer_search_url_is_returned_intact(self, client):
        url = "https://pubpeer.com/search?q=10.1000%2Fexample"
        with TestingSessionLocal() as db:
            db.get(Retraction, 1).notes = f"See {url};"
            db.commit()
        assert client.get("/lookup/pubpeer?record_id=1").json()["pubpeer_url"] == url
        assert client.get("/articles/1").json()["pubpeer_url"] == url




def test_notice_history_returns_all_matches_with_roles_and_snapshot(client):
    from datetime import date

    from app.models import DatasetImport, Retraction
    from tests.conftest import TestingSessionLocal

    digest = "a" * 64
    with TestingSessionLocal() as db:
        db.add(DatasetImport(
            id=1, source_filename="fixture.csv", source_sha256=digest,
            imported_at="2026-11-18T00:00:00Z", record_count=3, api_version="0.2.1",
        ))
        db.add(Retraction(
            record_id=3, title="Earlier correction", journal="Test Journal", paywalled="No",
            retraction_nature="Correction", retraction_date=date(2019, 1, 1),
            original_paper_doi="10.1000/ORIGINAL.DOI", original_paper_pubmed_id=87654321,
        ))
        db.commit()

    response = client.get("/lookup/notices", params={"doi": "10.1000/original.doi"})
    assert response.status_code == 200
    history = response.json()
    assert history["source_sha256"] == digest
    assert history["identifier_type"] == "doi"
    assert [row["record_id"] for row in history["records"]] == [3, 1]
    assert history["counts_by_nature"] == {"Correction": 1, "Retraction": 1}
    assert history["records"][0]["identifier_matches"] == [
        {"kind": "original_paper_doi", "identifier": "10.1000/original.doi"}
    ]
    batch = client.post("/lookup/batch", json={"pubmed_ids": [87654321, 12345678]}).json()
    assert batch["source_sha256"] == digest
    assert batch["records"][0]["identifier_matches"] == [
        {"kind": "original_paper_pmid", "identifier": 87654321},
        {"kind": "retraction_pmid", "identifier": 12345678},
    ]
    assert client.get("/lookup/doi/10.1000/original.doi").json()["record_id"] == 1
    assert client.get("/lookup/notices", params={"pubmed_id": 999}).json()["records"] == []
    assert client.get("/lookup/notices", params={"doi": "10.1000/original.doi", "pubmed_id": 999}).status_code == 422
