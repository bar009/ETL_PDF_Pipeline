# API Reliability & Provider Runtime Spec

Status: active project spec

## מטרת המסמך

להגדיר סטנדרט פרויקטלי מלא לכל שכבת העבודה מול API חיצוני בפרויקט, כך שהמערכת תהיה לא רק חכמה מבחינת לוגיקה, אלא גם אמינה, ניתנת לחידוש, בטוחה לעצירה, ברורה לדיבוג, ומוכנה לריצות רחבות.

המסמך הזה מאחד בין שני כיוונים:

1. **API job reliability** — resume, state, interruption, summary, provenance, retry, validation.
2. **Provider runtime boundary** — שכבת גבול אחידה מול Gemini או provider עתידי, כולל parse, repair, validate, classify, retry.

זהו ה-spec הנכון לשלב הנוכחי, כי צוואר הבקבוק של המערכת כבר אינו רק ארכיטקטורת הידע, אלא האמינות התפעולית של השכבה שמדברת עם המודל.

---

# 1. רקע והחלטת כיוון

## 1.1 מצב הפרויקט כרגע

במערכת כבר קיימים:

* Build pipeline
* F1 structural/system purity
* F2 semantic review
* F3 routing review
* F4 apply/preservation
* resume אמיתי ב־F2/F3
* interrupted state מסודר ב־F2/F3
* input-hash aware skipping ב־F2/F3

כלומר, הלוגיקה המרכזית כבר בנויה טוב.

## 1.2 הבעיה האמיתית שהתגלתה

בריצות מול Gemini מתקבלות לא מעט תקלות כמו:

* invalid JSON
* malformed payloads
* 429 quota/rate limiting
* 503 / high demand
* interrupted runs
* צורך ב־resume בטוח

מכאן נובע שהצעד הנכון אינו רק "לחזק סקריפט כזה או אחר", אלא:

**לבנות סטנדרט אחיד וקשיח לשכבת העבודה מול provider חיצוני.**

## 1.3 החלטה ארכיטקטונית

החל מהשלב הזה, כל קובץ בפרויקט שעובד מול provider חיצוני צריך להתיישר סביב שני עקרונות:

1. **Job-level reliability** — state, resume, interruption, summary, provenance.
2. **Provider boundary hardening** — request, parse, repair, validate, classify, retry.

---

# 2. מטרות־על

## 2.1 מטרות פונקציונליות

המערכת צריכה לאפשר לכל job מבוסס API:

1. לעבוד על units דטרמיניסטיים וברורים.
2. לשלוח בקשות ל־provider דרך שכבה אחידה.
3. לקבל payload מנורמל או structured failure.
4. לעצור באמצע בלי לאבד שליטה.
5. להמשיך בדיוק מהנקודה הנכונה.
6. לא לדלג בטעות על unit ששונה.
7. לשמור outputs עם provenance מלא.
8. להפיק summary ברור ואמין.

## 2.2 מטרות לא־פונקציונליות

השכבה צריכה להיות:

* אמינה תחת quota / rate / overload
* בטוחה לעצירה וחידוש
* ברורה לדיבוג
* לא שבירה תחת malformed model payloads
* ניתנת לשימוש חוזר ב־F2 / F3 / F5
* מתאימה לריצות ארוכות

---

# 3. Scope

## 3.1 In Scope

כל script בפרויקט אשר:

* שולח בקשות ל־API חיצוני
* משתמש ב־LLM provider
* תלוי ב־prompt / model / provider config
* מייצר outputs שמשפיעים על שלב אחר
* עובד על units רבים לאורך זמן

### קבצים בעדיפות מיידית

* `semantic_system_purity_review.py`
* `content_routing_review.py`
* כל wrapper קיים/עתידי סביב Gemini
* F5 עתידי אם יעשה draft generation דרך provider
* כל enrichment step עתידי מבוסס LLM

## 3.2 Out of Scope כרגע

