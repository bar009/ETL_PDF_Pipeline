# AGENTS.override.md

Local override for `PDF_handle/TOOLS/apply/`.

## Purpose

This folder contains mutation-oriented tools and controlled apply steps.

## Rules

1. Any script here must be explicit about what it mutates.
2. Prefer dry-run or preview support when the workflow allows it.
3. Keep backups, reports, and validation outputs visible.
4. Do not mix apply logic with diagnostic-only tooling.

## Verification

1. Run syntax checks on the touched apply script.
2. Verify the default mode is still safe and clearly documented.
3. Confirm mutation targets, backup/report paths, and preservation paths are still explicit.
4. Prefer validating a preview or plan path before trusting a live apply path.
