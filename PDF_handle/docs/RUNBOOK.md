# Runbook

Operational quick-reference for common `PDF_handle/` tasks.

## Preprocess A New Book

```bash
python3.11 PDF_handle/TOOLS/run_preprocess_01_04.py --book "<book>" --provider gemini --model gemini-2.5-flash
```

## Run Post-Merge Steps

```bash
python3.11 PDF_handle/TOOLS/run_postmerge_05_07.py --site-root 0.3
```

## Audit Sparse Entries

```bash
python3.11 PDF_handle/TOOLS/audit_sparse_entries.py --site-root 0.3
```

## Audit Degree Boundaries

```bash
python3.11 PDF_handle/TOOLS/audit_degree_classification.py --site-root 0.3 --degrees level1
```

## Run Semantic Boundary Review

```bash
python3.11 PDF_handle/TOOLS/semantic_system_purity_review.py --site-root 0.3 --provider heuristic
```

## Run Routing Review On Existing F2 Output

```bash
python3.11 PDF_handle/TOOLS/content_routing_review.py --f2-report-dir PDF_handle/TOOLS/reports/semantic_system_purity_review/0.3/<timestamp> --provider heuristic
```

## Safe Apply Planning

```bash
python3.11 PDF_handle/TOOLS/content_apply_engine.py --f3-report-dir PDF_handle/TOOLS/reports/content_routing_review/0.3/<timestamp> --mode plan
```

## Operator Rules

- prefer explicit `--site-root`
- prefer sandbox copies for experimental runs
- do not treat audit output as already-applied content
- capture new path decisions in `docs/DECISION_LOG.md`
