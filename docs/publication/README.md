# Timetable publication

Publication separates editable work from files that can be distributed. An approval is always pinned to one immutable draft version and its historical dataset revision.

## Lifecycle

`APPROVED -> PUBLISHED -> UNPUBLISHED -> PUBLISHED`

- **Approve** records the current conflict-free draft version. A version with hard validation errors cannot be approved.
- **Publish** creates XLSX and PDF artifacts for that exact version and records each filename, size, and SHA-256 digest.
- **Unpublish** immediately removes download access while retaining the approval and artifact metadata. The same approved version can be published again.

Further edits do not alter an existing approval. The operator must explicitly approve the new version before it can replace previously distributed files.

## Export layouts

Both formats contain separate schedules for every class and every teacher. Rows represent ordered periods, columns represent teaching days, and lesson cells include the subject plus the relevant teacher, class, and room details.

The XLSX workbook uses one frozen, filterable, landscape-print worksheet per resource. The PDF uses one landscape A4 page per resource with repeated headers, compact lesson cells, and page numbers.

## HTTP routes

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/drafts/{draft_id}/approve` | Approve the current conflict-free version. |
| `POST` | `/api/publications/{publication_id}/publish` | Create and expose XLSX and PDF artifacts. |
| `POST` | `/api/publications/{publication_id}/unpublish` | Revoke artifact download access. |
| `GET` | `/downloads/{filename}` | Download an artifact only while its publication is active. |

The state endpoint includes publication records so the local operator interface can show the correct action and download links.
