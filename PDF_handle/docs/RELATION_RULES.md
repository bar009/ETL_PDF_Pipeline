# Relation Rules

Guide for topic relations and movement rules across `library`, `level1`, and `level2`.

## Relation Buckets

- `prior`
- `companion`
- `deeper`

## Intended Meanings

### `prior`

Use for material that should normally be understood first.
Do not use it for weak thematic similarity.

### `companion`

Use for peer or adjacent material that helps understanding without implying strict sequence.

### `deeper`

Use for follow-on or more advanced material that extends the current topic.

## Boundary Rules

- avoid cross-degree `prior` links that flatten the degree boundary
- prefer `companion` when the relation is real but not sequential
- use routing and preservation decisions when material should move out of its current lane
- do not create relations only because two entries share a few surface keywords

## Audit Expectations

`audit_knowledge_flow.py` is the main warn-first check for:

- missing relation buckets
- duplicate or weak links
- branching problems
- imbalance between hub links and concrete instructional flow

## Practical Rule Of Thumb

If a relation changes the teaching order, treat it as a high-scrutiny decision.
If a relation only improves navigation, treat it as a lower-risk companion decision.
