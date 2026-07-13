"""Validate ScheduleGenerator JSON datasets structurally and semantically."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "school-dataset.schema.json"
CATALOG_PATH = ROOT / "docs" / "constraints" / "CATALOG.md"
CONSTRAINT_ID = re.compile(r"\b(?:HC|SC)-[0-9]{3}\b")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"file does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise ValueError(f"file is not valid UTF-8: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error


def path_text(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def validate_schema(
    dataset: Any, schema: Any, require_schema: bool, errors: list[str]
) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        message = "jsonschema is not installed; structural schema validation skipped"
        if require_schema:
            errors.append(message)
        else:
            print(f"Warning: {message}.", file=sys.stderr)
        return

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(dataset), key=lambda item: list(item.path)):
        errors.append(f"{path_text(error.path)}: {error.message}")


class SemanticValidator:
    """Validate references and invariants JSON Schema cannot express."""

    COLLECTION_TYPES = {
        "teacher": "teachers",
        "classroom": "classrooms",
        "class": "classes",
        "group": "groups",
        "cohort": "cohorts",
    }

    def __init__(self, dataset: dict[str, Any]) -> None:
        self.dataset = dataset
        self.errors: list[str] = []
        self.by_collection: dict[str, dict[str, dict[str, Any]]] = {}

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def build_index(self, collection: str) -> dict[str, dict[str, Any]]:
        records = self.dataset.get(collection, [])
        index: dict[str, dict[str, Any]] = {}
        if not isinstance(records, list):
            return index
        for position, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            record_id = record.get("id")
            if not isinstance(record_id, str):
                continue
            if record_id in index:
                self.error(
                    f"$.{collection}[{position}].id",
                    f"duplicate ID {record_id!r}",
                )
            else:
                index[record_id] = record
        return index

    def ref(
        self,
        collection: str,
        record_id: Any,
        location: str,
    ) -> dict[str, Any] | None:
        record = self.by_collection.get(collection, {}).get(record_id)
        if record is None:
            self.error(location, f"unknown {collection} ID {record_id!r}")
        return record

    def typed_ref(
        self,
        reference: Any,
        location: str,
        allowed: set[str] | None = None,
    ) -> dict[str, Any] | None:
        if not isinstance(reference, dict):
            return None
        resource_type = reference.get("type")
        record_id = reference.get("id")
        if allowed is not None and resource_type not in allowed:
            self.error(location, f"resource type {resource_type!r} is not allowed here")
            return None
        collection = self.COLLECTION_TYPES.get(resource_type)
        if collection is None:
            return None
        return self.ref(collection, record_id, f"{location}.id")

    def slot(self, slot: Any, location: str) -> bool:
        if not isinstance(slot, dict):
            return False
        day_ok = slot.get("day_id") in self.by_collection.get("days", {})
        period_ok = slot.get("period_id") in self.by_collection.get("periods", {})
        if not day_ok:
            self.error(f"{location}.day_id", f"unknown day ID {slot.get('day_id')!r}")
        if not period_ok:
            self.error(
                f"{location}.period_id",
                f"unknown period ID {slot.get('period_id')!r}",
            )
        return day_ok and period_ok

    def participant_classes(self, reference: dict[str, Any]) -> set[str]:
        resource_type = reference.get("type")
        record_id = reference.get("id")
        if resource_type == "class":
            return {record_id}
        if resource_type == "group":
            group = self.by_collection.get("groups", {}).get(record_id, {})
            return {group["class_id"]} if "class_id" in group else set()
        if resource_type == "cohort":
            result: set[str] = set()
            cohort = self.by_collection.get("cohorts", {}).get(record_id, {})
            for member in cohort.get("members", []):
                result.update(self.participant_classes(member))
            return result
        return set()

    def participant_size(self, reference: dict[str, Any]) -> int:
        resource_type = reference.get("type")
        record_id = reference.get("id")
        if resource_type == "class":
            return self.by_collection.get("classes", {}).get(record_id, {}).get(
                "student_count", 0
            )
        if resource_type == "group":
            return self.by_collection.get("groups", {}).get(record_id, {}).get(
                "student_count", 0
            )
        if resource_type == "cohort":
            cohort = self.by_collection.get("cohorts", {}).get(record_id, {})
            return sum(self.participant_size(member) for member in cohort.get("members", []))
        return 0

    def validate_calendar(self) -> None:
        period_ids = set(self.by_collection["periods"])
        for shift_id, shift in self.by_collection["shifts"].items():
            for period_id in shift.get("period_ids", []):
                if period_id not in period_ids:
                    self.error(
                        f"$.academic_period.shifts[{shift_id}].period_ids",
                        f"unknown period ID {period_id!r}",
                    )

        for class_id, class_record in self.by_collection["classes"].items():
            self.ref(
                "shifts",
                class_record.get("shift_id"),
                f"$.classes[{class_id}].shift_id",
            )

        period_order = [
            record.get("ordinal") for record in self.by_collection["periods"].values()
        ]
        if len(period_order) != len(set(period_order)):
            self.error("$.academic_period.periods", "period ordinals must be unique")

        day_order = [record.get("ordinal") for record in self.by_collection["days"].values()]
        if len(day_order) != len(set(day_order)):
            self.error("$.academic_period.days", "day ordinals must be unique")

        start = self.dataset.get("academic_period", {}).get("start_date")
        end = self.dataset.get("academic_period", {}).get("end_date")
        if isinstance(start, str) and isinstance(end, str) and start > end:
            self.error("$.academic_period", "start_date must not be after end_date")

    def validate_groups(self) -> None:
        totals: defaultdict[str, int] = defaultdict(int)
        for partition_id, partition in self.by_collection["group_partitions"].items():
            self.ref(
                "classes",
                partition.get("class_id"),
                f"$.group_partitions[{partition_id}].class_id",
            )

        for group_id, group in self.by_collection["groups"].items():
            class_record = self.ref(
                "classes",
                group.get("class_id"),
                f"$.groups[{group_id}].class_id",
            )
            partition = self.ref(
                "group_partitions",
                group.get("partition_id"),
                f"$.groups[{group_id}].partition_id",
            )
            if partition and partition.get("class_id") != group.get("class_id"):
                self.error(
                    f"$.groups[{group_id}]",
                    "group class_id differs from its partition class_id",
                )
            if class_record and group.get("student_count", 0) > class_record.get(
                "student_count", 0
            ):
                self.error(
                    f"$.groups[{group_id}].student_count",
                    "group size exceeds class size",
                )
            if isinstance(group.get("student_count"), int):
                totals[group.get("partition_id")] += group["student_count"]

        for partition_id, partition in self.by_collection["group_partitions"].items():
            class_record = self.by_collection["classes"].get(partition.get("class_id"))
            if not class_record:
                continue
            total = totals[partition_id]
            class_size = class_record.get("student_count")
            if total > class_size:
                self.error(
                    f"$.group_partitions[{partition_id}]",
                    f"group sizes total {total}, exceeding class size {class_size}",
                )
            if partition.get("complete") and total != class_size:
                self.error(
                    f"$.group_partitions[{partition_id}]",
                    f"complete partition totals {total}, expected {class_size}",
                )

    def validate_cohorts(self) -> None:
        for cohort_id, cohort in self.by_collection["cohorts"].items():
            for position, member in enumerate(cohort.get("members", [])):
                self.typed_ref(
                    member,
                    f"$.cohorts[{cohort_id}].members[{position}]",
                    {"class", "group"},
                )

    def validate_teachers(self) -> None:
        subjects = set(self.by_collection["subjects"])
        for teacher_id, teacher in self.by_collection["teachers"].items():
            for subject_id in teacher.get("qualified_subject_ids", []):
                if subject_id not in subjects:
                    self.error(
                        f"$.teachers[{teacher_id}].qualified_subject_ids",
                        f"unknown subject ID {subject_id!r}",
                    )

    def validate_requirements(self) -> None:
        for requirement_id, requirement in self.by_collection[
            "curriculum_requirements"
        ].items():
            location = f"$.curriculum_requirements[{requirement_id}]"
            participant = requirement.get("participant", {})
            self.typed_ref(participant, f"{location}.participant")
            subject = self.ref(
                "subjects", requirement.get("subject_id"), f"{location}.subject_id"
            )
            weekly = requirement.get("weekly_lessons")
            block = requirement.get("block_length")
            if isinstance(weekly, int) and isinstance(block, int) and block > 0:
                if weekly % block:
                    self.error(
                        location,
                        f"weekly_lessons {weekly} is not divisible by block_length {block}",
                    )

            for teacher_id in requirement.get("eligible_teacher_ids", []):
                teacher = self.ref(
                    "teachers", teacher_id, f"{location}.eligible_teacher_ids"
                )
                if (
                    teacher
                    and subject
                    and requirement.get("subject_id")
                    not in teacher.get("qualified_subject_ids", [])
                ):
                    self.error(
                        f"{location}.eligible_teacher_ids",
                        f"teacher {teacher_id!r} is not qualified for subject {requirement.get('subject_id')!r}",
                    )

            allowed_rooms = requirement.get("allowed_classroom_ids", [])
            candidate_rooms: list[dict[str, Any]] = []
            if allowed_rooms:
                for room_id in allowed_rooms:
                    room = self.ref(
                        "classrooms", room_id, f"{location}.allowed_classroom_ids"
                    )
                    if room:
                        candidate_rooms.append(room)
            else:
                candidate_rooms = list(self.by_collection["classrooms"].values())

            required_caps = set(requirement.get("required_room_capabilities", []))
            participant_size = self.participant_size(participant)
            suitable_rooms = [
                room
                for room in candidate_rooms
                if required_caps.issubset(set(room.get("capabilities", [])))
                and room.get("capacity", 0) >= participant_size
            ]
            if not suitable_rooms:
                self.error(
                    location,
                    "no candidate classroom satisfies required capabilities and capacity",
                )

    def validate_availability(self) -> None:
        for position, availability in enumerate(
            self.dataset.get("resource_availability", [])
        ):
            location = f"$.resource_availability[{position}]"
            self.typed_ref(availability.get("resource"), f"{location}.resource")
            unavailable: set[tuple[Any, Any]] = set()
            for list_name in ("unavailable_slots", "preferred_slots"):
                for slot_position, slot in enumerate(availability.get(list_name, [])):
                    self.slot(slot, f"{location}.{list_name}[{slot_position}]")
                    if list_name == "unavailable_slots":
                        unavailable.add((slot.get("day_id"), slot.get("period_id")))
                    elif (slot.get("day_id"), slot.get("period_id")) in unavailable:
                        self.error(
                            f"{location}.{list_name}[{slot_position}]",
                            "slot cannot be both unavailable and preferred",
                        )

    def occurrence_count(self, requirement: dict[str, Any]) -> int:
        weekly = requirement.get("weekly_lessons", 0)
        block = requirement.get("block_length", 1)
        return weekly // block if isinstance(weekly, int) and isinstance(block, int) and block else 0

    def validate_placement(
        self,
        record: dict[str, Any],
        location: str,
    ) -> None:
        requirement = self.ref(
            "curriculum_requirements",
            record.get("requirement_id"),
            f"{location}.requirement_id",
        )
        teacher = self.ref(
            "teachers", record.get("teacher_id"), f"{location}.teacher_id"
        )
        room = self.ref(
            "classrooms", record.get("classroom_id"), f"{location}.classroom_id"
        )
        slot_valid = self.slot(record.get("slot"), f"{location}.slot")
        if not requirement:
            return

        occurrence_index = record.get("occurrence_index")
        if isinstance(occurrence_index, int) and occurrence_index >= self.occurrence_count(
            requirement
        ):
            self.error(
                f"{location}.occurrence_index",
                f"index {occurrence_index} is outside the requirement occurrence count",
            )
        if teacher and record.get("teacher_id") not in requirement.get(
            "eligible_teacher_ids", []
        ):
            self.error(
                f"{location}.teacher_id",
                "teacher is not eligible for this requirement",
            )
        if room:
            allowed_rooms = requirement.get("allowed_classroom_ids", [])
            if allowed_rooms and record.get("classroom_id") not in allowed_rooms:
                self.error(
                    f"{location}.classroom_id",
                    "classroom is not in the requirement's allowed list",
                )
            required_caps = set(requirement.get("required_room_capabilities", []))
            if not required_caps.issubset(set(room.get("capabilities", []))):
                self.error(
                    f"{location}.classroom_id",
                    "classroom lacks a required capability",
                )
            if room.get("capacity", 0) < self.participant_size(
                requirement.get("participant", {})
            ):
                self.error(f"{location}.classroom_id", "classroom capacity is too small")

        if slot_valid:
            period_id = record["slot"]["period_id"]
            for class_id in self.participant_classes(requirement.get("participant", {})):
                class_record = self.by_collection["classes"].get(class_id, {})
                shift = self.by_collection["shifts"].get(class_record.get("shift_id"), {})
                if period_id not in shift.get("period_ids", []):
                    self.error(
                        f"{location}.slot.period_id",
                        f"period is outside the shift for class {class_id!r}",
                    )

    def validate_fixed_lessons(self) -> None:
        for fixed_id, lesson in self.by_collection["fixed_lessons"].items():
            self.validate_placement(lesson, f"$.fixed_lessons[{fixed_id}]")

    def validate_policies(self) -> None:
        policies = self.dataset.get("policies", {})
        known_constraints = set(CONSTRAINT_ID.findall(CATALOG_PATH.read_text(encoding="utf-8")))
        for position, limit in enumerate(policies.get("daily_limits", [])):
            self.typed_ref(
                limit.get("resource"),
                f"$.policies.daily_limits[{position}].resource",
            )
        for position, target in enumerate(policies.get("difficult_load_targets", [])):
            self.typed_ref(
                target.get("participant"),
                f"$.policies.difficult_load_targets[{position}].participant",
                {"class", "group", "cohort"},
            )
        seen: set[str] = set()
        for position, weight in enumerate(policies.get("soft_constraint_weights", [])):
            constraint_id = weight.get("constraint_id")
            location = f"$.policies.soft_constraint_weights[{position}].constraint_id"
            if constraint_id in seen:
                self.error(location, f"duplicate constraint weight for {constraint_id!r}")
            seen.add(constraint_id)
            if constraint_id not in known_constraints:
                self.error(location, f"constraint ID {constraint_id!r} is not in the catalog")

    def validate_timetable_versions(self) -> None:
        version_ids = set(self.by_collection["timetable_versions"])
        for version_id, version in self.by_collection["timetable_versions"].items():
            location = f"$.timetable_versions[{version_id}]"
            parent_id = version.get("parent_version_id")
            if parent_id is not None:
                if parent_id not in version_ids:
                    self.error(
                        f"{location}.parent_version_id",
                        f"unknown timetable version ID {parent_id!r}",
                    )
                if parent_id == version_id:
                    self.error(f"{location}.parent_version_id", "version cannot parent itself")

            assignment_ids: set[str] = set()
            for position, assignment in enumerate(version.get("assignments", [])):
                assignment_id = assignment.get("id")
                assignment_location = f"{location}.assignments[{position}]"
                if assignment_id in assignment_ids:
                    self.error(
                        f"{assignment_location}.id",
                        f"duplicate assignment ID {assignment_id!r} within version",
                    )
                assignment_ids.add(assignment_id)
                self.validate_placement(assignment, assignment_location)

    def validate(self) -> list[str]:
        collections = (
            "subjects",
            "teachers",
            "classrooms",
            "classes",
            "group_partitions",
            "groups",
            "cohorts",
            "curriculum_requirements",
            "fixed_lessons",
            "timetable_versions",
        )
        self.by_collection = {
            collection: self.build_index(collection) for collection in collections
        }

        academic_period = self.dataset.get("academic_period", {})
        for collection in ("days", "periods", "shifts"):
            original = self.dataset.get(collection)
            self.dataset[collection] = academic_period.get(collection, [])
            self.by_collection[collection] = self.build_index(collection)
            if original is None:
                self.dataset.pop(collection, None)
            else:
                self.dataset[collection] = original

        self.validate_calendar()
        self.validate_groups()
        self.validate_cohorts()
        self.validate_teachers()
        self.validate_requirements()
        self.validate_availability()
        self.validate_fixed_lessons()
        self.validate_policies()
        self.validate_timetable_versions()
        return self.errors


def validate_file(path: Path, schema: Any, require_schema: bool) -> list[str]:
    errors: list[str] = []
    try:
        dataset = load_json(path)
    except ValueError as error:
        return [str(error)]

    schema_errors: list[str] = []
    validate_schema(dataset, schema, require_schema, schema_errors)
    errors.extend(schema_errors)
    if isinstance(dataset, dict) and not schema_errors:
        errors.extend(SemanticValidator(dataset).validate())
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=Path, help="JSON datasets to validate")
    parser.add_argument(
        "--require-schema",
        action="store_true",
        help="fail when the jsonschema package is unavailable",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        schema = load_json(SCHEMA_PATH)
    except ValueError as error:
        print(f"Schema error: {error}", file=sys.stderr)
        return 1

    failed = False
    for raw_path in args.datasets:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        errors = validate_file(path.resolve(), schema, args.require_schema)
        display_path = path.resolve()
        try:
            display_path = display_path.relative_to(ROOT)
        except ValueError:
            pass

        if errors:
            failed = True
            print(f"{display_path}: validation failed", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
        else:
            print(f"{display_path}: validation passed")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
