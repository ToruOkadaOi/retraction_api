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

    def test_database_summary(self, client: TestClient):
        resp = client.get("/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_retractions"] == 2
        assert data["unique_journals"] == 2
        assert data["unique_publishers"] == 2
        assert data["retraction_natures"]["Retraction"] == 1
        assert data["paywalled_counts"]["No"] == 1

    def test_journal_profile_found(self, client: TestClient):
        resp = client.get("/stats/journal/Test%20Journal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["journal"] == "Test Journal"
        assert data["total_retractions"] == 1
        assert data["average_latency_days"] == 896.0
        assert data["top_reasons"][0]["reason"] == "Fake Data"

    def test_journal_profile_not_found(self, client: TestClient):
        resp = client.get("/stats/journal/Nonexistent%20Journal")
        assert resp.status_code == 404

    def test_latency_analysis(self, client: TestClient):
        resp = client.get("/stats/latency")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records_analyzed"] == 2
        assert data["average_latency_days"] > 0
        assert len(data["fastest_retractions"]) >= 1

    def test_detect_clusters(self, client: TestClient):
        resp = client.get("/stats/clusters?min_count=1")
        assert resp.status_code == 200
        clusters = resp.json()
        assert len(clusters) >= 1
        assert clusters[0]["retraction_count"] >= 1

