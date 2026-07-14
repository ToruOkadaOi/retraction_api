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
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        row_count = 0
        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            if not row["Record ID"].strip():
                raise ValueError(f"CSV row {line_number} has no Record ID")
            if not row["Title"].strip():
                raise ValueError(f"CSV row {line_number} has no title")

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
