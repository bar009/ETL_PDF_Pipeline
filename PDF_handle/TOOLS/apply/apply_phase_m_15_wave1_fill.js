/**
 * apply_phase_m_15_wave1_fill.js
 *
 * Wave 1 topic expansion — adds 3 new Level 2 entries and 3 new Level 3 entries
 * derived from NotebookLM subjects and phase_m_13_breadth_backlog.
 *
 * Level 2 new candidates (from notebooklm_subjects.md):
 *   - level2-winding-stairs-as-ascent-process
 *   - level2-jachin-boaz-threshold-and-symbol-structure
 *   - level2-geometry-and-letter-g-intellectual-center
 *
 * Level 3 new candidates (from phase_m_13_breadth_backlog):
 *   - level3-charge-and-duty-framework
 *   - level3-burial-honor-and-memorial-structure
 *   - level3-third-degree-tracing-board-map
 *
 * Usage:
 *   node PDF_handle/TOOLS/apply_phase_m_15_wave1_fill.js [--dry-run] [--site-root <path>]
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m15_wave1_fill";
const DEFAULT_SITE_ROOT = path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_15_wave1_fill_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_15_wave1_fill_validation.json");

const FORBIDDEN_LEVEL3_PATTERNS = [
  { label: "royal_arch", pattern: /royal arch|קשת מלכותית|רויאל ארץ׳/iu },
  { label: "return_from_babylon", pattern: /babylon|בבל/iu },
  { label: "hidden_vault", pattern: /vault|קמרון|אוצר נסתר/iu },
];

const FORBIDDEN_LEVEL2_PATTERNS = [
  { label: "master_mason_content", pattern: /master mason/iu },
  { label: "raising_body", pattern: /הקמה.*גופה|raising.*body/iu },
];

// ─────────────────────────────────────────────────────────
// New Level 2 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL2_ENTRIES = [
  {
    title: "מדרגות לולייניות כתהליך עלייה ולמידה",
    slug: "level2-winding-stairs-as-ascent-process",
    type: "topic",
    level2_content_type: "process_explanation",
    level2_type: "process",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "process",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "fc_learning_structure",
    parent_topic: null,
    aliases: ["מדרגות לולייניות", "Winding Stairs", "תהליך העלייה של דרגה שנייה"],
    keywords: ["מדרגות לולייניות", "3-5-7", "עלייה שכלית", "חושים", "אמנויות ומדעים", "דרגה 2"],
    related_topics: {
      prior: ["level2-lodge-as-learning-structure"],
      companion: ["level2-geometry-and-letter-g-intellectual-center", "level2-from-discipline-to-inner-formation"],
      deeper: ["level2-layers-of-the-tracing-board"],
    },
    short_summary:
      "בדרגה השנייה המדרגות הלולייניות אינן רק מעבר פיזי אלא תהליך עלייה מובנה. שלושה שלבים, חמישה חושים וסדרי אדריכלות, ושבע אמנויות ומדעים מרכיבים יחד מסגרת שבה כל קבוצה מוסיפה שכבת הבנה אחרת לקראת הלשכה האמצעית.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, שלוש קבוצות המדרגות מתארות שלושה סוגים שונים של ידע. השלוש הראשונות מייצגות שלבי חיים: נעורים, בגרות וזקנה. החמש שאחריהן מייצגות את החושים ואת סדרי האדריכלות. השבע האחרונות מייצגות את האמנויות הליברליות. העלייה לא תולשת את הלומד ממקומו אלא בונה עליו שכבה אחרי שכבה.",
      symbolic:
        "בקריאה הסמלית, 3-5-7 מהווים מספרים בעלי משמעות עמוקה בבנייה החופשית. השלוש מחזירה אל מקורות, החמש פותחת את השחקן כסובייקט חושי, והשבע מרחיבה אל הקוסמוס של הידע האנושי. ביחד הן מציגות עלייה לא מקרית: כל שלב שואל שאלה שהשלב הבא עונה עליה.",
      advanced:
        "בקריאה המבנית של דרגה 2, שאלת הליבה היא: כיצד הדרגה מארגנת את המסע הלימודי של חבר-הבונה? התשובה נמצאת במבנה 3-5-7: לא רק כמה מדרגות יש, אלא שכל קבוצה מוסיפה ממד חדש לאדם — מציאות כרונולוגית, מציאות חושית, מציאות שכלית. הלשכה האמצעית היא לא רק יעד פיזי אלא שכר שהוא ידע; העלייה כולה מגדירה מה פירוש ה'ידע' בדרגה זו.",
    },
    full_summary:
      "המדרגות הלולייניות הן הכלי המרכזי שבאמצעותו דרגת חבר-הבונה מארגנת את רעיון הלמידה כתהליך מדורג ולא כמסר אחד. שלוש המדרגות הראשונות מייצגות את שלבי החיים: נעורים, בגרות וזקנה. הן מזכירות שהאדם הלומד הוא אדם עם זמן, לא יצור נטול היסטוריה. חמש המדרגות האמצעיות מייצגות חמישה חושים — שמיעה, ראייה ומישוש חשובים במיוחד — ואת חמשת סדרי האדריכלות. כאן הבונה-הלומד מתחיל לקרוא את העולם כסובייקט חושי, לא רק כחוקר מוסרי. שבע המדרגות האחרונות מייצגות את שבע האמנויות הליברליות: דקדוק, רטוריקה, לוגיקה, אריתמטיקה, גיאומטריה, מוזיקה ואסטרונומיה. כאן הגיאומטריה בולטת כמדע הבסיסי שעליו מושתת כל שאר הידע.\n\nהעלייה כולה מובנית לכיוון הלשכה האמצעית, שבה ממתין השכר: לא מטבע אלא ידע. שכר תירס, יין ושמן מסמל הזנה, רענון ושמחה — מה שמלמד שהפרס על הלימוד הוא עצם מה שלמדת. זו הבחנה חשובה בין מסגרת הלמידה של דרגה שנייה לזו של דרגה ראשונה: בדרגה ראשונה הדגש על ההכנה והכניסה; כאן הדגש על מה שהאדם מסוגל לעלות אל תוכו ולקבל כשכר רוחני-שכלי.\n\nהמדרגות הלולייניות אינן עומדות בפני עצמן: הן קשורות ללשכה כמערכת חינוכית, ללוח הדרגה כמפת קריאה, ולמרכז השכלי של הגיאומטריה והאות G. הקריאה כמכלול מגלה שדרגת חבר-הבונה נבנתה סביב שאלת הידע: לא רק 'מה נכון' אלא 'כיצד עולים מן הנעלם אל הנגלה'.",
    practical_elements: [
      "לקרוא את שלוש קבוצות המדרגות כשלושה שאלות: מי אתה בזמן? כיצד אתה קולט? מה אתה מבין?",
      "לקשר את יעד הלשכה האמצעית לשאלה: מה המשמעות של 'שכר' כאשר השכר הוא ידע?",
    ],
    symbolic_meaning:
      "המשמעות הסמלית של המדרגות הלולייניות נמצאת במבנה 3-5-7 עצמו: לא מספרים אקראיים אלא שלושה ממדים של אנושיות. הזמן (3), החוויה החושית (5), והידע הכולל (7) יחד מגדירים מה פירושו להיות אדם לומד. כאשר עולים את המדרגות הסמל הזה מתגשם כתהליך ממשי של גדילה.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שלמידה אמיתית אינה צבירה אלא עלייה. 3-5-7 מלמדים שכל שלב בונה על קודמו, שהעלייה אינה רק מטפורה אלא מסלול שיש לו תחנות, ושהיעד — הלשכה האמצעית — מתגלה רק למי שסיים את העלייה.",
    tradition_notes: [
      "הערך נשען על חומר חבר-בונה בלבד, בעיקר מתאור מעוף המדרגות הלולייניות בפולחן.",
      "3-5-7 הם מספרים מרכזיים בבנייה החופשית המסורתית ולהם נקשרת פרשנות מגוונת.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן דרגה שלישית: הלשכה האמצעית שייכת לחבר-בונה בלבד.",
      "אין לבלבל בין הגיאומטריה כמדע לימודי כאן לבין המסגרת הטכנית של מלאכת בניין.",
    ],
    source_notes: [
      "מקור עיקרי: flight-of-winding-stairs (Blue Lodge Ritual Reference Guide 2021, section 0049)",
      "מקור תומך: fellow-craft-degree (Blue Lodge Ritual Reference Guide 2021, section 0042)",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0049-flight-of-winding-stairs",
      "blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level2-lodge-as-learning-structure", degree: "level2" },
      { slug: "level2-geometry-and-letter-g-intellectual-center", degree: "level2" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },

  {
    title: "יכין ובועז כמבנה סף וסמלות",
    slug: "level2-jachin-boaz-threshold-and-symbol-structure",
    type: "topic",
    level2_content_type: "symbol_relationship_analysis",
    level2_type: "symbol",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "symbol",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "symbols_and_architecture",
    parent_topic: null,
    aliases: ["יכין ובועז", "Jachin and Boaz", "שני עמודי המקדש", "עמודי הכניסה"],
    keywords: ["יכין", "בועז", "עמודים", "כותרות", "גלובוסים", "דרגה 2"],
    related_topics: {
      prior: ["level2-threshold-officers-and-candidate-structure"],
      companion: ["level2-light-placement-and-orientation", "level2-floor-frame-and-center-system"],
      deeper: ["level2-layers-of-the-tracing-board"],
    },
    short_summary:
      "בדרגה השנייה שני העמודים יכין ובועז אינם רק אלמנטים אדריכליים בכניסה למקדש. יחד עם כותרותיהם, עיטוריהן וגלובוסיהן הם מרכיבים מערכת סמלית שמגדירה את ה'סף' של הדרגה: ביסוס וכוח, שפע ואחדות, טווח עולמי ומשמעות.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, שני העמודים נחצבים ויצוקים ונושאים שמות: יכין מימין — 'הוא יבסס', ובועז משמאל — 'בכוח'. יחד הם אומרים שהבית הזה עומד בכוח ובביסוס. כותרותיהם מעוטרות ברשת (אחדות), שושן (שלום) ורימונים (שפע), וגלובוסים שמימיים וארציים מדגישים שעבודת הלשכה חובקת כל.",
      symbolic:
        "בקריאה הסמלית, יכין ובועז אינם רק שמות. שני עמוד מסמל עיקרון: ביסוס וכוח מחברים לשאלה 'על מה עומד הבית?' בכניסה, לפני שהחבר-הבונה נכנס ללמוד, הוא עומד מול שני עיקרונות — כוח שמצמיח ותמיכה שמיסדת. עיטורי הכותרות מוסיפים שכבת משמעות: שלום, אחדות ושפע הם הפרי שצמח בין שני הביסוסים.",
      advanced:
        "בקריאה המבנית של דרגה 2, שני העמודים הם דוגמה מובהקת לאיך הדרגה בונה מערכת סמלית מרכיבים אדריכליים. עמוד אחד לא מספיק: רק השניים ביחד יוצרים מבנה. אחדות, ריבוי, כוח ויסוד עובדים בדיאלוג. הגלובוסים מרחיבים את מרחב הדרגה לכלל היקום. כך מה שנראה כקישוט הכניסה הוא בעצם הצהרה על אופי הלשכה: אוניברסלית, מבוססת, ושלמה.",
    },
    full_summary:
      "שני העמודים הוצבו בכניסה לאולם המקדש של שלמה על ידי חירם (האומן, לא האדריכל): יכין מימין ובועז משמאל. יכין — 'הוא יבסס' — מסמל את העקרון הכיסוני, הביסוס שמאפשר לבניין לעמוד. בועז — 'בכוח' — מסמל את הכוח המניע. ביחד שני שמותיהם יוצרים משפט: 'בכוח יבוסס'. זהו לא סתם כותרת; זו הצהרת ייעוד של הלשכה עצמה.\n\nכותרות שני העמודים מעוטרות בשלושה סוגי עיטורים. הרשת מסמלת אחדות בין הבנאים; השושן מסמל שלום וטוהר; הרימונים — בשל שפע זרעיהם — מסמלים שפע. בראש הכותרות מונחים שני גלובוסים: אחד שמימי (המייצג את הגרמים השמימיים ואת גבולות היקום הרוחני) ואחד ארצי (המייצג את הכדור הארץ ואת תפוצת הבנייה החופשית). גלובוסים אלו מגדירים את הלשכה כמרחב שאינו מוגבל למקום אחד אלא חובק את כל הבריאה.\n\nמבחינת מערכת הסמלים של הדרגה השנייה, שני העמודים פועלים כ'מסגרת כניסה': לפני שהחבר-הבונה עולה את המדרגות הלולייניות ולפני שהוא זוכה בשכר הלשכה האמצעית, הוא עוצר בכניסה ורואה שני עמודים שמסבירים לו את עקרון הלשכה. הכניסה עצמה הופכת לשיעור. בנוסף, העמודים מחברים לשאלות של לשכה כמרחב: לא רק מי יושב בה ומה יש בה, אלא גם מה שומר עליה מהצד.",
    practical_elements: [
      "לשאול: מה שני עמודי יכין ובועז אומרים על אופי הלשכה, לא רק על בית המקדש ההיסטורי?",
      "לשים לב להבחנה בין 'עמוד אחד' (עיקרון בודד) לבין 'שני עמודים' (דיאלוג עיקרוני).",
    ],
    symbolic_meaning:
      "המשמעות הסמלית של יכין ובועז נבנית מן הדיאלוג ביניהם. לא עמוד אחד חזק, אלא שניים שמשלימים: ביסוס כנגד כוח, שמאל מול ימין, עמידה יציבה מול תנועה. כותרות העיטורים ממשיכות את הדיאלוג: שלום, אחדות ושפע אינם מסרים נפרדים אלא פירות של ה'ביחד' שהעמודים מייצגים.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שכניסה אינה רק דלת: היא הצהרה. יכין ובועז מלמדים שמה שמקדים את הלמידה — הסף, הכניסה, העמידה לפני — הוא חלק ממנה. בכניסה לדרגה נקבעים מראש שני עקרונות: ביסוס וכוח.",
    tradition_notes: [
      "יכין ובועז מוזכרים בספר מלכים א' ז' ומקבילים בדברי הימים ב' ג'.",
      "הפרשנות הבנייה-חופשית של השמות (ביסוס, כוח) היא מסורתית ולא רק פשוטת המקרא.",
    ],
    caution_notes: [
      "אין לבלבל בין עמוד 'בועז' לאישיות ספר רות — מדובר בשם עמוד בלבד בהקשר הבנייה החופשית.",
      "אין לגלוש לתוכן על הקמת גוף חירם, שיכיל את הדרגה השלישית.",
    ],
    source_notes: [
      "מקור עיקרי: fellow-craft-degree (Blue Lodge Ritual Reference Guide 2021, section 0042)",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level2-threshold-officers-and-candidate-structure", degree: "level2" },
      { slug: "level2-floor-frame-and-center-system", degree: "level2" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },

  {
    title: "גיאומטריה והאות G כמרכז השכלי של הדרגה השנייה",
    slug: "level2-geometry-and-letter-g-intellectual-center",
    type: "topic",
    level2_content_type: "structural_framework",
    level2_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "concept",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "fc_intellectual_framework",
    parent_topic: null,
    aliases: ["האות G", "גיאומטריה בדרגה שנייה", "Geometry and the Letter G", "מדע הגיאומטריה"],
    keywords: ["גיאומטריה", "האות G", "שבע אמנויות", "אסטרונומיה", "דרגה 2", "מרכז שכלי"],
    related_topics: {
      prior: ["level2-winding-stairs-as-ascent-process", "level2-lodge-as-learning-structure"],
      companion: ["level2-layers-of-the-tracing-board"],
      deeper: [],
    },
    short_summary:
      "בדרגה השנייה הגיאומטריה היא מלכת המדעים: הבסיס שעליו מושתתת הבנייה החופשית כולה. האות G התלויה בלשכה מייצגת גם אלוהים (God) וגם גיאומטריה (Geometry), ובכך היא מאחדת את שתי השאלות הגדולות של הדרגה: הידע השכלי ומעמד האלוהות.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, האות G תלויה בלשכה מעל כיסא הנשיא ונקראת כמזכירה כפולה. G = God (אלוהים): כל בנייה מוסרית מכוונת לבורא. G = Geometry: מדע הגיאומטריה הוא הבסיס של כל אמנות ומלאכה. שאלת חבר-הבונה היא: מה הקשר בין שני המשמעים האלה?",
      symbolic:
        "בקריאה הסמלית, הגיאומטריה איננה רק מתמטיקה. היא 'הבסיס הראשוני לכל אמנות'. המספר הגיאומטרי המרכזי — נקודה, קו, שטח, גוף — מייצג את ארבעת ממדי המציאות. כאשר G תולה בלשכה, היא שואלת את הבונה לא 'האם אתה עובד?' אלא 'האם אתה מבין את החוקיות שמאחורי העבודה?'",
      advanced:
        "בקריאה המבנית של דרגה 2, G ממוקמת בלשכה כ'מרכז מארגן' — בדיוק כמו שנקודה בתוך עיגול מגדירה מרחב. הגיאומטריה היא ה'מדע החמישי' בין שבע האמנויות הליברליות, אך בבנייה החופשית היא עולה למעלה לכולן. זה לא צירוף מקרים: חמישה הוא גם מספר החושים וגם מספר הכוכב המחומש שמופיע בסמלי הלשכה. G כמרכז שכלי מלמד שהדרגה השנייה בנויה סביב שאלת ה'סדר הנסתר מאחורי הנראה'.",
    },
    full_summary:
      "הגיאומטריה מוגדרת בבנייה החופשית כ'מדע העילאי' שממנו נגזרות כל האמנויות האחרות. בין שבע האמנויות הליברליות — דקדוק, רטוריקה, לוגיקה, אריתמטיקה, גיאומטריה, מוזיקה ואסטרונומיה — הגיאומטריה תופסת מקום מרכזי לא בשל מספרה (החמישי) אלא בשל תפקידה: היא זו שמאפשרת למדוד, לתכנן ולבנות. ללא גיאומטריה אין בנין ואין בנייה — מילולית וסמלית כאחת.\n\nהאות G, התלויה בלשכה, היא הסמל הריכוזי של הדרגה השנייה. שני פשריה מכוונות מהות הדרגה: God — הבורא שלמענו ועל פי חוקיו כל בנייה מוסרית מתרחשת; Geometry — המדע שחוקרת כיצד הבריאה עצמה בנויה. השניים אינם מתחרים אלא משלימים: מי שמבין את חוקיות הגיאומטריה מכיר בכוח שנתן לה את חוקיה. כך G נהיית שאלה פתוחה: אם המדע מגלה סדר, מיהו שקבע אותו?\n\nבמסגרת המדרגות הלולייניות, גיאומטריה מופיעה כמדע השיא אליו כל ה-7 שלבי העלייה מכוונים. ובלשכה עצמה, G תלויה במרכז — כמו הנקודה בתוך העיגול שמגדירה מרכז ומרחב. הדרגה השנייה בנויה על שאלת הסדר הנסתר: לא רק 'כיצד אבנה?' אלא 'מהו החוק שמאפשר את הבנייה?'",
    practical_elements: [
      "לשאול: מה פירוש ש-G מייצגת גם אלוהים וגם גיאומטריה — איפה שתי המשמעויות נפגשות?",
      "לחשוב על גיאומטריה לא כחישוב אלא כ'שפת הסדר': מה חוקיות קבועה שאינה תלויה בבחירה אנושית?",
    ],
    symbolic_meaning:
      "G היא אות ולא רק ראשית תיבה. כסמל בלשכה היא נוצרת ממתח בין שניים: המדע שמגלה חוקיות ואלוהים שנתן את החוקיות. כאשר G תלויה בלשכה מעל הלומד, היא שואלת: האם הלמידה שלך היא רק טכנית, או שאתה מכיר גם בסדר שמעבר לה?",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שידע אמיתי שואל לא רק 'מה' אלא 'למה'. הגיאומטריה מלמדת שיש חוקיות מאחורי הנראה, ו-G תלויה בלשכה כדי להזכיר שמי שלומד חוקיות מגיע בסוף לשאלה על מי נתן לה את תוקפה.",
    tradition_notes: [
      "הפרשנות הכפולה ל-G (God/Geometry) היא אמריקאית בעיקרה; פרשנויות אחרות קיימות.",
      "הגיאומטריה כ'אמנות עילאית' היא מסורת עתיקה שמגיעה מן הפילוסופיה היוונית ועברה לבנייה חופשית.",
    ],
    caution_notes: [
      "אין לפרש G כ-GAOTU (Grand Architect of the Universe) בלבד — המשמעות הגיאומטרית שקולה.",
      "אין לגלוש לפרשנויות קבליות או נומרולוגיות שאינן חלק מהמסורת הבנייה-חופשית הבסיסית.",
    ],
    source_notes: [
      "מקור עיקרי: geometry (Blue Lodge Ritual Reference Guide 2021, section 0055)",
      "מקור תומך: fellow-craft-degree (Blue Lodge Ritual Reference Guide 2021, section 0042)",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0055-geometry",
      "blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level2-winding-stairs-as-ascent-process", degree: "level2" },
      { slug: "level2-layers-of-the-tracing-board", degree: "level2" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },
];

// ─────────────────────────────────────────────────────────
// New Level 3 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL3_ENTRIES = [
  {
    title: "מטען ההקמה וחובת רב-בונה כמסגרת",
    slug: "level3-charge-and-duty-framework",
    type: "topic",
    level3_content_type: "structural_framework",
    level3_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "degree_structure",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "symbolic_systems",
    parent_topic: null,
    aliases: ["מטען רב-בונה", "חובת מאסטר", "The Charge at Raising"],
    keywords: ["מטען", "חובה", "הקמה", "רב-בונה", "ידידות מוסריות אהבת אחים", "דרגה 3"],
    related_topics: {
      prior: ["level3-hiram-loss-and-fidelity-system"],
      companion: ["level3-raising-and-restoration-process", "level3-burial-honor-and-memorial-structure"],
      deeper: [],
    },
    short_summary:
      "לאחר ההקמה, מטען הדרגה השלישית הוא לא שיר תהילה אלא הצהרת חובה. ידידות, מוסריות ואהבת אחים — שלושת הערכים הכלואים בין חודי המחוגה — מגדירים יחד מה פירוש להיות רב-בונה כאשר הסוד כבר נמסר.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, המטען מגדיר את מה שנדרש מהרב-בונה החדש: לבקר חולים, לסייע לנזקקים, לחפש את אחיו האבוד בחושך. הכלי הסמלי שלו — כף הבנאים — מדבר על מלט של אחווה שמאחד ולא קורות שמחלקות. מטרת המטען היא לתת לאדם מסגרת ערכית שתחזיק את כל ה'מה' שלמד בדרגה.",
      symbolic:
        "בקריאה הסמלית, כף הבנאים היא כלי שונה מכל כלים קודמים. המקבת מחתכת, האיזמל מדייק, הזוויתן מודד — אך כף הבנאים מורחת. היא מאחדת. כאשר נמסרת לרב-בונה, הנחת הרקע היא שהוא אדם שיודע לעבוד, ועכשיו השאלה היא: האם הוא יודע גם לאחד? ידידות, מוסריות ואהבת אחים הן שלוש שכבות של אחדות: אישית, ציבורית ואחוות המסדר.",
      advanced:
        "בקריאה המבנית של דרגה 3, המטען הוא רכיב אדריכלי: הוא מגדיר מה הדרגה דורשת מהרב-בונה לאחר שהמחזה נגמר. אם ההקמה היא ה'כיצד', המטען הוא ה'למה' — הצדקת הדרגה כמסגרת ערכית חיה. בלעדיו, ההקמה היא מחזה בלבד. עם המטען, ההקמה הופכת להשקה של חובה.",
    },
    full_summary:
      "המטען שניתן לרב-בונה בסיום טקס ההקמה הוא אחד המסמכים הרוחניים המרכזיים בדרגה. הוא מורכב מהצהרת חובות כלפי שלושה מרחבים: כלפי עצמו (מוסריות), כלפי בני אדם (ידידות), וכלפי אחיו בלשכה (אהבת אחים). שלושת הערכים הללו 'כלואים בין חודי המחוגה' — כלומר, הם הגבולות הפנימיים שמגדירים את חיי הרב-בונה.\n\nכף הבנאים, הכלי הייחודי לדרגה השלישית, נמסרת כחלק ממטען זה. בניגוד לכלים הקודמים שמפרידים, חותכים, מודדים ומכוונים — כף הבנאים מורחת. היא מייצגת את הכוח לאחד, לחבר, ולמלא פרצות עם 'מלט' של אחווה. הרב-בונה מקבל אותה כהצהרה: לאחר שלמדת לעבוד על עצמך, תפקידך הוא להחזיק אחרים יחד.\n\nמבחינת מסגרת הדרגה, המטען הוא הרכיב שמשלים את הטקסיות ומהפך אותה לחיים. ההקמה מדגימה תחייה; המטען שואל: מה אתה עושה עם התחייה הזו? לכן הוא לא נקרא רק 'מוסר' אלא 'מסגרת' — מבנה שבתוכו הרב-בונה מוצא את עצמו לאחר שהכניסה הסמלית לדרגה השלישית הושלמה.",
    practical_elements: [
      "לשאול: מהי ה'אחדות' שכף הבנאים דורשת ממני — כלפי מי, ובאיזה מרחב?",
      "לקרוא ידידות, מוסריות ואהבת אחים כשלוש שאלות ולא כשלושה כינויים יפים.",
    ],
    symbolic_meaning:
      "מטען ההקמה הוא מסגרת ולא סיום. כף הבנאים מסמלת אחדות — לא חוזק אלא יכולת לחבר. השלושה שבין חודי המחוגה (ידידות, מוסריות, אהבה) מסמלים שהרב-בונה אינו אדם גמור אלא אדם שיש לו כיוון. המטען נותן לכיוון הזה שם.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שלאחר ההקמה לא מספיק לחגוג: יש לחיות. המטען שואל מה עשית עם כל שלמדת. כף הבנאים בידי מסמלת שהתפקיד שלי עכשיו אינו רק לעבוד על עצמי אלא גם לאחד אחרים.",
    tradition_notes: [
      "הערך מבוסס על הטקסט של 'Charge at Raising to the Sublime Degree of Master Mason' בספרות הבנייה החופשית האנגלו-אמריקאית.",
      "שלושת הערכים (ידידות, מוסריות, אהבת אחים) הם סלוגן המסדר הנפוץ ולא רק מרכיב טקסי.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן Royal Arch: המטען שייך למסגרת הדרגה השלישית בלבד.",
      "אין לבלבל בין 'מטען' (charge) לבין 'חיוב' (obligation) — המטען ניתן לאחר ולא לפני.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
      "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level3-hiram-loss-and-fidelity-system", degree: "level3" },
      { slug: "level3-raising-and-restoration-process", degree: "level3" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },

  {
    title: "כבוד הקבורה והזיכרון כמבנה דרגה שלישית",
    slug: "level3-burial-honor-and-memorial-structure",
    type: "topic",
    level3_content_type: "symbolic_system_analysis",
    level3_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "ceremony",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "ritual_dynamics",
    parent_topic: null,
    aliases: ["טקס הקבורה הבנייה-חופשי", "האנדרטה ואזכרת חירם", "כבוד אחרון לרב-בונה"],
    keywords: ["קבורה", "זיכרון", "עמוד שבור", "בתולה בוכייה", "אנדרטה", "דרגה 3"],
    related_topics: {
      prior: ["level3-acacia-grave-and-immortality-relationship"],
      companion: ["level3-hiram-loss-and-fidelity-system", "level3-charge-and-duty-framework"],
      deeper: ["level3-third-degree-tracing-board-map"],
    },
    short_summary:
      "טקס הקבורה הבנייה-חופשי והאנדרטה לחירם מרכיבים יחד מבנה מוסדי ייחודי: לא רק סיום חיים אלא הצהרה על כיצד מחזיקים זיכרון. העמוד השבור, הבתולה הבוכייה, הכד עם האפר וספר הזיכרון פועלים כמערכת שמגדירה את יחסה של הדרגה השלישית למוות.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, טקס הקבורה של רב-בונה הוא טקס מיוחד הכולל לבישת כפפות לבנות וסינרים לבנים — סמל לידיים נקיות מרצח ולב שמור מחטא. האנדרטה בלשכה מציגה דמות בוכייה מעל עמוד שבור: מקדש שלא הושלם, עבודה שלא נסתיימה. הזיכרון אינו טשטוש האובדן אלא שמירה עליו.",
      symbolic:
        "בקריאה הסמלית, כל אלמנט באנדרטה נושא משמעות. העמוד השבור = בניין שלא הושלם; הבתולה הבוכייה = אחיזה בזיכרון שלא הרפתה; שיבולת השיטה בידה = נצח הנשמה (כמו ענף השיטה על קבר חירם); הכד עם האפר = מוות שנשמר ולא נשכח; הספר הפתוח = מעשים שנרשמו ולא נמחקו; הזמן הפורש את שיערה = זמן שמגלה ולא מוחה. כל אלמנט מחזיק אמת אחת: כבוד לאחים שעברו.",
      advanced:
        "בקריאה המבנית של דרגה 3, טקס הקבורה ומרכיבי האנדרטה יוצרים מבנה מוסדי: כיצד הדרגה מחזיקה מוות בלי להתעלם ממנו ובלי לטבוע בו. זהו ה'חלק השלישי' של מחזור ההקמה: חירם מת, חירם מוקם, ועכשיו — כיצד חיים בעולם שיש בו מוות? האנדרטה עונה: שומרים זיכרון, פועלים בכבוד, ומניחים לזמן לגלות מה צריך להיגלות.",
    },
    full_summary:
      "טקס הקבורה של בנייה חופשית הוא מסמך מוסדי: הוא מגדיר כיצד קהילה מחזיקה את מותו של אחד מחבריה. 12 בנאים שחזרו בתשובה לבשו כפפות לבנות וסינרים לבנים כסמל לידיים נקיות. הכפפות הלבנות מסמלות שאין להם חלק ברצח; הסינרים הלבנים מסמלים שלמות מוסרית. הטקס בנוי לא על אבל בלבד אלא על הכרה: האדם שמת פעל נאמנה, וכבודו שמור.\n\nאנדרטת חירם בלשכה מרכיבה שש שכבות של סמל. הבתולה הבוכייה על העמוד השבור מייצגת את הצד הרגשי: אדם חסר. השיטה בידה מחברת אל ענף הקבר ואל הנשמה הנצחית. הכד עם האפר והספר הפתוח מחברים בין עולם החומר (האפר) לעולם המעשים (הספר שנרשם ולא נמחק). הזמן שפורש את שיערה של הבתולה מוסיף שכבה נוספת: לא הכל נגלה מיד, אך עם הזמן האמת יוצאת לאור.\n\nהמבנה הזה חשוב בדרגה השלישית מפני שהוא משלים את מחזור ה'מוות–הקמה–זיכרון'. אחרי שחירם מת ומוקם, עולה השאלה: כיצד מחיים מוות בתוך מסגרת חיה? התשובה של הדרגה היא: בכבוד, בזיכרון פעיל ובנוכחות של אמנות ציבורית (האנדרטה) שמזכירה שאובדן אמיתי לא נעלם.",
    practical_elements: [
      "לבחון כל אלמנט באנדרטת חירם ולשאול: מה שמירה על האובדן, ומה תקווה למרות האובדן?",
      "לחשוב על ההבדל בין 'אבל' (כאב) לבין 'זיכרון' (שמירה פעילה) — היכן עוברת הגבול?",
    ],
    symbolic_meaning:
      "האנדרטה בלשכה מסמלת שדרגה שלישית היא דרגה שיודעת לחיות עם אובדן מבלי לשכחו. העמוד השבור אינו כישלון — הוא מציאות. הבתולה הבוכייה אינה חולשה — היא נאמנות לאמת. המבנה כולו מלמד שזיכרון ראוי אינו מחיקה ואינו טשטוש — הוא הכרה.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שכבוד לאדם שהלך אינו רק השתתפות בטקס: הוא שמירה פעילה על מה שהוא ייצג. כפפות לבנות, ספר פתוח ועמוד שבור — כולם אומרים: לא שכחנו, ולא נשכח.",
    tradition_notes: [
      "טקס הקבורה הבנייה-חופשי מבוסס על 'Burial Service' המסורתי בספרות הבנייה החופשית האנגלו-אמריקאית.",
      "האנדרטה עם הבתולה הבוכייה מופיעה בסמלי הדרגה השלישית ובתיאורי לוח הדרגה השלישית.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן Royal Arch: טקס הקבורה שייך לדרגה שלישית, לא להשלמה מאוחרת.",
      "אין לבלבל בין הקבורה הסמלית (מחזה ההקמה) לבין טקס הקבורה האמיתי של חבר שנפטר.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0077-burial-service",
      "מקור תומך: textbook-freemasonry-tracing-boards-en",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service",
      "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "textbook-freemasonry-tracing-boards-en",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level3-acacia-grave-and-immortality-relationship", degree: "level3" },
      { slug: "level3-hiram-loss-and-fidelity-system", degree: "level3" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },

  {
    title: "לוח הדרגה השלישית כמפת משמעות",
    slug: "level3-third-degree-tracing-board-map",
    type: "topic",
    level3_content_type: "symbolic_system_analysis",
    level3_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "symbol",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "relationships_between_symbols",
    parent_topic: null,
    aliases: ["לוח הדרגה שלוש", "third-degree tracing board", "מפת הסמלים של דרגה שלישית"],
    keywords: ["לוח דרגה", "כוורת", "שעון חול", "חרמש", "עין הבוחנת", "ארון קבורה", "דרגה 3"],
    related_topics: {
      prior: ["level3-acacia-grave-and-immortality-relationship"],
      companion: [
        "level3-burial-honor-and-memorial-structure",
        "level3-hiram-loss-and-fidelity-system",
        "level3-raising-and-restoration-process",
      ],
      deeper: [],
    },
    short_summary:
      "לוח הדרגה השלישית אינו אוסף של סמלים, הוא מפה. כוורת הדבורים, שעון החול, החרמש, עין הבוחנת, ארון הקבורה, האת והקבר — כל אחד נושא משמעות, אך יחד הם יוצרים שפה שלמה שמסבירה מה פירוש הזמן, המוות וההמשך בדרגה השלישית.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, לוח הדרגה השלישית מציג בפני הצופה שישה-שמונה סמלים יחד. הכוורת מזכירה חריצות; שעון החול מזכיר שהזמן חולף; החרמש מזכיר שמוות בא; עין הבוחנת מזכירה השגחה; הארון, האת והקבר מזכירים שגם אני אמות. ביחד הם מסגרת מוסרית: כל אחד מהסמלים שואל 'כיצד אתה חי בידיעה שתמות?'",
      symbolic:
        "בקריאה הסמלית, כל זוג סמלים בלוח עומד ביחס: כוורת (חריצות) מול ארון קבורה (סיום) — חי עד הסוף. שעון חול (זמן אוזל) מול עין הבוחנת (אלוהים רואה הכל) — גם אם לא תראה, יראו אותך. חרמש (מוות קוצר) מול שיטה (אלמוות) — מה שנקצר בגוף נשמר ברוח. הסמלים אינם מסרים בודדים אלא מערכת דיאלוגית.",
      advanced:
        "בקריאה המבנית של דרגה 3, לוח הדרגה פועל כ'מכשיר קריאה'. הוא מאפשר לאדם לקרוא את כל הדרגה בבת-אחת: איפה היא מתחילה (חריצות כהכנה), מה היא דורשת (עמידה בפני מוות), ואיפה היא מכוונת (שימור שמעבר לגוף). ללא לוח הדרגה, הסמלים הם פרחים בודדים; עם הלוח, הם גן שיש לו צורה.",
    },
    full_summary:
      "לוח הדרגה השלישית הוא כלי לימודי מסורתי שמציג בבת-אחת את שדה הסמלים של הדרגה. כוורת הדבורים מסמלת תעשייה וחריצות: האדם לא בא לעולם לבטל, אלא לעבוד. שעון החול מסמל שהחיים אוזלים — לא כדחייה אלא כעובדה מזמינה לעשות. החרמש מסמל שהזמן הוא גם הקוצר: מה שנסיים, ייגמר. עין הבוחנת מסמלת השגחה אלוהית — לא פיקוח שמפחיד, אלא ראייה שמזכירה שמה שנעשה, נרשם. ארון הקבורה, האת והקבר מסמלים שהמוות אינו נסתר: הדרגה השלישית מציבה אותו לנגד עיני הלומד, לא כדי לפחד אלא כדי להתיר.\n\nהאינטגרציה של כל הסמלים ב'מפה' אחת — לוח הדרגה — היא הפעולה הפדגוגית המרכזית. בשונה מדרגה ראשונה שמלמדת עבודה, ודרגה שנייה שמלמדת ידע, דרגה שלישית מלמדת זיכרון ומוות. לוח הדרגה הוא ה'מסגרת ראייה' שמסייעת לאדם לקרוא את כל ניסיוני הדרגה כמכלול.\n\nחשוב להבין ש'מפה' פירושה שהסמלים נמצאים ביחס זה לזה, לא רק זה אחרי זה. כוורת (חיים) מדברת עם ארון (מוות); שעון חול (זמן) מדבר עם עין (נצח); חרמש (קצירה) מדבר עם שיטה (השרדות). הדרגה השלישית מציגה את כל המתחים האלה בלי לפתור אותם — ובכך היא מציעה שלמות שאינה תלויה בסגירה.",
    practical_elements: [
      "לציין בלוח הדרגה אילו סמלים עומדים ביחסי 'מתח' אחד עם השני (למשל: כוורת vs. ארון) ולשאול: מה המתח אומר?",
      "לקרוא את לוח הדרגה כ'שאלות' ולא כ'תשובות': כל סמל הוא שאלה לחיים שלי.",
    ],
    symbolic_meaning:
      "לוח הדרגה השלישית מסמל את הדיאלוג בין חיים למוות כשפת הדרגה. לא מסר בודד אלא שדה: כוורת, שעון, חרמש, עין, קבר — כל אחד מחזיק קצה אחד של מתח. לוח הדרגה מאפשר לאדם לעמוד בתוך השדה הזה מבלי לפחד ממנו.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שלמידה אמיתית של המוות אינה לימוד אבל אלא לימוד חיים. כאשר ארון הקבורה, שעון החול והחרמש עומדים לנגד עיניך, השאלה שהם שואלים היא: כיצד תחי עכשיו, בידיעה שיש קצה?",
    tradition_notes: [
      "לוח הדרגה השלישית הוא מסמך מסורתי המתואר בספרות ה-Tracing Boards של הבנייה החופשית.",
      "הסמלים בלוח (כוורת, שעון, חרמש) שייכים ללשון המוות והשרדות שנפוצה גם בחוץ לבנייה חופשית.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן Royal Arch: לוח הדרגה השלישית הוא כלי Blue Lodge בלבד.",
      "אין לקרוא את הסמלים כמבשרי מוות-בפועל; הם כלי מדיטציה ולא נבואה.",
    ],
    source_notes: [
      "מקור עיקרי: textbook-freemasonry-tracing-boards-en",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    ],
    language: "he",
    work_id: null,
    work_title: null,
    source_kind: "degree_ritual",
    source_path: null,
    source_anchor: [
      "textbook-freemasonry-tracing-boards-en",
      "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    ],
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [
      { slug: "level3-acacia-grave-and-immortality-relationship", degree: "level3" },
      { slug: "level3-burial-honor-and-memorial-structure", degree: "level3" },
    ],
    chapter_toc: null,
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "universal",
    status: "draft",
    observability: "visible",
    relies_on_level1_topics: [],
  },
];

// ─────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmp = filePath + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(payload, null, 2) + "\n", "utf8");
  fs.renameSync(tmp, filePath);
}

function parseArgs(argv) {
  const opts = { dryRun: false, siteRoot: DEFAULT_SITE_ROOT };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--dry-run") opts.dryRun = true;
    if (argv[i] === "--site-root" && argv[i + 1]) {
      opts.siteRoot = path.resolve(argv[++i]);
    }
  }
  return opts;
}

// Only check content fields, not meta/caution/notes fields that are allowed to reference boundaries
const CONTENT_FIELDS_ONLY = ["short_summary", "full_summary", "reading_layers", "symbolic_meaning", "candidate_lesson", "practical_elements", "aliases", "keywords"];

function checkForbiddenPatterns(entry, patterns, degreeLabel) {
  const contentOnly = {};
  for (const f of CONTENT_FIELDS_ONLY) {
    if (f in entry) contentOnly[f] = entry[f];
  }
  const text = JSON.stringify(contentOnly);
  const violations = [];
  for (const { label, pattern } of patterns) {
    if (pattern.test(text)) {
      violations.push({ slug: entry.slug, degree: degreeLabel, forbidden: label });
    }
  }
  return violations;
}

function checkRequiredFields(entry, requiredFields) {
  return requiredFields.filter((f) => !(f in entry)).map((f) => ({ slug: entry.slug, missing_field: f }));
}

const REQUIRED_LEVEL2 = [
  "title", "slug", "type", "level2_content_type", "level2_type", "depth_scope",
  "boundary_guard_passed", "knowledge_type", "degree", "applies_to_degrees",
  "content_scope", "partition_role", "degree_owner", "product_state", "category",
  "parent_topic", "aliases", "keywords", "related_topics", "short_summary",
  "reading_layers", "full_summary", "practical_elements", "symbolic_meaning",
  "candidate_lesson", "tradition_notes", "caution_notes", "source_notes",
  "language", "knowledge_links", "chapter_toc", "visibility_level",
  "sensitivity_level", "tradition_scope", "status", "observability",
  "relies_on_level1_topics",
];

const REQUIRED_LEVEL3 = [
  "title", "slug", "type", "level3_content_type", "level3_type", "depth_scope",
  "boundary_guard_passed", "knowledge_type", "degree", "applies_to_degrees",
  "content_scope", "partition_role", "degree_owner", "product_state", "category",
  "parent_topic", "aliases", "keywords", "related_topics", "short_summary",
  "reading_layers", "full_summary", "practical_elements", "symbolic_meaning",
  "candidate_lesson", "tradition_notes", "caution_notes", "source_notes",
  "language", "knowledge_links", "chapter_toc", "visibility_level",
  "sensitivity_level", "tradition_scope", "status", "observability",
  "relies_on_level1_topics",
];

// ─────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────

function main() {
  const { dryRun, siteRoot } = parseArgs(process.argv.slice(2));
  const executedAt = new Date().toISOString();

  const level2Path = path.join(siteRoot, "data", "level2.json");
  const level3Path = path.join(siteRoot, "data", "level3.json");
  const level2BackupPath = path.join(siteRoot, "data", "level2.pre_m15_wave1_backup.json");
  const level3BackupPath = path.join(siteRoot, "data", "level3.pre_m15_wave1_backup.json");

  const report = {
    phase: PHASE_ID,
    executed_at: executedAt,
    dry_run: dryRun,
    site_root: siteRoot,
    new_level2_slugs: NEW_LEVEL2_ENTRIES.map((e) => e.slug),
    new_level3_slugs: NEW_LEVEL3_ENTRIES.map((e) => e.slug),
    actions: [],
    overall_status: "pending",
  };

  const validation = {
    phase: PHASE_ID,
    executed_at: executedAt,
    checks: {},
    failures: [],
    error_count: 0,
    overall_status: "pending",
  };

  try {
    // ── 1. Load existing data ──
    const level2Data = loadJson(level2Path);
    const level3Data = loadJson(level3Path);

    const existingL2Slugs = new Set((level2Data.entries || []).map((e) => e.slug));
    const existingL3Slugs = new Set((level3Data.entries || []).map((e) => e.slug));

    // ── 2. Boundary validation ──
    const allViolations = [];
    const allMissingFields = [];

    for (const entry of NEW_LEVEL2_ENTRIES) {
      allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL2_PATTERNS, "level2"));
      allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL2));
    }
    for (const entry of NEW_LEVEL3_ENTRIES) {
      allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL3_PATTERNS, "level3"));
      allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL3));
    }

    validation.checks.boundary_clean = {
      passed: allViolations.length === 0,
      violations: allViolations,
    };
    validation.checks.required_fields_complete = {
      passed: allMissingFields.length === 0,
      missing: allMissingFields,
    };

    if (allViolations.length > 0) {
      validation.failures.push({ check: "boundary_clean", detail: allViolations });
    }
    if (allMissingFields.length > 0) {
      validation.failures.push({ check: "required_fields_complete", detail: allMissingFields });
    }

    // ── 3. Duplicate check ──
    const duplicateL2 = NEW_LEVEL2_ENTRIES.filter((e) => existingL2Slugs.has(e.slug)).map((e) => e.slug);
    const duplicateL3 = NEW_LEVEL3_ENTRIES.filter((e) => existingL3Slugs.has(e.slug)).map((e) => e.slug);

    validation.checks.no_duplicates = {
      passed: duplicateL2.length === 0 && duplicateL3.length === 0,
      duplicate_level2: duplicateL2,
      duplicate_level3: duplicateL3,
    };
    if (duplicateL2.length > 0 || duplicateL3.length > 0) {
      validation.failures.push({ check: "no_duplicates", detail: { duplicateL2, duplicateL3 } });
    }

    const validationPassed = validation.failures.length === 0;
    validation.error_count = validation.failures.length;
    validation.overall_status = validationPassed ? "pass" : "fail";

    if (!validationPassed) {
      report.overall_status = "fail";
      report.error = "Validation failed before any writes.";
      writeJson(DEFAULT_REPORT_PATH, report);
      writeJson(DEFAULT_VALIDATION_PATH, validation);
      console.error("Validation failed. No writes performed.");
      process.exitCode = 1;
      return;
    }

    report.actions.push({ action: "validation_passed", detail: "boundary and field checks passed" });

    if (dryRun) {
      report.overall_status = "dry_run_ok";
      writeJson(DEFAULT_REPORT_PATH, report);
      writeJson(DEFAULT_VALIDATION_PATH, validation);
      console.log("DRY RUN — no files written.");
      console.log("Would add:", NEW_LEVEL2_ENTRIES.map((e) => e.slug));
      console.log("Would add:", NEW_LEVEL3_ENTRIES.map((e) => e.slug));
      return;
    }

    // ── 4. Backup ──
    fs.writeFileSync(level2BackupPath, JSON.stringify(level2Data, null, 2) + "\n", "utf8");
    fs.writeFileSync(level3BackupPath, JSON.stringify(level3Data, null, 2) + "\n", "utf8");
    report.actions.push({ action: "backups_written", level2: level2BackupPath, level3: level3BackupPath });

    // ── 5. Append new entries ──
    level2Data.entries = [...(level2Data.entries || []), ...NEW_LEVEL2_ENTRIES];
    level3Data.entries = [...(level3Data.entries || []), ...NEW_LEVEL3_ENTRIES];

    // Update meta
    level2Data.meta = { ...level2Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };
    level3Data.meta = { ...level3Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };

    // ── 6. Write ──
    writeJson(level2Path, level2Data);
    writeJson(level3Path, level3Data);

    report.actions.push({
      action: "entries_appended",
      level2_added: NEW_LEVEL2_ENTRIES.map((e) => e.slug),
      level3_added: NEW_LEVEL3_ENTRIES.map((e) => e.slug),
      level2_total: level2Data.entries.length,
      level3_total: level3Data.entries.length,
    });

    report.overall_status = "success";
    writeJson(DEFAULT_REPORT_PATH, report);
    writeJson(DEFAULT_VALIDATION_PATH, validation);

    console.log(`Level 2: ${level2Data.entries.length} entries (added ${NEW_LEVEL2_ENTRIES.length})`);
    console.log(`Level 3: ${level3Data.entries.length} entries (added ${NEW_LEVEL3_ENTRIES.length})`);
    console.log(`Report: ${DEFAULT_REPORT_PATH}`);
  } catch (err) {
    report.overall_status = "fail";
    report.error = err.message;
    validation.overall_status = "fail";
    if (validation.failures.length === 0) {
      validation.failures = [{ check: "execution", detail: err.message }];
      validation.error_count = 1;
    }
    writeJson(DEFAULT_REPORT_PATH, report);
    writeJson(DEFAULT_VALIDATION_PATH, validation);
    console.error(err.message);
    process.exitCode = 1;
  }
}

main();
