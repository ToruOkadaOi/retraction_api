"""Load retraction_watch.csv into the SQLite database."""

import csv
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import FTS_TABLE_DDL, SessionLocal, create_tables
from app.models import Retraction, RetractionCountry, RetractionReason, RetractionSubject

BATCH_SIZE = 500


def parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y %H:%M").date()
    except ValueError:
        return None


def parse_int(value: str):
    if not value or value == "0":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def clean_doi(value: str):
    if not value or value == "unavailable":
        return None
    return value


def split_semicolon(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def ingest():
    csv_path = Path(settings.csv_path)
    if not csv_path.exists():
        print(f"CSV not found at {csv_path}")
        sys.exit(1)

    create_tables()
    session = SessionLocal()

    # Clear existing data to prevent duplicates on re-run
    session.query(RetractionSubject).delete()
    session.query(RetractionReason).delete()
    session.query(RetractionCountry).delete()
    session.query(Retraction).delete()
    session.commit()

    row_count = 0
    skipped = 0

    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            batch: list[Retraction] = []

            for row in reader:
                record_id_raw = row.get("Record ID", "")
                if not record_id_raw:
                    skipped += 1
                    continue

                retraction = Retraction(
                    record_id=int(record_id_raw),
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

                for country in split_semicolon(row["Country"]):
                    retraction.countries.append(
                        RetractionCountry(country=country)
                    )

                for reason in split_semicolon(row["Reason"]):
                    retraction.reasons.append(
                        RetractionReason(reason=reason)
                    )

                for subject in split_semicolon(row["Subject"]):
                    retraction.subjects.append(
                        RetractionSubject(subject=subject)
                    )

                batch.append(retraction)
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

        session.execute(text("DROP TABLE IF EXISTS retractions_fts"))
        session.execute(text(FTS_TABLE_DDL))
        session.execute(text("INSERT INTO retractions_fts(retractions_fts) VALUES('rebuild')"))
        session.commit()

        print("\nIngestion complete:")
        print(f"  Rows loaded: {row_count}")
        print(f"  Rows skipped: {skipped}")

        count = session.query(Retraction).count()
        countries = session.query(RetractionCountry).count()
        reasons = session.query(RetractionReason).count()
        subjects = session.query(RetractionSubject).count()
        print("\nDatabase totals:")
        print(f"  retractions: {count}")
        print(f"  retraction_countries: {countries}")
        print(f"  retraction_reasons: {reasons}")
        print(f"  retraction_subjects: {subjects}")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    ingest()
