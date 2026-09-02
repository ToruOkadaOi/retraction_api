from fastapi.testclient import TestClient


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
        assert data["retracted_count"] == 1
        assert data["clean_count"] == 2
        assert len(data["retractions"]) == 1
        assert data["retractions"][0]["record_id"] == 1
        assert "original_paper_doi: 10.1000/original.doi" in data["retractions"][0]["matched_by"]
        assert "retraction_pmid: 12345678" in data["retractions"][0]["matched_by"]
        assert data["unmatched_dois"] == ["10.9999/clean.doi"]
        assert data["unmatched_pubmed_ids"] == [99999999]

