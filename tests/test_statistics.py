from fastapi.testclient import TestClient

from app.models import Retraction
from tests.conftest import TestingSessionLocal


class TestStatistics:
    def test_top_journals(self, client: TestClient):
        resp = client.get("/stats/top-journals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        journals = {entry["journal"]: entry["count"] for entry in data}
        assert journals["Test Journal"] == 1
        assert "Nature Climate" not in journals

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
        assert data["total_records"] == 2
        assert data["total_retractions"] == 1
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
        assert data["total_records_analyzed"] == 1
        assert data["average_latency_days"] > 0
        assert len(data["fastest_retractions"]) >= 1

    def test_detect_clusters(self, client: TestClient):
        resp = client.get("/stats/clusters?min_count=1")
        assert resp.status_code == 200
        clusters = resp.json()
        assert len(clusters) >= 1
        assert clusters[0]["retraction_count"] >= 1

    def test_non_retractions_are_excluded_from_retraction_statistics(self, client):
        summary = client.get("/stats/summary").json()
        assert summary["total_records"] == 2
        assert summary["total_retractions"] == 1
        assert summary["retraction_natures"] == {"Retraction": 1, "Expression of concern": 1}
        assert all(r["reason"] != "Results Unreliable" for r in client.get("/stats/top-reasons").json())
        assert all(r["country"] != "Canada" for r in client.get("/stats/top-countries").json())
        assert [c["journal"] for c in client.get("/stats/clusters?min_count=1").json()] == ["Test Journal"]
        latency = client.get("/stats/latency?journal=Nature%20Climate").json()
        assert latency["total_records_analyzed"] == 0
        assert latency["fastest_retractions"] == []
        profile = client.get("/stats/journal/Nature%20Climate").json()
        assert profile["total_records"] == 1
        assert profile["total_retractions"] == 0
        assert profile["counts_by_nature"] == {"Expression of concern": 1}
        assert profile["yearly_counts"] == {}
        assert profile["top_reasons"] == []
        assert profile["average_latency_days"] is None

    def test_retraction_counts_are_normalized_across_analytics(self, client):
        with TestingSessionLocal() as db:
            db.get(Retraction, 1).retraction_nature = " RETRACTION "
            db.commit()
        assert client.get("/stats/summary").json()["retraction_natures"]["Retraction"] == 1
        assert client.get("/stats/top-journals").json() == [{"journal": "Test Journal", "count": 1}]
        profile = client.get("/stats/journal/Test%20Journal").json()
        assert profile["counts_by_nature"] == {"Retraction": 1}
        assert profile["total_retractions"] == 1

