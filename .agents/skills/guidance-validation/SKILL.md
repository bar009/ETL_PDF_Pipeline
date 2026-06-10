---
name: guidance-validation
description: Validate Codex guidance files in this repository, including AGENTS.md layers, .codex/config.toml, docs, and repo skills. Use when adding or reviewing instruction files, checking whether skills will trigger correctly, verifying official Codex placement rules, or auditing whether the guidance layer is complete, specific, and internally consistent.
---

# Guidance Validation

Use this skill to review whether the repository's Codex guidance is actually operational, not just well written.

## Read First

Read these files in order:

1. `AGENTS.md`
2. `docs/CODEX_GUIDANCE_HARDENING.md`
3. `docs/PROJECT_SCOPE.md`
4. `docs/REPO_LAYOUT.md`

If the question is about `PDF_handle/`, then also read:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/PROJECT_SCOPE.md`
3. `PDF_handle/docs/ETL_FLOW.md`

## Validation Goals

Check all of the following:

1. instruction layering
2. placement in official Codex paths
3. path and command accuracy
4. skill trigger quality
5. missing coverage for operator workflows
6. drift between docs and current repository reality

## Workflow

1. Identify which layer is being reviewed:
   - workspace root
   - project root
   - specialized subfolder
   - skill
2. Verify the file is in the right place for Codex discovery.
3. Verify the file is specific enough to change behavior, not just descriptive.
4. Verify that any commands, paths, and defaults still match the codebase.
5. Verify that nested guidance adds something new rather than repeating its parent.
6. Write findings as:
   - incorrect placement
   - missing specificity
   - conflicting guidance
   - stale path or command
   - missing validation rule
   - optional polish

## Strong Heuristics

- If a skill is repo-scoped, prefer `.agents/skills/`.
- If a rule only applies to one sub-area, consider a closer override instead of bloating the parent file.
- If a skill `description` is vague, implicit triggering will be weak.
- If a doc explains a principle without an operator workflow, it is not yet complete.
- If a config value is important for safe behavior, decide explicitly whether to pin it or inherit it.

## Output Shape

Produce:

1. a short verdict
2. the top gaps in priority order
3. the smallest next actions that materially improve the guidance layer

For detailed official criteria, read `references/official-codex-checklist.md`.
