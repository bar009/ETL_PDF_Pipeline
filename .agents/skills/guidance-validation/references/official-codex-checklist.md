# Official Codex Checklist

Condensed checklist from OpenAI Codex docs for validating repo guidance.

## AGENTS.md

- Keep reusable defaults globally and repository rules locally.
- Place specialized overrides as close to the work as possible.
- Do not assume one root file is enough for all sub-areas.

## Config

- Use `.codex/config.toml` for project-scoped behavior.
- Remember project config only loads for trusted projects.
- Decide intentionally whether to pin approval, sandbox, web search, and personality.

## Skills

- Put repo skills in `.agents/skills/`.
- Keep each skill focused on one job.
- Use precise `description` text because it drives implicit triggering.
- Prefer instructions over scripts unless deterministic behavior is needed.
- Use references for detailed material.

## Validation

- Confirm which instruction sources Codex loaded.
- Test prompts that should and should not trigger a skill.
- Re-check paths, commands, and defaults after guidance edits.
- Use repeated prompt variants or eval-style checks when refining guidance.

## Official Sources

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/config-basic
- https://developers.openai.com/codex/skills
- https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide

Checked on 2026-03-27.
