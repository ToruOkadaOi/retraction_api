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
