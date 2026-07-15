"""Solver-independent quality evaluation for edited timetables."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from schedule_generator.related_subjects import RELATED_SUBJECT_PAIRS


def evaluate_quality(
    dataset: dict[str, Any], assignments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Evaluate the implemented soft constraints for an existing timetable."""

    days = [item["id"] for item in sorted(dataset["academic_period"]["days"], key=lambda item: item["ordinal"])]
    periods = [item["id"] for item in sorted(dataset["academic_period"]["periods"], key=lambda item: item["ordinal"])]
    requirements = {item["id"]: item for item in dataset["curriculum_requirements"]}
    subjects = {item["id"]: item for item in dataset["subjects"]}
    groups = {item["id"]: item for item in dataset["groups"]}
    cohorts = {item["id"]: item for item in dataset["cohorts"]}
    weights = {item["constraint_id"]: item["weight"] for item in dataset["policies"]["soft_constraint_weights"]}

    def participant_classes(participant: dict[str, str]) -> set[str]:
        if participant["type"] == "class":
            return {participant["id"]}
        if participant["type"] == "group":
            return {groups[participant["id"]]["class_id"]}
        result: set[str] = set()
        for member in cohorts[participant["id"]]["members"]:
            result.update(participant_classes(member))
        return result

    class_slots: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    teacher_slots: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    difficult: defaultdict[tuple[str, str], int] = defaultdict(int)
    subject_starts: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    violations: list[dict[str, Any]] = []

    def add(constraint_id: str, description: str, value: int) -> None:
        weight = weights.get(constraint_id)
        if weight is None or value <= 0:
            return
        violations.append(
            {
                "constraint_id": constraint_id,
                "description": description,
                "value": value,
                "weight": weight,
                "weighted_penalty": value * weight,
            }
        )

    preferred: dict[str, set[tuple[str, str]]] = {}
    for item in dataset["resource_availability"]:
        if item["resource"]["type"] == "teacher":
            preferred[item["resource"]["id"]] = {
                (slot["day_id"], slot["period_id"])
                for slot in item["preferred_slots"]
            }

    for assignment in assignments:
        requirement = requirements.get(assignment["requirement_id"])
        if requirement is None:
            continue
        day_id = assignment["slot"]["day_id"]
        class_ids = participant_classes(requirement["participant"])
        for period_id in assignment["occupied_period_ids"]:
            for class_id in class_ids:
                class_slots[(class_id, day_id)].add(period_id)
            teacher_slots[(assignment["teacher_id"], day_id)].add(period_id)
        if requirement["participant"]["type"] != "group":
            workload = subjects[requirement["subject_id"]]["default_workload"]
            workload *= len(assignment["occupied_period_ids"])
            for class_id in class_ids:
                difficult[(class_id, day_id)] += workload
                subject_starts[(class_id, requirement["subject_id"], day_id)] += 1
        teacher_preferred = preferred.get(assignment["teacher_id"], set())
        start = (day_id, assignment["slot"]["period_id"])
        if teacher_preferred and start not in teacher_preferred:
            add(
                "SC-007",
                f"Teacher {assignment['teacher_id']} non-preferred start",
                1,
            )

    targets = {
        item["participant"]["id"]: item["target"]
        for item in dataset["policies"]["difficult_load_targets"]
        if item["participant"]["type"] == "class"
    }
    for class_id, target in targets.items():
        for day_id in days:
            add(
                "SC-001",
                f"Difficult workload above target for {class_id} on {day_id}",
                max(0, difficult[(class_id, day_id)] - target),
            )

    for class_item in dataset["classes"]:
        class_id = class_item["id"]
        loads = [len(class_slots[(class_id, day_id)]) for day_id in days]
        add("SC-002", f"Daily load spread for {class_id}", max(loads) - min(loads))

    period_index = {period_id: index for index, period_id in enumerate(periods)}

    def add_gaps(
        constraint_id: str,
        resource_type: str,
        resource_ids: list[str],
        occupancy: dict[tuple[str, str], set[str]],
    ) -> None:
        for resource_id in resource_ids:
            for day_id in days:
                indexes = sorted(period_index[item] for item in occupancy[(resource_id, day_id)])
                if len(indexes) < 2:
                    continue
                occupied = set(indexes)
                for index in range(indexes[0] + 1, indexes[-1]):
                    if index not in occupied:
                        add(
                            constraint_id,
                            f"Internal {resource_type} gap for {resource_id} on {day_id} period {index + 1}",
                            1,
                        )

    add_gaps("SC-003", "class", [item["id"] for item in dataset["classes"]], class_slots)
    add_gaps("SC-004", "teacher", [item["id"] for item in dataset["teachers"]], teacher_slots)
    for (class_id, subject_id, day_id), starts in subject_starts.items():
        add(
            "SC-005",
            f"Repeated {subject_id} starts for {class_id} on {day_id}",
            max(0, starts - 1),
        )
    for class_item in dataset["classes"]:
        class_id = class_item["id"]
        for first_subject, second_subject in RELATED_SUBJECT_PAIRS:
            if not any(
                requirement["participant"] == {"type": "class", "id": class_id}
                and requirement["subject_id"] == first_subject
                for requirement in dataset["curriculum_requirements"]
            ) or not any(
                requirement["participant"] == {"type": "class", "id": class_id}
                and requirement["subject_id"] == second_subject
                for requirement in dataset["curriculum_requirements"]
            ):
                continue
            for day_id in days:
                mismatch = int(
                    bool(subject_starts[(class_id, first_subject, day_id)])
                    != bool(subject_starts[(class_id, second_subject, day_id)])
                )
                add(
                    "SC-019",
                    f"Unpaired {first_subject} and {second_subject} for {class_id} on {day_id}",
                    mismatch,
                )

    violations.sort(
        key=lambda item: (
            -item["weighted_penalty"],
            item["constraint_id"],
            item["description"],
        )
    )
    by_constraint: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"raw": 0, "weighted": 0}
    )
    for item in violations:
        values = by_constraint[item["constraint_id"]]
        values["raw"] += item["value"]
        values["weighted"] += item["weighted_penalty"]
    return {
        "total_penalty": sum(item["weighted_penalty"] for item in violations),
        "by_constraint": dict(sorted(by_constraint.items())),
        "violations": violations,
    }
