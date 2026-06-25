# Agent Skills

Reusable agent skills distilled from real ingest sessions. To activate in
Claude Code, copy a skill directory into your project or user `.claude/skills/`.

- `etl-source-ingest/` — run one source end to end: routing check, prep,
  heuristic preflight, Gemini stage, candidate review, selective approval,
  apply, structure builder, gates.
- `source-markdown-prep/` — raw OCR markdown to stage-ready semantic sections
  (decision tree over restructure_page_md_to_semantic.py).
