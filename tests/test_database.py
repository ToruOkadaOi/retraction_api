import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.database import FTS_TABLE_DDL, Base, check_fts_integrity, ensure_fts
from app.models import Retraction


@pytest.fixture
def populated_engine():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Retraction(record_id=1, title="ExistingDiscovery", journal="Journal",
                          retraction_nature="Retraction", paywalled="No"))
        db.commit()
    yield engine
    engine.dispose()


def matches(engine, word):
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT rowid FROM retractions_fts WHERE retractions_fts MATCH :word"),
            {"word": word},
        ).scalars().all()


def test_new_index_includes_existing_articles(populated_engine):
    ensure_fts(populated_engine)
    assert matches(populated_engine, "ExistingDiscovery") == [1]
    ensure_fts(populated_engine)
    assert matches(populated_engine, "ExistingDiscovery") == [1]


def test_empty_external_index_is_detected_and_repaired(populated_engine):
    with populated_engine.begin() as connection:
        connection.execute(text(FTS_TABLE_DDL))
        assert connection.execute(text("SELECT COUNT(*) FROM retractions_fts")).scalar() == 1
        with pytest.raises(DatabaseError):
            check_fts_integrity(connection)
    assert matches(populated_engine, "ExistingDiscovery") == []
    ensure_fts(populated_engine)
    assert matches(populated_engine, "ExistingDiscovery") == [1]


def test_stale_index_with_unchanged_row_count_is_repaired(populated_engine):
    ensure_fts(populated_engine)
    with populated_engine.begin() as connection:
        connection.execute(text("DROP TRIGGER retractions_fts_update"))
        connection.execute(text("UPDATE retractions SET title='ChangedDiscovery' WHERE record_id=1"))
    ensure_fts(populated_engine)
    assert matches(populated_engine, "ExistingDiscovery") == []
    assert matches(populated_engine, "ChangedDiscovery") == [1]
    with populated_engine.begin() as connection:
        connection.execute(text("UPDATE retractions SET title='NewestDiscovery' WHERE record_id=1"))
    assert matches(populated_engine, "ChangedDiscovery") == []
    assert matches(populated_engine, "NewestDiscovery") == [1]


def test_old_index_schema_is_rebuilt(populated_engine):
    with populated_engine.begin() as connection:
        connection.execute(text(
            "CREATE VIRTUAL TABLE retractions_fts USING fts5(title, journal, authors_raw, "
            "content=retractions, content_rowid=record_id)"
        ))
    ensure_fts(populated_engine)
    assert matches(populated_engine, "ExistingDiscovery") == [1]
