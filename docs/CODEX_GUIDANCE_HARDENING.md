# Codex Guidance Hardening

Note:
- The old workspace's `management/` control surface was not migrated to this repo.
  The active plan lives in `docs/STRUCTURE_ROADMAP.md`; lasting decisions live in
  `docs/DECISION_LOG.md`.
- This file remains the enduring guidance-quality reference and hardening policy doc.

Checklist and backlog for turning the current guidance layer into an official-grade Codex setup.

## Current State

We already have:

- root guidance for the whole workspace
- project-specific guidance for `PDF_handle/`
- project-specific docs for ETL, boundaries, schema, and runbook topics
- repo-scoped skills in `.agents/skills/`
- a small project-local draft-copy skill set in `PDF_handle/skills/`

This is a strong baseline.
It is not yet "perfect" by official Codex standards.

## What Official Codex Docs Emphasize

Based on OpenAI Codex docs and cookbook guidance:

1. Layer instructions.
   - Keep global defaults in `~/.codex/AGENTS.md`.
   - Keep repository expectations in repo-root `AGENTS.md`.
   - Put specialized overrides close to the work using nested `AGENTS.override.md` when needed.

2. Use project config intentionally.
   - Use `.codex/config.toml` to scope project behavior.
   - Project config overrides user config only when the project is trusted.

3. Put repo skills in official discovery paths.
   - Codex scans `.agents/skills` from the current working directory up to the repository root.
   - Skill descriptions drive implicit triggering, so scope and boundaries must be explicit.

4. Keep skills focused and progressive.
   - One job per skill.
   - Prefer instructions over scripts unless deterministic behavior is needed.
   - Use `references/` for detailed material instead of overloading `SKILL.md`.

5. Validate the guidance itself.
   - Test which instruction sources Codex loaded.
   - Test whether skill descriptions trigger correctly.
   - Use repeated prompts or eval-style checks when tuning prompts or guidance.

## Primary Gaps In The Current Workspace

### Gap 1: Canonical skill ownership is explicit, but duplicate draft copies still need cleanup

Current state:

- repo-facing skills now exist in `.agents/skills/`
- older project-local copies still exist in `PDF_handle/skills/`
- `.agents/skills/` is the canonical repo discovery path
- `PDF_handle/skills/` should be treated as draft/local-copy only

Why it matters:

- duplicate copies can still drift even after ownership is declared

Action:

- keep `.agents/skills/` canonical
- either remove `PDF_handle/skills/` later or keep it clearly marked as a draft/local-copy area

### Gap 2: Override coverage exists in the main operational sub-areas, but the guidance docs need to stay aligned with it

Current state:

- we have root guidance and project guidance
- local overrides now exist for major operational sub-areas including:
  - `PDF_handle/TOOLS/`
  - `PDF_handle/TOOLS/apply/`
  - `PDF_handle/TOOLS/audits/`
  - `PDF_handle/TOOLS/lib/`
  - `PDF_handle/TOOLS/reports/`
  - `PDF_handle/TOOLS/runners/`
  - `PDF_handle/TOOLS/specs/`
  - `PDF_handle/TOOLS/validation/`
  - `PDF_handle/preservation/`
  - `PDF_handle/pipeline_runs/`
  - `PDF_handle/qa_reports/`
  - `PDF_handle/staged_injection/`

Why it matters:

- official docs recommend placing overrides close to specialized work
- override coverage can drift if the hardening doc is not updated when local guidance is added
- adding more overrides by symmetry would be noise unless a folder truly behaves differently from its parent

Action:

- keep this file aligned with real override coverage
- add new overrides only where the workflow truly differs from the parent rules

### Gap 3: Project configs are minimal, not policy-rich

Current state:

- root and project `.codex/config.toml` files set model, reasoning effort, and Windows sandbox

Why it matters:

- official config docs highlight other common project-scoped decisions:
  - approval policy
  - sandbox mode
  - web search mode
  - personality

Action:

- decide deliberately whether to pin these values per project or inherit them from user config

### Gap 4: No explicit validation routine for guidance changes

Current state:

- docs exist, but there is no defined process for proving the guidance still works

Why it matters:

- guidance quality drifts silently when file names, paths, or workflows change

Action:

- define a repeatable validation checklist

### Gap 5: No UI metadata for custom skills

Current state:

- custom skills currently only use `SKILL.md`

Why it matters:

- official docs allow optional `agents/openai.yaml` for display metadata, invocation policy, and tool dependencies

Action:

- add `agents/openai.yaml` only for stable skills worth polishing

## Definition Of "Perfect Enough"

For this workspace, a "perfect enough" Codex setup means:

- Codex can always identify the correct instruction layer
- Codex can distinguish workspace rules from `PDF_handle` rules
- official repo-scoped skills are discoverable from the correct path
- every guidance file has a clear owner and purpose
- changes to guidance are testable, not just readable
- live-root and release naming decisions are documented as an operator workflow, not just as principles

## Improvement Backlog

### P0

- keep this hardening file as the source of truth for guidance quality work
- keep the validation-focused repo skill under `.agents/skills/`
- define a short validation checklist for guidance changes

### P1

- decide whether the draft copies in `PDF_handle/skills/` should eventually be removed after verification
- add a new `AGENTS.override.md` only if a future sub-area has materially different workflow that is not already covered by the current override map
- decide whether to pin `approval_policy`, `sandbox_mode`, `web_search`, and `personality` project-locally

### P2

- add optional `agents/openai.yaml` for mature repo skills
- create lightweight eval prompts for instruction loading and skill triggering
- add guidance around file-size or fallback filename tuning only if the current setup becomes too large

## Guidance Validation Routine

After changing `AGENTS.md`, `.codex/config.toml`, docs, or skills:

1. Ask Codex to list the instruction sources it loaded.
2. Ask Codex to summarize the active rules for the current directory.
3. Test at least one prompt that should trigger each relevant skill.
4. Test one prompt that should not trigger each skill.
5. Verify the cited file paths and commands still exist.
6. If guidance changes behavior, compare at least two prompt variants and keep only the generalized improvement.

## Suggested Next Files To Strengthen

- root `.agents/skills/` for official repo-discovered skills
- `PDF_handle/docs/RUNBOOK.md` with a concrete `0.4+` promotion workflow

## Official References

- AGENTS.md layering:
  https://developers.openai.com/codex/guides/agents-md
- Config basics:
  https://developers.openai.com/codex/config-basic
- Skills:
  https://developers.openai.com/codex/skills
- Codex prompting guide:
  https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide

Checked on 2026-03-27.
