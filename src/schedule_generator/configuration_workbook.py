"""Human-editable XLSX round-trip for school scheduling configuration."""

from __future__ import annotations

import re
import zipfile
from collections import defaultdict
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr


SHEETS = ("Difficulty", "Teachers", "Classrooms", "Curriculum")
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PACKAGE_NS = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _column_name(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _column_index(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    value = 0
    for character in match.group(0) if match else "A":
        value = value * 26 + ord(character) - 64
    return value - 1


def _cell(reference: str, value: Any, style: int) -> str:
    if isinstance(value, int):
        return f'<c r="{reference}" s="{style}"><v>{value}</v></c>'
    text = str(value or "")
    preserve = ' xml:space="preserve"' if text.strip() != text else ""
    return (
        f'<c r="{reference}" t="inlineStr" s="{style}"><is><t{preserve}>'
        f"{escape(text)}</t></is></c>"
    )


def _sheet_xml(
    headers: list[str], rows: list[list[Any]], widths: list[int], row_height: int = 21
) -> str:
    last_column = _column_name(len(headers))
    xml_rows = [
        '<row r="1" ht="25" customHeight="1">'
        + "".join(
            _cell(f"{_column_name(index)}1", header, 1)
            for index, header in enumerate(headers, start=1)
        )
        + "</row>"
    ]
    for row_index, row in enumerate(rows, start=2):
        xml_rows.append(
            f'<row r="{row_index}" ht="{row_height}" customHeight="1">'
            + "".join(
                _cell(f"{_column_name(column_index)}{row_index}", value, 2)
                for column_index, value in enumerate(row, start=1)
            )
            + "</row>"
        )
    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    last_row = max(1, len(rows) + 1)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_column}{last_row}"/>'
        '<sheetViews><sheetView showGridLines="0" workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        f"<cols>{columns}</cols><sheetData>{''.join(xml_rows)}</sheetData>"
        f'<autoFilter ref="A1:{last_column}{last_row}"/>'
        '<pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.2"/>'
        "</worksheet>"
    )


def export_configuration_xlsx(dataset: dict[str, Any]) -> bytes:
    """Export editable scheduling inputs as four normalized worksheets."""

    participants = {
        (kind, item["id"]): item["label"]
        for kind, collection in (
            ("class", "classes"),
            ("group", "groups"),
            ("cohort", "cohorts"),
        )
        for item in dataset[collection]
    }
    difficulty = [
        [item["id"], item["label"], item["default_workload"]]
        for item in dataset["subjects"]
    ]

    assignments: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for requirement in dataset["curriculum_requirements"]:
        for teacher_id in requirement["eligible_teacher_ids"]:
            assignments[(teacher_id, requirement["subject_id"])].append(requirement)
    teacher_rows: list[list[Any]] = []
    for teacher in dataset["teachers"]:
        by_type: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for subject_id in teacher["qualified_subject_ids"]:
            for requirement in assignments[(teacher["id"], subject_id)]:
                participant = requirement["participant"]
                by_type[participant["type"]][subject_id].append(participant["id"])
        assignment_text = {
            participant_type: ";".join(
                f"{subject_id}={','.join(participant_ids)}"
                for subject_id, participant_ids in grouped.items()
            )
            for participant_type, grouped in by_type.items()
        }
        teacher_rows.append(
            [
                teacher["id"],
                teacher["label"],
                ";".join(teacher["qualified_subject_ids"]),
                assignment_text.get("class", ""),
                assignment_text.get("group", ""),
                assignment_text.get("cohort", ""),
            ]
        )

    teacher_room = {
        teacher.get("classroom_id"): teacher["id"]
        for teacher in dataset["teachers"]
        if teacher.get("classroom_id")
    }
    classroom_rows = [
        [
            room["id"],
            room["label"],
            room["capacity"],
            ";".join(room["capabilities"]),
            teacher_room.get(room["id"], ""),
        ]
        for room in dataset["classrooms"]
    ]
    curriculum_rows = [
        [
            requirement["id"],
            requirement["participant"]["type"],
            requirement["participant"]["id"],
            participants.get(
                (
                    requirement["participant"]["type"],
                    requirement["participant"]["id"],
                ),
                "",
            ),
            requirement["subject_id"],
            requirement["weekly_lessons"],
            requirement["block_length"],
            ";".join(requirement["required_room_capabilities"]),
            ";".join(requirement["allowed_classroom_ids"]),
        ]
        for requirement in dataset["curriculum_requirements"]
    ]
    tables = [
        (["subject_id", "subject_name", "difficulty"], difficulty, [22, 30, 12], 21),
        (
            [
                "teacher_id",
                "teacher_name",
                "subject_ids",
                "class_assignments",
                "subgroup_assignments",
                "cohort_assignments",
            ],
            teacher_rows,
            [22, 26, 36, 60, 60, 40],
            60,
        ),
        (
            [
                "classroom_id",
                "classroom_name",
                "capacity",
                "capabilities",
                "assigned_teacher_id",
            ],
            classroom_rows,
            [22, 27, 12, 32, 24],
            32,
        ),
        (
            [
                "requirement_id",
                "participant_type",
                "participant_id",
                "participant_name",
                "subject_id",
                "weekly_lessons",
                "block_length",
                "required_room_capabilities",
                "allowed_classroom_ids",
            ],
            curriculum_rows,
            [30, 18, 25, 30, 24, 16, 14, 32, 34],
            21,
        ),
    ]
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
        for index in range(1, len(SHEETS) + 1)
    )
    content_types.append("</Types>")
    workbook_sheets = "".join(
        f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(SHEETS, start=1)
    )
    workbook_rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(SHEETS) + 1)
    )
    workbook_rels += f'<Relationship Id="rId{len(SHEETS) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="10"/><name val="Aptos"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF153E75"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><bottom style="thin"><color rgb="FFD5DEE8"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
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
        for index, (headers, rows, widths, row_height) in enumerate(tables, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet_xml(headers, rows, widths, row_height),
            )
    return output.getvalue()


