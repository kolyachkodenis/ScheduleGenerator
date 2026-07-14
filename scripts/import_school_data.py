"""Preview or apply a school dataset import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from schedule_generator.data_import import apply_import, preview_import
from schedule_generator.storage import DatasetStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--database", type=Path, default=Path("schedule-generator.db"))
    parser.add_argument("--apply", action="store_true", help="save a valid preview")
    args = parser.parse_args()
    preview = preview_import(args.source)
    print(json.dumps({"valid": preview.valid, "errors": [issue.__dict__ for issue in preview.errors]}, indent=2))
    if not preview.valid:
        return 1
    if args.apply:
        with DatasetStore(args.database) as store:
            stored = apply_import(store, preview)
        print(f"Saved {stored.dataset_id} revision {stored.revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
