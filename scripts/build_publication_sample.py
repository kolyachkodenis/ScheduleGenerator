"""Build representative timetable publication artifacts for visual review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schedule_generator.prototype import solve_dataset
from schedule_generator.publication import export_pdf, export_xlsx


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=ROOT / "outputs" / "stage-11-publication" / "sample-timetable.xlsx",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "output" / "pdf" / "sample-timetable.pdf",
    )
    args = parser.parse_args()
    dataset = json.loads(
        (ROOT / "examples" / "small-school.json").read_text(encoding="utf-8")
    )
    result = solve_dataset(dataset, time_limit=15, seed=1, workers=1)
    if result["status"] not in {"OPTIMAL", "FEASIBLE"} or result["validation_errors"]:
        raise RuntimeError(f"sample generation failed: {result['status']}")
    export_xlsx(dataset, result["assignments"], args.xlsx)
    export_pdf(dataset, result["assignments"], args.pdf)
    print(f"XLSX: {args.xlsx}")
    print(f"PDF: {args.pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
