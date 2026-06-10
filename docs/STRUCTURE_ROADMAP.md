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

## Phase 0: Freeze The Contract

Before moving code around, lock down the rules.

Deliverables:

- keep `data/` limited to small fixtures, samples, and schemas
- keep `.env.example` as the only committed secret/config template
- keep `PDF_handle/prod/` as the canonical Python ETL execution surface
- keep the React pilot read-only with respect to runtime JSON contracts
- treat reports, exports, and generated outputs as evidence, not source

Exit criteria:

- the repo docs agree on the same boundaries
- new work has a clear place to land

## Phase 1: Clarify The Code Homes

The first structural cleanup is naming and ownership, not feature work.

Deliverables:

- keep new ETL logic in `PDF_handle/prod/cli/`, `PDF_handle/prod/steps/`, `PDF_handle/prod/core/`, or adjacent prod modules
- keep compatibility wrappers thin
- stop adding new one-off scripts at the repo root
- keep frontend data access behind adapter layers instead of direct JSON mutation

Exit criteria:

- no new core logic is added to compatibility wrappers
- the boundary between source code, adapters, and runtime data is obvious

## Phase 2: Split Runtime From Review Material

The most important cleanup is to keep ETL states distinct.

Deliverables:

- staging output stays staging
- canonical content stays canonical
- site runtime stays site runtime
- validation output stays validation output
- large PDF, JSON, and DB artifacts stay out of git

Exit criteria:

- a newcomer can tell, from the folder name alone, whether a file is source, staging, or output
- no pipeline stage reads directly from a later stage's output by accident

## Phase 3: Make The React Pilot Adapter-Driven

The React shell should consume a stable contract, not the ETL internals.

Deliverables:

- keep the UI reading through adapter contracts
- keep the runtime JSON shape documented
- keep UI tests focused on boundaries and user flows
- avoid mutating site JSON during front-end iteration

Exit criteria:

- the UI can be iterated on without reshaping the source ETL data model
- adapter tests prove the boundary stays stable

## Phase 4: Reduce Compatibility Surface

Once the boundaries are stable, the repo can get simpler.

Deliverables:

- delete or retire old duplicate paths after the newer path is verified
- collapse repeated helper logic into shared modules
- keep only the wrappers that are still required for migration
- document any remaining compatibility path explicitly

Exit criteria:

- the repo has fewer duplicate concepts, not more
- any retained legacy path has a named reason to exist

## Phase 5: Lock In Verification

The structure is not real until it is enforced.

Deliverables:

- schema and uniqueness tests for canonical data
- import boundary checks for ETL code
- adapter boundary checks for the React pilot
- smoke checks for the smallest useful pipeline path

Exit criteria:

- the repo can prove the structure, not just describe it

## Immediate Next Steps

1. Confirm the active product scope for the new repo.
2. Decide whether the next refactor pass starts in `PDF_handle/prod/` or the React adapter layer.
3. Add the first small source-of-truth fixtures for the new data contract.
4. Introduce the first structural tests for boundary and idempotency rules.
5. Only then start moving folders or renaming paths.

## Decisions Still Open

- whether `sites/work/v2.0/` material should be imported at all
- whether the next pass should prioritize ETL hardening or frontend stabilization
- which legacy compatibility wrappers are still worth keeping
