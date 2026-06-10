/**
 * apply_phase_m_18_wave4_fill.js
 *
 * Wave 4 (final) — adds 3 new Level 1 entries and 1 new Level 3 entry.
 * Focuses on genuinely uncovered topic clusters identified in the coverage map.
 *
 * Level 1 new candidates:
 *   - l1-cardinal-virtues-fortitude-caution-relief
 *   - l1-chalk-charcoal-clay-freedom-fervor-zeal
 *   - l1-penalty-structure-and-oath-consequences
 *
 * Level 3 new candidates:
 *   - level3-mm-obligation-preparation-and-penalty
 *
 * Usage:
 *   node PDF_handle/TOOLS/apply_phase_m_18_wave4_fill.js [--dry-run] [--site-root <path>]
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m18_wave4_fill";
const DEFAULT_SITE_ROOT = path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_18_wave4_fill_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_18_wave4_fill_validation.json");

const FORBIDDEN_LEVEL1_PATTERNS = [
  { label: "master_mason_content", pattern: /master mason/iu },
  { label: "royal_arch", pattern: /royal arch/iu },
  { label: "third_degree", pattern: /third degree|level3/iu },
];

const FORBIDDEN_LEVEL3_PATTERNS = [
  { label: "royal_arch", pattern: /royal arch/iu },
  { label: "return_from_babylon", pattern: /babylon/iu },
  { label: "hidden_vault", pattern: /vault/iu },
];

const CONTENT_FIELDS_ONLY = ["short_summary", "full_summary", "reading_layers", "symbolic_meaning", "candidate_lesson", "practical_elements", "aliases", "keywords"];

// ─────────────────────────────────────────────────────────
// New Level 1 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL1_ENTRIES = [
  {
    title: "מידות המוסר: גבורה, זהירות, סעד ומידות נוספות",
    slug: "l1-cardinal-virtues-fortitude-caution-relief",
    type: "topic",
    level1_content_type: "structural_framework",
    level1_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "concept",
    degree: "level1",
    applies_to_degrees: ["level1"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level1",
    product_state: "built",
    category: "moral_framework",
    parent_topic: null,
    aliases: ["ארבע מידות המוסר", "Cardinal Virtues", "גבורה", "Fortitude", "זהירות", "Prudence", "Caution", "סעד", "Relief", "מזג", "Temperance", "צדק", "Justice"],
    keywords: ["גבורה", "אומץ לב", "fortitude", "זהירות", "prudence", "caution", "סעד", "עזרה", "relief", "מזג", "temperance", "צדק", "justice", "מידות", "מוסר", "דרגה 1", "לשון שותקת", "silent tongue", "לב נאמן", "faithful heart"],
    related_topics: {
      prior: [],
      companion: ["l1-obligation-mashmaut-hahitchayvut"],
      deeper: [],
    },
    short_summary:
      "הפולחן של דרגה ראשונה מלמד ארבע מידות מוסר: גבורה (אומץ לב לעשות את הנכון), זהירות (חכמה לדעת מתי ואיך לפעול), מזג (ריסון עצמי) וצדק (הגינות). לצדן עומד הסעד — חובת העזרה לאח נזקק. ולשון שותקת ולב נאמן משלימות: לדעת לשתוק ולשמור.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, ארבע מידות המוסר מוזכרות בהרצאת הדרגה הראשונה. גבורה (Fortitude) — אומץ לב לעמוד מול קושי ולעשות את הנכון. זהירות (Prudence/Caution) — חכמה לשקול לפני שפועלים. מזג (Temperance) — ריסון עצמי והתנהלות מאוזנת. צדק (Justice) — לתת לכל אדם את המגיע לו. סעד (Relief) — חובה לעזור לאח שזקוק.",
      symbolic:
        "בקריאה הסמלית, ארבע המידות מייצגות ארבע רגלי יציבות מוסרית — כמו ארבע רגלי כיסא. ללא אחת מהן, האדם נופל. הלשון השותקת מייצגת שלא כל ידע ראוי לחשיפה, והלב הנאמן מייצג שיש דברים ששומרים בפנים ולא מוציאים.",
      advanced:
        "בקריאה המבנית, המידות אינן רשימה מנותקת אלא מערכת: זהירות מנחה לפני הפעולה, גבורה מפעילה ברגע הנדרש, מזג מגביל אחרי, וצדק שופט את התוצאה. סעד הוא היישום המעשי: מידות ללא פעולה הן ריקות.",
    },
    full_summary:
      "בהרצאת הדרגה הראשונה נלמדות ארבע מידות מוסר מרכזיות: גבורה (Fortitude), זהירות (Prudence), מזג (Temperance) וצדק (Justice). אלו אינן ערכים מופשטים בלבד — הן מצפן להתנהגות.\n\nגבורה היא אומץ הלב לעשות את הנכון גם כשזה קשה. זהירות היא החכמה לשקול לפני שפועלים, לא להיחפז ולא להימנע. מזג הוא ריסון עצמי — היכולת לשלוט ברגשות ובתשוקות. צדק הוא ההגינות — לתת לכל אדם את המגיע לו ולא לקחת מה שאינו שלך.\n\nלצד המידות, הפולחן מדגיש את חובת הסעד (Relief): עזרה לאח שנמצא בצורך, בכסף, בעצה או בנוכחות. ומושגי 'הלשון השותקת' (Silent Tongue) ו'הלב הנאמן' (Faithful Heart) משלימים: לדעת מתי לדבר ומתי לשתוק, ולשמור בלב את מה שנמסר באמון.\n\nמידות אלו מהוות את הבסיס המוסרי שעליו כל שאר הלמידה בבנייה החופשית נבנית.",
    practical_elements: [
      "לשאול לפני פעולה: האם אני פועל מתוך גבורה או מפחד? מתוך זהירות או מתוך עצלות?",
      "לזהות שסעד אינו רק כספי — הוא יכול להיות זמן, הקשבה או עצה.",
    ],
    symbolic_meaning:
      "ארבע המידות מסמלות ארבע עמודי התנהגות שהתלמיד מתחייב אליהם. ללא גבורה — פחד. ללא זהירות — פזיזות. ללא מזג — פרץ. ללא צדק — עוול. ביחד הן מרכיבות דמות של אדם שלם.",
    candidate_lesson:
      "הלקח הוא שדרגה ראשונה לא מלמדת רק סמלים וטקסים — היא מלמדת איך לחיות. ארבע המידות הן הוראות שימוש, לא פילוסופיה.",
    tradition_notes: [
      "ארבע מידות המוסר מקורן בפילוסופיה היוונית (אפלטון, אריסטו) ועברו למסורת הנוצרית.",
      "בבנייה החופשית הן מופיעות כחלק מהרצאת הדרגה הראשונה בכל המוניטורים המרכזיים.",
    ],
    caution_notes: [],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0008-entered-apprentice-or-first-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "l1-obligation-mashmaut-hahitchayvut", degree: "level1" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
  {
    title: "גיר, פחם וחימר — חירות, להט ונאמנות",
    slug: "l1-chalk-charcoal-clay-freedom-fervor-zeal",
    type: "topic",
    level1_content_type: "structural_framework",
    level1_type: "symbol",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "symbol",
    degree: "level1",
    applies_to_degrees: ["level1"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level1",
    product_state: "built",
    category: "symbolic_elements",
    parent_topic: null,
    aliases: ["גיר פחם וחימר", "Chalk Charcoal Clay", "חירות להט ונאמנות", "Freedom Fervor Zeal"],
    keywords: ["גיר", "chalk", "פחם", "charcoal", "חימר", "clay", "חירות", "freedom", "להט", "fervor", "נאמנות", "zeal", "דרגה 1"],
    related_topics: {
      prior: [],
      companion: ["l1-tools-mashmaut-meshulevet-klei-hatalmid"],
      deeper: [],
    },
    short_summary:
      "שלושה חומרים בסיסיים — גיר, פחם וחימר — מסמלים שלוש מידות יסוד. הגיר מציין חירות (Freedom): כפי שהגיר מסמן בקלות, כך האדם החופשי מסמן את דרכו. הפחם מציין להט (Fervor): כפי שהפחם בוער, כך הנאמנות צריכה להיות לוהטת. החימר מציין נאמנות (Zeal): כפי שהחימר מחבר אבנים, כך הנאמנות מחברת אנשים.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, גיר, פחם וחימר הם שלושה חומרים שהבנאים האופרטיביים השתמשו בהם: הגיר לסימון, הפחם לשרטוט, והחימר (מלט) לחיבור אבנים. בפולחן הם מייצגים שלוש מידות: חירות (Freedom), להט (Fervor) ונאמנות (Zeal).",
      symbolic:
        "בקריאה הסמלית, שלושת החומרים מייצגים שלושה שלבים של מחויבות. הגיר (חירות) — הבחירה החופשית להצטרף ולפעול. הפחם (להט) — האנרגיה והתשוקה שמניעות את העבודה. החימר (נאמנות) — החומר שמחבר, המחויבות שמחזיקה הכל ביחד.",
      advanced:
        "בקריאה המבנית, שלושת החומרים מרכיבים מערכת: בלי חירות אין בחירה, בלי להט אין מוטיבציה, בלי נאמנות אין קשר. זהו מודל מינימלי של השתייכות: אדם חופשי שבוער בלהט ומחובר בנאמנות.",
    },
    full_summary:
      "גיר (Chalk), פחם (Charcoal) וחימר (Clay) הם שלושה חומרים בסיסיים מעולם הבנייה האופרטיבית שנכנסו לפולחן הבנייה החופשית כסמלים.\n\nהגיר מציין חירות (Freedom): כפי שהבנאי הראשי משתמש בגיר כדי לסמן תוכניות על לוח השרטוט, כך האדם החופשי מסמן את דרכו בעולם. חירות פירושה שהכניסה לאחווה נעשית מבחירה, לא מכפייה.\n\nהפחם מציין להט (Fervor): כפי שהפחם בוער ונותן חום, כך על הבונה לשמור על להט פנימי — מוטיבציה, מחויבות ותשוקה לעבודה הפנימית.\n\nהחימר מציין נאמנות (Zeal): כפי שהחימר (מלט) מחבר אבנים זו לזו ויוצר קיר יציב, כך הנאמנות מחברת בין בני אדם ויוצרת קהילה.\n\nשלושת החומרים יחד מרכיבים מודל של השתייכות מלאה: בחירה חופשית, פעולה נלהבת, וקשר נאמן.",
    practical_elements: [
      "לשאול: האם הצטרפתי/פעלתי מתוך חירות אמיתית? האם אני שומר על להט? האם אני מחובר בנאמנות?",
      "לזהות שהנאמנות (חימר) היא החומר שמחזיק את הכל — ללא קשר, החירות והלהט לא מספיקים.",
    ],
    symbolic_meaning:
      "גיר = בחירה חופשית. פחם = להט פנימי. חימר = חיבור ונאמנות. שלושתם יחד מגדירים מה נדרש כדי להיות חלק מהאחווה: לבחור, לבעור ולהיקשר.",
    candidate_lesson:
      "הלקח הוא ששלושה חומרים פשוטים מכילים שלושה עקרונות עמוקים. חירות ללא להט היא אדישות. להט ללא נאמנות הוא בזבוז. נאמנות ללא חירות היא כפייה. רק שלושתם יחד עובדים.",
    tradition_notes: [
      "גיר, פחם וחימר מוזכרים בהרצאת הדרגה הראשונה ברוב המוניטורים.",
      "הקשר בין שלושת החומרים לשלושת הערכים (Freedom, Fervor, Zeal) הוא חלק מהפרשנות המסורתית.",
    ],
    caution_notes: [],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "l1-tools-mashmaut-meshulevet-klei-hatalmid", degree: "level1" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
  {
    title: "עונשי ההתחייבות ומשמעותם הסמלית",
    slug: "l1-penalty-structure-and-oath-consequences",
    type: "topic",
    level1_content_type: "structural_framework",
    level1_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "ceremony",
    degree: "level1",
    applies_to_degrees: ["level1"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level1",
    product_state: "built",
    category: "obligation_and_ceremony",
    parent_topic: null,
    aliases: ["עונשי ההתחייבות", "Penalty of the Obligation", "חיתוך הגרון", "Throat Cut Across", "עקירת הלשון", "Tongue Torn Out", "קבורה בחולות הים", "Buried in the Rough Sands", "פיקדון מתכתי", "Metallic Deposit"],
    keywords: ["עונש", "penalty", "חיתוך", "גרון", "throat", "לשון", "tongue", "חולות הים", "rough sands", "קבורה", "buried", "פיקדון", "מתכתי", "metallic deposit", "דרגה 1", "התחייבות"],
    related_topics: {
      prior: ["l1-obligation-mashmaut-hahitchayvut"],
      companion: ["l1-cardinal-virtues-fortitude-caution-relief"],
      deeper: [],
    },
    short_summary:
      "בדרגה ראשונה, ההתחייבות כוללת עונשים סמליים: חיתוך הגרון, עקירת הלשון מהשורש, וקבורת הגופה בחולות הים. עונשים אלו אינם איומים ממשיים — הם סמלים לחומרת ההתחייבות. הפיקדון המתכתי (ריקנות הכיסים) מסמל שהכניסה היא ללא תנאים חומריים.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, בזמן ההתחייבות של הדרגה הראשונה, המועמד נשבע לשמור על סודות האחווה. העונשים המוזכרים הם: חיתוך הגרון (Throat Cut Across), עקירת הלשון מהשורש (Tongue Torn Out), וקבורה בחולות הים (Buried in the Rough Sands of the Sea). הפיקדון המתכתי (Metallic Deposit) הוא הרגע שבו מוכח שהמועמד נכנס ללא כסף או מתכות — ריק.",
      symbolic:
        "בקריאה הסמלית, כל עונש מקודד חלק מהגוף ששייך לשמירת סוד: הגרון (שדרכו עובר הדיבור), הלשון (שמבטאת מילים), והים (שמבליע ומסתיר). העונשים מלמדים שהסוד חמור: לא דבר שניתן להפר בקלילות. הפיקדון המתכתי מסמל שהאחווה לא נקנית בכסף — היא נקנית בהתחייבות.",
      advanced:
        "בקריאה המבנית, מבנה העונשים חוזר בכל שלוש הדרגות אך מתחלף: דרגה 1 — גרון ולשון; דרגה 2 — חזה ולב. כל דרגה מתמקדת באיבר אחר ובחומרה גדלה. המבנה המקביל מלמד שההתחייבות מתעמקת עם כל דרגה. העונשים הם שפה, לא משפט.",
    },
    full_summary:
      "בדרגה הראשונה, ההתחייבות (Obligation) כוללת שבועה לשמור על סודות האחווה, ועמה עונשים סמליים שנועדו להמחיש את חומרת ההתחייבות.\n\nשלושה עונשים מוזכרים: חיתוך הגרון (Throat Cut Across) — סמל לכך שמי שמפר את הסוד 'חותך' את הקשר שלו לאחווה דרך הגרון שדיבר. עקירת הלשון מהשורש (Tongue Torn Out by Its Roots) — סמל לכך שהלשון שגילתה את הסוד ראויה להיעקר. קבורה בחולות הים (Buried in the Rough Sands of the Sea at Low-Water Mark) — סמל לכך שמי שמפר נעלם ללא זכר.\n\nחשוב להבין שעונשים אלו הם סמליים, לא ממשיים. הם שפה עתיקה שמבטאת חומרה, לא איום. בלשכות מודרניות רבות, הנוסח הומתן.\n\nהפיקדון המתכתי (Metallic Deposit) הוא מרכיב נפרד: המועמד מתבקש לתת פיקדון ומגלה שאין לו כלום (הכיסים רוקנו לפני הכניסה). זהו לקח על ענווה ועל כך שהכניסה לאחווה אינה עסקה כספית.",
    practical_elements: [
      "להבין שהעונשים הם סמליים — שפה שמבטאת חומרת שבועה, לא איום פיזי.",
      "לזהות שהפיקדון המתכתי מלמד ענווה: הכניסה לאחווה היא ללא תנאים חומריים.",
    ],
    symbolic_meaning:
      "העונשים מסמלים שהסוד הוא חמור: הגרון, הלשון והים מייצגים את שלושת הערוצים של הפרת סוד (דיבור, ביטוי, היעלמות). הפיקדון המתכתי מסמל ענווה ותחילה מאפס.",
    candidate_lesson:
      "הלקח הוא שההתחייבות אינה טקסט ריק — היא שבועה שנושאת משקל סמלי כבד. העונשים מלמדים שיש מחיר למילים שנאמרות ולמילים שלא נשמרות.",
    tradition_notes: [
      "העונשים הסמליים מוזכרים בכל הפולחנים המרכזיים אך רבות מהלשכות המודרניות הפסיקו לקרוא אותם.",
      "הפיקדון המתכתי מופיע בדנקנ'ס מוניטור ובמוניטורים אחרים.",
    ],
    caution_notes: [
      "אל תציג את העונשים כאיומים ממשיים — הם סמלים. חשוב להדגיש את ההקשר הסמלי.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0008-entered-apprentice-or-first-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0011-entered-apprentice-degree", "duncans-ritual-monitor-1866-section-0008-entered-apprentice-or-first-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "l1-obligation-mashmaut-hahitchayvut", degree: "level1" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "elevated",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: ["l1-obligation-mashmaut-hahitchayvut"],
  },
];

// ─────────────────────────────────────────────────────────
// New Level 3 Entry
// ─────────────────────────────────────────────────────────

const NEW_LEVEL3_ENTRIES = [
  {
    title: "הכנת המועמד, התחייבות ועונש בדרגה שלישית",
    slug: "level3-mm-obligation-preparation-and-penalty",
    type: "topic",
    level3_content_type: "structural_framework",
    level3_type: "process",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "ceremony",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "ritual_meaning",
    parent_topic: null,
    aliases: ["הכנת המועמד דרגה 3", "MM Preparation", "שתי ברכיים חשופות", "Both Knees Bare", "כבל גרירה משולש", "Cable-Tow Three Times", "חציית הגוף", "Body Severed", "שריפת המעיים", "Bowels Burned"],
    keywords: ["שתי ברכיים", "both knees", "כבל גרירה", "משולש", "three times", "שתי הידיים", "both hands", "חציית הגוף", "body severed", "שריפת המעיים", "bowels burned", "אפר", "ashes", "פסולת המקדש", "rubbish", "קודש הקודשים", "sanctum sanctorum", "כפפות", "סינר", "white gloves", "aprons", "דרגה 3"],
    related_topics: {
      prior: ["level3-charge-and-duty-framework"],
      companion: ["level3-five-points-of-fellowship-value-structure", "level3-substitute-word-and-what-was-lost"],
      deeper: [],
    },
    short_summary:
      "בדרגה שלישית ההכנה מגיעה לשיא: שתי הברכיים חשופות, שתי הידיים על התנ\"ך, כבל הגרירה כרוך שלוש פעמים. העונשים הם החמורים ביותר: חציית הגוף לשניים ושריפת המעיים לאפר שיפוזר לארבע רוחות השמים. קודש הקודשים הוא המרחב שבו ההתחייבות הזו ניתנת.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, ההכנה של המועמד בדרגה 3 שונה מדרגות קודמות: שתי הברכיים חשופות (לא רק אחת), שתי הידיים מונחות על התנ\"ך (לא רק אחת), וכבל הגרירה כרוך שלוש פעמים. העונש הסמלי: הגוף ייחצה לשניים, המעיים יישרפו לאפר, והאפר יפוזר. פסולת המקדש (Rubbish of the Temple) היא המקום שבו הגופה נקברה ראשונה.",
      symbolic:
        "בקריאה הסמלית, הכפילות (שתי ברכיים, שתי ידיים, שלושה כריכות) מסמלת שבדרגה שלישית אין חצאי-מחויבויות. הכל כפול ומשולש — מלא. העונש הקשה ביותר (חציית הגוף, שריפת מעיים) מסמל שהפרת האמון בדרגה זו היא הפרה של הכל. קודש הקודשים מסמל את המקום הפנימי ביותר — שם, בנקודה הקדושה ביותר, ניתנת ההתחייבות הכבדה ביותר.",
      advanced:
        "בקריאה המבנית, מבנה ההכנה בשלוש הדרגות הוא פרוגרסיבי: דרגה 1 = אחד (ברך אחת, יד אחת, כריכה אחת); דרגה 2 = שניים (צד אחר, כריכה כפולה); דרגה 3 = הכל (שתי ברכיים, שתי ידיים, שלוש כריכות). המבנה המספרי (1-2-3) מקודד עלייה בחומרה ובמחויבות. כפפות וסינרים לבנים ניתנים כסמל לטוהר וכקישור חזרה לדרגה הראשונה.",
    },
    full_summary:
      "בדרגה השלישית, הכנת המועמד מגיעה לשיאה. שתי הברכיים חשופות (לא רק אחת כבדרגות קודמות), שתי הידיים מונחות על ספר החוקים הקדוש, וכבל הגרירה כרוך שלוש פעמים סביב הגוף.\n\nהעונשים הסמליים של דרגה שלישית הם החמורים ביותר: הגוף ייחצה לשניים (Body Severed in Two), המעיים יישרפו לאפר (Bowels Burned to Ashes), והאפר יפוזר לארבע רוחות השמים כך שלא יישאר זכר. פסולת המקדש (Rubbish of the Temple) מוזכרת כמקום שבו גופת חירם נקברה ראשונה על ידי המתנקשים.\n\nקודש הקודשים (Sanctum Sanctorum) — החלק הפנימי ביותר של המקדש — הוא ההקשר שבו ההתחייבות ניתנת. המסר: במקום הקדוש ביותר ניתנת ההבטחה הכבדה ביותר.\n\nכפפות וסינרים לבנים (White Gloves and Aprons) ניתנים כסמל לטוהר ולחזרה אל ראשית הדרך — תזכורת שגם בדרגה הגבוהה ביותר, הערכים הבסיסיים (תמימות, טוהר, עבודה) נשארים.",
    practical_elements: [
      "לשים לב למבנה הפרוגרסיבי: 1 → 2 → 3 — כל דרגה מגדילה את המחויבות בצורה מספרית.",
      "להבין שקודש הקודשים הוא סמל למקום הפנימי ביותר של ההתחייבות — לא מבנה פיזי.",
    ],
    symbolic_meaning:
      "ההכנה הכפולה והמשולשת מסמלת שבדרגה שלישית אין עוד מקום לחצי-מחויבות. העונשים החמורים מסמלים שהסודות של דרגה זו הם הכבדים ביותר. קודש הקודשים מייצג את הנקודה הפנימית ביותר של האדם — שם ניתנת השבועה.",
    candidate_lesson:
      "הלקח הוא שדרגה שלישית דורשת הכל: שתי ברכיים, שתי ידיים, שלוש כריכות. אין פשרה ואין מחצית. ההתחייבות המלאה היא התנאי למה שעומד להתגלות.",
    tradition_notes: [
      "מבנה ההכנה הפרוגרסיבי (1-2-3) מתועד בכל המוניטורים המרכזיים.",
      "קודש הקודשים מקביל למקום שבו ארון הברית עמד בבית המקדש.",
      "כפפות וסינרים לבנים ניתנים לרב-בונה החדש כסמל לטוהר.",
    ],
    caution_notes: [
      "אל תערבב בין פסולת המקדש (מקום קבורה ראשוני) לבין הגבעה המערבית (מקום קבורה שני).",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0064-third-section",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree", "blue-lodge-ritual-reference-guide-2021-section-0064-third-section"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-charge-and-duty-framework", degree: "level3" }, { slug: "level3-five-points-of-fellowship-value-structure", degree: "level3" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "elevated",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
];

// ─────────────────────────────────────────────────────────
// Infrastructure
// ─────────────────────────────────────────────────────────

function loadJson(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function writeJson(p, data) { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(data, null, 2) + "\n", "utf8"); }
function parseArgs(args) { let dryRun = false; let siteRoot = DEFAULT_SITE_ROOT; for (let i = 0; i < args.length; i++) { if (args[i] === "--dry-run") dryRun = true; if (args[i] === "--site-root" && args[i + 1]) siteRoot = path.resolve(args[++i]); } return { dryRun, siteRoot }; }

function checkForbiddenPatterns(entry, patterns, degreeLabel) {
  const contentOnly = {};
  for (const f of CONTENT_FIELDS_ONLY) { if (f in entry) contentOnly[f] = entry[f]; }
  const text = JSON.stringify(contentOnly);
  const violations = [];
  for (const { label, pattern } of patterns) { if (pattern.test(text)) violations.push({ slug: entry.slug, degree: degreeLabel, forbidden: label }); }
  return violations;
}

const REQUIRED_LEVEL1 = ["title","slug","type","level1_content_type","level1_type","depth_scope","boundary_guard_passed","knowledge_type","degree","applies_to_degrees","content_scope","partition_role","degree_owner","product_state","category","parent_topic","aliases","keywords","related_topics","short_summary","reading_layers","full_summary","practical_elements","symbolic_meaning","candidate_lesson","tradition_notes","caution_notes","source_notes","language","knowledge_links","chapter_toc","visibility_level","sensitivity_level","tradition_scope","status","observability","relies_on_level1_topics"];
const REQUIRED_LEVEL3 = ["title","slug","type","level3_content_type","level3_type","depth_scope","boundary_guard_passed","knowledge_type","degree","applies_to_degrees","content_scope","partition_role","degree_owner","product_state","category","parent_topic","aliases","keywords","related_topics","short_summary","reading_layers","full_summary","practical_elements","symbolic_meaning","candidate_lesson","tradition_notes","caution_notes","source_notes","language","knowledge_links","chapter_toc","visibility_level","sensitivity_level","tradition_scope","status","observability","relies_on_level1_topics"];

function checkRequiredFields(entry, requiredFields) { return requiredFields.filter((f) => !(f in entry)).map((f) => ({ slug: entry.slug, missing_field: f })); }

function main() {
  const { dryRun, siteRoot } = parseArgs(process.argv.slice(2));
  const executedAt = new Date().toISOString();
  const level1Path = path.join(siteRoot, "data", "level1.json");
  const level3Path = path.join(siteRoot, "data", "level3.json");
  const level1BackupPath = path.join(siteRoot, "data", "level1.pre_m18_wave4_backup.json");
  const level3BackupPath = path.join(siteRoot, "data", "level3.pre_m18_wave4_backup.json");

  const report = { phase: PHASE_ID, executed_at: executedAt, dry_run: dryRun, site_root: siteRoot, new_level1_slugs: NEW_LEVEL1_ENTRIES.map((e) => e.slug), new_level3_slugs: NEW_LEVEL3_ENTRIES.map((e) => e.slug), actions: [], overall_status: "pending" };
  const validation = { phase: PHASE_ID, executed_at: executedAt, checks: {}, failures: [], error_count: 0, overall_status: "pending" };

  try {
    const level1Data = loadJson(level1Path);
    const level3Data = loadJson(level3Path);
    const existingL1Slugs = new Set((level1Data.entries || []).map((e) => e.slug));
    const existingL3Slugs = new Set((level3Data.entries || []).map((e) => e.slug));

    const allViolations = [];
    const allMissingFields = [];
    for (const entry of NEW_LEVEL1_ENTRIES) { allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL1_PATTERNS, "level1")); allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL1)); }
    for (const entry of NEW_LEVEL3_ENTRIES) { allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL3_PATTERNS, "level3")); allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL3)); }

    validation.checks.boundary_clean = { passed: allViolations.length === 0, violations: allViolations };
    validation.checks.required_fields_complete = { passed: allMissingFields.length === 0, missing: allMissingFields };
    if (allViolations.length > 0) validation.failures.push({ check: "boundary_clean", detail: allViolations });
    if (allMissingFields.length > 0) validation.failures.push({ check: "required_fields_complete", detail: allMissingFields });

    const duplicateL1 = NEW_LEVEL1_ENTRIES.filter((e) => existingL1Slugs.has(e.slug)).map((e) => e.slug);
    const duplicateL3 = NEW_LEVEL3_ENTRIES.filter((e) => existingL3Slugs.has(e.slug)).map((e) => e.slug);
    validation.checks.no_duplicates = { passed: duplicateL1.length === 0 && duplicateL3.length === 0, duplicate_level1: duplicateL1, duplicate_level3: duplicateL3 };
    if (duplicateL1.length > 0 || duplicateL3.length > 0) validation.failures.push({ check: "no_duplicates", detail: { duplicateL1, duplicateL3 } });

    validation.error_count = validation.failures.length;
    validation.overall_status = validation.failures.length === 0 ? "pass" : "fail";

    if (validation.failures.length > 0) { report.overall_status = "fail"; report.error = "Validation failed."; writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation); console.error("Validation failed. No writes performed."); console.error(JSON.stringify(validation.failures, null, 2)); process.exitCode = 1; return; }

    report.actions.push({ action: "validation_passed" });

    if (dryRun) { report.overall_status = "dry_run_ok"; writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation); console.log("DRY RUN — no files written."); console.log("Would add L1:", NEW_LEVEL1_ENTRIES.map((e) => e.slug)); console.log("Would add L3:", NEW_LEVEL3_ENTRIES.map((e) => e.slug)); return; }

    fs.writeFileSync(level1BackupPath, JSON.stringify(level1Data, null, 2) + "\n", "utf8");
    fs.writeFileSync(level3BackupPath, JSON.stringify(level3Data, null, 2) + "\n", "utf8");
    report.actions.push({ action: "backups_written" });

    level1Data.entries = [...(level1Data.entries || []), ...NEW_LEVEL1_ENTRIES];
    level3Data.entries = [...(level3Data.entries || []), ...NEW_LEVEL3_ENTRIES];
    level1Data.meta = { ...level1Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };
    level3Data.meta = { ...level3Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };

    writeJson(level1Path, level1Data);
    writeJson(level3Path, level3Data);
    report.actions.push({ action: "entries_appended", level1_added: NEW_LEVEL1_ENTRIES.map((e) => e.slug), level3_added: NEW_LEVEL3_ENTRIES.map((e) => e.slug), level1_total: level1Data.entries.length, level3_total: level3Data.entries.length });
    report.overall_status = "success";
    writeJson(DEFAULT_REPORT_PATH, report);
    writeJson(DEFAULT_VALIDATION_PATH, validation);

    console.log(`Level 1: ${level1Data.entries.length} entries (added ${NEW_LEVEL1_ENTRIES.length})`);
    console.log(`Level 3: ${level3Data.entries.length} entries (added ${NEW_LEVEL3_ENTRIES.length})`);
    console.log(`Report: ${DEFAULT_REPORT_PATH}`);
  } catch (err) {
    report.overall_status = "fail"; report.error = err.message; validation.overall_status = "fail";
    writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation);
    console.error(err.message); process.exitCode = 1;
  }
}

main();
