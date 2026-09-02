from fastapi.testclient import TestClient

from app.models import Retraction
from tests.conftest import TestingSessionLocal


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

    def test_fts_tracks_insert_update_and_delete(self, client: TestClient):
        with TestingSessionLocal() as session:
            article = Retraction(
                record_id=3,
                title="Inserted Discovery",
                journal="Test Journal",
                retraction_nature="Retraction",
                paywalled="No",
            )
            session.add(article)
            session.commit()

            assert client.get("/search?q=Inserted").json()["total"] == 1

            article.title = "Updated Discovery"
            session.commit()

            assert client.get("/search?q=Inserted").json()["total"] == 0
            assert client.get("/search?q=Updated").json()["total"] == 1

            session.delete(article)
            session.commit()

        assert client.get("/search?q=Updated").json()["total"] == 0

    def test_search_author_endpoint(self, client: TestClient):
        resp = client.get("/search/author?author=Jane")
        assert resp.status_code == 200
        data = resp.json()
        assert data["author"] == "Jane"
        assert data["total_retractions"] == 1
        assert len(data["articles"]) == 1
        assert data["top_reasons"][0]["reason"] == "Fake Data"
        assert data["top_journals"][0]["journal"] == "Test Journal"

    def test_get_integrity_dossier_author(self, client: TestClient):
        resp = client.get("/search/dossier?target_type=author&target_name=Jane%20Smith")
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_type"] == "author"
        assert data["target_name"] == "Jane Smith"
        assert data["total_retractions"] == 1
        assert len(data["narrative_notes"]) == 1
        assert "investigation finding" in data["narrative_notes"][0]

    def test_get_integrity_dossier_institution(self, client: TestClient):
        resp = client.get("/search/dossier?target_type=institution&target_name=University")
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_type"] == "institution"
        assert data["total_retractions"] == 1

    def test_get_integrity_dossier_not_found(self, client: TestClient):
        resp = client.get("/search/dossier?target_type=author&target_name=NonexistentPerson")
        assert resp.status_code == 404

    def test_search_investigation_notes(self, client: TestClient):
        resp = client.get("/search/investigation?q=finding")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 1
        assert data["items"][0]["pubpeer_url"] == "https://pubpeer.com/publications/ABC12345"
        assert "investigation finding" in data["items"][0]["notes_snippet"]

    def test_search_taxonomy(self, client: TestClient):
        resp = client.get("/search/taxonomy")
        assert resp.status_code == 200
        concepts = resp.json()
        concept_names = {c["concept"] for c in concepts}
        assert "image_manipulation" in concept_names
        assert "data_fabrication" in concept_names
        assert "fake_peer_review" in concept_names

    def test_search_by_concept(self, client: TestClient):
        resp = client.get("/search/concept/data_fabrication")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["record_id"] == 1

    def test_search_by_unknown_concept(self, client: TestClient):
        resp = client.get("/search/concept/alien_abduction")
        assert resp.status_code == 404


