# NotebookLM Validation

NotebookLM-related validation work is part of the evidence and calibration layer, not the canonical ETL path.

## Purpose

Use NotebookLM validation work to:

- compare coverage assumptions
- inspect generated summaries or gaps
- test whether topic boundaries hold up under another reading surface
- gather curated samples for decision support

## Storage Rule

- stable guidance belongs in `docs/`
- experiment-specific output belongs in `experiments/` or generated report folders
- do not let NotebookLM notes become implicit schema truth

## Practical Boundary

NotebookLM findings may inform:

- queue building
- boundary review
- sparse-entry prioritization
- operator confidence

NotebookLM findings should not automatically:

- rewrite canonical site JSON
- replace Step 5 or Step 6 review artifacts
- redefine the degree partition on their own

## Follow-Up Rule

When a NotebookLM insight matters, translate it into one of:

- a decision log entry
- a queue or report artifact
- a mapping rule
- a validation rule

That keeps experiments from turning into undocumented policy.