* local transforms ללא provider
* normalize / merge / link steps שאינם נוגעים ב־API
* scripts ללא state ארוך טווח מול ספק חיצוני

---

# 4. עקרונות מחייבים

## 4.1 Deterministic Unit Model

כל job חייב לעבוד על יחידת עבודה דטרמיניסטית עם מזהה יציב.

דוגמאות:

* `review_unit_id`
* paragraph unit
* entry-field unit
* routing unit

אסור שמזהה unit יהיה תלוי בסדר מקרי, timestamp, או מצב ריצה קודם.

## 4.2 Resume מבוסס הצלחה אמיתית בלבד

אסור לדלג על unit רק כי קיים output file.

דלג רק אם:

* unit הושלם בהצלחה
* נשמר state תקין
* ה־input basis תואם
* גרסת prompt/provider/config תואמת אם רלוונטי

## 4.3 Input Change Invalidates Resume

שינוי באחד מהבאים חייב לפסול reuse שגוי:

* תוכן
* shortlist
* prompt
* prompt version
* provider options
* model name
* parsing mode
* routing taxonomy relevant version
* schema version relevant

## 4.4 Interrupted הוא מצב ראשון־במעלה

`interrupted` אינו success, אינו partial success disguised, ואינו "נראה לי שכמעט סיימנו".

זו חייבת להיות ישות מפורשת ברמת run.

## 4.5 No Silent Success

אם הייתה תקלה משמעותית כמו quota exhaustion, overload, parse collapse, runtime stop או retry budget exhausted:

* אסור לסמן success כאילו הכול הושלם
* אסור להשאיר ambiguity בלוגיקה
* חייבים summary ברור עם `run_status` ו־`interrupt_reason`

הבהרה:

המערכת יכולה להכיל fallback מסומן ומבוקר, אך **אסור fallback לא מסומן** ואסור success שקט.

## 4.6 Outputs חייבים להיות Traceable

כל output משמעותי חייב לכלול provenance ברור:

* provider
* model
* prompt version/hash
* input hash
* execution timestamp
* report dir
* resume mode
* retry count אם רלוונטי
* repair applied כן/לא

## 4.7 Provider Boundary חייב להיות משותף

אין לשכפל parse/retry/repair logic בכל script מחדש.

כל interaction עם provider צריך לעבור דרך שכבת runtime משותפת.

---

# 5. הארכיטקטורה האחידה המומלצת

יש להפריד בין שתי שכבות:

## 5.1 Job Layer

השכבה העסקית של F2 / F3 / F5.

אחראית על:

* איסוף units
* בחירת input
* קריאה ל־provider runtime
* פירוש התוצאה העסקית
* כתיבת entries/findings/summary/state

## 5.2 Provider Runtime Layer

שכבת גבול אחידה מול Gemini או provider אחר.

אחראית על:

* request building
* provider invocation
* retry/backoff
* 429/503 classification
* raw payload capture
* strict parse
* repair pass
* strict re-parse
* schema validation
* normalized failure model
* telemetry/provenance metadata

---

# 6. Provider Runtime Spec

זהו החלק החדש והמחייב ביותר במסמך.

## 6.1 מטרת השכבה

לתת לכל caller אחת משתי תוצאות בלבד:

1. `validated_payload`
2. `structured_failure`

כלומר scripts כמו F2/F3 לא אמורים להתמודד ישירות עם פסיקים מיותרים, unquoted keys, או payload מעוות.

## 6.2 זרימת עבודה מחייבת

### שלב A — Build Request

השכבה בונה request קנוני שכולל:

* provider
* model
* prompt text / prompt template id
* prompt hash
* input payload
* input hash
* generation options
* timeout budget

### שלב B — Provider Call

שולחת את הבקשה ומקבלת raw response.

### שלב C — Raw Capture

שומרת metadata של raw response:

* response text present/empty
* transport status אם קיים
* provider status
* attempt number
* latency

