from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.dependencies import get_db
from app.main import app


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
