# Sites

- `work/react-v2-prototype/` — the front-end pilot
- `site_roots.example.json` — template for the site-roots config

## Site Roots Config

The pipeline has **no built-in site roots**. Steps that touch a site root take an explicit
`--site-root`, or resolve one through `sites/site_roots.json` (read by both
`PDF_handle/prod/core/site_roots.py` and `PDF_handle/TOOLS/lib/site_roots.js`).

To configure local roots:

```powershell
Copy-Item sites/site_roots.example.json sites/site_roots.json
# then edit the paths (relative to the repo root, or absolute)
```

Paths in the example follow the target layout in `docs/REPO_LAYOUT.md`. A valid site root is
a directory containing `data/content.schema.json` — the smallest example is
`data/fixtures/runtime_site_root/` (fixtures are for tests; never point a writing pipeline
step at them).
