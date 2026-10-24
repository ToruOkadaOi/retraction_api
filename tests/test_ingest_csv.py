import csv
import hashlib
import sqlite3
from datetime import date

import pytest

from scripts.ingest_csv import ingest, parse_date
from scripts.validate_csv import REQUIRED_COLUMNS


def write_source_csv(path, rows, encoding="utf-8"):
    with path.open("w", encoding=encoding, newline="") as file:
        columns = ["Record ID", *sorted(REQUIRED_COLUMNS - {"Record ID"})]
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def source_row(record_id="1"):
    row = dict.fromkeys(REQUIRED_COLUMNS, "")
    row.update(
        {
            "Record ID": record_id,
            "Title": "Atomic ingestion test",
            "Journal": "Test Journal",
            "RetractionNature": "Retraction",
            "Paywalled": "No",
            "Author": "Jane Smith",
            "Country": "USA;UK",
            "Reason": "Fake Data",
            "Subject": "Medicine",
        }
    )
    return row


def sqlite_url(path):
    return f"sqlite:///{path}"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_ingest_builds_and_promotes_valid_database(tmp_path, encoding):
    csv_path = tmp_path / "source.csv"
    database_path = tmp_path / "retraction_watch.db"
    database_path.write_bytes(b"previous database")
    write_source_csv(csv_path, [source_row()], encoding=encoding)

    result = ingest(csv_path, sqlite_url(database_path))

    assert result.rows == 1
    assert result.countries == 2
    assert result.reasons == 1
    assert result.subjects == 1
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM retractions").fetchone()[0] == 1
        assert connection.execute(
            "SELECT rowid FROM retractions_fts WHERE retractions_fts MATCH 'Atomic'"
        ).fetchall() == [(1,)]
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_ingest_keeps_live_database_when_import_fails(tmp_path):
    csv_path = tmp_path / "source.csv"
    database_path = tmp_path / "retraction_watch.db"
    original = b"existing live database"
    database_path.write_bytes(original)
    write_source_csv(csv_path, [source_row(record_id="not-an-integer")])

    with pytest.raises(ValueError, match="invalid Record ID"):
        ingest(csv_path, sqlite_url(database_path))

    assert database_path.read_bytes() == original
    assert list(tmp_path.glob(".retraction_watch.db.*.tmp*")) == []


def test_ingest_keeps_live_database_when_index_validation_fails(tmp_path, monkeypatch):
    import scripts.ingest_csv as importer

    csv_path = tmp_path / "source.csv"
    database_path = tmp_path / "retraction_watch.db"
    original = b"existing live database"
    database_path.write_bytes(original)
    write_source_csv(csv_path, [source_row()])

    def invalid_index(connection):
        raise RuntimeError("FTS integrity failure")

    monkeypatch.setattr(importer, "check_fts_integrity", invalid_index)
    with pytest.raises(RuntimeError, match="FTS integrity failure"):
        ingest(csv_path, sqlite_url(database_path))
    assert database_path.read_bytes() == original
    assert list(tmp_path.glob(".retraction_watch.db.*.tmp*")) == []


@pytest.mark.parametrize(("value", "expected"), [
    ("", None), ("   ", None),
    ("6/24/1756 12:00:00 AM", date(1756, 6, 24)),
    ("1/1/1753 12:00:00 AM", date(1753, 1, 1)),
    ("6/24/2020 23:30", date(2020, 6, 24)),
    ("6/24/2020 23:30:59", date(2020, 6, 24)),
    ("6/24/2020", date(2020, 6, 24)),
    ("2020-06-24", date(2020, 6, 24)),
])
def test_supported_date_formats(value, expected):
    assert parse_date(value) == expected


def test_invalid_populated_date_does_not_replace_database(tmp_path):
    source = tmp_path / "source.csv"
    database = tmp_path / "live.db"
    database.write_bytes(b"previous valid database")
    row = source_row()
    row["OriginalPaperDate"] = "2/30/2020"
    write_source_csv(source, [row])
    with pytest.raises(ValueError, match="Record ID 1: invalid OriginalPaperDate"):
        ingest(source, sqlite_url(database))
    assert database.read_bytes() == b"previous valid database"
    assert list(tmp_path.glob(".*.tmp*")) == []


def test_ingestion_records_verifiable_dataset_metadata(tmp_path):
    source = tmp_path / "source.csv"
    database = tmp_path / "live.db"
    row = source_row()
    row["RetractionDate"] = "6/24/1756 12:00:00 AM"
    row["OriginalPaperDate"] = "1/1/1753 12:00:00 AM"
    write_source_csv(source, [row], encoding="utf-8-sig")
    ingest(source, sqlite_url(database))
    with sqlite3.connect(database) as connection:
        name, digest, imported_at, count, version = connection.execute(
            "SELECT source_filename, source_sha256, imported_at, record_count, api_version FROM dataset_import"
        ).fetchone()
        assert name == "source.csv"
        assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
        assert imported_at.endswith("+00:00")
        assert count == 1
        assert version == "0.2.1"
        assert connection.execute("SELECT retraction_date, original_paper_date FROM retractions").fetchone() == (
            "1756-06-24", "1753-01-01",
        )


def test_changed_source_does_not_publish_metadata_or_database(tmp_path, monkeypatch):
    import scripts.ingest_csv as importer

    source, database = tmp_path / "source.csv", tmp_path / "live.db"
    write_source_csv(source, [source_row()])
    database.write_bytes(b"previous database")
    digests = iter(["original", "changed"])
    monkeypatch.setattr(importer, "source_digest", lambda path: next(digests))
    with pytest.raises(ValueError, match="CSV changed during ingestion"):
        ingest(source, sqlite_url(database))
    assert database.read_bytes() == b"previous database"
