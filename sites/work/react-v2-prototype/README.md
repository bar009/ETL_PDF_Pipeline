# react-v2-prototype

Bounded React pilot for the site UI.

## Why this exists

The active `sites/work/v2.0` root is still the product work root, and its current readiness note explicitly keeps broad frontend redesign out of scope.

This folder gives us a safe place to test a React-based shell without mutating the current runtime, data contract, or ETL outputs.

## What this prototype proves

- React can improve maintainability of the current UI layer.
- We can separate shell, degree navigation, topic list, full article pages, and library research surfaces into components.
- We can support clean routes, metadata updates, and RTL/LTR shell direction before real data integration.
- We do not need to rewrite `degrees.json` or degree content files just to start the migration.

## Product planning

- Product definition: [`docs/PRODUCT_DEFINITION.md`](docs/PRODUCT_DEFINITION.md)
- Frontend stack decision: [`docs/FRONTEND_STACK_DECISION.md`](docs/FRONTEND_STACK_DECISION.md)
- Design system foundation: [`docs/DESIGN_SYSTEM_FOUNDATION.md`](docs/DESIGN_SYSTEM_FOUNDATION.md)
- Information architecture: [`docs/INFORMATION_ARCHITECTURE.md`](docs/INFORMATION_ARCHITECTURE.md)
- Accessibility and multilingual checklist: [`docs/ACCESSIBILITY_MULTILINGUAL_CHECKLIST.md`](docs/ACCESSIBILITY_MULTILINGUAL_CHECKLIST.md)
- SEO and metadata model: [`docs/SEO_METADATA_MODEL.md`](docs/SEO_METADATA_MODEL.md)
- Component boundary contract: [`docs/COMPONENT_BOUNDARY_CONTRACT.md`](docs/COMPONENT_BOUNDARY_CONTRACT.md)
- ETL/runtime data boundary: [`docs/ETL_RUNTIME_DATA_BOUNDARY.md`](docs/ETL_RUNTIME_DATA_BOUNDARY.md)
- Read-only adapter plan: [`docs/READ_ONLY_DATA_ADAPTER_PLAN.md`](docs/READ_ONLY_DATA_ADAPTER_PLAN.md)
- Adapter interface contract: [`docs/ADAPTER_INTERFACE_CONTRACT.md`](docs/ADAPTER_INTERFACE_CONTRACT.md)
- Prototype checkpoint: [`docs/REACT_V2_PROTOTYPE_CHECKPOINT_2026_06_03.md`](docs/REACT_V2_PROTOTYPE_CHECKPOINT_2026_06_03.md)
- Migration strategy: [`docs/MIGRATION_STRATEGY.md`](docs/MIGRATION_STRATEGY.md)
- Architecture plan: [`docs/PRODUCT_ARCHITECTURE_PLAN.md`](docs/PRODUCT_ARCHITECTURE_PLAN.md)

## Current limitations

- this is a UI pilot, not a full runtime replacement
- it uses a representative content slice, not all `v2.0` JSON
- auth is intentionally not implemented as frontend security
- multilingual content data is not connected yet; only shell direction/chrome is prototyped

## Auth boundary

The React shell may display access state, but it must not be treated as the security boundary.

Any real gated or commercial access should be enforced server-side before protected content is delivered to the browser.

## Recommended migration order

1. Keep `sites/work/v2.0/data/*.json` as the canonical frontend data contract.
2. Move only the shell and list/detail presentation into React first.
3. Port search, degree switching, and mode switching next.
4. Keep hardening routing, article pages, library, accessibility, and multilingual direction.
5. Migrate auth, Next.js, and real JSON only after the new shell is visually accepted.

## Run

```powershell
npm.cmd install
npm.cmd run dev
```

Then open `http://127.0.0.1:4174/`.

## Verify

```powershell
npm.cmd run build
npm.cmd run verify:ui
```

The UI smoke suite checks:

- serious accessibility violations with Axe
- keyboard focus through the core shell controls
- full article route rendering
- language direction switching
- route metadata, canonical URLs, and Open Graph tags
- component boundary contracts for migration
- no-mutation guard for protected ETL/runtime JSON files
- the explicit server-side auth boundary
- mobile horizontal overflow
- invalid clean-route fallback
