import csv
import sqlite3

import pytest

from scripts.ingest_csv import ingest
from scripts.validate_csv import REQUIRED_COLUMNS


def write_source_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=sorted(REQUIRED_COLUMNS))
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


def test_ingest_builds_and_promotes_valid_database(tmp_path):
    csv_path = tmp_path / "source.csv"
    database_path = tmp_path / "retraction_watch.db"
    database_path.write_bytes(b"previous database")
    write_source_csv(csv_path, [source_row()])

    result = ingest(csv_path, sqlite_url(database_path))

    assert result.rows == 1
    assert result.countries == 2
    assert result.reasons == 1
    assert result.subjects == 1
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM retractions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM retractions_fts").fetchone()[0] == 1
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_ingest_keeps_live_database_when_import_fails(tmp_path):
    csv_path = tmp_path / "source.csv"
    database_path = tmp_path / "retraction_watch.db"
    original = b"existing live database"
    database_path.write_bytes(original)
    write_source_csv(csv_path, [source_row(record_id="not-an-integer")])

    with pytest.raises(ValueError, match="invalid literal"):
        ingest(csv_path, sqlite_url(database_path))

    assert database_path.read_bytes() == original
    assert list(tmp_path.glob(".retraction_watch.db.*.tmp*")) == []