### שלב D — Strict Parse

מנסה `json.loads` על התוכן שהתקבל.

### שלב E — Repair Pass

אם strict parse נכשל:

* מפעילה repair מבוקר
* מנסה strict parse מחדש
* מסמנת `json_repaired=true` אם עבר

### שלב F — Schema Validation

בודקת שהשדות הנדרשים קיימים ובטיפוסים הנכונים.

### שלב G — Classification

אם עדיין יש כישלון, מסווגת אותו לקטגוריה ברורה.

### שלב H — Retry / Stop

בהתאם לקטגוריה:

* retryable
* non-retryable
* quota stop
* overload stop
* runtime interrupt

### שלב I — Normalized Result

מחזירה caller-friendly object אחיד.

## 6.3 Failure Classes מחייבות

לפחות הקטגוריות הבאות חייבות להיות קיימות:

* `transport_error`
* `rate_limited`
* `quota_exhausted`
* `provider_overloaded`
* `empty_response`
* `malformed_json`
* `json_repair_failed`
* `schema_invalid`
* `bad_request`
* `local_write_failure`
* `runtime_interrupted`

## 6.4 Repair Policy

מותר repair רק בשכבת runtime המשותפת.

העקרונות:

* repair חייב להיות מסומן
* repair אינו מחליף validation
* repair failure חייב להיות גלוי
* אם payload עבר repair, זה חייב להופיע ב־provenance

## 6.5 Schema Validation Policy

לא מספיק שה־JSON parseable.

הוא חייב לעמוד ב־output schema של אותו job.

כלומר:

* required keys present
* expected types valid
* enum values valid אם נדרש
* missing critical fields = invalid

## 6.6 Runtime Metadata

כל call צריך להחזיר metadata כמו:

* provider
* model
* prompt_hash
* input_hash
* attempt_count
* retry_count
* raw_response_present
* json_parse_ok
* json_repaired
* schema_valid
* final_status
* latency_ms

---

# 7. Job Reliability Spec

## 7.1 Input Layer

כל job חייב לייצר input units דטרמיניסטיים עם:

* stable ids
* normalized source payload
* input hash
* optional shortlist hash
* optional taxonomy/config hash relevant to result

## 7.2 State Layer

לכל job חייב להיות state file נפרד.

state צריך לשמור לפחות:

* run identity
* completed units
* failed units אם רלוונטי
* interrupted reason אם רלוונטי
* input basis info
* last write timestamp
* schema version

### 7.2.1 Explicit Schema Version Fields

לא מספיק לכתוב "schema version" בצורה כללית.

כל job חייב להגדיר ולשמור במפורש:

* `state_schema_version`
* `summary_schema_version`
* `row_schema_version`

למה זה קריטי:

* מבנה state משתנה אחרת resume ישן עלול "לעבוד" אבל לעבוד עקום
* מבנה summary משתנה אחרת tooling downstream עלול לפרש שדות בצורה שגויה
* מבנה row/provenance משתנה אחרת השוואות, audits או apply logic עלולים להסתמך על payload ישן

כל mismatch בגרסאות האלה חייב לגרום לאחד מהבאים:

* explicit migration
* explicit resume rejection
* explicit fresh-run requirement

אסור ש-state ישן ייטען בשקט כאילו הוא תואם רק כי ה-JSON parseable.

## 7.3 Resume Logic

resume צריך:

* לטעון state קיים
* לדלג רק על completed-success units
* לא לדלג על interrupted/partial/failed
* להשוות input basis
* להיות חסין ל־partial writes

## 7.4 Idempotency and Rerun Policy

כל job חייב להגדיר במפורש מה קורה כשמריצים אותו שוב על אותו `report_dir`.

המדיניות חייבת לענות לפחות על השאלות הבאות:

