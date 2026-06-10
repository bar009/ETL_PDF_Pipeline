# AGENTS.override.md

Local override for `PDF_handle/TOOLS/validation/`.

## Purpose

This folder contains validation, regression, seed-building, and coverage-check scripts.

## Rules

1. Validation scripts should explain what contract they are asserting.
2. Prefer failing loudly over silently weakening checks.
3. If a validation script depends on generated artifacts, name those dependencies clearly.
4. Keep seed-building scripts distinct from live mutation scripts even when both emit JSON.

## Verification

1. Run syntax checks on the touched validation script.
2. Verify failure conditions still produce explicit non-success output.
3. Verify generated artifact paths still land under the expected `TOOLS/data/` or report location.
4. If a legacy root shim exists, verify that old command path still resolves.
