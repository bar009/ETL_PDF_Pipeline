# AGENTS.override.md

Local override for `PDF_handle/TOOLS/runners/`.

## Purpose

This folder contains orchestration entrypoints and operational runners.

## Rules

1. Treat runner scripts as coordination layers, not the canonical ETL implementation.
2. Prefer delegating to step scripts or lower-level tool modules instead of duplicating logic here.
3. Be explicit about the target site root, report dir, and child tool invocations.
4. When changing a runner, verify that child command paths and report locations still resolve correctly.

## Verification

1. Run a syntax check on the touched runner.
2. Verify any child tool paths still resolve after file moves.
3. If the runner still has a legacy root shim, verify that old entrypoint too.
4. Confirm the runner remains orchestration-only and did not absorb lower-level business logic.
