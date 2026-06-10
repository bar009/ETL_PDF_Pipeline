# Rules

These rules keep the repo understandable after the fresh start.

## Do Commit

- source code
- tests
- small fixtures
- JSON schemas and data contracts
- prompt templates
- active documentation
- representative sample data

## Do Not Commit

- original PDFs
- provider responses and run logs
- generated chunks, staging output, backups, or QA output
- local databases
- `.env` files
- `node_modules`
- build output
- historical site snapshots

## Data Boundaries

- staging data is review material
- canonical data is approved source of truth
- site data is the exported runtime shape consumed by the frontend

The site should not read directly from first-pass ETL staging output.

## Content Rules

- do not edit generated files by hand unless the file is explicitly a reviewed override layer
- do not change a published canonical ID or slug without a migration note
- do not add content without a source basis
- do not treat reports as canonical data unless a workflow explicitly consumes them

## Safety Checks Before Upload

Before pushing a large change, check for:

- API keys
- tokens
- passwords
- private paths
- raw PDFs
- large JSON or JSONL exports
- databases

Useful PowerShell search:

```powershell
Select-String -Path .\* -Pattern "api_key|secret|token|password" -Recurse
```

