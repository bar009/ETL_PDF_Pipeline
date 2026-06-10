# Structure Roadmap

This document turns the fresh-start decision into an execution plan.

The goal is not to rewrite everything at once. The goal is to move the repo toward a cleaner
structure without losing the working pipeline or the React prototype.

## Current Baseline

The new repo already has the right starting shape:

- `PDF_handle/` contains the ETL and supporting runtime code
- `sites/work/react-v2-prototype/` contains the UI pilot
- `data/` is reserved for small samples, schemas, and fixtures
- `.agents/skills/` is the canonical skill home
- `docs/` holds policy, contracts, and migration guidance

That is the foundation. The next work is to harden boundaries and then simplify the code layout
inside each area.

## Target Shape

The target is a repo where each kind of work has one obvious home.

```text
code-clean-start/
  AGENTS.md
  README.md
  MIGRATION_MANIFEST.md
  .env.example
  .agents/
  data/
    fixtures/
    samples/
    schemas/
  docs/
    DATA_CONTRACT.md
    DECISION_LOG.md
    DOMAIN_BOUNDARIES.md
    PROJECT_SCOPE.md
    REPO_LAYOUT.md
    RULES.md
    STRUCTURE_ROADMAP.md
  PDF_handle/
    prod/
    docs/
    prompts/
    tests/
    TOOLS/
  sites/
    work/
      react-v2-prototype/
```

## What We Are Optimizing For

- one canonical ETL implementation surface
- one canonical front-end pilot surface
- one clear data contract
- no committed generated data dumps
- no hidden source of truth outside the repo docs
- small, explicit compatibility layers instead of sprawling legacy copies

## Phase Overview

Run the refactor as a sequence of small, verifiable passes.

```text
Phase 0: Freeze the contract
Phase 1: Clarify code homes
Phase 2: Split data states
Phase 3: Make the React pilot adapter-driven
Phase 4: Reduce compatibility surface
Phase 5: Lock in verification
Phase 6: Operationalize the new structure
```

Each phase should finish with a small commit and a short note in `docs/DECISION_LOG.md` when a
lasting ownership or path decision changes.

## Phase Rules

- do not move folders before the destination ownership is documented
- do not delete compatibility paths before a replacement command is verified
- do not make the React pilot depend on ETL staging files
- do not commit raw, generated, or large runtime data
- do not mix behavior changes into pure path moves unless the test proves the move requires it
- keep each phase small enough to review from `git diff --stat`

## Phase 0: Freeze The Contract

Before moving code around, lock down the rules.

Scope:

- docs, contracts, manifests, and ignore rules
- no code moves except tiny README or path-reference fixes

Deliverables:

- keep `data/` limited to small fixtures, samples, and schemas
- keep `.env.example` as the only committed secret/config template
- keep `PDF_handle/prod/` as the canonical Python ETL execution surface
- keep the React pilot read-only with respect to runtime JSON contracts
- treat reports, exports, and generated outputs as evidence, not source
- align `README.md`, `MIGRATION_MANIFEST.md`, `docs/RULES.md`, and `docs/DATA_CONTRACT.md`

Exit criteria:

- the repo docs agree on the same boundaries
- new work has a clear place to land
- `git check-ignore` confirms raw data, generated data, outputs, DB files, and local env files are ignored

Suggested checks:

```powershell
git check-ignore .env data/raw/input.pdf data/generated/out.json outputs/result.json
python PDF_handle/prod/check_import_boundaries.py
```

## Phase 1: Clarify The Code Homes

The first structural cleanup is naming and ownership, not feature work.

Scope:

- ETL source ownership
- wrappers versus implementation modules
- command entry points
- front-end adapter ownership

Deliverables:

- keep new ETL logic in `PDF_handle/prod/cli/`, `PDF_handle/prod/steps/`, `PDF_handle/prod/core/`, or adjacent prod modules
- keep compatibility wrappers thin
- stop adding new one-off scripts at the repo root
- keep frontend data access behind adapter layers instead of direct JSON mutation
- document the allowed homes for new ETL code in `PDF_handle/docs/` or `PDF_handle/prod/README.md`
- identify root-level step wrappers that should remain wrappers only
- identify `PDF_handle/TOOLS/` scripts that are operational wrappers, not product logic

Exit criteria:

- no new core logic is added to compatibility wrappers
- the boundary between source code, adapters, and runtime data is obvious
- a contributor can tell where to add a new step, helper, provider, schema, CLI command, test, or prompt

Suggested checks:

```powershell
python -m compileall -q PDF_handle/prod PDF_handle/tests
python PDF_handle/prod/check_import_boundaries.py
```

## Phase 2: Split Runtime From Review Material

