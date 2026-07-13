"""Validate repository documentation using only the Python standard library."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "docs" / "PROJECT_CHARTER.md",
    ROOT / "docs" / "ROADMAP.md",
    ROOT / "docs" / "GLOSSARY.md",
    ROOT / "docs" / "adr" / "README.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts
    )


def validate_required_documents(errors: list[str]) -> None:
    for path in REQUIRED_DOCUMENTS:
        if not path.is_file():
            errors.append(f"Missing required document: {path.relative_to(ROOT)}")


def validate_whitespace(path: Path, text: str, errors: list[str]) -> None:
    for number, line in enumerate(text.splitlines(), start=1):
        if line.endswith((" ", "\t")):
            errors.append(f"{path.relative_to(ROOT)}:{number}: trailing whitespace")
        if "\t" in line:
            errors.append(f"{path.relative_to(ROOT)}:{number}: tab character")


def validate_local_links(path: Path, text: str, errors: list[str]) -> None:
    for match in MARKDOWN_LINK.finditer(text):
        destination = match.group(1).strip()
        if not destination or destination.startswith(("#", "http://", "https://", "mailto:")):
            continue

        target_text = destination.split("#", maxsplit=1)[0].strip("<>")
        target = (path.parent / unquote(target_text)).resolve()

        try:
            target.relative_to(ROOT)
        except ValueError:
            errors.append(
                f"{path.relative_to(ROOT)}: local link escapes repository: {destination}"
            )
            continue

        if not target.exists():
            errors.append(
                f"{path.relative_to(ROOT)}: broken local link: {destination}"
            )


def main() -> int:
    errors: list[str] = []
    validate_required_documents(errors)

    files = markdown_files()
    if not files:
        errors.append("No Markdown documentation found")

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path.relative_to(ROOT)}: file is not valid UTF-8")
            continue

        validate_whitespace(path, text, errors)
        validate_local_links(path, text, errors)

    if errors:
        print("Documentation checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Documentation checks passed for {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
