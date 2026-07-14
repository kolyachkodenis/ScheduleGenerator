"""Preview and atomically import canonical datasets from CSV or XLSX tables."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from schedule_generator.storage import DatasetStore, StoredDataset
from schedule_generator.validation import dataset_validation_errors


@dataclass(frozen=True)
class ImportIssue:
    source: str
    row: int
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ImportPreview:
    dataset: dict[str, Any] | None
    errors: tuple[ImportIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.errors and self.dataset is not None


def _preview_rows(rows: list[dict[str, str]], source: str) -> ImportPreview:
    errors: list[ImportIssue] = []
    dataset: dict[str, Any] = {}
    for number, row in enumerate(rows, start=2):
        section = (row.get("section") or "").strip()
        value = row.get("value_json") or ""
        if not section:
            errors.append(ImportIssue(source, number, "section", "required", "section is required"))
            continue
        if section in dataset:
            errors.append(ImportIssue(source, number, "section", "duplicate", f"duplicate section {section!r}"))
            continue
        try:
            dataset[section] = json.loads(value)
        except json.JSONDecodeError as error:
            errors.append(
                ImportIssue(source, number, "value_json", "invalid_json", f"{error.msg} at column {error.colno}")
            )
    if not errors:
        for message in dataset_validation_errors(dataset):
            errors.append(ImportIssue(source, 0, "$", "invalid_dataset", message))
    return ImportPreview(dataset if dataset else None, tuple(errors))


def preview_csv(path: str | Path) -> ImportPreview:
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return _preview_rows(list(csv.DictReader(stream)), path.name)


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    value = 0
    for character in letters.group(0) if letters else "A":
        value = value * 26 + ord(character) - 64
    return value - 1


def _xlsx_rows(path: Path, sheet_name: str = "Dataset") -> list[dict[str, str]]:
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    package_relationships = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels.findall("p:Relationship", package_relationships)}
        sheet = next((item for item in workbook.findall("m:sheets/m:sheet", namespace) if item.attrib["name"] == sheet_name), None)
        if sheet is None:
            raise ValueError(f"worksheet {sheet_name!r} is missing")
        target = targets[sheet.attrib[f"{{{namespace['r']}}}id"]].lstrip("/")
        target = target if target.startswith("xl/") else f"xl/{target}"
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", namespace)) for item in strings.findall("m:si", namespace)]
        worksheet = ET.fromstring(archive.read(target))
        matrix: list[list[str]] = []
        for row in worksheet.findall(".//m:sheetData/m:row", namespace):
            values: list[str] = []
            for cell in row.findall("m:c", namespace):
                index = _column_index(cell.attrib.get("r", "A1"))
                while len(values) <= index:
                    values.append("")
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    values[index] = "".join(node.text or "" for node in cell.findall(".//m:t", namespace))
                else:
                    node = cell.find("m:v", namespace)
                    raw = node.text if node is not None and node.text is not None else ""
                    values[index] = shared[int(raw)] if kind == "s" and raw else raw
            matrix.append(values)
    if not matrix:
        return []
    headers = matrix[0]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in matrix[1:] if any(row)]


def preview_xlsx(path: str | Path) -> ImportPreview:
    path = Path(path)
    try:
        return _preview_rows(_xlsx_rows(path), f"{path.name}:Dataset")
    except (KeyError, ValueError, zipfile.BadZipFile, ET.ParseError) as error:
        return ImportPreview(None, (ImportIssue(path.name, 0, "$", "invalid_workbook", str(error)),))


def preview_import(path: str | Path) -> ImportPreview:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return preview_csv(path)
    if path.suffix.lower() == ".xlsx":
        return preview_xlsx(path)
    raise ValueError("supported import formats are .csv and .xlsx")


def apply_import(store: DatasetStore, preview: ImportPreview) -> StoredDataset:
    if not preview.valid or preview.dataset is None:
        raise ValueError("cannot apply an invalid import preview")
    return store.save(preview.dataset)


def export_csv(dataset: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("section", "value_json"))
        writer.writeheader()
        for section, value in dataset.items():
            writer.writerow({"section": section, "value_json": json.dumps(value, ensure_ascii=False, separators=(",", ":"))})
    return path
