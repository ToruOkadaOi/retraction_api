from fastapi.testclient import TestClient


class TestSearch:
    def test_search_by_title(self, client: TestClient):
        resp = client.get("/search?q=cancer")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["record_id"] == 1

    def test_search_by_author(self, client: TestClient):
        resp = client.get("/search?q=Jane")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_no_results(self, client: TestClient):
        resp = client.get("/search?q=xyznonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_empty_query(self, client: TestClient):
        resp = client.get("/search?q=")
        assert resp.status_code == 422
