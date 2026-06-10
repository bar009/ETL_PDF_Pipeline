# Schemas

JSON schemas and contract examples that are safe to commit.

- `content.schema.json` — the runtime site data contract for degree files
  (`level1.json`, `level2.json`, ...). This is the contract home; the runtime fixture at
  `data/fixtures/runtime_site_root/data/content.schema.json` carries a copy because a site
  root must be self-contained. A test
  (`PDF_handle/tests/test_data_state_contracts.py`) fails if the two copies drift —
  update both together.

Large generated data should stay out of this folder.