* מתי rerun נחשב run-compatible
* מתי rerun נחשב resume-compatible
* מתי חייבים `--resume`
* מתי חייבים `--force` או equivalent
* מתי חייבים `report_dir` חדש
* מה מותר overwrite
* מה אסור overwrite

חוקי הבסיס המומלצים:

* אותו `report_dir` + אותו run basis + `--resume` -> המשך רק על pending units
* אותו `report_dir` + אותו run basis בלי `--resume` -> fail fast, אלא אם הוגדר explicit force-rerun mode
* אותו `report_dir` + run basis שונה -> fail fast כ-run incompatible
* overwrite מותר רק לקבצים שמוגדרים במפורש כ-refreshable artifacts
* completed-state artifacts לא יידרסו בשקט על ידי fresh run

בלי סעיף idempotency מפורש, כל rerun הופך להחלטה אד-hoc, וזה בדיוק מה שה-spec אמור למנוע.

## 7.5 Run Manifest Layer

לכל `report_dir` חייב להיות `run_manifest.json` קבוע.

ה-manifest אינו summary.
ה-summary אומר מה קרה.
ה-manifest אומר עם מה בכלל יצאת לקרב.

`run_manifest.json` צריך לכלול לפחות:

* `script_name`
* `script_version`
* `command_line_args`
* `provider`
* `model`
* `prompt_hash` או `prompt_basis`
* `input_hash_basis`
* `shortlist_basis` אם רלוונטי
* `taxonomy_or_config_basis` אם רלוונטי
* `state_schema_version`
* `summary_schema_version`
* `row_schema_version`
* `started_at`
* `report_dir`
* `resume_requested`

אופציונלית, אבל מומלצת מאוד:

* `finished_at`
* `final_run_status`
* `interrupt_reason`

## 7.6 Summary Layer

summary אינו state.
state אינו summary.
manifest אינו summary.

summary צריך להיות human-readable וגם machine-usable.

## 7.7 Validation Before Completion

unit לא ייחשב completed לפני ש:

* provider result תקין
* output payload תקין
* write הצליח
* state update הצליח

---

# 8. סטנדרט כתיבה בטוחה (Atomic Write Spec)

זהו פער ממשי שזוהה בפרויקט, ולכן הוא נכנס כדרישה מפורשת.

## 8.1 הבעיה

כתיבה ישירה לקובצי JSON/TXT יוצרת סיכון ל:

* corruption במקרה interrupt
* truncated files
* state לא עקבי
* summary חלקי שנראה כאילו הוא truth

## 8.2 החלטה

כל כתיבת state/summary/entries/findings קריטיים צריכה להשתמש ב־safe write helper.

## 8.3 Helper משותף נדרש

יש להוציא helper אחיד כגון:

* `atomic_write_text(...)`
* `atomic_write_json(...)`
* `safe_json_write(...)`

## 8.4 דרישות ההתנהגות

* כתיבה ל־temp file
* flush / close
* rename atomic ככל שהפלטפורמה מאפשרת
* invalid JSON לא יישמר כקובץ סופי
* optional backup/rollback אם נדרש

## 8.5 קבצים שחייבים לעבור atomic write

* state files
* summary files
* entries files
* findings files
* manifest files

---

# 9. סטנדרט Summary מחייב

זהו פער נוסף שזוהה וצריך להיסגר.

כל job API צריך לייצר `*_summary.json` שיכלול לפחות:

* `run_status`
* `started_at`
* `finished_at`
* `elapsed_seconds`
* `report_dir`
* `resume_mode`
* `provider`
* `model`
* `total_units`
* `completed_units`
* `skipped_units`
* `failed_units`
* `pending_units`
* `interrupted_units_pending`
* `interrupt_reason` אם קיים
* `input_hash_basis`
* `prompt_hash` או `prompt_basis`
* `taxonomy_or_config_hash` אם רלוונטי
* `state_schema_version`
* `summary_schema_version`
* `row_schema_version`
* `run_manifest_path`
* `repair_applied_count`
* `malformed_json_count`
* `rate_limit_count`
* `overload_count`

