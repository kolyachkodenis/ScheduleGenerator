from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from schedule_generator.data_import import apply_import, export_csv, preview_csv, preview_xlsx
from schedule_generator.storage import DatasetStore

ROOT = Path(__file__).resolve().parents[1]
DEMO = json.loads((ROOT / "examples" / "small-school.json").read_text(encoding="utf-8"))

class StorageImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_migrations_and_dataset_crud_are_idempotent(self) -> None:
        with DatasetStore(self.directory / "school.db") as store:
            store.migrate()
            self.assertEqual(store.save(DEMO).revision, 1)
            self.assertEqual(store.list()[0].data, DEMO)
            changed = copy.deepcopy(DEMO)
            changed["school"]["label"] = "Updated synthetic school"
            self.assertEqual(store.save(changed).revision, 2)
            self.assertEqual(store.get(DEMO["dataset_id"], revision=1).data, DEMO)
            store.delete(DEMO["dataset_id"])
            with self.assertRaises(KeyError):
                store.get(DEMO["dataset_id"])

    def test_collection_replacement_is_validated_before_commit(self) -> None:
        with DatasetStore(self.directory / "school.db") as store:
            store.save(DEMO)
            with self.assertRaisesRegex(ValueError, "invalid dataset"):
                store.replace_collection(DEMO["dataset_id"], "teachers", [])
            self.assertEqual(store.get(DEMO["dataset_id"]).revision, 1)

    def test_csv_round_trip_preview_and_apply(self) -> None:
        preview = preview_csv(export_csv(DEMO, self.directory / "school.csv"))
        self.assertTrue(preview.valid)
        self.assertEqual(preview.dataset, DEMO)
        with DatasetStore(self.directory / "school.db") as store:
            self.assertEqual(apply_import(store, preview).data, DEMO)

    def test_invalid_csv_reports_row_field_and_is_not_applied(self) -> None:
        source = self.directory / "invalid.csv"
        source.write_text(
            'section,value_json\nschema_version,"not json"\n', encoding="utf-8"
        )
        preview = preview_csv(source)
        self.assertFalse(preview.valid)
        self.assertEqual((preview.errors[0].row, preview.errors[0].field), (2, "value_json"))
        with DatasetStore(self.directory / "school.db") as store:
            with self.assertRaisesRegex(ValueError, "invalid import preview"):
                apply_import(store, preview)
            self.assertEqual(store.list(), [])

    def test_xlsx_template_is_a_valid_demo_import(self) -> None:
        template = ROOT / "outputs" / "stage-7" / "school-data-import-template.xlsx"
        preview = preview_xlsx(template)
        self.assertTrue(preview.valid, preview.errors)
        self.assertEqual(preview.dataset, DEMO)

    def test_json_export_and_database_backup(self) -> None:
        with DatasetStore(self.directory / "school.db") as store:
            store.save(DEMO)
            exported = store.export_json(
                DEMO["dataset_id"], self.directory / "export.json"
            )
            backup = store.backup(self.directory / "backup.db")
        self.assertEqual(json.loads(exported.read_text(encoding="utf-8")), DEMO)
        with DatasetStore(backup) as restored:
            self.assertEqual(restored.get(DEMO["dataset_id"]).data, DEMO)
