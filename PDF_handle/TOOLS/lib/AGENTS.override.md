# AGENTS.override.md

Local override for `PDF_handle/TOOLS/lib/`.

## Purpose

This folder contains shared runtime helpers used across runners, audits, validation, and apply scripts.

## Rules

1. Keep these modules generic and reusable.
2. Do not hide workflow-specific behavior in shared helpers unless multiple tools truly depend on it.
3. Preserve backward compatibility for imports from the legacy `TOOLS/` root when practical.
4. Any path helpers here should prefer canonical workspace/config resolution over fresh hardcoded version folders.

## Verification

1. Run syntax checks on touched modules.
2. Verify legacy root import wrappers still resolve.
3. Check at least one downstream tool that imports the helper still loads correctly.
