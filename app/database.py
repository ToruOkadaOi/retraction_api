from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables() -> None:
    Base.metadata.create_all(engine)

FTS_TABLE_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS retractions_fts USING fts5(
    title,
    journal,
    authors_raw,
    content=retractions,
    content_rowid=record_id
)
"""

FTS_TRIGGER_DDLS = (
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_insert AFTER INSERT ON retractions BEGIN
        INSERT INTO retractions_fts(rowid, title, journal, authors_raw)
        VALUES (new.record_id, new.title, new.journal, new.authors_raw);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_delete AFTER DELETE ON retractions BEGIN
        INSERT INTO retractions_fts(retractions_fts, rowid, title, journal, authors_raw)
        VALUES ('delete', old.record_id, old.title, old.journal, old.authors_raw);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_update AFTER UPDATE ON retractions BEGIN
        INSERT INTO retractions_fts(retractions_fts, rowid, title, journal, authors_raw)
        VALUES ('delete', old.record_id, old.title, old.journal, old.authors_raw);
        INSERT INTO retractions_fts(rowid, title, journal, authors_raw)
        VALUES (new.record_id, new.title, new.journal, new.authors_raw);
    END
    """,
)


def ensure_fts(bind: Engine = engine, *, rebuild: bool = False) -> None:
    with bind.begin() as connection:
        connection.execute(text(FTS_TABLE_DDL))
        for trigger_ddl in FTS_TRIGGER_DDLS:
            connection.execute(text(trigger_ddl))

        indexed_count = connection.execute(text("SELECT COUNT(*) FROM retractions_fts")).scalar_one()
        article_count = connection.execute(text("SELECT COUNT(*) FROM retractions")).scalar_one()
        if rebuild or indexed_count != article_count:
            connection.execute(
                text("INSERT INTO retractions_fts(retractions_fts) VALUES('rebuild')")
            )
