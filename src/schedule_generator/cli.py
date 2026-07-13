"""Command-line interface for the scheduling core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schedule_generator.api import GenerationOptions, SchedulingProblem, generate_schedule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
        problem = SchedulingProblem.from_mapping(dataset)
        options = GenerationOptions(args.time_limit, args.seed, args.workers)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2

    result = generate_schedule(problem, options)
    output = json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    print(
        f"Generation status: {result.status.value}; assignments: {len(result.assignments)}",
        file=sys.stderr,
    )
    return 0 if result.is_success else 1

