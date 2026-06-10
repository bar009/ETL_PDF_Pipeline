# Fixtures

Small, deterministic test fixtures used by automated checks. Safe to publish.

Each fixture is the smallest useful example of one ETL **data state**, so tests can prove the
states stay distinct (see `docs/STRUCTURE_ROADMAP.md`, Phase 2, and `docs/REPO_LAYOUT.md`,
"Data States"):

| Fixture | Data state | Represents |
|---------|------------|------------|
| `runtime_site_root/` | **runtime** | a minimal valid site root: `data/content.schema.json` plus a valid `level1.json`. This is the shape `--site-root` must point at. |
| `staging_minimal/` | **staging** | a minimal Step 5 review artifact (`level1.patch.json` with one staged operation). Review material — never site runtime. |

Contract tests live in `PDF_handle/tests/test_data_state_contracts.py`. They pin that:

- the runtime fixture satisfies the site-root contract and the staging fixture does not
- the fixture degree file normalizes, validates, and has unique, resolvable references
- the fixture schema copy never drifts from `data/schemas/content.schema.json`
- the staged patch applies cleanly onto the runtime fixture and the result still validates

When changing a fixture, run from the repo root:

```bash
python -m unittest discover -s PDF_handle/tests
```
