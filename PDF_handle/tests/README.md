# Tests

Run from repo root:

```bash
python -m unittest discover -s PDF_handle/tests -v
```

Uses only the standard library `unittest` framework. No third-party test runner required.

Tests are scoped to the canonical `prod/` surface and the bugs hardened in the postmerge skip-detection and atomic-write paths. They are deliberately small and fast: each test creates a temporary site root + staging dir, populates the JSON files it needs, and asserts behavior. No real PDFs or LLM calls.
