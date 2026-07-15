"""Atomically load retraction_watch.csv into a SQLite database."""

import csv
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import Base, ensure_fts
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject
from scripts.validate_csv import validate_csv

BATCH_SIZE = 500


@dataclass(frozen=True)
class IngestionResult:
    rows: int
    skipped: int
    countries: int
    reasons: int
    subjects: int
    database_path: Path


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y %H:%M").date()
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    if not value or value == "0":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def clean_doi(value: str) -> str | None:
    if not value or value == "unavailable":
        return None
    return value


def split_semicolon(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _sqlite_target(database_url: str) -> tuple[Path, Path, URL]:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("Atomic ingestion requires a file-backed SQLite DATABASE_URL")

    live_path = Path(url.database).resolve()
    live_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = live_path.with_name(f".{live_path.name}.{uuid.uuid4().hex}.tmp")
    return live_path, temporary_path, url.set(database=str(temporary_path))


def _build_retraction(row: dict[str, str]) -> Retraction:
    retraction = Retraction(
        record_id=int(row["Record ID"]),
        title=row["Title"],
        journal=row["Journal"],
        retraction_nature=row["RetractionNature"],
        paywalled=row["Paywalled"],
        publisher=row["Publisher"] or None,
        article_type=row["ArticleType"].rstrip(";").strip() or None,
        institution=row["Institution"].rstrip(";").strip() or None,
        urls=row["URLS"] or None,
        authors_raw=row["Author"] or None,
        notes=row["Notes"] or None,
        retraction_date=parse_date(row["RetractionDate"]),
        original_paper_date=parse_date(row["OriginalPaperDate"]),
        retraction_doi=clean_doi(row["RetractionDOI"]),
        retraction_pubmed_id=parse_int(row["RetractionPubMedID"]),
        original_paper_doi=clean_doi(row["OriginalPaperDOI"]),
        original_paper_pubmed_id=parse_int(row["OriginalPaperPubMedID"]),
    )

    retraction.countries.extend(
        RetractionCountry(country=country) for country in split_semicolon(row["Country"])
    )
    retraction.reasons.extend(
        RetractionReason(reason=reason) for reason in split_semicolon(row["Reason"])
    )
    retraction.subjects.extend(
        RetractionSubject(subject=subject) for subject in split_semicolon(row["Subject"])
    )
    return retraction


def _validate_database(engine: Engine, expected_rows: int) -> tuple[int, int, int]:
    with engine.connect() as connection:
        article_count = connection.execute(text("SELECT COUNT(*) FROM retractions")).scalar_one()
        fts_count = connection.execute(text("SELECT COUNT(*) FROM retractions_fts")).scalar_one()
        if article_count != expected_rows:
            raise RuntimeError(
                f"Imported {article_count} records but CSV validation found {expected_rows}"
            )
        if fts_count != article_count:
            raise RuntimeError(f"FTS contains {fts_count} records but expected {article_count}")

        integrity = [row[0] for row in connection.execute(text("PRAGMA integrity_check"))]
        if integrity != ["ok"]:
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")

        foreign_key_errors = connection.execute(text("PRAGMA foreign_key_check")).all()
        if foreign_key_errors:
            raise RuntimeError(f"SQLite foreign key check failed: {foreign_key_errors}")

        trigger_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type = 'trigger' AND name LIKE 'retractions_fts_%'"
            )
        ).scalar_one()
        if trigger_count != 3:
            raise RuntimeError(f"Expected 3 FTS triggers but found {trigger_count}")

        countries = connection.execute(text("SELECT COUNT(*) FROM retraction_countries")).scalar_one()
        reasons = connection.execute(text("SELECT COUNT(*) FROM retraction_reasons")).scalar_one()
        subjects = connection.execute(text("SELECT COUNT(*) FROM retraction_subjects")).scalar_one()
        return countries, reasons, subjects


def _remove_temporary_files(path: Path) -> None:
    for candidate in (path, Path(f"{path}-journal"), Path(f"{path}-shm"), Path(f"{path}-wal")):
        candidate.unlink(missing_ok=True)


def ingest(
    csv_path: Path | None = None,
    database_url: str | None = None,
) -> IngestionResult:
    source_path = Path(csv_path or settings.csv_path)
    if not source_path.exists():
        raise FileNotFoundError(f"CSV not found at {source_path}")

    expected_rows = validate_csv(source_path)
    live_path, temporary_path, temporary_url = _sqlite_target(
        database_url or settings.database_url
    )
    engine = create_engine(temporary_url, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    row_count = 0
    skipped = 0

    try:
        try:
            Base.metadata.create_all(engine)
            with source_path.open(encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                batch: list[Retraction] = []

                for row in reader:
                    if not any((value or "").strip() for value in row.values()):
                        skipped += 1
                        continue

                    batch.append(_build_retraction(row))
                    row_count += 1

                    if len(batch) >= BATCH_SIZE:
                        session.add_all(batch)
                        session.commit()
                        batch.clear()
                        if row_count % 10000 == 0:
                            print(f"  ...{row_count} rows ingested")

                if batch:
                    session.add_all(batch)
                    session.commit()

            ensure_fts(engine, rebuild=True)
            countries, reasons, subjects = _validate_database(engine, expected_rows)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()

        os.replace(temporary_path, live_path)
    except Exception:
        _remove_temporary_files(temporary_path)
        raise

    return IngestionResult(
        rows=row_count,
        skipped=skipped,
        countries=countries,
        reasons=reasons,
        subjects=subjects,
        database_path=live_path,
    )


def main() -> None:
    try:
        result = ingest()
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        raise SystemExit(1) from exc

    print("\nIngestion complete:")
    print(f"  Rows loaded: {result.rows}")
    print(f"  Blank rows skipped: {result.skipped}")
    print(f"  Database replaced: {result.database_path}")
    print("\nDatabase totals:")
    print(f"  retractions: {result.rows}")
    print(f"  retraction_countries: {result.countries}")
    print(f"  retraction_reasons: {result.reasons}")
    print(f"  retraction_subjects: {result.subjects}")


if __name__ == "__main__":
    main()
