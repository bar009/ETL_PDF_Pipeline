# Invalid Fixtures

Deliberately broken degree files. Each one must **fail** the validation gate
(`PDF_handle/prod/cli/validate_runtime.py`) for a specific, expected reason — the contract
is proven by failure, not only by success
(`PDF_handle/tests/test_invalid_fixture_contracts.py`).

| File | Breaks | Expected gate error mentions |
|------|--------|------------------------------|
| `duplicate_slug.level1.json` | the same slug appears twice | `duplicated in source file` |
| `missing_relation_target.level1.json` | `related_topics.prior` names a nonexistent entry | `missing related_topics ref` |
| `illegal_status.level1.json` | status outside the allowed set | `status must be one of` |
| `missing_required_fields.level1.json` | one entry has no title, another no slug | `missing a title` / `missing a slug` |

The fifth invalid case — **staging treated as runtime** — is the committed
`data/fixtures/staging_minimal/` directory itself: the gate must reject it because it is
not a site root.

These files are derived from `data/fixtures/runtime_site_root/data/level1.json`; if the
valid fixture changes shape, regenerate these with the same single mutation each.
