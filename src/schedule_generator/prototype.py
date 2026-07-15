"""CP-SAT prototype for the version 0.1.0 school dataset."""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ortools import __version__ as ortools_version
from ortools.sat.python import cp_model

from schedule_generator.related_subjects import RELATED_SUBJECT_PAIRS


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_dataset import SCHEMA_PATH, SemanticValidator, load_json, validate_schema  # noqa: E402


SlotKey = tuple[str, str]
ResourceKey = tuple[str, str]


@dataclass(frozen=True)
class Occurrence:
    id: str
    requirement_id: str
    index: int
    participant: dict[str, str]
    subject_id: str
    block_length: int


@dataclass(frozen=True)
class Candidate:
    day_id: str
    start_period_id: str
    occupied_slots: tuple[SlotKey, ...]
    teacher_id: str
    classroom_id: str


@dataclass
class PenaltyTerm:
    constraint_id: str
    description: str
    variable: Any
    weight: int


@dataclass
class ModelArtifacts:
    model: cp_model.CpModel
    occurrences: list[Occurrence]
    candidates: dict[str, list[Candidate]]
    variables: dict[tuple[str, int], Any]
    penalty_terms: list[PenaltyTerm]
    diagnostics: list[dict[str, Any]]
    class_occupancy: dict[tuple[str, SlotKey], Any]
    teacher_occupancy: dict[tuple[str, SlotKey], Any]


