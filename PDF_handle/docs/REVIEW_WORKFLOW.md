# Review Workflow

Staged content moves through explicit states. "The AI suggested it" and "it entered the
canon" are never the same thing.

## States

```text
suggested -> reviewed -> approved -> published
     \            \           \
      +-> rejected +-> rejected +-> rejected
```

| State | Meaning | Set by |
|-------|---------|--------|
| `suggested` | the pipeline produced it; nobody looked at it | Step 5 / `build_degree_patch_operation` (automatic) |
| `reviewed` | a human read it and did not reject it | review tooling / manual edit of the staged file |
| `approved` | explicitly cleared to merge into runtime data | review decision |
| `published` | the merge landed in a release | release flow |
| `rejected` | terminal; never merges | review decision |

## Rules

- new staged operations are stamped `suggested` automatically
- **only `approved` operations may cross the staging→runtime door** —
  `assert_operations_approved` in `PDF_handle/prod/schema/review_states.py` enforces this
  and is the door new merge code must call before `apply_degree_patches`
- operations written before this field existed have no `review_state`; merging them
  requires the explicit `allow_unreviewed_legacy=True` flag and produces warnings
- transitions outside the diagram raise `ReviewBoundaryError`; `published` and `rejected`
  are terminal

## Enforcement

- `PDF_handle/tests/test_review_workflow.py` pins the transition matrix and the door
- the offline smoke (`prod/cli/smoke_fixture.py`) refuses to merge the staging fixture
  unless it is `approved`
- the legacy approval-selector flow in Step 6 (`--approve-level1 ...`) continues to work;
  it predates these states and is the explicit-legacy path
