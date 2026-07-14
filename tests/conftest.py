from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, ensure_fts
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
    r1 = Retraction(
        record_id=1,
        title="Test Article About Cancer Research",
        journal="Test Journal",
        publisher="Test Publisher",
        article_type="Research Article",
        retraction_nature="Retraction",
        retraction_date=date(2020, 6, 15),
        retraction_doi="10.1000/test.doi",
        retraction_pubmed_id=12345678,
        paywalled="No",
        notes="Test notes",
        institution="Test University",
        urls="https://example.com",
        authors_raw="John Doe;Jane Smith",
    )
    session.add(r1)
    session.add(RetractionCountry(record_id=1, country="USA"))
    session.add(RetractionCountry(record_id=1, country="UK"))
    session.add(RetractionReason(record_id=1, reason="Fake Data"))

    r2 = Retraction(
        record_id=2,
        title="A Study on Climate Change",
        journal="Nature Climate",
        publisher="Springer",
        article_type=None,
        retraction_nature="Expression of Concern",
        retraction_date=date(2021, 3, 10),
        retraction_doi=None,
        retraction_pubmed_id=None,
        paywalled="Yes",
        notes=None,
        institution=None,
        urls=None,
        authors_raw="Alice Smith",
    )
    session.add(r2)
    session.add(RetractionCountry(record_id=2, country="Canada"))
    session.add(RetractionReason(record_id=2, reason="Results Unreliable"))

    session.commit()
    session.close()


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS retractions_fts"))
    Base.metadata.create_all(bind=engine)
    _seed()
    ensure_fts(engine, rebuild=True)
    yield
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS retractions_fts"))
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
