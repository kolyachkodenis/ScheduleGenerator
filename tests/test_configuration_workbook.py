from __future__ import annotations

import copy
import json
import unittest
import zipfile
from io import BytesIO

from schedule_generator.configuration_workbook import (
    SHEETS,
    export_configuration_xlsx,
    import_configuration_xlsx,
)
from schedule_generator.prototype import ROOT
from schedule_generator.validation import dataset_validation_errors


class ConfigurationWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = json.loads(
            (ROOT / "examples" / "small-school.json").read_text(encoding="utf-8")
        )

    def test_export_contains_four_editable_worksheets(self) -> None:
        content = export_configuration_xlsx(self.dataset)
        with zipfile.ZipFile(BytesIO(content)) as archive:
            workbook = archive.read("xl/workbook.xml").decode("utf-8")
        for sheet in SHEETS:
            self.assertIn(f'name="{sheet}"', workbook)

    def test_export_import_round_trip_is_valid(self) -> None:
        updates = import_configuration_xlsx(
            self.dataset, export_configuration_xlsx(self.dataset)
        )
        updated = copy.deepcopy(self.dataset)
        updated.update(updates)
        self.assertEqual(dataset_validation_errors(updated), [])
        self.assertEqual(updates["subjects"], self.dataset["subjects"])
        self.assertEqual(updates["classrooms"], self.dataset["classrooms"])
        self.assertEqual(updates["teachers"], self.dataset["teachers"])


if __name__ == "__main__":
    unittest.main()
