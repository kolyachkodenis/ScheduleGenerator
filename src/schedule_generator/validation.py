"""Dataset validation shared by persistence and import services."""

from __future__ import annotations

import json
from typing import Any

from scripts.validate_dataset import SCHEMA_PATH, SemanticValidator, validate_schema


def dataset_validation_errors(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_schema(dataset, schema, require_schema=True, errors=errors)
    if not errors:
        errors.extend(SemanticValidator(dataset).validate())
    return errors
