"""Validate the source CSV before ingestion or automated updates."""

import argparse
import csv
from pathlib import Path

REQUIRED_COLUMNS = {
    "Record ID",
    "Title",
    "Journal",
    "RetractionNature",
    "Paywalled",
    "Publisher",
    "ArticleType",
    "Institution",
    "URLS",
    "Author",
    "Notes",
    "RetractionDate",
    "OriginalPaperDate",
    "RetractionDOI",
    "RetractionPubMedID",
    "OriginalPaperDOI",
    "OriginalPaperPubMedID",
    "Country",
    "Reason",
    "Subject",
}


def validate_csv(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        columns = set(reader.fieldnames or [])
        if len(columns) != len(reader.fieldnames or []):
            raise ValueError("CSV has duplicate column names")
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        row_count = 0
        record_ids: set[int] = set()
        try:
            for row in reader:
                line_number = reader.line_num
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"CSV row ending at line {line_number} has the wrong number of columns")
                if not any(value.strip() for value in row.values()):
                    continue
                row_count += 1
                raw_id = row["Record ID"].strip()
                if not raw_id:
                    raise ValueError(f"CSV row ending at line {line_number} has no Record ID")
                if not raw_id.isascii() or not raw_id.isdecimal() or not 0 < int(raw_id) <= 2**63 - 1:
                    raise ValueError(f"CSV row ending at line {line_number} has an invalid Record ID: {raw_id!r}")
                record_id = int(raw_id)
                if record_id in record_ids:
                    raise ValueError(f"CSV row ending at line {line_number} has duplicate Record ID {record_id}")
                record_ids.add(record_id)
                if not row["Title"].strip():
                    raise ValueError(f"CSV row ending at line {line_number} has no title")
        except csv.Error as exc:
            raise ValueError(f"Malformed CSV near line {reader.line_num}: {exc}") from exc

    if row_count == 0:
        raise ValueError("CSV contains no data rows")
    return row_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    row_count = validate_csv(args.path)
    print(f"Validated {row_count} CSV rows")


if __name__ == "__main__":
    main()
