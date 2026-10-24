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


@pytest.mark.parametrize("record_id", ["oops", "-1", "0", "1.5", "１２", str(2**63)])
def test_validate_csv_rejects_invalid_ids(tmp_path, record_id):
    path = tmp_path / "data.csv"
    row = dict.fromkeys(REQUIRED_COLUMNS, "value")
    row["Record ID"] = record_id
    write_csv(path, sorted(REQUIRED_COLUMNS), [row])
    with pytest.raises(ValueError, match="invalid Record ID"):
        validate_csv(path)


def test_validate_csv_rejects_duplicate_numeric_ids(tmp_path):
    path = tmp_path / "data.csv"
    row = dict.fromkeys(REQUIRED_COLUMNS, "value")
    write_csv(path, sorted(REQUIRED_COLUMNS), [row | {"Record ID": "1"}, row | {"Record ID": "01"}])
    with pytest.raises(ValueError, match="duplicate Record ID 1"):
        validate_csv(path)


@pytest.mark.parametrize("extra", [False, True])
def test_validate_csv_rejects_wrong_row_width(tmp_path, extra):
    path = tmp_path / "data.csv"
    columns = ["Record ID", "Title", *sorted(REQUIRED_COLUMNS - {"Record ID", "Title"})]
    values = ["1", "Title", *([""] * (len(columns) - 2))]
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerow(values + ["extra"] if extra else values[:-1])
    with pytest.raises(ValueError, match="wrong number of columns"):
        validate_csv(path)


def test_validate_csv_rejects_duplicate_headers(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text(",".join([*sorted(REQUIRED_COLUMNS), "Title"]) + "\n")
    with pytest.raises(ValueError, match="duplicate column"):
        validate_csv(path)


def test_validate_csv_accepts_quoted_multiline_fields(tmp_path):
    path = tmp_path / "data.csv"
    row = dict.fromkeys(REQUIRED_COLUMNS, "")
    row.update({"Record ID": "1", "Title": 'Title with "quotes", commas\nand a newline'})
    write_csv(path, sorted(REQUIRED_COLUMNS), [row])
    assert validate_csv(path) == 1


def test_validate_csv_rejects_unclosed_quote(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text(",".join(sorted(REQUIRED_COLUMNS)) + '\n"unfinished')
    with pytest.raises(ValueError, match="Malformed CSV"):
        validate_csv(path)
