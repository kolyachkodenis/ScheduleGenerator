"""Approval, publication, and printer-friendly timetable exports."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr

from schedule_generator.editing import TimetableEditingService
from schedule_generator.storage import DatasetStore


@dataclass(frozen=True)
class Publication:
    publication_id: str
    draft_id: str
    version: int
    status: str
    artifacts: dict[str, dict[str, str | int]]
    approved_at: str
    published_at: str | None
    unpublished_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _participant_classes(dataset: dict[str, Any], participant: dict[str, str]) -> set[str]:
    if participant["type"] == "class":
        return {participant["id"]}
    if participant["type"] == "group":
        groups = {item["id"]: item for item in dataset["groups"]}
        return {groups[participant["id"]]["class_id"]}
    cohorts = {item["id"]: item for item in dataset["cohorts"]}
    result: set[str] = set()
    for member in cohorts[participant["id"]]["members"]:
        result.update(_participant_classes(dataset, member))
    return result


def timetable_views(
    dataset: dict[str, Any], assignments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return class and teacher grids in deterministic print order."""

    period = dataset["academic_period"]
    days = sorted(period["days"], key=lambda item: item["ordinal"])
    periods = sorted(period["periods"], key=lambda item: item["ordinal"])
    requirements = {item["id"]: item for item in dataset["curriculum_requirements"]}
    subjects = {item["id"]: item["label"] for item in dataset["subjects"]}
    teachers = {item["id"]: item["label"] for item in dataset["teachers"]}
    rooms = {item["id"]: item["label"] for item in dataset["classrooms"]}
    classes = {item["id"]: item["label"] for item in dataset["classes"]}

    resolved = []
    for assignment in assignments:
        requirement = requirements[assignment["requirement_id"]]
        class_ids = _participant_classes(dataset, requirement["participant"])
        resolved.append(
            (
                assignment,
                subjects[requirement["subject_id"]],
                class_ids,
            )
        )

    views: list[dict[str, Any]] = []
    resources = (
        ("class", sorted(dataset["classes"], key=lambda item: (item["grade"], item["label"]))),
        ("teacher", sorted(dataset["teachers"], key=lambda item: item["label"])),
    )
    for kind, items in resources:
        for resource in items:
            cells: dict[tuple[str, str], str] = {}
            for assignment, subject, class_ids in resolved:
                matches = (
                    resource["id"] in class_ids
                    if kind == "class"
                    else assignment["teacher_id"] == resource["id"]
                )
                if not matches:
                    continue
                detail = (
                    f"{teachers[assignment['teacher_id']]} | {rooms[assignment['classroom_id']]}"
                    if kind == "class"
                    else f"{', '.join(classes[item] for item in sorted(class_ids))} | "
                    f"{rooms[assignment['classroom_id']]}"
                )
                text = f"{subject}\n{detail}"
                for period_id in assignment["occupied_period_ids"]:
                    cells[(assignment["slot"]["day_id"], period_id)] = text
            views.append(
                {
                    "kind": kind,
                    "resource_id": resource["id"],
                    "label": resource["label"],
                    "days": days,
                    "periods": periods,
                    "cells": cells,
                }
            )
    return views


def _safe_sheet_names(views: list[dict[str, Any]]) -> list[str]:
    used: set[str] = set()
    names = []
    for view in views:
        prefix = "Class" if view["kind"] == "class" else "Teacher"
        base = re.sub(r"[\\/*?:\[\]]", "-", f"{prefix} - {view['label']}")[:31].strip()
        name = base
        suffix = 2
        while name.casefold() in used:
            tail = f" {suffix}"
            name = f"{base[:31 - len(tail)]}{tail}"
            suffix += 1
        used.add(name.casefold())
        names.append(name)
    return names


