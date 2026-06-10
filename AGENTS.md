# AGENTS.md

Guidance for human and AI contributors working in the workspace root.

## Purpose

This workspace contains multiple active areas:

- `PDF_handle/` for the PDF knowledge pipeline
- `paperclip-master/` for the Paperclip project and related clones
- site roots and published copies
- experiments, archive material, and shared scripts

Use this file for workspace-level navigation.
Use project-local docs for detailed behavior.

## Read Order

1. `management/CURRENT_PLAN.md`
2. `management/RUN_QUEUE.md`
3. `management/BACKLOG.md`
4. `management/APPROVAL_LEVELS.md`
5. `docs/PROJECT_SCOPE.md`
6. `docs/REPO_LAYOUT.md`
7. `docs/DOMAIN_BOUNDARIES.md`
8. `docs/KNOWN_ISSUES.md`
9. `docs/DECISION_LOG.md`

For `PDF_handle/` work, then read:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/PROJECT_SCOPE.md`

For Paperclip work, then read:

1. `paperclip-master/paperclip-master/paperclip/AGENTS.md`

## Root Rules

1. Do not create new top-level numeric folders.
2. Do not create new site copies outside the `sites/`, `published_sites/`, or `sandbox_sites/` migration path.
3. Keep project-specific guidance inside the project, not only at workspace root.
4. Prefer documenting path and naming decisions before doing large moves.
5. Treat `PDF_handle/` as a project and not merely as a random utility folder.
6. Repo-native canonical Codex skills live in `.agents/skills/`.
7. Treat `management/` as the canonical current operational state and active control surface.
8. Keep enduring architecture and policy in `docs/`, not in `management/`.
9. Treat reports and artifacts as evidence, not as instruction files or silent data sources.
10. Treat `PDF_handle/skills/` as a draft or local-copy area unless a skill is explicitly promoted into `.agents/skills/`.

## Non-Trivial Tasks

For any non-trivial task:

1. Read `management/CURRENT_PLAN.md`.
2. Read `management/RUN_QUEUE.md` when the user wants continuous follow-through across bounded steps.
3. Check `management/APPROVAL_LEVELS.md` before making behavior-changing edits.
4. If the task is not represented in `management/BACKLOG.md` or conflicts with the current plan, stop and map it before substantial work.

## Important Distinction

- root `AGENTS.md` explains the workspace
- `management/*` holds the current operational state and active control surface
- `.agents/skills/` is the canonical repo skill home
- `PDF_handle/AGENTS.md` explains the ETL project
- `PDF_handle/skills/` is draft/local-copy only unless explicitly promoted
- `docs/*` holds enduring architecture and policy
- reports/artifacts hold evidence
- Paperclip keeps its own repo-local guidance
