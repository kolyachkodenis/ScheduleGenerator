# Contributing

## Workflow

1. Start from the latest `main` branch.
2. Create a short-lived branch named `feature/<topic>`, `fix/<topic>`, or `docs/<topic>`.
3. Keep each task focused and deliver it as one coherent commit whenever practical.
4. Run the available checks locally.
5. Open a pull request using the repository template.
6. Merge only after required checks pass and review comments are resolved.

Direct pushes to `main` should be limited to initial repository setup or explicit maintenance decisions. Branch protection should be enabled when collaboration begins.

## Commit messages

Use an imperative Conventional Commit-style subject:

```text
<type>: <short description>
```

Common types are `feat`, `fix`, `docs`, `test`, `refactor`, `build`, and `chore`.

## Documentation

- Use terms defined in the [domain glossary](docs/GLOSSARY.md).
- Update the roadmap when stage status changes.
- Record consequential technical decisions in `docs/adr/`.
- Keep examples free of real personal data unless their use is explicitly authorized.

## Local checks

Run the documentation checks from the repository root:

```powershell
python scripts/check_docs.py
```

The script validates required documents, whitespace, and local Markdown links.
