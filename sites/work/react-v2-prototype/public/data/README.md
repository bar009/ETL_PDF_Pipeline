# Runtime Data

Full runtime JSON is intentionally not committed in the clean repo.

The prototype currently uses `src/data/demoContent.js` for local UI work.
When the real adapter is enabled, provide runtime JSON from an approved data export or a local ignored data source.

Expected runtime filenames:

- `degrees.json`
- `level1.json`
- `level2.json`
- `level3.json`
- `library.json`

The degree files must satisfy the committed contract at `data/schemas/content.schema.json`
(repo root). A minimal valid example lives at
`data/fixtures/runtime_site_root/data/level1.json`. The adapter boundary —
including how missing fields, unknown routes, locale direction, and relation
references are handled — is pinned by `src/lib/adapterBoundary.test.js` (`npm test`).