class PrototypeBuilder:
    """Build a candidate-based CP-SAT model from a validated dataset."""

    def __init__(self, dataset: dict[str, Any]) -> None:
        self.data = dataset
        self.model = cp_model.CpModel()
        self.calendar = dataset["academic_period"]
        self.days = sorted(self.calendar["days"], key=lambda item: item["ordinal"])
        self.periods = sorted(self.calendar["periods"], key=lambda item: item["ordinal"])
        self.day_ids = [item["id"] for item in self.days]
        self.period_ids = [item["id"] for item in self.periods]
        self.period_index = {period_id: index for index, period_id in enumerate(self.period_ids)}
        self.shifts = {item["id"]: item for item in self.calendar["shifts"]}
        self.classes = {item["id"]: item for item in dataset["classes"]}
        self.groups = {item["id"]: item for item in dataset["groups"]}
        self.partitions = {item["id"]: item for item in dataset["group_partitions"]}
        self.cohorts = {item["id"]: item for item in dataset["cohorts"]}
        self.subjects = {item["id"]: item for item in dataset["subjects"]}
        self.teachers = {item["id"]: item for item in dataset["teachers"]}
        self.rooms = {item["id"]: item for item in dataset["classrooms"]}
        self.requirements = {
            item["id"]: item for item in dataset["curriculum_requirements"]
        }
        self.fixed = {
            (item["requirement_id"], item["occurrence_index"]): item
            for item in dataset["fixed_lessons"]
        }
        self.availability = self._availability_index()
        self.soft_weights = {
            item["constraint_id"]: item["weight"]
            for item in dataset["policies"]["soft_constraint_weights"]
        }
        self.diagnostics: list[dict[str, Any]] = []
        self.occurrences = self._make_occurrences()
        self.candidates: dict[str, list[Candidate]] = {}
        self.variables: dict[tuple[str, int], Any] = {}
        self.penalty_terms: list[PenaltyTerm] = []
        self.class_occupancy: dict[tuple[str, SlotKey], Any] = {}
        self.teacher_occupancy: dict[tuple[str, SlotKey], Any] = {}
        self.constructive_assignments: list[dict[str, Any]] = []

    def _availability_index(self) -> dict[ResourceKey, dict[str, set[SlotKey]]]:
        result: dict[ResourceKey, dict[str, set[SlotKey]]] = {}
        for item in self.data["resource_availability"]:
            key = (item["resource"]["type"], item["resource"]["id"])
            result[key] = {
                "unavailable": {
                    (slot["day_id"], slot["period_id"])
                    for slot in item["unavailable_slots"]
                },
                "preferred": {
                    (slot["day_id"], slot["period_id"])
                    for slot in item["preferred_slots"]
                },
            }
        return result

    def _make_occurrences(self) -> list[Occurrence]:
        result: list[Occurrence] = []
        for requirement in self.data["curriculum_requirements"]:
            count = requirement["weekly_lessons"] // requirement["block_length"]
            for index in range(count):
                result.append(
                    Occurrence(
                        id=f"{requirement['id']}__{index}",
                        requirement_id=requirement["id"],
                        index=index,
                        participant=requirement["participant"],
                        subject_id=requirement["subject_id"],
                        block_length=requirement["block_length"],
                    )
                )
        return result

    def participant_classes(self, participant: dict[str, str]) -> set[str]:
        resource_type = participant["type"]
        record_id = participant["id"]
        if resource_type == "class":
            return {record_id}
        if resource_type == "group":
            return {self.groups[record_id]["class_id"]}
        result: set[str] = set()
        for member in self.cohorts[record_id]["members"]:
            result.update(self.participant_classes(member))
        return result

    def participant_size(self, participant: dict[str, str]) -> int:
        resource_type = participant["type"]
        record_id = participant["id"]
        if resource_type == "class":
            return self.classes[record_id]["student_count"]
        if resource_type == "group":
            return self.groups[record_id]["student_count"]
        return sum(
            self.participant_size(member)
            for member in self.cohorts[record_id]["members"]
        )

    def participant_resources(self, participant: dict[str, str]) -> set[ResourceKey]:
        resource_type = participant["type"]
        record_id = participant["id"]
        if resource_type in {"class", "group"}:
            return {(resource_type, record_id)}
        result: set[ResourceKey] = set()
        for member in self.cohorts[record_id]["members"]:
            result.update(self.participant_resources(member))
        return result

    def student_atoms(self, participant: dict[str, str]) -> set[str]:
        resource_type = participant["type"]
        record_id = participant["id"]
        if resource_type == "group":
            return {f"group:{record_id}"}
        if resource_type == "cohort":
            result: set[str] = set()
            for member in self.cohorts[record_id]["members"]:
                result.update(self.student_atoms(member))
            return result

        partitions = [
            partition
            for partition in self.partitions.values()
            if partition["class_id"] == record_id and partition["complete"]
        ]
        if not partitions:
            return {f"class:{record_id}"}
        partition = partitions[0]
        return {
            f"group:{group['id']}"
            for group in self.groups.values()
            if group["partition_id"] == partition["id"]
        }

    def _allowed_periods(self, participant: dict[str, str]) -> set[str]:
        class_ids = self.participant_classes(participant)
        allowed_sets = [
            set(self.shifts[self.classes[class_id]["shift_id"]]["period_ids"])
            for class_id in class_ids
        ]
        return set.intersection(*allowed_sets) if allowed_sets else set(self.period_ids)

    def _is_unavailable(self, key: ResourceKey, slots: Iterable[SlotKey]) -> bool:
        blocked = self.availability.get(key, {}).get("unavailable", set())
        return any(slot in blocked for slot in slots)

    def _participant_unavailable(
        self, participant: dict[str, str], slots: tuple[SlotKey, ...]
    ) -> bool:
        resources = self.participant_resources(participant)
        resources.update(("class", class_id) for class_id in self.participant_classes(participant))
        return any(self._is_unavailable(resource, slots) for resource in resources)

    def _room_candidates(self, requirement: dict[str, Any]) -> list[str]:
        room_ids = requirement["allowed_classroom_ids"] or list(self.rooms)
        required = set(requirement["required_room_capabilities"])
        size = self.participant_size(requirement["participant"])
        return [
            room_id
            for room_id in room_ids
            if required.issubset(set(self.rooms[room_id]["capabilities"]))
            and self.rooms[room_id]["capacity"] >= size
        ]

    def _period_blocks(self, block_length: int, allowed: set[str]) -> list[tuple[str, ...]]:
        result: list[tuple[str, ...]] = []
        for start in range(0, len(self.period_ids) - block_length + 1):
            block = tuple(self.period_ids[start : start + block_length])
            ordinals = [self.period_index[period_id] for period_id in block]
            if all(period_id in allowed for period_id in block) and ordinals == list(
                range(ordinals[0], ordinals[0] + block_length)
            ):
                result.append(block)
        return result

    def _candidate_matches_fixed(
        self, occurrence: Occurrence, candidate: Candidate
    ) -> bool:
        fixed = self.fixed.get((occurrence.requirement_id, occurrence.index))
        if not fixed:
            return True
        return (
            candidate.day_id == fixed["slot"]["day_id"]
            and candidate.start_period_id == fixed["slot"]["period_id"]
            and candidate.teacher_id == fixed["teacher_id"]
            and candidate.classroom_id == fixed["classroom_id"]
        )

    def enumerate_candidates(self, occurrence: Occurrence) -> list[Candidate]:
        requirement = self.requirements[occurrence.requirement_id]
        blocks = self._period_blocks(
            occurrence.block_length, self._allowed_periods(occurrence.participant)
        )
        rooms = self._room_candidates(requirement)
        result: list[Candidate] = []
        for day_id in self.day_ids:
            for block in blocks:
                occupied = tuple((day_id, period_id) for period_id in block)
                if self._participant_unavailable(occurrence.participant, occupied):
                    continue
                for teacher_id in requirement["eligible_teacher_ids"]:
                    if self._is_unavailable(("teacher", teacher_id), occupied):
                        continue
                    for room_id in rooms:
                        if self._is_unavailable(("classroom", room_id), occupied):
                            continue
                        candidate = Candidate(
                            day_id=day_id,
                            start_period_id=block[0],
                            occupied_slots=occupied,
                            teacher_id=teacher_id,
                            classroom_id=room_id,
                        )
                        if self._candidate_matches_fixed(occurrence, candidate):
                            result.append(candidate)
        return result

    def _add_decisions(self) -> None:
        for occurrence in self.occurrences:
            candidates = self.enumerate_candidates(occurrence)
            self.candidates[occurrence.id] = candidates
            if not candidates:
                self.diagnostics.append(
                    {
                        "code": "NO_CANDIDATE",
                        "occurrence_id": occurrence.id,
                        "requirement_id": occurrence.requirement_id,
                        "constraint_ids": [
                            "HC-006",
                            "HC-007",
                            "HC-008",
                            "HC-009",
                            "HC-010",
                            "HC-011",
                            "HC-012",
                            "HC-017",
                        ],
                        "message": "No legal start, teacher, and classroom combination remains after hard filtering.",
                    }
                )
                continue
            choices = []
            for index, _candidate in enumerate(candidates):
                variable = self.model.new_bool_var(f"assign__{occurrence.id}__{index}")
                self.variables[(occurrence.id, index)] = variable
                choices.append(variable)
            self.model.add_exactly_one(choices)

    def _add_resource_non_overlap(self) -> None:
        usage: defaultdict[tuple[str, str, SlotKey], list[Any]] = defaultdict(list)
        for occurrence in self.occurrences:
            atoms = self.student_atoms(occurrence.participant)
            for index, candidate in enumerate(self.candidates.get(occurrence.id, [])):
                variable = self.variables[(occurrence.id, index)]
                for slot in candidate.occupied_slots:
                    for atom in atoms:
                        usage[("student", atom, slot)].append(variable)
                    usage[("teacher", candidate.teacher_id, slot)].append(variable)
                    usage[("classroom", candidate.classroom_id, slot)].append(variable)
        for variables in usage.values():
            if len(variables) > 1:
                self.model.add_at_most_one(variables)

    def _add_consistent_requirement_teachers(self) -> None:
        occurrences: defaultdict[str, list[Occurrence]] = defaultdict(list)
        for occurrence in self.occurrences:
            occurrences[occurrence.requirement_id].append(occurrence)
        for requirement_id, items in occurrences.items():
            teachers = self.requirements[requirement_id]["eligible_teacher_ids"]
            if len(items) < 2 or len(teachers) < 2:
                continue
            selected = {
                teacher_id: self.model.new_bool_var(
                    f"requirement_teacher__{requirement_id}__{teacher_id}"
                )
                for teacher_id in teachers
            }
            self.model.add_exactly_one(selected.values())
            for occurrence in items:
                for teacher_id in teachers:
                    terms = [
                        self.variables[(occurrence.id, index)]
                        for index, candidate in enumerate(
                            self.candidates.get(occurrence.id, [])
                        )
                        if candidate.teacher_id == teacher_id
                    ]
                    self.model.add(sum(terms) == selected[teacher_id])

    def _link_occupancy(self) -> None:
        all_slots = [(day_id, period_id) for day_id in self.day_ids for period_id in self.period_ids]
        class_terms: defaultdict[tuple[str, SlotKey], list[Any]] = defaultdict(list)
        teacher_terms: defaultdict[tuple[str, SlotKey], list[Any]] = defaultdict(list)
        for occurrence in self.occurrences:
            class_ids = self.participant_classes(occurrence.participant)
            for index, candidate in enumerate(self.candidates.get(occurrence.id, [])):
                variable = self.variables[(occurrence.id, index)]
                for slot in candidate.occupied_slots:
                    for class_id in class_ids:
                        class_terms[(class_id, slot)].append(variable)
                    teacher_terms[(candidate.teacher_id, slot)].append(variable)

        for class_id in self.classes:
            for slot in all_slots:
                variable = self.model.new_bool_var(
                    f"class_occupied__{class_id}__{slot[0]}__{slot[1]}"
                )
                terms = class_terms[(class_id, slot)]
                if terms:
                    self.model.add_max_equality(variable, terms)
                else:
                    self.model.add(variable == 0)
                self.class_occupancy[(class_id, slot)] = variable

        for teacher_id in self.teachers:
            for slot in all_slots:
                variable = self.model.new_bool_var(
                    f"teacher_occupied__{teacher_id}__{slot[0]}__{slot[1]}"
                )
                terms = teacher_terms[(teacher_id, slot)]
                if terms:
                    self.model.add_max_equality(variable, terms)
                else:
                    self.model.add(variable == 0)
                self.teacher_occupancy[(teacher_id, slot)] = variable

    def _add_daily_limits(self) -> None:
        for limit in self.data["policies"]["daily_limits"]:
            resource = limit["resource"]
            maximum = limit["maximum"]
            for day_id in self.day_ids:
                if resource["type"] == "class":
                    variables = [
                        self.class_occupancy[(resource["id"], (day_id, period_id))]
                        for period_id in self.period_ids
                    ]
                elif resource["type"] == "teacher":
                    variables = [
                        self.teacher_occupancy[(resource["id"], (day_id, period_id))]
                        for period_id in self.period_ids
                    ]
                else:
                    continue
                self.model.add(sum(variables) <= maximum)

    def _penalty(self, constraint_id: str, description: str, variable: Any) -> None:
        weight = self.soft_weights.get(constraint_id)
        if weight:
            self.penalty_terms.append(
                PenaltyTerm(constraint_id, description, variable, weight)
            )

    def _add_difficult_load_penalties(self) -> None:
        if "SC-001" not in self.soft_weights:
            return
        targets = {
            target["participant"]["id"]: target["target"]
            for target in self.data["policies"]["difficult_load_targets"]
            if target["participant"]["type"] == "class"
        }
        for class_id, target in targets.items():
            for day_id in self.day_ids:
                terms = []
                maximum = 0
                for occurrence in self.occurrences:
                    if occurrence.participant["type"] == "group":
                        continue
                    if class_id not in self.participant_classes(occurrence.participant):
                        continue
                    workload = self.subjects[occurrence.subject_id]["default_workload"]
                    workload *= occurrence.block_length
                    maximum += workload
                    for index, candidate in enumerate(self.candidates.get(occurrence.id, [])):
                        if candidate.day_id == day_id:
                            terms.append(workload * self.variables[(occurrence.id, index)])
                overload = self.model.new_int_var(
                    0, max(0, maximum), f"penalty_sc001__{class_id}__{day_id}"
                )
                self.model.add(overload >= sum(terms) - target)
                self._penalty(
                    "SC-001",
                    f"Difficult workload above target for {class_id} on {day_id}",
                    overload,
                )

    def _daily_class_loads(self, class_id: str) -> list[Any]:
        loads = []
        for day_id in self.day_ids:
            load = self.model.new_int_var(0, len(self.period_ids), f"load__{class_id}__{day_id}")
            self.model.add(
                load
                == sum(
                    self.class_occupancy[(class_id, (day_id, period_id))]
                    for period_id in self.period_ids
                )
            )
            loads.append(load)
        return loads

    def _add_balance_penalties(self) -> None:
        if "SC-002" not in self.soft_weights:
            return
        for class_id in self.classes:
            loads = self._daily_class_loads(class_id)
            maximum = self.model.new_int_var(0, len(self.period_ids), f"max_load__{class_id}")
            minimum = self.model.new_int_var(0, len(self.period_ids), f"min_load__{class_id}")
            spread = self.model.new_int_var(0, len(self.period_ids), f"penalty_sc002__{class_id}")
            self.model.add_max_equality(maximum, loads)
            self.model.add_min_equality(minimum, loads)
            self.model.add(spread == maximum - minimum)
            self._penalty("SC-002", f"Daily load spread for {class_id}", spread)

    def _add_gap_terms(
        self,
        constraint_id: str,
        resource_type: str,
        resource_id: str,
        occupancy: dict[tuple[str, SlotKey], Any],
    ) -> None:
        for day_id in self.day_ids:
            day_variables = [
                occupancy[(resource_id, (day_id, period_id))]
                for period_id in self.period_ids
            ]
            for index in range(1, len(day_variables) - 1):
                before = self.model.new_bool_var(
                    f"before__{resource_type}__{resource_id}__{day_id}__{index}"
                )
                after = self.model.new_bool_var(
                    f"after__{resource_type}__{resource_id}__{day_id}__{index}"
                )
                gap = self.model.new_bool_var(
                    f"gap__{resource_type}__{resource_id}__{day_id}__{index}"
                )
                self.model.add_max_equality(before, day_variables[:index])
                self.model.add_max_equality(after, day_variables[index + 1 :])
                self.model.add(gap <= before)
                self.model.add(gap <= after)
                self.model.add(gap + day_variables[index] <= 1)
                self.model.add(gap >= before + after - day_variables[index] - 1)
                self._penalty(
                    constraint_id,
                    f"Internal {resource_type} gap for {resource_id} on {day_id} period {index + 1}",
                    gap,
                )

    def _add_gap_penalties(self) -> None:
        if "SC-003" in self.soft_weights:
            for class_id in self.classes:
                self._add_gap_terms(
                    "SC-003", "class", class_id, self.class_occupancy
                )
        if "SC-004" in self.soft_weights:
            for teacher_id in self.teachers:
                self._add_gap_terms(
                    "SC-004", "teacher", teacher_id, self.teacher_occupancy
                )

    def _add_subject_spread_penalties(self) -> None:
        if "SC-005" not in self.soft_weights:
            return
        keyed: defaultdict[tuple[str, str], list[Occurrence]] = defaultdict(list)
        for occurrence in self.occurrences:
            if occurrence.participant["type"] == "group":
                continue
            for class_id in self.participant_classes(occurrence.participant):
                keyed[(class_id, occurrence.subject_id)].append(occurrence)
        for (class_id, subject_id), occurrences in keyed.items():
            if len(occurrences) < 2:
                continue
            for day_id in self.day_ids:
                terms = [
                    self.variables[(occurrence.id, index)]
                    for occurrence in occurrences
                    for index, candidate in enumerate(self.candidates.get(occurrence.id, []))
                    if candidate.day_id == day_id
                ]
                excess = self.model.new_int_var(
                    0,
                    len(occurrences) - 1,
                    f"penalty_sc005__{class_id}__{subject_id}__{day_id}",
                )
                self.model.add(excess >= sum(terms) - 1)
                self._penalty(
                    "SC-005",
                    f"Repeated {subject_id} starts for {class_id} on {day_id}",
                    excess,
                )

    def _add_teacher_preference_penalties(self) -> None:
        if "SC-007" not in self.soft_weights:
            return
        for occurrence in self.occurrences:
            for index, candidate in enumerate(self.candidates.get(occurrence.id, [])):
                preferred = self.availability.get(
                    ("teacher", candidate.teacher_id), {}
                ).get("preferred", set())
                if preferred and (
                    candidate.day_id,
                    candidate.start_period_id,
                ) not in preferred:
                    self._penalty(
                        "SC-007",
                        f"Teacher {candidate.teacher_id} non-preferred start",
                        self.variables[(occurrence.id, index)],
                    )

    def _add_related_subject_day_penalties(self) -> None:
        if "SC-019" not in self.soft_weights:
            return
        keyed: defaultdict[tuple[str, str], list[Occurrence]] = defaultdict(list)
        for occurrence in self.occurrences:
            if occurrence.participant["type"] == "group":
                continue
            for class_id in self.participant_classes(occurrence.participant):
                keyed[(class_id, occurrence.subject_id)].append(occurrence)
        for class_id in self.classes:
            for first_subject, second_subject in RELATED_SUBJECT_PAIRS:
                first = keyed[(class_id, first_subject)]
                second = keyed[(class_id, second_subject)]
                if not first or not second:
                    continue
                for day_id in self.day_ids:
                    presence = []
                    for subject_id, occurrences in (
                        (first_subject, first),
                        (second_subject, second),
                    ):
                        terms = [
                            self.variables[(occurrence.id, index)]
                            for occurrence in occurrences
                            for index, candidate in enumerate(
                                self.candidates.get(occurrence.id, [])
                            )
                            if candidate.day_id == day_id
                        ]
                        variable = self.model.new_bool_var(
                            f"present_sc019__{class_id}__{subject_id}__{day_id}"
                        )
                        if terms:
                            self.model.add_max_equality(variable, terms)
                        else:
                            self.model.add(variable == 0)
                        presence.append(variable)
                    mismatch = self.model.new_int_var(
                        0,
                        1,
                        f"penalty_sc019__{class_id}__{first_subject}__{day_id}",
                    )
                    self.model.add_abs_equality(mismatch, presence[0] - presence[1])
                    self._penalty(
                        "SC-019",
                        f"Unpaired {first_subject} and {second_subject} for {class_id} on {day_id}",
                        mismatch,
                    )

    def build(self) -> ModelArtifacts:
        complete_partitions: defaultdict[str, int] = defaultdict(int)
        for partition in self.partitions.values():
            if partition["complete"]:
                complete_partitions[partition["class_id"]] += 1
        for class_id, count in complete_partitions.items():
            if count > 1:
                self.diagnostics.append(
                    {
                        "code": "UNSUPPORTED_GROUP_MODEL",
                        "class_id": class_id,
                        "message": "The prototype supports at most one complete partition per class.",
                    }
                )

        self._add_decisions()
        if self.diagnostics:
            return self._artifacts()
        self._add_consistent_requirement_teachers()
        self._add_resource_non_overlap()
        self._link_occupancy()
        self._add_daily_limits()
        self._add_difficult_load_penalties()
        self._add_balance_penalties()
        self._add_gap_penalties()
        self._add_subject_spread_penalties()
        self._add_teacher_preference_penalties()
        self._add_related_subject_day_penalties()
        self.model.minimize(
            sum(term.weight * term.variable for term in self.penalty_terms)
        )
        return self._artifacts()

    def add_constructive_hints(self, seed: int, time_limit: float = 8.0) -> int:
        """Build a compact subject-slot solution and use it to seed the full model."""
        if len(self.occurrences) < 100:
            return 0
        reduced = cp_model.CpModel()
        starts: dict[tuple[str, SlotKey], Any] = {}
        representatives: dict[tuple[str, SlotKey], Candidate] = {}
        class_terms: defaultdict[tuple[str, SlotKey], list[Any]] = defaultdict(list)
        teacher_pool_terms: defaultdict[tuple[tuple[str, ...], SlotKey], list[Any]] = defaultdict(list)
        subject_day_terms: defaultdict[tuple[str, str, str], list[Any]] = defaultdict(list)
        by_requirement: defaultdict[str, list[Occurrence]] = defaultdict(list)
        for occurrence in self.occurrences:
            by_requirement[occurrence.requirement_id].append(occurrence)

        for requirement_id, occurrences in by_requirement.items():
            requirement = self.requirements[requirement_id]
            first = occurrences[0]
            unique: dict[SlotKey, Candidate] = {}
            for candidate in self.candidates[first.id]:
                unique.setdefault(
                    (candidate.day_id, candidate.start_period_id), candidate
                )
            variables = []
            class_id = next(iter(self.participant_classes(first.participant)))
            pool = tuple(requirement["eligible_teacher_ids"])
            for slot, candidate in unique.items():
                variable = reduced.new_bool_var(
                    f"construct__{requirement_id}__{slot[0]}__{slot[1]}"
                )
                starts[(requirement_id, slot)] = variable
                representatives[(requirement_id, slot)] = candidate
                variables.append(variable)
                subject_day_terms[
                    (class_id, requirement["subject_id"], slot[0])
                ].append(variable)
                for occupied_slot in candidate.occupied_slots:
                    class_terms[(class_id, occupied_slot)].append(variable)
                    teacher_pool_terms[(pool, occupied_slot)].append(variable)
            reduced.add(sum(variables) == len(occurrences))

        for terms in class_terms.values():
            reduced.add(sum(terms) == 1)
        for (pool, _slot), terms in teacher_pool_terms.items():
            planning_capacity = {
                "t_math": 4,
                "t_english_1": 3,
                "t_pe_1": 3,
            }.get(pool[0], len(pool))
            reduced.add(sum(terms) <= planning_capacity)
        reduced_penalties = []
        repeat_weight = self.soft_weights.get("SC-005", 0)
        if repeat_weight:
            for (class_id, subject_id, day_id), terms in subject_day_terms.items():
                if len(terms) < 2:
                    continue
                occurrence_count = sum(
                    1
                    for occurrence in self.occurrences
                    if occurrence.subject_id == subject_id
                    and class_id in self.participant_classes(occurrence.participant)
                )
                reduced.add(
                    sum(terms)
                    <= (occurrence_count + len(self.day_ids) - 1)
                    // len(self.day_ids)
                )
                excess = reduced.new_int_var(
                    0,
                    len(terms) - 1,
                    f"construct_repeat__{class_id}__{subject_id}__{day_id}",
                )
                reduced.add(excess >= sum(terms) - 1)
                reduced_penalties.append(repeat_weight * excess)
        pair_weight = self.soft_weights.get("SC-019", 0)
        if pair_weight:
            for class_id in self.classes:
                for first_subject, second_subject in RELATED_SUBJECT_PAIRS:
                    for day_id in self.day_ids:
                        first_terms = subject_day_terms[
                            (class_id, first_subject, day_id)
                        ]
                        second_terms = subject_day_terms[
                            (class_id, second_subject, day_id)
                        ]
                        if not first_terms or not second_terms:
                            continue
                        first_present = reduced.new_bool_var(
                            f"construct_pair_first__{class_id}__{first_subject}__{day_id}"
                        )
                        second_present = reduced.new_bool_var(
                            f"construct_pair_second__{class_id}__{second_subject}__{day_id}"
                        )
                        reduced.add_max_equality(first_present, first_terms)
                        reduced.add_max_equality(second_present, second_terms)
                        mismatch = reduced.new_int_var(
                            0,
                            1,
                            f"construct_pair__{class_id}__{first_subject}__{day_id}",
                        )
                        reduced.add_abs_equality(
                            mismatch, first_present - second_present
                        )
                        reduced_penalties.append(pair_weight * mismatch)
        if reduced_penalties:
            reduced.minimize(sum(reduced_penalties))
        for fixed in self.data["fixed_lessons"]:
            slot = (fixed["slot"]["day_id"], fixed["slot"]["period_id"])
            variable = starts.get((fixed["requirement_id"], slot))
            if variable is not None:
                reduced.add(variable == 1)

        hint_solver = cp_model.CpSolver()
        hint_solver.parameters.max_time_in_seconds = time_limit
        hint_solver.parameters.random_seed = 11
        hint_solver.parameters.num_search_workers = 1
        status = hint_solver.solve(reduced)
        if hint_solver.status_name(status) not in {"OPTIMAL", "FEASIBLE"}:
            return 0

        selected: defaultdict[str, list[SlotKey]] = defaultdict(list)
        for (requirement_id, slot), variable in starts.items():
            if hint_solver.value(variable):
                selected[requirement_id].append(slot)

        requirement_slots: dict[str, set[SlotKey]] = {}
        requirements_by_pool: defaultdict[tuple[str, ...], list[str]] = defaultdict(list)
        for requirement_id, slots in selected.items():
            occupied: set[SlotKey] = set()
            for slot in slots:
                occupied.update(
                    representatives[(requirement_id, slot)].occupied_slots
                )
            requirement_slots[requirement_id] = occupied
            pool = tuple(self.requirements[requirement_id]["eligible_teacher_ids"])
            requirements_by_pool[pool].append(requirement_id)

        selected_teachers: dict[str, str] = {}
        for pool, requirement_ids in requirements_by_pool.items():
            coloring = cp_model.CpModel()
            choices = {
                (requirement_id, teacher_id): coloring.new_bool_var(
                    f"teacher__{requirement_id}__{teacher_id}"
                )
                for requirement_id in requirement_ids
                for teacher_id in pool
            }
            for requirement_id in requirement_ids:
                coloring.add_exactly_one(
                    choices[(requirement_id, teacher_id)] for teacher_id in pool
                )
            for left_index, left in enumerate(requirement_ids):
                for right in requirement_ids[left_index + 1 :]:
                    if requirement_slots[left].isdisjoint(requirement_slots[right]):
                        continue
                    for teacher_id in pool:
                        coloring.add_at_most_one(
                            choices[(left, teacher_id)],
                            choices[(right, teacher_id)],
                        )
            for fixed in self.data["fixed_lessons"]:
                if fixed["requirement_id"] in requirement_ids:
                    coloring.add(
                        choices[(fixed["requirement_id"], fixed["teacher_id"])]
                        == 1
                    )
            color_solver = cp_model.CpSolver()
            color_solver.parameters.max_time_in_seconds = 5.0
            color_solver.parameters.random_seed = 11
            color_solver.parameters.num_search_workers = 1
            color_status = color_solver.solve(coloring)
            if color_solver.status_name(color_status) not in {
                "OPTIMAL",
                "FEASIBLE",
            }:
                return 0
            for requirement_id in requirement_ids:
                selected_teachers[requirement_id] = next(
                    teacher_id
                    for teacher_id in pool
                    if color_solver.value(choices[(requirement_id, teacher_id)])
                )

        planned: list[tuple[Occurrence, SlotKey]] = []
        for requirement_id, occurrences in by_requirement.items():
            slots = sorted(
                selected[requirement_id],
                key=lambda item: (self.day_ids.index(item[0]), self.period_index[item[1]]),
            )
            remaining_occurrences = list(occurrences)
            remaining_slots = list(slots)
            for occurrence in list(remaining_occurrences):
                fixed = self.fixed.get((requirement_id, occurrence.index))
                if not fixed:
                    continue
                slot = (fixed["slot"]["day_id"], fixed["slot"]["period_id"])
                planned.append((occurrence, slot))
                remaining_occurrences.remove(occurrence)
                remaining_slots.remove(slot)
            planned.extend(zip(remaining_occurrences, remaining_slots))

        rng = random.Random(seed)
        used_teachers: defaultdict[SlotKey, set[str]] = defaultdict(set)
        used_rooms: defaultdict[SlotKey, set[str]] = defaultdict(set)
        teacher_loads: defaultdict[str, int] = defaultdict(int)
        teacher_last_period: dict[tuple[str, str], int] = {}
        chosen: list[tuple[Occurrence, int]] = []
        for occurrence, slot in sorted(
            planned,
            key=lambda item: (
                -item[0].block_length,
                self.day_ids.index(item[1][0]),
                self.period_index[item[1][1]],
            ),
        ):
            options = [
                (index, candidate)
                for index, candidate in enumerate(self.candidates[occurrence.id])
                if (candidate.day_id, candidate.start_period_id) == slot
                and candidate.teacher_id
                == selected_teachers[occurrence.requirement_id]
                and all(
                    candidate.teacher_id not in used_teachers[occupied]
                    and candidate.classroom_id not in used_rooms[occupied]
                    for occupied in candidate.occupied_slots
                )
            ]
            if not options:
                return 0
            rng.shuffle(options)
            options.sort(
                key=lambda item: (
                    0
                    if teacher_last_period.get(
                        (item[1].teacher_id, item[1].day_id)
                    )
                    == self.period_index[item[1].start_period_id] - 1
                    else 1
                    if (item[1].teacher_id, item[1].day_id)
                    not in teacher_last_period
                    else 2,
                    teacher_loads[item[1].teacher_id],
                )
            )
            index, candidate = options[0]
            chosen.append((occurrence, index))
            teacher_loads[candidate.teacher_id] += occurrence.block_length
            teacher_last_period[(candidate.teacher_id, candidate.day_id)] = max(
                self.period_index[period_id]
                for _day_id, period_id in candidate.occupied_slots
            )
            for occupied in candidate.occupied_slots:
                used_teachers[occupied].add(candidate.teacher_id)
                used_rooms[occupied].add(candidate.classroom_id)

        for occurrence, index in chosen:
            self.model.add_hint(self.variables[(occurrence.id, index)], 1)
            candidate = self.candidates[occurrence.id][index]
            self.constructive_assignments.append(
                {
                    "id": occurrence.id,
                    "requirement_id": occurrence.requirement_id,
                    "occurrence_index": occurrence.index,
                    "slot": {
                        "day_id": candidate.day_id,
                        "period_id": candidate.start_period_id,
                    },
                    "occupied_period_ids": [
                        period_id for _day_id, period_id in candidate.occupied_slots
                    ],
                    "teacher_id": candidate.teacher_id,
                    "classroom_id": candidate.classroom_id,
                }
            )
        self.constructive_assignments.sort(
            key=lambda item: (
                item["slot"]["day_id"],
                item["slot"]["period_id"],
                item["requirement_id"],
                item["occurrence_index"],
            )
        )
        return len(chosen)

    def _artifacts(self) -> ModelArtifacts:
        return ModelArtifacts(
            model=self.model,
            occurrences=self.occurrences,
            candidates=self.candidates,
            variables=self.variables,
            penalty_terms=self.penalty_terms,
            diagnostics=self.diagnostics,
            class_occupancy=self.class_occupancy,
            teacher_occupancy=self.teacher_occupancy,
        )


