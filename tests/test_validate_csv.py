import csv

import pytest

from scripts.validate_csv import REQUIRED_COLUMNS, validate_csv


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_validate_csv_accepts_valid_data(tmp_path):
    path = tmp_path / "data.csv"
    row = dict.fromkeys(REQUIRED_COLUMNS, "value")
    row["Record ID"] = "1"
    row["Title"] = "Test article"
    write_csv(path, sorted(REQUIRED_COLUMNS), [row])

    assert validate_csv(path) == 1


def test_validate_csv_rejects_missing_columns(tmp_path):
    path = tmp_path / "data.csv"
    write_csv(path, ["Record ID", "Title"], [{"Record ID": "1", "Title": "Test"}])

    with pytest.raises(ValueError, match="missing required columns"):
        validate_csv(path)


def test_validate_csv_rejects_empty_data(tmp_path):
    path = tmp_path / "data.csv"
    write_csv(path, sorted(REQUIRED_COLUMNS), [])

    with pytest.raises(ValueError, match="no data rows"):
        validate_csv(path)
