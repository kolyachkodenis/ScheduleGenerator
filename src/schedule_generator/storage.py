"""SQLite persistence for versioned school datasets."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from schedule_generator.api import SchedulingProblem


MIGRATIONS = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS dataset_revisions (
            dataset_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            fingerprint TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (dataset_id, revision)
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS generation_jobs (
            job_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            dataset_revision INTEGER NOT NULL,
            dataset_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            progress_completed INTEGER NOT NULL DEFAULT 0,
            progress_total INTEGER NOT NULL,
            cancellation_requested INTEGER NOT NULL DEFAULT 0,
            best_alternative INTEGER,
            result_json TEXT,
            diagnostics_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS generation_jobs_dataset_id
            ON generation_jobs(dataset_id, created_at);
        CREATE TABLE IF NOT EXISTS generation_alternatives (
            job_id TEXT NOT NULL,
            alternative_index INTEGER NOT NULL,
            seed INTEGER NOT NULL,
            status TEXT NOT NULL,
            quality_penalty INTEGER,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (job_id, alternative_index),
            FOREIGN KEY (job_id) REFERENCES generation_jobs(job_id) ON DELETE CASCADE
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS timetable_drafts (
            draft_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL UNIQUE,
            dataset_id TEXT NOT NULL,
            dataset_revision INTEGER NOT NULL,
            current_version INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES generation_jobs(job_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS timetable_draft_versions (
            draft_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            assignments_json TEXT NOT NULL,
            quality_json TEXT,
            validation_errors_json TEXT NOT NULL DEFAULT '[]',
            change_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (draft_id, version),
            FOREIGN KEY (draft_id) REFERENCES timetable_drafts(draft_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS timetable_locks (
            draft_id TEXT NOT NULL,
            assignment_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (draft_id, assignment_id),
            FOREIGN KEY (draft_id) REFERENCES timetable_drafts(draft_id) ON DELETE CASCADE
        );
        """,
    ),
)


@dataclass(frozen=True)
class StoredDataset:
    dataset_id: str
    schema_version: str
    fingerprint: str
    revision: int
    data: dict[str, Any]


class DatasetStore:
    """Store complete validated datasets and their immutable revisions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> DatasetStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def migrate(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {
            row[0] for row in self.connection.execute("SELECT version FROM schema_migrations")
        }
        for version, sql in MIGRATIONS:
            if version in applied:
                continue
            with self.connection:
                self.connection.executescript(sql)
                self.connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
                )

    @staticmethod
    def _problem(dataset: Mapping[str, Any]) -> SchedulingProblem:
        from schedule_generator.validation import dataset_validation_errors

        errors = dataset_validation_errors(dict(dataset))
        if errors:
            raise ValueError("invalid dataset: " + "; ".join(errors))
        return SchedulingProblem.from_mapping(dataset)

    def save(self, dataset: Mapping[str, Any]) -> StoredDataset:
        """Create or replace a dataset in one transaction."""

        problem = self._problem(dataset)
        payload = json.dumps(
            problem.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        current = self.connection.execute(
            "SELECT MAX(revision) FROM dataset_revisions WHERE dataset_id = ?",
            (problem.dataset_id,),
        ).fetchone()
        revision = 1 if current is None or current[0] is None else int(current[0]) + 1
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO datasets(dataset_id, schema_version, fingerprint, revision, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    fingerprint = excluded.fingerprint,
                    revision = excluded.revision,
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    problem.dataset_id,
                    problem.schema_version,
                    problem.fingerprint,
                    revision,
                    payload,
                ),
            )
            self.connection.execute(
                "INSERT INTO dataset_revisions(dataset_id, revision, fingerprint, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (problem.dataset_id, revision, problem.fingerprint, payload),
            )
        return self.get(problem.dataset_id)

    def get(self, dataset_id: str, revision: int | None = None) -> StoredDataset:
        if revision is None:
            row = self.connection.execute(
                "SELECT dataset_id, schema_version, fingerprint, revision, payload_json "
                "FROM datasets WHERE dataset_id = ?", (dataset_id,)
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT dataset_id, json_extract(payload_json, '$.schema_version'), "
                "fingerprint, revision, payload_json FROM dataset_revisions "
                "WHERE dataset_id = ? AND revision = ?", (dataset_id, revision)
            ).fetchone()
        if row is None:
            raise KeyError(dataset_id)
        return StoredDataset(row[0], row[1], row[2], int(row[3]), json.loads(row[4]))

    def list(self) -> list[StoredDataset]:
        ids = self.connection.execute(
            "SELECT dataset_id FROM datasets ORDER BY dataset_id"
        ).fetchall()
        return [self.get(row[0]) for row in ids]

    def delete(self, dataset_id: str) -> None:
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,)
            )
        if cursor.rowcount == 0:
            raise KeyError(dataset_id)

    def replace_collection(
        self, dataset_id: str, collection: str, records: Iterable[Mapping[str, Any]]
    ) -> StoredDataset:
        stored = self.get(dataset_id)
        if collection not in stored.data or not isinstance(stored.data[collection], list):
            raise KeyError(collection)
        stored.data[collection] = [dict(record) for record in records]
        return self.save(stored.data)

    def export_json(self, dataset_id: str, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.get(dataset_id).data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination

    def backup(self, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.connection.commit()
        target = sqlite3.connect(destination)
        try:
            self.connection.backup(target)
        finally:
            target.close()
        return destination
