from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import DatabaseError
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
    notes,
    institution,
    content=retractions,
    content_rowid=record_id
)
"""

FTS_TRIGGER_DDLS = (
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_insert AFTER INSERT ON retractions BEGIN
        INSERT INTO retractions_fts(rowid, title, journal, authors_raw, notes, institution)
        VALUES (new.record_id, new.title, new.journal, new.authors_raw, new.notes, new.institution);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_delete AFTER DELETE ON retractions BEGIN
        INSERT INTO retractions_fts(retractions_fts, rowid, title, journal, authors_raw, notes, institution)
        VALUES ('delete', old.record_id, old.title, old.journal, old.authors_raw, old.notes, old.institution);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS retractions_fts_update AFTER UPDATE ON retractions BEGIN
        INSERT INTO retractions_fts(retractions_fts, rowid, title, journal, authors_raw, notes, institution)
        VALUES ('delete', old.record_id, old.title, old.journal, old.authors_raw, old.notes, old.institution);
        INSERT INTO retractions_fts(rowid, title, journal, authors_raw, notes, institution)
        VALUES (new.record_id, new.title, new.journal, new.authors_raw, new.notes, new.institution);
    END
    """,
)


def check_fts_integrity(connection: Connection) -> None:
    # rank=1 also compares the index to the external retractions content table.
    connection.execute(text(
        "INSERT INTO retractions_fts(retractions_fts, rank) VALUES('integrity-check', 1)"
    ))


def ensure_fts(bind: Engine = engine, *, rebuild: bool = False) -> None:
    with bind.begin() as connection:
        existing_cols = [
            row[1]
            for row in connection.execute(text("PRAGMA table_info(retractions_fts)")).all()
        ]
        needed_cols = {"title", "journal", "authors_raw", "notes", "institution"}
        if not existing_cols:
            rebuild = True
        if existing_cols and not needed_cols.issubset(set(existing_cols)):
            connection.execute(text("DROP TABLE IF EXISTS retractions_fts"))
            for trigger_name in (
                "retractions_fts_insert",
                "retractions_fts_delete",
                "retractions_fts_update",
            ):
                connection.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
            rebuild = True

        connection.execute(text(FTS_TABLE_DDL))
        for trigger_ddl in FTS_TRIGGER_DDLS:
            connection.execute(text(trigger_ddl))

        if not rebuild:
            try:
                check_fts_integrity(connection)
            except DatabaseError as exc:
                # FTS reports content/index disagreement as SQLITE_CORRUPT_VTAB.
                # The message fallback supports Python 3.10's sqlite3 exceptions.
                error_name = getattr(exc.orig, "sqlite_errorname", "")
                if not error_name.startswith("SQLITE_CORRUPT") and str(exc.orig) != "database disk image is malformed":
                    raise
                rebuild = True

        if rebuild:
            connection.execute(
                text("INSERT INTO retractions_fts(retractions_fts) VALUES('rebuild')")
            )
            check_fts_integrity(connection)

