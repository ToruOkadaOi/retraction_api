from fastapi.testclient import TestClient


class TestStatistics:
    def test_top_journals(self, client: TestClient):
        resp = client.get("/stats/top-journals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        journals = {entry["journal"]: entry["count"] for entry in data}
        assert journals["Test Journal"] == 1
        assert journals["Nature Climate"] == 1

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

    def test_statistics_limit(self, client: TestClient):
        resp = client.get("/stats/top-countries?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_statistics_rejects_excessive_limit(self, client: TestClient):
        resp = client.get("/stats/top-journals?limit=101")
        assert resp.status_code == 422