## 9.1 Human Report

בנוסף, צריך להיות גם `*_report.md` ברור שעונה על:

* מה רץ?
* על איזה input?
* כמה הושלמו?
* כמה דולגו?
* למה נעצר אם נעצר?
* מה next step המומלץ?

---

# 10. סטנדרט Provenance ברמת Unit

זהו פער שלישי שזוהה.

כל row ברמת unit צריך לשמור לפחות:

* unit id
* source metadata
* input hash
* `row_schema_version`
* provider
* model
* prompt hash/version
* runtime config hash אם רלוונטי
* attempt count
* retry count
* raw_response_present
* json_parse_ok
* json_repaired
* schema_valid
* final_provider_status
* unit processing status
* warnings/errors
* processed_at

## 10.1 למה זה קריטי

בלי זה, קשה מאוד להבין:

* איפה המודל מתבלבל
* איזה fields בעייתיים יותר
* האם prompt מסוים מייצר יותר malformed JSON
* האם repair באמת עוזר

---

# 11. Checklist מלא לכל קובץ API

להלן checklist מחייב שיש לעבור עליו עבור כל script רלוונטי.

## 11.1 Interface / CLI

האם יש:

* `--report-dir`
* `--resume`
* `--max-runtime-seconds`
* `--max-units` או limiting mechanism
* `--provider`
* `--model`
* `--verbose`
* `--dry-run` אם רלוונטי

## 11.2 Unit Identity

האם לכל unit יש:

* id יציב
* deterministic serialization
* source metadata
* stable ordering

## 11.3 Hashing Strategy

האם hash basis מכסה:

* content
* shortlist
* prompt
* provider/model settings
* taxonomy/config relevant version
* output schema version אם משפיע

## 11.4 Schema Versioning

האם קיימים במפורש:

* `state_schema_version`
* `summary_schema_version`
* `row_schema_version`

והאם mismatch בהם פוסל resume או מפעיל migration מפורש?

## 11.5 Resume Logic

האם resume:

* state-based
* success-only skip
* hash-aware
* resilient to interrupted writes
* לא נשען על file existence בלבד

## 11.6 Run Manifest

האם לכל `report_dir` יש `run_manifest.json` שמכיל:

* script name/version
* command line args
* provider/model
* prompt/input/config basis
* schema versions
* `started_at`

## 11.7 Idempotency Policy

האם הקובץ מגדיר ומממש:

* same-report-dir rerun behavior
* compatible resume rules
* incompatible rerun rejection
* overwrite policy
* force-rerun policy אם קיים

## 11.8 Provider Boundary Usage

האם הקובץ משתמש ב־runtime boundary משותף ולא בלוגיקה מפוזרת?

## 11.9 Error Classification

האם יש הפרדה בין:

* retryable
* non-retryable
* quota
* overload
* malformed payload
* schema invalid
* local failure

## 11.10 Output Integrity

האם כל write קריטי הוא atomic או safe?

## 11.11 Summary Quality

האם summary עומד בסטנדרט של סעיף 9?

## 11.12 Provenance Quality

האם row-level provenance עומד בסטנדרט של סעיף 10?

## 11.13 Runtime Validation

האם הקובץ עבר smoke test חי?

---

# 12. מטריצת בדיקות חובה

כל script API חייב לעבור לפחות את המטריצה הבאה.

## 12.1 Fresh Run Test

מטרה: לוודא ריצה חדשה תקינה.

בדיקות:

* report dir חדש
* outputs תקינים
* state תקין
* summary תקין

## 12.2 Resume After Runtime Stop

מטרה: לעצור בכוונה עם `--max-runtime-seconds`.

בדיקות:

* `run_status = interrupted`
* pending נשמר נכון
* rerun עם `--resume` ממשיך בדיוק על החלק הנכון

