from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.dependencies import get_db
from app.main import app
from app.models import DatasetImport
from tests.conftest import TestingSessionLocal


class TestHealth:
    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"

    def test_health_returns_503_when_database_fails(self, client: TestClient):
        class BrokenSession:
            def execute(self, statement):
                raise OperationalError(str(statement), {}, Exception("database unavailable"))

            def rollback(self):
                pass

        def broken_db():
            yield BrokenSession()

        app.dependency_overrides[get_db] = broken_db
        resp = client.get("/health")

        assert resp.status_code == 503
        assert resp.json() == {"status": "error", "database": "error"}


def add_metadata(record_count=2):
    with TestingSessionLocal() as db:
        db.add(DatasetImport(id=1, source_filename="source.csv", source_sha256="a" * 64,
                             imported_at="2026-10-24T12:00:00+00:00", record_count=record_count,
                             api_version="0.2.1"))
        db.commit()


def test_ready_requires_import_metadata(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.get("/dataset").status_code == 503


def test_ready_returns_dataset_provenance(client):
    add_metadata()
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["dataset"]["record_count"] == 2
    metadata = client.get("/dataset").json()
    assert metadata["source_sha256"] == "a" * 64
    assert metadata["source_filename"] == "source.csv"
    assert metadata["api_version"] == "0.2.1"


def test_ready_rejects_mismatched_row_count(client):
    add_metadata(record_count=100)
    assert client.get("/ready").status_code == 503


def test_ready_rejects_missing_search_index(client):
    add_metadata()
    with TestingSessionLocal() as db:
        db.execute(text("DROP TABLE retractions_fts"))
        db.commit()
    assert client.get("/ready").status_code == 503


def test_ready_rejects_an_empty_database(client):
    add_metadata(record_count=0)
    with TestingSessionLocal() as db:
        db.execute(text("DELETE FROM retractions"))
        db.commit()
    assert client.get("/ready").status_code == 503
