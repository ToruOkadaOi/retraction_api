from fastapi.testclient import TestClient


class TestArticles:
    def test_list_articles_defaults(self, client: TestClient):
        resp = client.get("/articles")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["record_id"] == 1
        assert data[0]["title"] == "Test Article About Cancer Research"

    def test_list_articles_pagination(self, client: TestClient):
        resp = client.get("/articles?skip=0&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_articles_skip_beyond(self, client: TestClient):
        resp = client.get("/articles?skip=100")
        assert resp.status_code == 200
        assert resp.json() == []

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