## 12.3 Resume After 429

בדיקות:

* interrupt reason ברור
* no silent success
* rerun safe

## 12.4 Resume After 503 / High Demand

בדיקות:

* retry budget מנוהל נכון
* interrupt reason ברור
* state עקבי
* rerun safe

## 12.5 Input Change Invalidates Resume

לשנות אחד מאלה:

* content
* shortlist
* prompt
* model/config

ולוודא שה-unit הרלוונטי לא מדולג בטעות.

## 12.6 Malformed JSON Test

מטרה: לבדוק strict parse → repair → validate → classify.

בדיקות:

* malformed_json מזוהה
* repair מופעל אם מתאים
* repair success/failure מסומן
* fallback אינו שקט

## 12.7 Partial Output Corruption Test

מטרה: לדמות state/output חלקי.

בדיקות:

* invalid state לא מתקבל כ-truth
* failure ברור
* resume לא נשען על זבל חצי כתוב

## 12.8 Deterministic Ordering Test

אותו input → אותם unit ids → אותו ordering.

## 12.9 Batch Limit Test

אם יש `--max-units` או equivalent:

* subset run תקין
* resume אחרי subset לא יוצר skip שגוי

---

# 13. ביקורת ייעודית על הקבצים הנוכחיים

## 13.1 `semantic_system_purity_review.py`

### מה כבר טוב

* יש resume אמיתי
* יש state נפרד
* יש input-hash aware skipping
* יש interrupted summary/state
* יש stop handling על quota / overload / max runtime

### מה חסר מול ה-spec

* provider runtime boundary אחיד עדיין לא מופרד מספיק
* malformed JSON handling צריך להיות חלק משכבת runtime משותפת
* atomic write עדיין חסר
* `run_manifest.json` ייעודי עדיין חסר
* explicit `state_schema_version` / `summary_schema_version` / `row_schema_version` עדיין חסרים
* idempotency policy מפורשת עדיין לא מוגדרת ברמת rerun behavior
* summary עדיין לא ברמת הסטנדרט המלא
* row-level provenance עדיין חלקי
* runtime validation חיה עדיין נדרשת

### ציון מוכנות נוכחי

מוכן טוב לפיילוט רחב, אך עדיין לא מוכן להיחשב fully hardened.

## 13.2 `content_routing_review.py`

### מה כבר טוב

* יש resume אמיתי
* יש state נפרד
* יש stop conditions מסודרים
* interrupted state/summary קיים

### מה חסר מול ה-spec

* provider boundary משותף
* atomic write
* `run_manifest.json` ייעודי עדיין חסר
* explicit `state_schema_version` / `summary_schema_version` / `row_schema_version` עדיין חסרים
* idempotency policy מפורשת עדיין לא מוגדרת ברמת rerun behavior
* summary enrichment
* provenance enrichment
* malformed payload handling תחת runtime layer אחיד
* runtime validation חיה

### ציון מוכנות נוכחי

קרוב מאוד לריצת batch רחבה, אך דורש hardening לפי הסעיפים לעיל.

## 13.3 `pipeline_utils.py`

### מצב נוכחי

כרגע helpers של write כותבים ישירות לקובץ.

### פער מול ה-spec

* אין atomic write
* אין safe_json_write מחייב

### החלטה

זהו יעד hardening בעדיפות גבוהה מאוד.

---

# 14. Inventory & Audit Table Spec

יש לבצע שלב inventory רוחבי על כל קובצי ה־API.

## 14.1 טבלת audit נדרשת

עמודות מומלצות:

* file name
* purpose
* provider
* unit type
* report dir outputs
* schema versioning
* run manifest
* idempotency policy
* uses shared runtime boundary
* resume support
* hash basis coverage
* retry handling
* interruption handling
* atomic write support
* summary completeness
* provenance completeness
* runtime validated
* readiness score
* action needed

## 14.2 מטרת הטבלה

