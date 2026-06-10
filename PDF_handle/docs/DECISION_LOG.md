# Decision Log

Short log of active repository decisions.

## 2026-03-27

### Treat `PDF_handle/` as the operational project root

Reason:
- pipeline docs, scripts, prompts, and outputs already live here
- the surrounding workspace contains unrelated projects

Consequence:
- repo-local AI guidance and skills live under `PDF_handle/`

### Keep step scripts as the canonical implementation layer

Reason:
- `TOOLS/` is useful but too broad to act as the primary source of truth

Consequence:
- behavior changes should be anchored in `step_01` to `step_07` and shared utils first

### Keep `0.3` as a compatibility default for now

Reason:
- `pipeline_utils.DEFAULT_SITE_ROOT` still points to workspace `0.3`
- several scripts rely on that shared default

Consequence:
- new docs should discourage new hardcoded `0.3` assumptions
- operators should prefer explicit `--site-root`

### Add workspace-level site-root configuration before moving live folders

Reason:
- the workspace needs real structural progress, but moving `0.3` or `0.3-copy` immediately would still break active scripts

Consequence:
- `sites/site_roots.json` is now the first place to declare canonical live/work/published/sandbox roots
- pipeline defaults should resolve through that config and only then fall back to legacy version-number folders

### Adopt a single-live-root model for `0.4+`

Reason:
- numeric top-level folders are easy to create but hard to reason about
- published snapshots, sandboxes, and active roots currently blur together

Consequence:
- when `0.4` becomes active, the old live root should become a frozen published or archived snapshot
- future naming should encode state such as live, sandbox, published, and archive separately from version

### Start a Codex-first repo layer

Reason:
- the project benefits from stable docs, decision memory, and task-specific skills

Consequence:
- `AGENTS.md`, `.codex/config.toml`, docs, and `skills/` become part of normal repo hygiene

### Add local `AGENTS.override.md` files for operational sub-areas

Reason:
- `TOOLS/`, reports, staging, preservation, and run-history folders behave differently from the main project root

Consequence:
- Codex now has closer guidance for tool-layer behavior, generated artifacts, and safety boundaries
- additional overrides should now be added only when a new sub-area has materially different workflow from its parent guidance

### Split `TOOLS/` implementations by role while keeping root compatibility shims

Reason:
- the flat `TOOLS/` root made it too hard to tell runners, audits, validation, and apply logic apart

Consequence:
- canonical implementations now live under `TOOLS/runners/`, `TOOLS/audits/`, `TOOLS/validation/`, and `TOOLS/apply/`
- root-level script names remain as compatibility shims during the transition
- local subfolder overrides now carry role-specific verification expectations so changes are validated differently for runners, audits, validation, and apply paths

### Treat optional `level3` as part of Step 7 data QA

Reason:
- `level3` had started to exist as real site data, but Step 7 still behaved as if only `library`, `level1`, and `level2` were canonical

Consequence:
- Step 7 now validates `level3.json` when present in the selected site root
- Step 7 now checks that `degrees.json` and `level3.json` agree about whether `level3` exists
- browser access rules and Step 5/6 mutation flow still need separate hardening before `level3` is fully canonical end to end

### Extend optional `level3` into Step 5 and Step 6

Reason:
- `level3` could now be validated in Step 7, but it still was not part of the canonical staging and reviewed-merge lane

Consequence:
- Step 5 now stages `level3` patch/candidate artifacts when the selected site root already includes `level3.json`
- Step 6 now supports `--level3` and `--approve-level3`, plus level3 previews and validation, when both live and staged `level3` data exist
- legacy roots such as `0.3` still work unchanged because `level3` remains optional rather than globally required

### Bootstrap real `v0.4` live/work roots

Why:

- the path layer and runtime contract were already pointing toward `v0.4`, but the roots themselves were still placeholders
- keeping `v0.4` empty would leave the new contract half-real and force continued fallback behavior

Decision:

- `sites/work/v0.4/` is now bootstrapped from `0.3-copy`
- `sites/live/v0.4-current/` is now bootstrapped from `0.3`
- both roots now carry a schema-valid `level3` gate and manifest entry as the initial `0.4` baseline

### Add a shared JS site-root resolver for main operational tools

Why:

- Python had already moved toward `sites/site_roots.json`, but several JS tools still hardcoded `0.3`, `0.3-copy`, or dated sandbox snapshots
- that mismatch made `v0.4` real in one layer but still optional in another

Decision:

- `PDF_handle/TOOLS/lib/site_roots.js` now mirrors the workspace site-root contract for JS tools
- main smoke, discovery, publish, level3-build, and finalize scripts now resolve defaults from that shared helper
- `sites/work/v0.4/` and `sites/live/v0.4-current/` now also include runtime shell assets so release-oriented JS tools can treat them as full site roots

### Adopt the bounded `level3` data-lifecycle contract

Reason:

- `level3` was already present in Step 5, Step 6, Step 7, runtime data, and release packaging, but the repo still treated its lifecycle, access policy, and expansion policy as one unresolved bundle
- the next useful lock was to fix the lifecycle contract first without forcing an access-policy decision too early

Consequence:

- `level3` is now a canonical optional lane when a selected site root carries `data/level3.json` and `degrees.json` declares it
- Step 5, Step 6, and Step 7 now have one explicit answer about when `level3` is canonical and when it is simply absent
- release packaging should only ship `level3` when the selected root already satisfies the same declared-lane contract
- access policy and scope-expansion decisions remain separate follow-on items

### Adopt the bounded `level3` access-policy direction

Reason:

- the lifecycle contract was already locked, but `level3` access behavior was still review-pending even though both live/work `degrees.json` already declared a dedicated password gate
- the safest next decision was to align policy with the current declared data contract instead of broadening access early

Consequence:

- `level3` remains a dedicated `password` lane rather than inheriting `shared` access from lower degrees
- `library` remains the only `shared` lane in the current broad contract
- the `v0.4` shell is now aligned to consume the adopted policy through the same degree/auth wiring model already used in `sites/work/v0.4`
