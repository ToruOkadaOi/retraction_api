from fastapi.testclient import TestClient


class TestArticles:
    def test_list_articles_defaults(self, client: TestClient):
        resp = client.get("/articles")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["skip"] == 0
        assert data["limit"] == 20
        assert len(data["items"]) == 2
        assert data["items"][0]["record_id"] == 1

    def test_list_articles_pagination(self, client: TestClient):
        resp = client.get("/articles?skip=0&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["skip"] == 0
        assert data["limit"] == 1
        assert len(data["items"]) == 1

    def test_list_articles_skip_beyond(self, client: TestClient):
        resp = client.get("/articles?skip=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 2

    def test_get_article_found(self, client: TestClient):
        resp = client.get("/articles/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == 1
        assert data["publisher"] == "Test Publisher"
        assert data["countries"] == ["USA", "UK"]
        assert data["reasons"] == ["Fake Data"]
        assert data["authors"] == ["John Doe", "Jane Smith"]
        assert data["urls"] == ["https://example.com"]

    def test_get_article_not_found(self, client: TestClient):
        resp = client.get("/articles/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Article not found"

    def test_list_articles_invalid_limit(self, client: TestClient):
        resp = client.get("/articles?limit=0")
        assert resp.status_code == 422

    def test_filter_by_journal(self, client: TestClient):
        resp = client.get("/articles?journal=Nature%20Climate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 2

    def test_filter_by_publisher(self, client: TestClient):
        resp = client.get("/articles?publisher=Springer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 2

    def test_filter_by_retraction_nature(self, client: TestClient):
        resp = client.get("/articles?retraction_nature=Retraction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 1

    def test_filter_by_year(self, client: TestClient):
        resp = client.get("/articles?year=2020")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 1

    def test_filter_no_results(self, client: TestClient):
        resp = client.get("/articles?journal=Nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_filter_combined(self, client: TestClient):
        resp = client.get(
            "/articles?year=2020&retraction_nature=Retraction"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
