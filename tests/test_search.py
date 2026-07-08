from fastapi.testclient import TestClient


class TestSearch:
    def test_search_by_title(self, client: TestClient):
        resp = client.get("/search?q=cancer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["record_id"] == 1

    def test_search_by_author(self, client: TestClient):
        resp = client.get("/search?q=Jane")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_search_matches_multiple(self, client: TestClient):
        resp = client.get("/search?q=Smith")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_search_no_results(self, client: TestClient):
        resp = client.get("/search?q=xyznonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_search_empty_query(self, client: TestClient):
        resp = client.get("/search?q=")
        assert resp.status_code == 422

    def test_search_pagination(self, client: TestClient):
        resp = client.get("/search?q=Smith&skip=0&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
