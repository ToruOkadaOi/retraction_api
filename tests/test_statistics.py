from fastapi.testclient import TestClient


class TestStatistics:
    def test_top_journals(self, client: TestClient):
        resp = client.get("/stats/top-journals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["journal"] == "Test Journal"
        assert data[0]["count"] == 1

    def test_top_reasons(self, client: TestClient):
        resp = client.get("/stats/top-reasons")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["reason"] == "Fake Data"

    def test_top_countries(self, client: TestClient):
        resp = client.get("/stats/top-countries")
        assert resp.status_code == 200
        data = resp.json()
        # Two countries: USA and UK, both count=1
        assert len(data) >= 2