להפוך את ה-spec לכלי עבודה ממשי, ולא למסמך יפה שמעלה אבק מכובד.

---

# 15. תוכנית עבודה פרקטית

זה סדר העבודה המומלץ.

## שלב A — לקבע את המסמך כ־Spec רשמי

לשמור את ה-spec תחת `PDF_handle/TOOLS/` או מיקום שקוף אחר בריפו.

## שלב B — Inventory

למפות את כל הקבצים בפרויקט שנוגעים ב־API.

## שלב C — Audit Table

למלא טבלת audit לפי סעיף 14.

## שלב D — Schema + Manifest Contract

להגדיר ולהטמיע:

* `state_schema_version`
* `summary_schema_version`
* `row_schema_version`
* `run_manifest.json`
* חוקי rerun/idempotency מפורשים

## שלב E — Safe Write Helpers

להוציא:

* `atomic_write_text`
* `atomic_write_json`
* `safe_json_write`

וליישם על state/summary/entries/findings.

## שלב F — Shared Runtime Extraction

להוציא שכבת runtime משותפת עבור:

* provider invocation
* parse
* repair
* validation
* retry
* classification
* metadata capture

## שלב G — לחבר F2/F3 לשכבה החדשה

לא לכתוב עוד לוגיקה כפולה.

## שלב H — Summary + Provenance Hardening

להרחיב F2/F3 כך שיעמדו בסטנדרט של סעיפים 9–10.

הסיבה לסדר הזה פשוטה:

אם metadata ותוצרי provenance אמורים להיוולד משכבת runtime תקינה, עדיף לחלץ קודם את boundary המשותף ורק אחר כך להרחיב סביבו summary ו־unit provenance.

## שלב I — Runtime Validation Matrix

להריץ בפועל את מטריצת הבדיקות מסעיף 12 על F2/F3.

## שלב J — Wider Pilot

אחרי hardening ו-validation:

* Core 24
* ועוד batch רחב יותר
* sandbox preservation בלבד

## שלב K — רק אז Full Run

רק אחרי שהשכבה התפעולית מוקשחת, ניתן לחשוב על full-site run ברמה בטוחה.

---

# 16. Definition of Done

script API ייחשב "מוכן" רק אם:

1. יש לו unit identity יציב
2. יש לו hash basis נכון
3. יש לו resume תקין
4. יש לו `state_schema_version`, `summary_schema_version`, ו־`row_schema_version` מפורשים
5. יש לו `run_manifest.json` תקין
6. יש לו idempotency/rerun policy מפורשת
7. יש לו interrupted model ברור
8. הוא משתמש ב־shared provider runtime or approved equivalent
9. יש לו malformed JSON handling מסודר
10. יש לו atomic write על outputs קריטיים
11. יש לו summary מלא לפי ה-spec
12. יש לו row-level provenance מלא לפי ה-spec
13. עבר smoke test חי
14. עבר לפחות interruption/resume test אחד
15. אינו עושה silent success

---

# 17. מסקנה

השלב הנכון לפרויקט עכשיו אינו "עוד פיצ'רים", אלא hardening שיטתי של שכבת ה־API וה־provider runtime.

במילים פשוטות:

המערכת כבר יודעת **מה לחשוב**.
עכשיו היא צריכה לדעת **איך לרוץ בעולם האמיתי בלי להתפרק מכל פסיק עקום של Gemini**.

לכן זה ה-spec המומלץ והנכון:

* לקבע סטנדרט reliability לכל API job
* להקשיח שכבת provider boundary משותפת
* להוסיף atomic write
* להרחיב summary/provenance
* לבצע inventory + audit table
* להריץ validation matrix
* ורק אז להתקדם לפיילוט רחב ול־full run

זה נותן לך מסלול ברור, הנדסי, וניתן לביצוע — בלי לקפוץ ישר לים עם מערכת תפעולית חצי מוקשחת.