The most important cleanup is to keep ETL states distinct.

Scope:

- source input
- staging review material
- canonical approved content
- site runtime export
- validation evidence

Deliverables:

- staging output stays staging
- canonical content stays canonical
- site runtime stays site runtime
- validation output stays validation output
- large PDF, JSON, and DB artifacts stay out of git
- create or document small fixtures that represent each data state
- add schema or contract checks for the smallest useful canonical/runtime examples
- make path names reflect whether data is source, staging, canonical, runtime, or evidence

Exit criteria:

- a newcomer can tell, from the folder name alone, whether a file is source, staging, or output
- no pipeline stage reads directly from a later stage's output by accident
- tests or contract checks fail when a staged artifact is treated as site runtime

## Phase 3: Make The React Pilot Adapter-Driven

The React shell should consume a stable contract, not the ETL internals.

Scope:

- `sites/work/react-v2-prototype/src/lib/`
- adapter fixtures
- route and UI boundary tests
- `public/data/README.md`

Deliverables:

- keep the UI reading through adapter contracts
- keep the runtime JSON shape documented
- keep UI tests focused on boundaries and user flows
- avoid mutating site JSON during front-end iteration
- keep demo content separate from runtime contract fixtures
- make adapter tests cover missing fields, unknown routes, locale direction, and relation references

Exit criteria:

- the UI can be iterated on without reshaping the source ETL data model
- adapter tests prove the boundary stays stable
- runtime data can be replaced without changing page components

Suggested checks:

```powershell
cd sites/work/react-v2-prototype
npm.cmd run build
npm.cmd test
```

## Phase 4: Reduce Compatibility Surface

Once the boundaries are stable, the repo can get simpler.

Scope:

- duplicate wrappers
- old script entry points
- stale docs
- compatibility notes

Deliverables:

- delete or retire old duplicate paths after the newer path is verified
- collapse repeated helper logic into shared modules
- keep only the wrappers that are still required for migration
- document any remaining compatibility path explicitly
- create small replacement notes for any command whose path changes
- update docs before removing the old path

Exit criteria:

- the repo has fewer duplicate concepts, not more
- any retained legacy path has a named reason to exist
- every removed wrapper has an equivalent documented command or is explicitly obsolete

## Phase 5: Lock In Verification

The structure is not real until it is enforced.

Scope:

- tests
- import checks
- fixture validation
- smoke commands
- CI readiness

Deliverables:

- schema and uniqueness tests for canonical data
- import boundary checks for ETL code
- adapter boundary checks for the React pilot
- smoke checks for the smallest useful pipeline path
- a local test command list that can be used by GitHub Actions later
- a tiny fixture set that is safe to commit and quick to run

Exit criteria:

- the repo can prove the structure, not just describe it
- a clean checkout can run the documented checks without private data

## Phase 6: Operationalize The New Structure

After the repo shape is stable, make it easy to keep stable.

Scope:

- GitHub branch hygiene
- CI setup
- release and publish notes
- onboarding

Deliverables:

- add a minimal CI workflow for Python boundary checks and React checks
- document the default local setup path in `README.md`
- add branch protection expectations for `main`
- add a short "new work checklist" for future changes

Exit criteria:

- new changes are checked automatically before merging
- a new contributor can clone, install, run checks, and understand what not to commit
- `main` remains the clean source of truth

## Immediate Next Steps

1. Treat Phase 0 as complete only after ignore rules and docs are rechecked.
2. Start Phase 1 in `PDF_handle/prod/`, because it is the canonical ETL implementation surface.
3. Add a short code-home note for ETL modules before moving or deleting wrappers.
4. Add the first small fixture set for Phase 2.
5. Add boundary/idempotency tests before any broad folder move.
6. Move only one path family at a time, then run checks and commit.

## Decisions Still Open

- whether `sites/work/v2.0/` material should be imported at all
- whether the next pass should prioritize ETL hardening or frontend stabilization
- which legacy compatibility wrappers are still worth keeping

## Recommended First Refactor Pass

Begin with Phase 1 for `PDF_handle/prod/`.

Why:

- `PDF_handle/prod/` is already documented as the canonical ETL surface
- the root `step_01..07` files can stay as compatibility wrappers while prod gets cleaner
- import boundary checks already exist, so the risk is measurable
- React can stay stable while the ETL implementation surface becomes easier to reason about

First pass deliverables:

- document ETL code homes in `PDF_handle/prod/README.md`
- map root wrappers to prod modules
- find duplicated helper logic between root scripts, `TOOLS/`, and `prod/`
- add or strengthen the smallest boundary tests before moving code
- commit the documentation and tests before any broad code move
