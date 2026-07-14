# School data storage and import

Stage 7 uses SQLite for durable configuration data. Each save creates an immutable revision, and validation happens before the transaction starts.

## Import formats

Both CSV and XLSX use the same two-column contract on the `Dataset` worksheet or in the CSV file:

| Column | Meaning |
| --- | --- |
| `section` | A unique top-level key from the versioned dataset schema. |
| `value_json` | The complete JSON value for that section. |

The XLSX template contains synthetic demonstration data. The CSV equivalent can be created with `export_csv` from `schedule_generator.data_import`.

## Preview and apply

Preview never writes data:

```powershell
python scripts/import_school_data.py outputs/stage-7/school-data-import-template.xlsx
```

After correcting every error, apply the same source atomically:

```powershell
python scripts/import_school_data.py outputs/stage-7/school-data-import-template.xlsx --database school.db --apply
```

Invalid input exits with status 1 and cannot be applied. JSON export and consistent SQLite backup are available through `DatasetStore.export_json` and `DatasetStore.backup`.
