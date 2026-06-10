# Workspace Project Scope

## What This Workspace Contains

This workspace is not a single app.
It is a mixed working environment that currently includes:

- a PDF ETL and site-generation project in `PDF_handle/`
- a Paperclip codebase under `paperclip-master/`
- active and historical site roots
- experiments, archive material, and helper scripts

## Why This Matters

Many current pain points are workspace problems rather than project-only problems:

- numeric site roots at top level
- published and sandbox copies outside a single naming model
- duplicated or nested project roots
- difficulty knowing what is source, what is generated output, and what is historical

## Workspace Principle

The workspace should answer these questions quickly:

- where is the real project root?
- what is safe to edit?
- what is generated output?
- what is current live content?
- what is historical and should stay frozen?

## Project-Level Ownership

- `PDF_handle/` owns PDF ETL and site-data transformation
- `paperclip-master/` owns Paperclip-related code
- `docs/` at workspace root owns cross-workspace structure and decisions

## Non-Goal

The workspace root should not become the place where every project-specific implementation detail lives.
It should stay a navigation and governance layer.