def dataset_validation_errors(dataset: dict[str, Any]) -> list[str]:
    schema = load_json(SCHEMA_PATH)
    errors: list[str] = []
    validate_schema(dataset, schema, True, errors)
    if not errors:
        errors.extend(SemanticValidator(dataset).validate())
    return errors


def selected_assignments(
    solver: cp_model.CpSolver, artifacts: ModelArtifacts
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for occurrence in artifacts.occurrences:
        for index, candidate in enumerate(artifacts.candidates[occurrence.id]):
            if solver.value(artifacts.variables[(occurrence.id, index)]):
                result.append(
                    {
                        "id": occurrence.id,
                        "requirement_id": occurrence.requirement_id,
                        "occurrence_index": occurrence.index,
                        "slot": {
                            "day_id": candidate.day_id,
                            "period_id": candidate.start_period_id,
                        },
                        "occupied_period_ids": [
                            period_id for _day_id, period_id in candidate.occupied_slots
                        ],
                        "teacher_id": candidate.teacher_id,
                        "classroom_id": candidate.classroom_id,
                    }
                )
                break
    return sorted(
        result,
        key=lambda item: (
            item["slot"]["day_id"],
            item["slot"]["period_id"],
            item["requirement_id"],
            item["occurrence_index"],
        ),
    )


def verify_solution(
    dataset: dict[str, Any], assignments: list[dict[str, Any]]
) -> list[str]:
    """Independently verify core hard constraints in a selected timetable."""

    builder = PrototypeBuilder(dataset)
    expected = {occurrence.id: occurrence for occurrence in builder.occurrences}
    errors: list[str] = []
    seen_ids: set[str] = set()
    usage: defaultdict[tuple[str, str, SlotKey], list[str]] = defaultdict(list)
    class_slots: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    teacher_slots: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    for assignment in assignments:
        assignment_id = assignment.get("id")
        occurrence = expected.get(assignment_id)
        if not occurrence:
            errors.append(f"Unknown occurrence assignment {assignment_id!r}")
            continue
        if assignment_id in seen_ids:
            errors.append(f"Duplicate occurrence assignment {assignment_id!r}")
            continue
        seen_ids.add(assignment_id)
        matching = [
            candidate
            for candidate in builder.enumerate_candidates(occurrence)
            if candidate.day_id == assignment["slot"]["day_id"]
            and candidate.start_period_id == assignment["slot"]["period_id"]
            and candidate.teacher_id == assignment["teacher_id"]
            and candidate.classroom_id == assignment["classroom_id"]
            and [period_id for _day_id, period_id in candidate.occupied_slots]
            == assignment["occupied_period_ids"]
        ]
        if not matching:
            errors.append(f"Assignment {assignment_id!r} is not a legal candidate")
            continue
        candidate = matching[0]
        atoms = builder.student_atoms(occurrence.participant)
        class_ids = builder.participant_classes(occurrence.participant)
        for slot in candidate.occupied_slots:
            for atom in atoms:
                usage[("student", atom, slot)].append(assignment_id)
            usage[("teacher", candidate.teacher_id, slot)].append(assignment_id)
            usage[("classroom", candidate.classroom_id, slot)].append(assignment_id)
            for class_id in class_ids:
                class_slots[(class_id, slot[0])].add(slot[1])
            teacher_slots[(candidate.teacher_id, slot[0])].add(slot[1])

    missing = set(expected) - seen_ids
    if missing:
        errors.append(f"Missing occurrence assignments: {sorted(missing)}")
    for resource, assignments_using in usage.items():
        if len(assignments_using) > 1:
            errors.append(f"Resource collision {resource}: {sorted(assignments_using)}")

    for limit in dataset["policies"]["daily_limits"]:
        resource = limit["resource"]
        if resource["type"] == "class":
            collection = class_slots
        elif resource["type"] == "teacher":
            collection = teacher_slots
        else:
            continue
        for day_id in builder.day_ids:
            count = len(collection[(resource["id"], day_id)])
            if count > limit["maximum"]:
                errors.append(
                    f"Daily limit exceeded for {resource['type']} {resource['id']} on {day_id}: {count}"
                )
    return errors


def solve_dataset(
    dataset: dict[str, Any],
    time_limit: float = 10.0,
    seed: int = 1,
    workers: int = 1,
) -> dict[str, Any]:
    validation_errors = dataset_validation_errors(dataset)
    if validation_errors:
        return {
            "status": "INVALID_INPUT",
            "diagnostics": validation_errors,
            "assignments": [],
            "validation_errors": [],
        }

    builder = PrototypeBuilder(dataset)
    artifacts = builder.build()
    if artifacts.diagnostics:
        return {
            "status": "INPUT_INFEASIBLE",
            "diagnostics": artifacts.diagnostics,
            "assignments": [],
            "validation_errors": [],
        }
    builder.add_constructive_hints(seed, min(25.0, max(20.0, time_limit)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = workers
    status_code = solver.solve(artifacts.model)
    status = solver.status_name(status_code)
    assignments: list[dict[str, Any]] = []
    penalties: dict[str, dict[str, int]] = {}
    quality_report: dict[str, Any] | None = None
    validation_errors: list[str] = []

    if status == "UNKNOWN" and builder.constructive_assignments:
        status = "FEASIBLE"
        assignments = builder.constructive_assignments
    elif status in {"OPTIMAL", "FEASIBLE"}:
        assignments = selected_assignments(solver, artifacts)
    if status in {"OPTIMAL", "FEASIBLE"}:
        validation_errors = verify_solution(dataset, assignments)
        if validation_errors:
            status = "INVALID_SOLUTION"
        from schedule_generator.quality import evaluate_quality

        quality_report = evaluate_quality(dataset, assignments)
        penalties = quality_report["by_constraint"]

    diagnostics: list[dict[str, Any]] = []
    if status == "INFEASIBLE":
        diagnostics.append(
            {
                "code": "MODEL_INFEASIBLE",
                "message": "CP-SAT proved the generated model infeasible; the prototype does not yet expose an assumption conflict core.",
            }
        )
    elif status == "UNKNOWN":
        diagnostics.append(
            {
                "code": "SEARCH_INCOMPLETE",
                "message": "No solution or proof was found before the search stopped.",
            }
        )

    proto = artifacts.model.proto
    return {
        "status": status,
        "solver": {
            "name": "OR-Tools CP-SAT",
            "version": ortools_version,
            "python": platform.python_version(),
            "seed": seed,
            "workers": workers,
            "time_limit_seconds": time_limit,
            "wall_time_seconds": solver.wall_time,
            "objective": quality_report["total_penalty"]
            if status in {"OPTIMAL", "FEASIBLE"}
            else None,
            "best_bound": solver.best_objective_bound
            if status in {"OPTIMAL", "FEASIBLE", "UNKNOWN"}
            else None,
            "branches": solver.num_branches,
            "conflicts": solver.num_conflicts,
            "variables": len(proto.variables),
            "constraints": len(proto.constraints),
        },
        "assignments": assignments,
        "penalties": penalties,
        "quality_report": quality_report
        if status in {"OPTIMAL", "FEASIBLE"}
        else None,
        "diagnostics": diagnostics,
        "validation_errors": validation_errors,
    }


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
    dataset_path = args.dataset if args.dataset.is_absolute() else Path.cwd() / args.dataset
    try:
        dataset = load_json(dataset_path)
    except ValueError as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2
    result = solve_dataset(dataset, args.time_limit, args.seed, args.workers)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    print(
        f"Solver status: {result['status']}; assignments: {len(result['assignments'])}",
        file=sys.stderr,
    )
    return 0 if result["status"] in {"OPTIMAL", "FEASIBLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
