from sqlalchemy import create_engine, text
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

def ensure_fts() -> None:
    with SessionLocal() as session:
        session.execute(text(FTS_TABLE_DDL))
        count = (
            session.execute(text("SELECT COUNT(*) FROM retractions_fts"))
            .scalar()
        )
        if count == 0:
            session.execute(
                text("INSERT INTO retractions_fts(retractions_fts) VALUES('rebuild')")
            )
            session.commit()
