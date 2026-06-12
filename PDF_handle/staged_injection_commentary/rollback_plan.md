# Rollback Plan

Generated after Step 6 apply for work_id=None.
Copy each backup file back to its live target to undo this apply.

## Restore Commands (shell)

```bash
cp "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\content.overrides.json" "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot\data\content.overrides.json"
cp "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\library.json" "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot\data\library.json"
cp "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level1.json" "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot\data\level1.json"
cp "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level2.json" "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot\data\level2.json"
cp "C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level3.json" "C:\Users\bar16\OneDrive\Documents\etl-run-sandbox\work-english-degree-pilot\data\level3.json"
```

## Post-Rollback Validation

After restoring, run Step 7 to confirm site data integrity:

```bash
python3 PDF_handle/prod/steps/qa.py --site-root <site-root>
```

## Backup Files

- `overrides`: `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\content.overrides.json`
- `library`: `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\library.json`
- `level1`: `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level1.json`
- `level2`: `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level2.json`
- `level3`: `C:\Users\bar16\OneDrive\Documents\code-clean-start\PDF_handle\merge_backups\work-english-degree-pilot--9d25f783\2026-06-11T22-41-47+00-00\level3.json`