def _read_sheet(archive: zipfile.ZipFile, sheet_name: str) -> list[dict[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall("p:Relationship", PACKAGE_NS)
    }
    sheet = next(
        (
            item
            for item in workbook.findall("m:sheets/m:sheet", NS)
            if item.attrib["name"] == sheet_name
        ),
        None,
    )
    if sheet is None:
        raise ValueError(f"worksheet {sheet_name!r} is missing")
    target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
    target = target if target.startswith("xl/") else f"xl/{target}"
    shared: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
        strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.findall(".//m:t", NS))
            for item in strings.findall("m:si", NS)
        ]
    worksheet = ET.fromstring(archive.read(target))
    matrix: list[list[str]] = []
    for row in worksheet.findall(".//m:sheetData/m:row", NS):
        values: list[str] = []
        for cell in row.findall("m:c", NS):
            index = _column_index(cell.attrib.get("r", "A1"))
            while len(values) <= index:
                values.append("")
            kind = cell.attrib.get("t")
            if kind == "inlineStr":
                values[index] = "".join(
                    node.text or "" for node in cell.findall(".//m:t", NS)
                )
            else:
                node = cell.find("m:v", NS)
                raw = node.text if node is not None and node.text is not None else ""
                values[index] = shared[int(raw)] if kind == "s" and raw else raw
        matrix.append(values)
    if not matrix:
        return []
    headers = matrix[0]
    return [
        dict(zip(headers, row + [""] * (len(headers) - len(row))))
        for row in matrix[1:]
        if any(row)
    ]


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def import_configuration_xlsx(
    dataset: dict[str, Any], content: bytes
) -> dict[str, Any]:
    """Parse configuration worksheets into atomically validated dataset updates."""

    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            rows = {name: _read_sheet(archive, name) for name in SHEETS}
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        raise ValueError(f"invalid configuration workbook: {error}") from error

    subjects = [dict(item) for item in dataset["subjects"]]
    subjects_by_id = {item["id"]: item for item in subjects}
    seen_subjects: set[str] = set()
    for row in rows["Difficulty"]:
        subject_id = row.get("subject_id", "").strip()
        if subject_id not in subjects_by_id or subject_id in seen_subjects:
            raise ValueError(f"invalid or duplicate subject_id {subject_id!r} in Difficulty")
        try:
            difficulty = int(row.get("difficulty", ""))
        except ValueError as error:
            raise ValueError(f"invalid difficulty for {subject_id!r}") from error
        if not 1 <= difficulty <= 5:
            raise ValueError(f"difficulty for {subject_id!r} must be between 1 and 5")
        subjects_by_id[subject_id]["default_workload"] = difficulty
        seen_subjects.add(subject_id)
    if seen_subjects != set(subjects_by_id):
        raise ValueError("Difficulty must contain every subject exactly once")

    teacher_data: dict[str, dict[str, Any]] = {}
    assignment_teachers: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows["Teachers"]:
        teacher_id = row.get("teacher_id", "").strip()
        teacher_name = row.get("teacher_name", "").strip()
        subject_ids = _split(row.get("subject_ids", ""))
        if (
            not teacher_id
            or teacher_id in teacher_data
            or not teacher_name
            or not subject_ids
            or any(subject_id not in subjects_by_id for subject_id in subject_ids)
        ):
            raise ValueError("Teachers contains an invalid teacher or subject")
        teacher_data[teacher_id] = {
            "id": teacher_id,
            "label": teacher_name,
            "qualified_subject_ids": subject_ids,
        }
        for participant_type, field in (
            ("class", "class_assignments"),
            ("group", "subgroup_assignments"),
            ("cohort", "cohort_assignments"),
        ):
            for assignment in _split(row.get(field, "")):
                subject_id, separator, participant_list = assignment.partition("=")
                if (
                    not separator
                    or subject_id not in subject_ids
                    or not participant_list
                ):
                    raise ValueError(
                        f"invalid {field} entry {assignment!r} for {teacher_id!r}"
                    )
                for participant_id in _split(participant_list.replace(",", ";")):
                    assignment_teachers[
                        (participant_type, participant_id, subject_id)
                    ].add(teacher_id)
    teachers = list(teacher_data.values())
    teacher_ids = set(teacher_data)
    if not teachers:
        raise ValueError("Teachers must contain at least one teacher")

    classrooms: list[dict[str, Any]] = []
    classroom_ids: set[str] = set()
    assigned_rooms: dict[str, str] = {}
    for row in rows["Classrooms"]:
        classroom_id = row.get("classroom_id", "").strip()
        if not classroom_id or classroom_id in classroom_ids:
            raise ValueError(f"invalid or duplicate classroom_id {classroom_id!r}")
        try:
            capacity = int(row.get("capacity", ""))
        except ValueError as error:
            raise ValueError(f"invalid capacity for {classroom_id!r}") from error
        capabilities = _split(row.get("capabilities", ""))
        if capacity < 1 or not capabilities:
            raise ValueError(f"classroom {classroom_id!r} needs capacity and capabilities")
        classrooms.append(
            {
                "id": classroom_id,
                "label": row.get("classroom_name", "").strip(),
                "capacity": capacity,
                "capabilities": capabilities,
            }
        )
        classroom_ids.add(classroom_id)
        assigned_teacher = row.get("assigned_teacher_id", "").strip()
        if assigned_teacher:
            if assigned_teacher not in teacher_ids or assigned_teacher in assigned_rooms:
                raise ValueError(f"invalid or duplicate room assignment for {assigned_teacher!r}")
            assigned_rooms[assigned_teacher] = classroom_id
    if not classrooms:
        raise ValueError("Classrooms must contain at least one classroom")
    for teacher in teachers:
        if teacher["id"] in assigned_rooms:
            teacher["classroom_id"] = assigned_rooms[teacher["id"]]

    curriculum: list[dict[str, Any]] = []
    requirement_ids: set[str] = set()
    for row in rows["Curriculum"]:
        requirement_id = row.get("requirement_id", "").strip()
        participant_type = row.get("participant_type", "").strip()
        participant_id = row.get("participant_id", "").strip()
        subject_id = row.get("subject_id", "").strip()
        if not requirement_id or requirement_id in requirement_ids:
            raise ValueError(f"invalid or duplicate requirement_id {requirement_id!r}")
        eligible = sorted(
            assignment_teachers[(participant_type, participant_id, subject_id)]
        )
        if not eligible:
            raise ValueError(f"no teacher assignment for requirement {requirement_id!r}")
        try:
            weekly = int(row.get("weekly_lessons", ""))
            block = int(row.get("block_length", ""))
        except ValueError as error:
            raise ValueError(f"invalid lesson count for {requirement_id!r}") from error
        curriculum.append(
            {
                "id": requirement_id,
                "participant": {"type": participant_type, "id": participant_id},
                "subject_id": subject_id,
                "eligible_teacher_ids": eligible,
                "weekly_lessons": weekly,
                "block_length": block,
                "required_room_capabilities": _split(
                    row.get("required_room_capabilities", "")
                ),
                "allowed_classroom_ids": _split(
                    row.get("allowed_classroom_ids", "")
                ),
            }
        )
        requirement_ids.add(requirement_id)
    if not curriculum:
        raise ValueError("Curriculum must contain at least one requirement")
    return {
        "subjects": subjects,
        "teachers": teachers,
        "classrooms": classrooms,
        "curriculum_requirements": curriculum,
    }
