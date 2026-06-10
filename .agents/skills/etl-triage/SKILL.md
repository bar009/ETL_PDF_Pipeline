---
name: etl-triage
description: Diagnose failures, stalls, path confusion, resume issues, and output mismatches in the PDF_handle seven-step ETL pipeline and TOOLS wrappers. Use when Codex needs to debug step execution, staging artifacts, site-root selection, report-to-data confusion, or broken ETL assumptions in this repository.
---

# ETL Triage

Treat `PDF_handle/` as the project root for this skill.

## Read First

Read these files in order:

1. `PDF_handle/AGENTS.md`
2. `PDF_handle/docs/PROJECT_SCOPE.md`
3. `PDF_handle/docs/ETL_FLOW.md`
4. `PDF_handle/docs/DOMAIN_BOUNDARIES.md`
5. `PDF_handle/docs/KNOWN_ISSUES.md`

Then read only the step or tool script directly involved in the failure.

## Triage Workflow

1. Identify whether the failing command belongs to the canonical step layer or `TOOLS/`.
2. Identify the selected or implicit `--site-root`.
3. Identify the expected inputs and outputs for that step.
4. Check whether the issue is one of:
   - missing input artifact
   - path-root confusion
   - staged vs live confusion
   - schema or reference validation failure
   - provider/runtime interruption
   - resume-state inconsistency
5. Fix the smallest layer that restores the intended contract.

## Strong Heuristics

- If the bug changes ETL semantics, inspect `step_01` to `step_07` first.
- If the bug is mostly orchestration, inspect `TOOLS/` next.
- If live data changed unexpectedly, inspect Step 6 or explicit apply flows.
- If a command "worked" but the wrong site was touched, suspect implicit `0.3` defaults first.

## Do Not

- treat reports as canonical data
- patch around path confusion by creating more duplicate roots
- silently broaden mutation scope when the real problem is missing review gating