def _column_name(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _cell(reference: str, value: str, style: int = 0) -> str:
    preserve = ' xml:space="preserve"' if value.strip() != value or "\n" in value else ""
    return (
        f'<c r="{reference}" t="inlineStr" s="{style}"><is><t{preserve}>'
        f"{escape(value)}</t></is></c>"
    )


def export_xlsx(
    dataset: dict[str, Any], assignments: list[dict[str, Any]], destination: Path
) -> Path:
    """Write an XLSX workbook without requiring an office installation."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    views = timetable_views(dataset, assignments)
    names = _safe_sheet_names(views)
    sheet_xml = []
    for view in views:
        last_column = _column_name(len(view["days"]) + 1)
        rows = [
            '<row r="1" ht="30" customHeight="1">'
            + _cell("A1", f"{dataset['school']['label']} - {view['label']}", 1)
            + "</row>",
            '<row r="2" ht="22" customHeight="1">'
            + _cell("A2", dataset["academic_period"]["label"], 2)
            + "</row>",
        ]
        header = [_cell("A4", "Period", 3)]
        for index, day in enumerate(view["days"], start=2):
            header.append(_cell(f"{_column_name(index)}4", day["label"], 3))
        rows.append('<row r="4" ht="24" customHeight="1">' + "".join(header) + "</row>")
        for row_index, period in enumerate(view["periods"], start=5):
            label = period["label"]
            if period.get("start_time") and period.get("end_time"):
                label += f"\n{period['start_time']}-{period['end_time']}"
            cells = [_cell(f"A{row_index}", label, 4)]
            for column_index, day in enumerate(view["days"], start=2):
                value = view["cells"].get((day["id"], period["id"]), "")
                cells.append(_cell(f"{_column_name(column_index)}{row_index}", value, 5))
            rows.append(
                f'<row r="{row_index}" ht="48" customHeight="1">' + "".join(cells) + "</row>"
            )
        merges = f'<mergeCells count="2"><mergeCell ref="A1:{last_column}1"/><mergeCell ref="A2:{last_column}2"/></mergeCells>'
        sheet_xml.append(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="A1:{last_column}{len(view["periods"]) + 4}"/>'
            '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            '<cols><col min="1" max="1" width="17" customWidth="1"/>'
            f'<col min="2" max="{len(view["days"]) + 1}" width="25" customWidth="1"/></cols>'
            f"<sheetData>{''.join(rows)}</sheetData>{merges}"
            f'<autoFilter ref="A4:{last_column}{len(view["periods"]) + 4}"/>'
            '<pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.2"/>'
            '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="1" paperSize="9"/>'
            '</worksheet>'
        )

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    content_types.extend(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, len(views) + 1)
    )
    content_types.append("</Types>")
    workbook_sheets = "".join(
        f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(names, start=1)
    )
    workbook_rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(views) + 1)
    )
    workbook_rels += f'<Relationship Id="rId{len(views) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3"><font><sz val="10"/><name val="Aptos"/></font><font><b/><sz val="18"/><color rgb="FFFFFFFF"/><name val="Aptos Display"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font></fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF153E75"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDCE6F1"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"><color rgb="FFB8C5D6"/></left><right style="thin"><color rgb="FFB8C5D6"/></right><top style="thin"><color rgb="FFB8C5D6"/></top><bottom style="thin"><color rgb="FFB8C5D6"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets>'
            + workbook_sheets
            + "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + workbook_rels
            + "</Relationships>",
        )
        archive.writestr("xl/styles.xml", styles)
        for index, xml in enumerate(sheet_xml, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
    return destination


def export_pdf(
    dataset: dict[str, Any], assignments: list[dict[str, Any]], destination: Path
) -> Path:
    """Write one landscape A4 page per class or teacher."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle
    except ImportError as error:  # pragma: no cover - exercised only in incomplete installs
        raise RuntimeError("PDF export requires reportlab") from error

    destination.parent.mkdir(parents=True, exist_ok=True)
    views = timetable_views(dataset, assignments)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ScheduleTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=colors.HexColor("#153E75"), spaceAfter=3 * mm)
    cell_style = ParagraphStyle("ScheduleCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9, alignment=TA_LEFT)
    header_style = ParagraphStyle("ScheduleHeader", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER)
    document = SimpleDocTemplate(str(destination), pagesize=landscape(A4), leftMargin=9 * mm, rightMargin=9 * mm, topMargin=9 * mm, bottomMargin=9 * mm, title=f"{dataset['school']['label']} timetable")
    story = []
    for view_index, view in enumerate(views):
        kind = "Class" if view["kind"] == "class" else "Teacher"
        story.append(Paragraph(f"{escape(dataset['school']['label'])} - {kind}: {escape(view['label'])}", title_style))
        story.append(Paragraph(escape(dataset["academic_period"]["label"]), cell_style))
        data = [[Paragraph("Period", header_style)] + [Paragraph(escape(day["label"]), header_style) for day in view["days"]]]
        for period in view["periods"]:
            label = period["label"]
            if period.get("start_time") and period.get("end_time"):
                label += f"<br/>{period['start_time']}-{period['end_time']}"
            row = [Paragraph(label, cell_style)]
            for day in view["days"]:
                value = escape(view["cells"].get((day["id"], period["id"]), "")).replace("\n", "<br/>")
                row.append(Paragraph(value, cell_style))
            data.append(row)
        page_width = landscape(A4)[0] - 18 * mm
        table = Table(data, colWidths=[28 * mm] + [(page_width - 28 * mm) / len(view["days"])] * len(view["days"]), repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153E75")),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#DCE6F1")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        if view_index < len(views) - 1:
            story.append(PageBreak())

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#52657A"))
        canvas.drawRightString(landscape(A4)[0] - 9 * mm, 5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return destination


class PublicationService:
    """Approve immutable draft versions and control their distributed files."""

    def __init__(self, store: DatasetStore, output_directory: str | Path) -> None:
        self.store = store
        self.output_directory = Path(output_directory)

    @staticmethod
    def _from_row(row: Any) -> Publication:
        return Publication(
            publication_id=row["publication_id"],
            draft_id=row["draft_id"],
            version=int(row["version"]),
            status=row["status"],
            artifacts=json.loads(row["artifacts_json"]),
            approved_at=row["approved_at"],
            published_at=row["published_at"],
            unpublished_at=row["unpublished_at"],
        )

    def approve(self, draft_id: str) -> Publication:
        draft = TimetableEditingService(self.store).get(draft_id)
        if draft.version.validation_errors:
            raise ValueError("a timetable with validation errors cannot be approved")
        existing = self.store.connection.execute(
            "SELECT * FROM timetable_publications WHERE draft_id = ? AND version = ?",
            (draft_id, draft.current_version),
        ).fetchone()
        if existing:
            return self._from_row(existing)
        publication_id = uuid.uuid4().hex
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO timetable_publications(publication_id, draft_id, version, status) "
                "VALUES (?, ?, ?, 'APPROVED')",
                (publication_id, draft_id, draft.current_version),
            )
        return self.get(publication_id)

    def get(self, publication_id: str) -> Publication:
        row = self.store.connection.execute(
            "SELECT * FROM timetable_publications WHERE publication_id = ?", (publication_id,)
        ).fetchone()
        if row is None:
            raise KeyError(publication_id)
        return self._from_row(row)

    def list(self) -> list[Publication]:
        rows = self.store.connection.execute(
            "SELECT * FROM timetable_publications ORDER BY approved_at, publication_id"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def publish(self, publication_id: str) -> Publication:
        publication = self.get(publication_id)
        if publication.status == "PUBLISHED":
            return publication
        if publication.status not in {"APPROVED", "UNPUBLISHED"}:
            raise ValueError("only an approved timetable can be published")
        draft = TimetableEditingService(self.store)._version(
            publication.draft_id, publication.version
        )
        if draft.validation_errors:
            raise ValueError("a timetable with validation errors cannot be published")
        parent = self.store.connection.execute(
            "SELECT dataset_id, dataset_revision FROM timetable_drafts WHERE draft_id = ?",
            (publication.draft_id,),
        ).fetchone()
        dataset = self.store.get(parent["dataset_id"], int(parent["dataset_revision"])).data
        stem = f"timetable-{publication.publication_id}"
        xlsx_path = export_xlsx(dataset, draft.assignments, self.output_directory / f"{stem}.xlsx")
        pdf_path = export_pdf(dataset, draft.assignments, self.output_directory / f"{stem}.pdf")
        artifacts = {}
        for kind, path in (("xlsx", xlsx_path), ("pdf", pdf_path)):
            content = path.read_bytes()
            artifacts[kind] = {
                "filename": path.name,
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE timetable_publications SET status = 'PUBLISHED', artifacts_json = ?, "
                "published_at = CURRENT_TIMESTAMP, unpublished_at = NULL WHERE publication_id = ?",
                (json.dumps(artifacts, sort_keys=True), publication_id),
            )
        return self.get(publication_id)

    def unpublish(self, publication_id: str) -> Publication:
        publication = self.get(publication_id)
        if publication.status != "PUBLISHED":
            raise ValueError("only a published timetable can be unpublished")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE timetable_publications SET status = 'UNPUBLISHED', "
                "unpublished_at = CURRENT_TIMESTAMP WHERE publication_id = ?",
                (publication_id,),
            )
        return self.get(publication_id)

    def download(self, filename: str) -> tuple[Path, str]:
        if Path(filename).name != filename:
            raise ValueError("invalid download filename")
        row = self.store.connection.execute(
            "SELECT artifacts_json FROM timetable_publications WHERE status = 'PUBLISHED'"
        ).fetchall()
        for record in row:
            artifacts = json.loads(record[0])
            for kind, artifact in artifacts.items():
                if artifact["filename"] == filename:
                    path = self.output_directory / filename
                    if not path.is_file():
                        raise KeyError(filename)
                    content_type = (
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if kind == "xlsx"
                        else "application/pdf"
                    )
                    return path, content_type
        raise KeyError(filename)
