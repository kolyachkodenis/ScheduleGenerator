"""Ensure every catalog constraint has one declared testing status."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "constraints" / "CATALOG.md"
COVERAGE = ROOT / "docs" / "testing" / "CONSTRAINT_COVERAGE.md"
ID_PATTERN = re.compile(r"\b(?:HC|SC)-[0-9]{3}\b")
ROW_PATTERN = re.compile(r"^\| ((?:HC|SC)-[0-9]{3}) \| (Automated|Deferred) \|", re.MULTILINE)


def main() -> int:
    catalog_ids = set(ID_PATTERN.findall(CATALOG.read_text(encoding="utf-8")))
    rows = ROW_PATTERN.findall(COVERAGE.read_text(encoding="utf-8"))
    row_ids = [constraint_id for constraint_id, _status in rows]
    counts = Counter(row_ids)
    errors = []

    missing = sorted(catalog_ids - set(row_ids))
    extra = sorted(set(row_ids) - catalog_ids)
    duplicates = sorted(
        constraint_id for constraint_id, count in counts.items() if count != 1
    )
    if missing:
        errors.append(f"Missing coverage rows: {missing}")
    if extra:
        errors.append(f"Unknown coverage rows: {extra}")
    if duplicates:
        errors.append(f"Duplicate coverage rows: {duplicates}")

    if errors:
        print("Constraint coverage check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    status_counts = Counter(status for _constraint_id, status in rows)
    print(
        f"Constraint coverage passed for {len(rows)} rules: "
        f"{status_counts['Automated']} automated, {status_counts['Deferred']} deferred."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

