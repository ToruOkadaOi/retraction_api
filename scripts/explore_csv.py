import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

CSV_PATH = settings.csv_path

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

print(f"Found file at {CSV_PATH}")


@dataclass
class RetractionStats:
    row_count: int = 0

    nature_counter: Counter = field(default_factory=Counter)
    paywalled_counter: Counter = field(default_factory=Counter)
    article_type_counter: Counter = field(default_factory=Counter)

    # Sentinel val detection
    retraction_doi_unavailable: int = 0
    retraction_pmid_zero: int = 0
    original_doi_unavailable: int = 0
    original_pmid_zero: int = 0

    # Empty string detection
    empty_title: int = 0
    empty_journal: int = 0
    empty_retraction_date: int = 0
    empty_original_date: int = 0


stats = RetractionStats()

with open(CSV_PATH, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stats.row_count += 1

        stats.nature_counter[row["RetractionNature"]] += 1
        stats.paywalled_counter[row["Paywalled"]] += 1
        stats.article_type_counter[row["ArticleType"]] += 1

        if row["RetractionDOI"] == "unavailable":
            stats.retraction_doi_unavailable += 1
        if row["RetractionPubMedID"] == "0":
            stats.retraction_pmid_zero += 1
        if row["OriginalPaperDOI"] == "unavailable":
            stats.original_doi_unavailable += 1
        if row["OriginalPaperPubMedID"] == "0":
            stats.original_pmid_zero += 1

        if row["Title"] == "":
            stats.empty_title += 1
        if row["Journal"] == "":
            stats.empty_journal += 1
        if row["RetractionDate"] == "":
            stats.empty_retraction_date += 1
        if row["OriginalPaperDate"] == "":
            stats.empty_original_date += 1


# Summary. !r wraps strings in quotes so empty strings are visible
print(f"\nTotal rows: {stats.row_count}")

print("\nRetractionNature values:")
for value, count in stats.nature_counter.most_common():
    print(f"  {value!r}: {count}")  # !r - call the __repr__ # new to me

print("\nPaywalled values:")
for value, count in stats.paywalled_counter.most_common():
    print(f"  {value!r}: {count}")

print("\nArticleType values (top 10):")
for value, count in stats.article_type_counter.most_common(10):
    print(f"  {value!r}: {count}")

print("\nSentinel values:")
print(
    f"  RetractionDOI == 'unavailable': {stats.retraction_doi_unavailable} "
    f"({stats.retraction_doi_unavailable / stats.row_count:.1%})"
)
print(
    f"  RetractionPubMedID == '0': {stats.retraction_pmid_zero} "
    f"({stats.retraction_pmid_zero / stats.row_count:.1%})"
)
print(
    f"  OriginalPaperDOI == 'unavailable': {stats.original_doi_unavailable} "
    f"({stats.original_doi_unavailable / stats.row_count:.1%})"
)
print(
    f"  OriginalPaperPubMedID == '0': {stats.original_pmid_zero} "
    f"({stats.original_pmid_zero / stats.row_count:.1%})"
)

print("\nEmpty-string counts on required fields:")
print(
    f"  Title: {stats.empty_title} "
    f"({stats.empty_title / stats.row_count:.1%})"
)
print(
    f"  Journal: {stats.empty_journal} "
    f"({stats.empty_journal / stats.row_count:.1%})"
)
print(
    f"  RetractionDate: {stats.empty_retraction_date} "
    f"({stats.empty_retraction_date / stats.row_count:.1%})"
)
print(
    f"  OriginalPaperDate: {stats.empty_original_date} "
    f"({stats.empty_original_date / stats.row_count:.1%})"
)
