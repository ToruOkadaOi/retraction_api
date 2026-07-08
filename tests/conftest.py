from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.dependencies import get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def _seed():
    from app.models import Retraction, RetractionCountry, RetractionReason

    session = TestingSessionLocal()
    r = Retraction(
        record_id=1,
        title="Test Article About Cancer Research",
        journal="Test Journal",
        publisher="Test Publisher",
        article_type="Research Article",
        retraction_nature="Retraction",
        retraction_date=None,
        retraction_doi="10.1000/test.doi",
        retraction_pubmed_id=12345678,
        paywalled="No",
        notes="Test notes",
        institution="Test University",
        urls="https://example.com",
        authors_raw="John Doe;Jane Smith",
    )
    session.add(r)
    session.add(RetractionCountry(record_id=1, country="USA"))
    session.add(RetractionCountry(record_id=1, country="UK"))
    session.add(RetractionReason(record_id=1, reason="Fake Data"))
    session.commit()
    session.close()


def override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    _seed()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
