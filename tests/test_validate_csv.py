import csv

import pytest

from scripts.validate_csv import REQUIRED_COLUMNS, validate_csv


def write_csv(path, columns, rows, encoding="utf-8"):
    with path.open("w", encoding=encoding, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_validate_csv_accepts_valid_data(tmp_path, encoding):
    path = tmp_path / "data.csv"
    row = dict.fromkeys(REQUIRED_COLUMNS, "value")
    row["Record ID"] = "1"
    row["Title"] = "Test article"
    columns = ["Record ID", *sorted(REQUIRED_COLUMNS - {"Record ID"})]
    write_csv(path, columns, [row], encoding=encoding)

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


def test_validate_csv_ignores_blank_rows(tmp_path):
    path = tmp_path / "data.csv"
    valid_row = dict.fromkeys(REQUIRED_COLUMNS, "value")
    valid_row["Record ID"] = "1"
    valid_row["Title"] = "Test article"
    blank_row = dict.fromkeys(REQUIRED_COLUMNS, "")
    write_csv(path, sorted(REQUIRED_COLUMNS), [valid_row, blank_row, blank_row])

    assert validate_csv(path) == 1
