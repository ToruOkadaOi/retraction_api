"""
One-off script to verify assumptions about the Retraction Watch CSV
before we design the database schema. Run once, read the output, delete
or keep for reference.

Usage: python scripts/explore_csv.py
"""

# 1. Import csv from stdlib, and Counter from collections.
#    Counter is a dict subclass that counts things — perfect for "how
#    many of each value appears in this column".

import csv
from collections import Counter
from pathlib import Path
from itertools import islice

# 2. Define the path to the CSV as a constant at the top.
#    Use pathlib.Path, not a string. It handles OS path differences and
#    has nice methods like .exists().

CSV_PATH = Path.cwd() / "retraction_watch.csv"

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

print(f"Found file at {CSV_PATH}")

# 3. Open the CSV with encoding="utf-8" and newline="".
#    The newline="" is a csv module quirk — it handles quoted fields with
#    embedded newlines correctly. Always do this when using csv.

with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in islice(reader, 5):
        print(row)

# 4. Use csv.DictReader so each row is a dict keyed by column name.
#    Makes the code readable: row["RetractionNature"] beats row[16].

# 5. Initialize before the loop:
#    - a row counter (int)
#    - Counter() for RetractionNature
#    - Counter() for Paywalled
#    - Counter() for ArticleType (bonus — useful later)
#    - an int counter for rows where RetractionDOI == "unavailable"
#    - an int counter for rows where OriginalPaperPubMedID == "0"

# 6. Loop over the reader. For each row:
#    - increment row counter
#    - update each Counter with the relevant field
#    - check the sentinel conditions and increment those counters

# 7. After the loop, print a summary. Use f-strings. Show:
#    - total rows
#    - the Counters (they print nicely with .most_common())
#    - the sentinel counts as percentages of total

# 8. Run it. You should see ~70k rows. If you see 0 or an error,
#    the CSV path is wrong.