/**
 * apply_phase_m_17_wave3_fill.js
 *
 * Wave 3 topic expansion — adds 4 new Level 2 entries and 3 new Level 3 entries.
 *
 * Level 2 new candidates:
 *   - level2-fc-apron-and-dress-symbolism
 *   - level2-intellectual-illumination-and-integration
 *   - level2-seven-arts-five-orders-five-senses-system
 *   - level2-fc-preparation-and-candidate-body
 *
 * Level 3 new candidates:
 *   - level3-substitute-word-and-what-was-lost
 *   - level3-search-for-the-body-process
 *   - level3-mm-working-tools-and-mortality-symbols
 *
 * Usage:
 *   node PDF_handle/TOOLS/apply_phase_m_17_wave3_fill.js [--dry-run] [--site-root <path>]
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m17_wave3_fill";
const DEFAULT_SITE_ROOT = path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_17_wave3_fill_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_17_wave3_fill_validation.json");

const FORBIDDEN_LEVEL3_PATTERNS = [
  { label: "royal_arch", pattern: /royal arch/iu },
  { label: "return_from_babylon", pattern: /babylon/iu },
  { label: "hidden_vault", pattern: /vault/iu },
];

const FORBIDDEN_LEVEL2_PATTERNS = [
  { label: "master_mason_content", pattern: /master mason/iu },
  { label: "raising_body", pattern: /raising.*body/iu },
];

const CONTENT_FIELDS_ONLY = ["short_summary", "full_summary", "reading_layers", "symbolic_meaning", "candidate_lesson", "practical_elements", "aliases", "keywords"];

// ─────────────────────────────────────────────────────────
// New Level 2 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL2_ENTRIES = [
  {
    title: "סינר חבר-בונה וסמלות הלבוש הטקסי",
    slug: "level2-fc-apron-and-dress-symbolism",
    type: "topic",
    level2_content_type: "structural_framework",
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
    category: "fc_dress_and_preparation",
    parent_topic: null,
    aliases: ["סינר חבר-בונה", "FC Apron", "דש מורד ופינה מורמת", "Flap down corner up"],
    keywords: ["סינר", "דש", "פינה", "לבוש טקסי", "עור כבש", "דרגה 2", "חבר-בונה"],
    related_topics: {
      prior: ["level2-preparation-as-structured-transition"],
      companion: ["level2-operative-vs-speculative-framing", "level2-fc-jewels-ear-tongue-breast"],
      deeper: [],
    },
    short_summary:
      "בדרגה שנייה הסינר משתנה: הדש יורד והפינה מורמת. שינוי זה מסמל מעבר מלומד פסיבי (דרגה 1, דש מורם כמגן) לעובד פעיל (דרגה 2, פינה מורמת כסימן למלאכה). הסינר הוא עור כבש לבן — סמל לתמימות ולטוהר — והוא האות הנראה ביותר של השתייכות לאחווה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, סינר חבר-הבונה עשוי מעור כבש לבן. בדרגה ראשונה הדש מורם כלפי מעלה; בדרגה שנייה הדש מורד והפינה השמאלית התחתונה מורמת. הסינר הוא הלבוש הטקסי הראשון שהחניך מקבל, ומי שנפטר נקבר עמו. הוא עתיק יותר מכל עיטור אחר.",
      symbolic:
        "בקריאה הסמלית, הדש המורם בדרגה 1 מייצג מגן — החניך עדיין צריך הגנה. כשהדש יורד בדרגה 2, ההגנה הופכת לעבודה: חבר-הבונה כבר לא זקוק למגן אלא לכלי עבודה. הפינה המורמת מסמלת שהמלאכה התחילה אך טרם הושלמה. עור הכבש מייצג תמימות שלא ניתן לקנות.",
      advanced:
        "בקריאה המבנית, הסינר הוא מערכת סימנים ויזואלית שמתעדכנת עם כל דרגה. כל שינוי בדש או בפינה מקודד מעמד: מה האדם כבר עשה, ומה עדיין לפניו. כך הסינר הופך ל'תעודת זהות' חזותית. בדרגה 2, המסר הוא: המלאכה כבר בעיצומה, ההגנה כבר לא נדרשת, אך הסיום עוד לא הגיע.",
    },
    full_summary:
      "הסינר הוא הלבוש הטקסי העתיק והחשוב ביותר בבנייה החופשית. עשוי מעור כבש לבן, הוא מייצג תמימות וטוהר שלא ניתן לקנות ושאין מלך יכול להעניק.\n\nבדרגה הראשונה, הדש (Flap) מורם כלפי מעלה — סמל להגנה. התלמיד עדיין בתחילת דרכו וזקוק למגן. בדרגה השנייה, הדש מורד והפינה השמאלית התחתונה מורמת. מעבר זה מסמל שחבר-הבונה כבר עובד, ולא רק לומד: הפינה המורמת היא סימן למלאכה פעילה שטרם הושלמה.\n\nהסינר הוא האות הנראה ביותר של השתייכות. מי שנכנס ללשכה לובש סינר; מי שנפטר נקבר עמו. הוא מקשר בין עולם האופרטיבי (סינר אמיתי של בנאי) לעולם העיוני (סינר טקסי של אחווה). בדרגה שנייה, שינוי הסינר מלמד שהידע והמעמד אינם מילים בלבד — הם נראים לעין.",
    practical_elements: [
      "לשים לב לאופן הלבישה של הסינר בלשכה — הוא מעיד על הדרגה והמעמד.",
      "להבין שהסינר אינו תלבושת אלא סמל: שינוי הדש והפינה מקודד את ההתקדמות.",
    ],
    symbolic_meaning:
      "הסינר מסמל שהשתייכות לאחווה אינה מופשטת אלא נראית. הדש שיורד מלמד שההגנה כבר לא נחוצה; הפינה שעולה מלמדת שהעבודה בעיצומה. עור הכבש הוא תמימות שלא נקנית — רק נשמרת.",
    candidate_lesson:
      "הלקח של סינר חבר-הבונה הוא שכל דרגה משנה את מה שנראה כלפי חוץ. הסינר אינו רק לבוש — הוא מראה לכולם מה עשית ומה נותר לך לעשות.",
    tradition_notes: [
      "הסינר מתואר כ'עתיק יותר מגיזת הזהב או מנשר הרומי'.",
      "הטקסט קובע: 'more ancient than the Golden Fleece or Roman Eagle'.",
      "נוהג קבורה עם הסינר מוזכר בפולחן ובשירותי הלוויה.",
    ],
    caution_notes: [
      "בדרגה שלישית הסינר משתנה שוב (כל הפינות מורדות) — אל תערבב בין שלוש התצורות.",
    ],
    source_notes: [
      "מקור עיקרי: deeper-meaning-of-fc-degree-section-0010-the-apron",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["deeper-meaning-of-fc-degree-section-0010-the-apron", "blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-operative-vs-speculative-framing", degree: "level2" }, { slug: "level2-fc-jewels-ear-tongue-breast", degree: "level2" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: ["l1-tools-mashmaut-meshulevet-klei-hatalmid"],
  },
  {
    title: "הארה שכלית ואיחוד השכל והלב",
    slug: "level2-intellectual-illumination-and-integration",
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
    aliases: ["הארה שכלית", "Mental Illumination", "איחוד השכל והלב", "Reason and Intuition"],
    keywords: ["הארה", "שכל", "לב", "אינטואיציה", "חושים", "עליית מדרגה", "דרגה 2"],
    related_topics: {
      prior: ["level2-geometry-and-letter-g-intellectual-center"],
      companion: ["level2-winding-stairs-as-ascent-process", "level2-seven-arts-five-orders-five-senses-system"],
      deeper: [],
    },
    short_summary:
      "דרגה שנייה מלמדת שהידע אינו מסתיים בחושים — הוא מתחיל בהם. חמשת החושים קולטים את העולם, אך רק ההארה השכלית ממיינת, מבינה ומחברת. איחוד השכל והלב פירושו שלמידה אמיתית היא גם רציונלית וגם אינטואיטיבית.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, הלקטורה של דרגת חבר-בונה מתארת מסע מהחושים אל השכל. חמשת החושים (שמיעה, ראייה, תחושה, ריח, טעם) הם השער הראשון, אך הם לא מספיקים. ההארה השכלית (Mental Illumination) היא השלב שבו הידע מתחבר ומשתלב — לא רק עובדות אלא הבנה.",
      symbolic:
        "בקריאה הסמלית, המסע מחושים לשכל מייצג עלייה מחומר לרוח. החושים שייכים לגוף — הם מוגבלים, שטחיים, מיידיים. ההארה השכלית שייכת לנפש — היא מקשרת, מפרשת ובונה. האות G בלשכה האמצעית מסמלת את נקודת המפגש: גיאומטריה (שכל) ואלוהות (לב).",
      advanced:
        "בקריאה המבנית, 'הארה שכלית' היא לא רגע חד-פעמי אלא תהליך מתמשך שדרגה 2 מתארת כמבנה: חושים → סדר → שכל → אינטגרציה. האיחוד של שכל ולב פירושו שלמידה ללא חמלה היא ריקה, וחמלה ללא ידע היא עיוורת. דרגה 2 טוענת ששניהם נדרשים.",
    },
    full_summary:
      "אחד המוטיבים המרכזיים בלקטורה של דרגת חבר-בונה הוא המסע השכלי: מתוך החושים הגשמיים ודרכם אל הבנה שלמה יותר. חמשת החושים (Five Senses) מוזכרים כשער הראשון — הם הדרך שבה אדם קולט מידע מהעולם. אך הדרגה מלמדת שתפיסה חושית לבדה אינה מספקת.\n\nההארה השכלית (Mental Illumination) היא השלב הבא: לא רק לראות ולשמוע, אלא להבין. גיאומטריה, לפי הלקטורה, היא מלכת המדעים מפני שהיא מלמדת סדר, מבנה ויחס — דברים שהחושים לבדם לא יכולים ללמד.\n\nהמעבר מחושים לשכל אינו חד-כיווני. הדרגה מציעה שהשכל צריך גם את הלב — אינטואיציה, חמלה, הקשבה פנימית. איחוד זה מוביל למה שהטקסט קורא 'הארה': מצב שבו הידע אינו רק מידע אלא הבנה חיה, משולבת ופעילה. האות G, שמסמלת גם אלוהות וגם גיאומטריה, מגלמת איחוד זה.",
    practical_elements: [
      "להקשיב לא רק לעובדות (חושים) אלא גם להקשר ולמשמעות (שכל).",
      "לזהות את ההבדל בין 'לדעת' (מידע) לבין 'להבין' (אינטגרציה) בלמידה.",
    ],
    symbolic_meaning:
      "ההארה השכלית מסמלת שמטרת הלמידה היא לא צבירת עובדות אלא בניית הבנה. חמשת החושים הם שער; השכל הוא הנתיב; הלב הוא היעד. האות G מייצגת את נקודת האיחוד.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שידע אמיתי דורש גם שכל וגם לב. מי שרק מנתח — מחמיץ את החמלה. מי שרק מרגיש — מחמיץ את הסדר. חבר-הבונה מבקש לאחד את שניהם.",
    tradition_notes: [
      "הלקטורה של הדרגה השנייה מקדישה חלק נרחב לחמשת החושים ולשבע האמנויות.",
      "הביטוי 'Mental Illumination' מופיע בהרצאות של מוניטורים מהמאה ה-19.",
    ],
    caution_notes: [
      "אל תערבב בין 'הארה שכלית' של דרגה 2 לבין 'אור רוחני' של דרגות גבוהות יותר.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0055-geometry",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0051-the-five-senses",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0055-geometry", "blue-lodge-ritual-reference-guide-2021-section-0051-the-five-senses"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-geometry-and-letter-g-intellectual-center", degree: "level2" }, { slug: "level2-winding-stairs-as-ascent-process", degree: "level2" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: ["l1-or-meshulash-basisei-haor-balishka"],
  },
  {
    title: "שבע האמנויות, חמשת הסדרים וחמשת החושים כמערכת ידע",
    slug: "level2-seven-arts-five-orders-five-senses-system",
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
    category: "fc_learning_structure",
    parent_topic: null,
    aliases: ["שבע האמנויות והמדעים", "Seven Liberal Arts", "חמשת סדרי האדריכלות", "Five Orders of Architecture", "חמשת החושים", "Five Senses"],
    keywords: ["שבע אמנויות", "חמישה סדרים", "חמישה חושים", "טוסקני", "דורי", "יוני", "קורינתי", "משולב", "דקדוק", "רטוריקה", "לוגיקה", "אריתמטיקה", "גיאומטריה", "מוסיקה", "אסטרונומיה", "דרגה 2"],
    related_topics: {
      prior: ["level2-winding-stairs-as-ascent-process"],
      companion: ["level2-geometry-and-letter-g-intellectual-center", "level2-intellectual-illumination-and-integration"],
      deeper: [],
    },
    short_summary:
      "שלוש הקבוצות — חמשת החושים, חמשת סדרי האדריכלות ושבע האמנויות והמדעים — הן התוכן שממלא את מבנה המדרגות הלולייניות. יחד הן מרכיבות קוריקולום שלם: קליטה (חושים), מבנה (סדרים) וידע (אמנויות). הסדר אינו מקרי.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, הלקטורה של חבר-בונה מונה שלוש קבוצות ידע. חמשת החושים (שמיעה, ראייה, תחושה, ריח, טעם) — הדרך שבה אדם קולט את העולם. חמשת סדרי האדריכלות (טוסקני, דורי, יוני, קורינתי, משולב) — הדרך שבה אדם מארגן את מה שקלט. שבע האמנויות והמדעים (דקדוק, רטוריקה, לוגיקה, אריתמטיקה, גיאומטריה, מוסיקה, אסטרונומיה) — הדרך שבה אדם מרחיב את הידע.",
      symbolic:
        "בקריאה הסמלית, שלוש הקבוצות מייצגות שלושה שלבי למידה עולים: קליטה → מבנה → ידע. החושים הם הדלת; סדרי האדריכלות הם השלד; האמנויות הן הגוף. המספרים עצמם (5, 5, 7) נושאים משמעות: חמש = יד אחת = חישה; שבע = שלמות = ידע מושלם.",
      advanced:
        "בקריאה המבנית, הקוריקולום של דרגה 2 בנוי כפירמידה: בבסיס — מה שהגוף תופס (חושים), באמצע — מה שהשכל מארגן (סדרי אדריכלות כדגם ל'סדר'), ובראש — מה שהנפש מבינה (אמנויות). שילוב זה מלמד שלמידה אינה רק צבירה אלא בנייה — מבנה שעולה מנתונים גולמיים אל הבנה מופשטת.",
    },
    full_summary:
      "בלקטורה של דרגת חבר-בונה, המדרגות הלולייניות מלאות בתוכן: קבוצות ידע מספריות שיחד מרכיבות קוריקולום שלם.\n\nחמשת החושים (שמיעה, ראייה, תחושה, ריח, טעם) הם השכבה הראשונה — מה שהגוף קולט. ללא חושים אין ידע, אך חושים לבדם אינם מספיקים.\n\nחמשת סדרי האדריכלות (טוסקני, דורי, יוני, קורינתי, משולב) הם השכבה השנייה — מה שהשכל מארגן. כל סדר אדריכלי מייצג יחס שונה בין כוח לנוי, בין פשטות למורכבות. הם מלמדים שהסדר עצמו הוא ערך.\n\nשבע האמנויות והמדעים (דקדוק, רטוריקה, לוגיקה, אריתמטיקה, גיאומטריה, מוסיקה, אסטרונומיה) הן השכבה השלישית — מה שהנפש מבינה. הן מחולקות ל'טריוויום' (שפה) ו'קוואדריוויום' (מספר), ויחד הן מייצגות את מלוא הידע האנושי כפי שהעולם הקלאסי הבין אותו.\n\nשלוש הקבוצות אינן רשימה מקרית. הן מסודרות כפירמידת למידה: תפיסה → ארגון → הבנה. הסדר חשוב.",
    practical_elements: [
      "לזהות את שלושת שלבי הלמידה בחיי היום-יום: מה אני קולט (חושים)? מה אני מארגן (מבנה)? מה אני באמת מבין (ידע)?",
      "להכיר את חמשת סדרי האדריכלות ושבע האמנויות כמערכת, לא כרשימה.",
    ],
    symbolic_meaning:
      "שלוש הקבוצות יחד מסמלות שלמידה היא בנייה מדורגת: מהגוף (חושים) דרך הסדר (אדריכלות) אל השכל (אמנויות). המספרים 5-5-7 מקודדים מסע עולה.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שלמידה אמיתית אינה רשימה של עובדות אלא מבנה: קליטה, ארגון, הבנה. מי שמדלג על שלב — בונה בניין ללא יסודות.",
    tradition_notes: [
      "שבע האמנויות החופשיות מקורן בחינוך הקלאסי היווני-רומי.",
      "חלוקת הטריוויום (שפה) והקוואדריוויום (מספר) שימשה את האוניברסיטאות הראשונות באירופה.",
      "חמשת סדרי האדריכלות מבוססים על ויטרוביוס ופלאדיו.",
    ],
    caution_notes: [
      "אל תתייחס לחמשת החושים כאל 'דרגה נמוכה' — הלקטורה מציגה אותם כנדבך הכרחי.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0052-the-liberal-arts-and-sciences",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0050-the-five-orders-in-architecture",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0051-the-five-senses",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0052-the-liberal-arts-and-sciences",
      "blue-lodge-ritual-reference-guide-2021-section-0050-the-five-orders-in-architecture",
      "blue-lodge-ritual-reference-guide-2021-section-0051-the-five-senses",
    ],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-winding-stairs-as-ascent-process", degree: "level2" }, { slug: "level2-geometry-and-letter-g-intellectual-center", degree: "level2" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
  {
    title: "הכנת המועמד וחשיפת הגוף בדרגה שנייה",
    slug: "level2-fc-preparation-and-candidate-body",
    type: "topic",
    level2_content_type: "structural_framework",
    level2_type: "process",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "ceremony",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "fc_dress_and_preparation",
    parent_topic: null,
    aliases: ["הכנת המועמד", "FC Preparation", "ברך ימנית חשופה", "חזה ימני חשוף", "כבל גרירה כפול"],
    keywords: ["ברך ימנית", "חזה ימני", "כבל גרירה", "כפול", "הכנה", "חשיפה", "מועמד", "דרגה 2"],
    related_topics: {
      prior: ["level2-preparation-as-structured-transition"],
      companion: ["level2-cable-tow-entry-and-guided-movement-process", "level2-fc-apron-and-dress-symbolism"],
      deeper: [],
    },
    short_summary:
      "בדרגה שנייה, ההכנה הגופנית של המועמד משתנה: הברך הימנית חשופה (במקום השמאלית בדרגה 1), החזה הימני חשוף, וכבל הגרירה כרוך פעמיים. כל שינוי מקודד עומק מחויבות גדל — לא חזרה אלא העמקה של אותו תהליך.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, המועמד בדרגה 2 מוכן כך: העין מכוסה (hoodwink), הברך הימנית חשופה, החזה הימני חשוף, הרגל הימנית יחפה, וכבל הגרירה כרוך פעמיים סביב הזרוע. כל פרט הוא שינוי מדרגה 1 — שם הצד השמאלי חשוף וכבל הגרירה כרוך פעם אחת.",
      symbolic:
        "בקריאה הסמלית, המעבר מצד שמאל לצד ימין מייצג התקדמות. שמאל = קבלה; ימין = פעולה. הברך הימנית החשופה מייצגת נכונות לכרוע בעומק רב יותר. כבל הגרירה הכפול מסמל שהמחויבות גדלה — לא שהאדם פחות חופשי, אלא שהוא מקבל על עצמו יותר.",
      advanced:
        "בקריאה המבנית, הכנת הגוף בכל דרגה היא מערכת מקבילית: אותם אלמנטים (ברך, חזה, כבל, עין) חוזרים אך משתנים. השינוי אינו מקרי — הוא מקודד. דרגה 1 = שמאל + פעם אחת. דרגה 2 = ימין + פעמיים. מבנה זה מלמד שהטקס הוא שפה: כל שינוי קטן נושא משמעות.",
    },
    full_summary:
      "בכל דרגה, המועמד עובר הכנה גופנית לפני כניסתו ללשכה. בדרגה שנייה ההכנה כוללת: כיסוי עיניים (Hoodwink), חשיפת הברך הימנית, חשיפת החזה הימני, הסרת נעל מהרגל הימנית, וכבל גרירה (Cable-Tow) כרוך פעמיים סביב הזרוע.\n\nכל פרט הוא שינוי ממה שנעשה בדרגה הראשונה, שבה הצד השמאלי נחשף וכבל הגרירה נכרך פעם אחת. המעבר מצד שמאל לצד ימין מייצג שינוי כיוון: מקבלה (שמאל) לפעולה (ימין). כבל הגרירה הכפול מסמל שהמחויבות גדלה — לא שהאדם מוגבל יותר, אלא שהוא מקבל על עצמו יותר.\n\nהכנת הגוף היא שפה טקסית: כל שינוי קטן בין דרגה לדרגה מקודד משמעות. הברך החשופה מייצגת ענווה ונכונות לכרוע; החזה החשוף מייצג פתיחות ואי-הסתרה; הרגל היחפה מייצגת מגע ישיר עם אדמת קודש.",
    practical_elements: [
      "לשים לב לכל ההבדלים בין הכנת דרגה 1 להכנת דרגה 2 — השינויים מכוונים.",
      "להבין שכבל הגרירה הכפול אינו עונש אלא סמל להעמקת המחויבות.",
    ],
    symbolic_meaning:
      "ההכנה הגופנית מסמלת שהגוף עצמו הוא חלק מהטקס. כל חשיפה היא הצהרה: אני מוכן, אני פתוח, אני מקבל על עצמי. המעבר משמאל לימין מלמד שהעבודה הופכת מפסיבית לפעילה.",
    candidate_lesson:
      "הלקח הוא שהדרגה השנייה אינה חזרה על הראשונה — היא העמקה. אותו תהליך, אותם אלמנטים, אבל הכל עמוק יותר, מחייב יותר, ודורש יותר.",
    tradition_notes: [
      "ההכנה הגופנית מתוארת בפירוט בדנקנ'ס מוניטור ובמוניטורים אחרים.",
      "ההבדלים בין צד שמאל לימין מוזכרים בכל המסורות המרכזיות.",
    ],
    caution_notes: [
      "אל תפרט את ההכנה של דרגה 3 בהקשר זה — היא שונה שוב ושייכת למשמעות אחרת.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree", "duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-cable-tow-entry-and-guided-movement-process", degree: "level2" }, { slug: "level2-preparation-as-structured-transition", degree: "level2" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: ["l1-ritual-hahovala-harishona-bemerkhav-halishka"],
  },
];

// ─────────────────────────────────────────────────────────
// New Level 3 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL3_ENTRIES = [
  {
    title: "המילה החלופית ומה שאבד",
    slug: "level3-substitute-word-and-what-was-lost",
    type: "topic",
    level3_content_type: "structural_framework",
    level3_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "concept",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "ritual_meaning",
    parent_topic: null,
    aliases: ["המילה החלופית", "Substitute Word", "מה שאבד", "What Was Lost", "טובל קין", "Tubal Cain"],
    keywords: ["מילה חלופית", "אבדה", "טובל קין", "סוד", "דרגה 3", "מילה אמיתית"],
    related_topics: {
      prior: ["level3-hiram-loss-and-fidelity-system"],
      companion: ["level3-raising-and-restoration-process", "level3-five-points-of-fellowship-value-structure"],
      deeper: [],
    },
    short_summary:
      "כשחירם נרצח, המילה האמיתית אבדה עמו. בדרגה השלישית, המילה שניתנת היא מילה חלופית — תחליף, לא המקור. 'מה שאבד' אינו רק סוד טכני אלא ביטוי למצב האנושי: ידע מושלם הוא בלתי ניתן להשגה, ובכל זאת השאיפה אליו היא החובה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, חירם אביף היה היחיד שידע את המילה האמיתית. כשנרצח, המילה אבדה. שלמה המלך קבע שהמילה הראשונה שתיאמר כשהגופה תימצא תשמש כמילה חלופית. טובל קין מוזכר כשם נוסף הקשור לזיהוי ולמעבר.",
      symbolic:
        "בקריאה הסמלית, המילה האבודה מייצגת ידע מושלם שאדם אינו יכול להגיע אליו. המילה החלופית היא הודאה בכך: אנחנו עובדים עם תחליף, לא עם מקור. זהו מצב של ענווה שכלית — היודע באמת יודע שאינו יודע הכל.",
      advanced:
        "בקריאה המבנית של דרגה 3, 'מה שאבד' הוא מושג מרכזי שנותן לדרגה את מבנה הדרמה שלה. אם המילה לא הייתה אובדת, לא היה צורך בחיפוש, בהקמה ובמילה חלופית. האבדן הוא מנוע הסיפור כולו. העובדה שהדרגה אינה מחזירה את המקור אלא רק תחליף מלמדת שהדרגה השלישית חיה עם חוסר שלמות מודע.",
    },
    full_summary:
      "בלב הסיפור של דרגת רב-בונה עומד האבדן: חירם אביף, שהיה היחיד שידע את המילה האמיתית, נרצח על ידי שלושה מתנקשים. עם מותו, המילה אבדה.\n\nשלמה המלך, כשנודע לו על הרצח, קבע שהמילה הראשונה שתיאמר ברגע גילוי הגופה תהפוך למילה חלופית — תחליף זמני למילה שאבדה. המילה החלופית ניתנת לכל רב-בונה בטקס ההקמה, יחד עם חמש נקודות האחווה.\n\nהשם טובל קין (Tubal Cain), שמופיע כמילת מעבר (Pass Word) של הדרגה, מקשר לדמות מקראית שהייתה 'לוטשת כל חורש נחושת וברזל' — סמל לאומנות ולמלאכה.\n\nמושג 'מה שאבד' הוא מרכזי: הוא מלמד שידע מושלם אינו זמין לבני אדם, אך השאיפה אליו היא המניע. הדרגה השלישית חיה עם חוסר שלמות מודע — לא ייאוש, אלא ענווה.",
    practical_elements: [
      "להבין שהמילה שניתנת בדרגה שלישית היא חלופית — תחליף, לא מקור.",
      "לזהות את 'מה שאבד' כמצב אנושי: השאיפה לשלמות מבלי להגיע אליה.",
    ],
    symbolic_meaning:
      "המילה החלופית מסמלת שכל ידע אנושי הוא קירוב, לא מקור. האבדן של חירם אינו רק טרגדיה אלא מנוע: הוא יוצר את הצורך בחיפוש, בחלופה ובענווה. 'מה שאבד' הוא מה שמניע את כל הדרגה.",
    candidate_lesson:
      "הלקח הוא שדרגה 3 אינה מציעה תשובה שלמה — היא מציעה מודעות לחוסר. המילה החלופית מלמדת שלחיות עם תחליף בכנות טוב מלהתיימר שיש לך את המקור.",
    tradition_notes: [
      "המילה החלופית ניתנת בזמן ההקמה, בחמש נקודות האחווה.",
      "טובל קין מופיע בבראשית ד:כב כלוטש נחושת וברזל.",
      "במסורות שונות, המילה האמיתית מתגלה בדרגות גבוהות יותר — אך בלו ג'ודג' היא נשארת אבודה.",
    ],
    caution_notes: [
      "אין להרחיב כאן אל תוך גילוי המילה בדרגות מעבר ללו ג'ודג' — זה חומר שאינו שייך לדרגה שלישית.",
      "אל תכתוב את המילה החלופית עצמה בטקסט פתוח.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0068-q-what-did-they-do-with-the-body",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree", "duncans-ritual-monitor-1866-section-0068-q-what-did-they-do-with-the-body"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-hiram-loss-and-fidelity-system", degree: "level3" }, { slug: "level3-raising-and-restoration-process", degree: "level3" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "elevated",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
  {
    title: "חיפוש הגופה והמסע אל הגבעה",
    slug: "level3-search-for-the-body-process",
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
    aliases: ["חיפוש הגופה", "Search for the Body", "שנים עשר החברים", "Twelve Fellow Crafts", "גבעה מערבית", "Hill West of Mt. Moriah"],
    keywords: ["חיפוש", "גופה", "שנים עשר", "חברים", "גבעה", "מוריה", "נקיקי סלעים", "חצות", "שיטה", "דרגה 3"],
    related_topics: {
      prior: ["level3-three-ruffians-and-gates-dramatic-structure"],
      companion: ["level3-acacia-grave-and-immortality-relationship", "level3-raising-and-restoration-process"],
      deeper: [],
    },
    short_summary:
      "לאחר הרצח, שלמה שלח שתים-עשרה קבוצות חברים לחפש את חירם. החיפוש עבר דרך נקיקי סלעים ומדבריות, ובסופו של דבר הגופה נמצאה בגבעה מערבית להר המוריה, מסומנת בענף שיטה. תהליך החיפוש עצמו הוא הטקס.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, כששלמה הבין שחירם נעלם, הוא שלח שתים-עשרה קבוצות של חברי-בונים לחפש אותו. שלוש קבוצות הלכו דרומה, שלוש צפונה, שלוש מזרחה ושלוש מערבה. לאחר חיפוש ארוך, הקבוצה שהלכה מערבה מצאה גבעה ליד הר המוריה ועליה ענף שיטה שנראה לא טבעי. כשחפרו — גילו את גופת חירם.",
      symbolic:
        "בקריאה הסמלית, החיפוש מייצג את המסע האנושי לגלות את מה שאבד. שתים-עשרה הקבוצות לארבע רוחות השמים מסמלות חיפוש מקיף שאינו משאיר פינה. נקיקי הסלעים מייצגים את המקומות הקשים ביותר. הגבעה המערבית — כיוון מערב = שקיעה = מוות — היא המקום שבו הנסתר מתגלה.",
      advanced:
        "בקריאה המבנית של דרגה 3, תהליך החיפוש הוא חלק מהמבנה הדרמטי: רצח → חיפוש → גילוי → הקמה. ללא החיפוש, אין גילוי; ללא גילוי, אין הקמה. שנים-עשר החברים שחזרו בתשובה (שנודע להם על הקנוניה אך לא מנעו אותה) מוסיפים שכבת אשמה ותיקון: החיפוש הוא גם כפרה.",
    },
    full_summary:
      "לאחר שנודע לשלמה המלך שחירם אביף נעלם, הוא שלח שתים-עשרה קבוצות של חברי-בונים לחפש אותו — שלוש לכל כיוון. המסורת מספרת ששנים-עשר חברים מתוך קבוצת המתנקשים ידעו על הקנוניה אך חזרו בתשובה ודיווחו לשלמה.\n\nהחיפוש כלל מסע דרך נקיקי סלעים, מדבריות ומקומות סתר. בחצות (Low Twelve), כשהתקווה כמעט אבדה, אחת הקבוצות הגיעה לגבעה מערבית להר המוריה ושמה לב לענף שיטה שצמח באופן לא טבעי מהאדמה. כשחפרו, גילו את גופת חירם.\n\nתהליך החיפוש אינו רק תיאור סיפורי — הוא חלק מהמבנה הטקסי. החיפוש הוא שלב הכרחי: ללא חיפוש אין גילוי, ללא גילוי אין הקמה, ללא הקמה אין מילה חלופית. כל הדרגה בנויה כשרשרת שמתחילה ברצח ומגיעה דרך חיפוש לתיקון חלקי.",
    practical_elements: [
      "לזהות שבתהליך החיפוש עצמו יש ערך — לא רק בתוצאה.",
      "להבין את תפקיד שנים-עשר החברים כדוגמה לחזרה בתשובה ותיקון.",
    ],
    symbolic_meaning:
      "החיפוש מסמל שאמת נמצאת רק למי שמחפש בנחישות, גם במקומות החשוכים ביותר. ענף השיטה שמסמן את הקבר מלמד שהחיים (הצמח) מצביעים על מקום המוות. הגבעה המערבית — כיוון השקיעה — מסמלת שגילוי מגיע דווקא בנקודת החושך.",
    candidate_lesson:
      "הלקח הוא שתהליך החיפוש עצמו הוא חלק מהתשובה. מי שלא מחפש — לא מוצא. ומי שמחפש מגלה לא רק את מה שחיפש, אלא גם את עצמו.",
    tradition_notes: [
      "גרסאות שונות מספרות על 12 או 15 חברים ששלמה שלח.",
      "נקיקי הסלעים (Clefts of the Rocks) מוזכרים בחלק מהמוניטורים כמקום מחבוא של הרוצחים.",
      "Low Twelve (חצות) מנוגד ל-High Twelve (צהריים) — שעת ההרצח.",
    ],
    caution_notes: [
      "אל תערבב בין חיפוש הגופה של דרגה 3 לבין גילוי הכמרה בדרגות אחרות — אלו סיפורים נפרדים.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0062-second-section",
      "מקור תומך: duncans-ritual-monitor-1866-section-0068-q-what-did-they-do-with-the-body",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0062-second-section", "duncans-ritual-monitor-1866-section-0068-q-what-did-they-do-with-the-body"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-three-ruffians-and-gates-dramatic-structure", degree: "level3" }, { slug: "level3-acacia-grave-and-immortality-relationship", degree: "level3" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "elevated",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: [],
  },
  {
    title: "כלי העבודה וסמלי התמותה של דרגה שלישית",
    slug: "level3-mm-working-tools-and-mortality-symbols",
    type: "topic",
    level3_content_type: "structural_framework",
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
    category: "ritual_meaning",
    parent_topic: null,
    aliases: ["כלי עבודה דרגה 3", "MM Working Tools", "כף בנאים", "Trowel", "שעון חול", "Hour Glass", "חרמש", "Scythe", "העין הבוחנת", "All-Seeing Eye"],
    keywords: ["כף בנאים", "שעון חול", "חרמש", "עין בוחנת", "תמותה", "זמן", "כלי עבודה", "דרגה 3"],
    related_topics: {
      prior: ["level3-charge-and-duty-framework"],
      companion: ["level3-third-degree-tracing-board-map", "level3-burial-honor-and-memorial-structure"],
      deeper: [],
    },
    short_summary:
      "כלי העבודה של דרגה שלישית הם כף הבנאים (Trowel) — כלי שמפזר את המלט של האחווה — ולצדה סמלי התמותה: שעון החול שמזכיר שהזמן אוזל, והחרמש שמזכיר שהמוות אינו מבחין בין בני אדם. העין הבוחנת צופה בכל — לא כאיום אלא כנוכחות מוסרית.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, כף הבנאים היא הכלי של דרגה 3. היא מפזרת מלט — חומר שמחבר אבנים — ומסמלת את החיבור בין בני אדם. שעון החול מראה שזמן החיים מוגבל. החרמש (Scythe) מלמד שהמוות קוצר את כולם ללא הבחנה. העין הבוחנת (All-Seeing Eye) מסמלת שיש מי שרואה את כל מעשינו.",
      symbolic:
        "בקריאה הסמלית, כף הבנאים מייצגת את הפעולה המרכזית של דרגה 3: לחבר. אם דרגה 1 מלמדת לחצוב (קורנס) ודרגה 2 מלמדת למדוד (זוויתן, פלס, מפלס), דרגה 3 מלמדת לחבר — לא אבנים, אלא אנשים. שעון החול והחרמש הם זוג: הזמן אוזל, והמוות מגיע. העין הבוחנת מקשרת: אם אתה יודע שהזמן קצר ושמישהו רואה — תפעל נכון.",
      advanced:
        "בקריאה המבנית, כלי העבודה של שלוש הדרגות מרכיבים מערכת אחת. דרגה 1: כלי חציבה (הכנת חומר). דרגה 2: כלי מדידה (ארגון חומר). דרגה 3: כלי חיבור (בניית מבנה שלם). סמלי התמותה מוסיפים את הציר הרביעי: הזמן. כל הבנייה מתרחשת בתוך חלון זמן מוגבל.",
    },
    full_summary:
      "בדרגה השלישית, כלי העבודה הם כף הבנאים (Trowel) — כלי שמפזר מלט ומחבר אבנים זו לזו. בעוד הקורנס של דרגה 1 מחצב והזוויתן של דרגה 2 מודד, כף הבנאים של דרגה 3 מחברת. המלט שהיא מפזרת מסמל את האחווה, החמלה והאהבה שמחברות בין בני אדם.\n\nלצד כלי העבודה, הדרגה השלישית מציגה סמלי תמותה: שעון החול (Hour Glass) מזכיר שהזמן חולף ללא הפסקה. החרמש (Scythe) — סמל המוות — מלמד שאין אדם שיכול לברוח מהקציר הסופי. העין הבוחנת (All-Seeing Eye) מייצגת את הנוכחות של כוח עליון שרואה כל מעשה.\n\nהמערכת פועלת יחד: אם אתה יודע שהזמן מוגבל (שעון חול), שהסוף בלתי נמנע (חרמש), ושמישהו רואה (עין בוחנת) — מה עליך לעשות? לחבר, לבנות, לפעול לטובה. כף הבנאים היא התשובה.",
    practical_elements: [
      "להבין שכף הבנאים מייצגת חיבור — כלי העבודה של דרגה 3 הוא 'לחבר אנשים', לא לחצוב או למדוד.",
      "לזהות ששעון החול, החרמש והעין פועלים יחד כמערכת מוטיבציה: הזמן קצר, הסוף בטוח, ומישהו רואה.",
    ],
    symbolic_meaning:
      "כלי העבודה של דרגה 3 מסמלים שתכלית כל הבנייה היא חיבור. סמלי התמותה מסמלים שהחיבור הזה דחוף: הזמן אוזל, והעבודה חייבת להיעשות עכשיו. העין מלמדת שהעבודה נעשית לפני עד — לא בסתר.",
    candidate_lesson:
      "הלקח הוא שדרגה 3 מביאה את המוות לתוך הלמידה — לא כאיום אלא כדחיפות. מי שיודע שהזמן מוגבל — ישתמש בכף הבנאים כדי לחבר, לא לפרק.",
    tradition_notes: [
      "כף הבנאים מופיעה כ'כלי העבודה של הדרגה השלישית' בכל המוניטורים המרכזיים.",
      "שעון החול והחרמש מוזכרים בהרצאה השלישית של הדרגה.",
      "העין הבוחנת היא סמל משותף לכל שלוש הדרגות אך מקבלת משמעות מיוחדת בדרגה 3.",
    ],
    caution_notes: [
      "אל תערבב בין כף הבנאים (כלי חיבור) לבין הכלים שנמצאו ליד גופת חירם (כלי הרצח).",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0061-the-working-tools",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0073-the-hour-glass",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0074-the-scythe",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0070-all-seeing-eye",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0061-the-working-tools",
      "blue-lodge-ritual-reference-guide-2021-section-0073-the-hour-glass",
      "blue-lodge-ritual-reference-guide-2021-section-0074-the-scythe",
      "blue-lodge-ritual-reference-guide-2021-section-0070-all-seeing-eye",
    ],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-third-degree-tracing-board-map", degree: "level3" }, { slug: "level3-burial-honor-and-memorial-structure", degree: "level3" }],
    chapter_toc: null,
    visibility_level: "visible",
    sensitivity_level: "standard",
    tradition_scope: "cross_tradition",
    status: "active",
    observability: { views: 0, bookmarks: 0, last_viewed: null },
    relies_on_level1_topics: ["l1-tools-mashmaut-meshulevet-klei-hatalmid"],
  },
];

// ─────────────────────────────────────────────────────────
// Infrastructure (same as wave 2)
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

const REQUIRED_LEVEL2 = ["title","slug","type","level2_content_type","level2_type","depth_scope","boundary_guard_passed","knowledge_type","degree","applies_to_degrees","content_scope","partition_role","degree_owner","product_state","category","parent_topic","aliases","keywords","related_topics","short_summary","reading_layers","full_summary","practical_elements","symbolic_meaning","candidate_lesson","tradition_notes","caution_notes","source_notes","language","knowledge_links","chapter_toc","visibility_level","sensitivity_level","tradition_scope","status","observability","relies_on_level1_topics"];
const REQUIRED_LEVEL3 = ["title","slug","type","level3_content_type","level3_type","depth_scope","boundary_guard_passed","knowledge_type","degree","applies_to_degrees","content_scope","partition_role","degree_owner","product_state","category","parent_topic","aliases","keywords","related_topics","short_summary","reading_layers","full_summary","practical_elements","symbolic_meaning","candidate_lesson","tradition_notes","caution_notes","source_notes","language","knowledge_links","chapter_toc","visibility_level","sensitivity_level","tradition_scope","status","observability","relies_on_level1_topics"];

function checkRequiredFields(entry, requiredFields) { return requiredFields.filter((f) => !(f in entry)).map((f) => ({ slug: entry.slug, missing_field: f })); }

function main() {
  const { dryRun, siteRoot } = parseArgs(process.argv.slice(2));
  const executedAt = new Date().toISOString();
  const level2Path = path.join(siteRoot, "data", "level2.json");
  const level3Path = path.join(siteRoot, "data", "level3.json");
  const level2BackupPath = path.join(siteRoot, "data", "level2.pre_m17_wave3_backup.json");
  const level3BackupPath = path.join(siteRoot, "data", "level3.pre_m17_wave3_backup.json");

  const report = { phase: PHASE_ID, executed_at: executedAt, dry_run: dryRun, site_root: siteRoot, new_level2_slugs: NEW_LEVEL2_ENTRIES.map((e) => e.slug), new_level3_slugs: NEW_LEVEL3_ENTRIES.map((e) => e.slug), actions: [], overall_status: "pending" };
  const validation = { phase: PHASE_ID, executed_at: executedAt, checks: {}, failures: [], error_count: 0, overall_status: "pending" };

  try {
    const level2Data = loadJson(level2Path);
    const level3Data = loadJson(level3Path);
    const existingL2Slugs = new Set((level2Data.entries || []).map((e) => e.slug));
    const existingL3Slugs = new Set((level3Data.entries || []).map((e) => e.slug));

    const allViolations = [];
    const allMissingFields = [];
    for (const entry of NEW_LEVEL2_ENTRIES) { allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL2_PATTERNS, "level2")); allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL2)); }
    for (const entry of NEW_LEVEL3_ENTRIES) { allViolations.push(...checkForbiddenPatterns(entry, FORBIDDEN_LEVEL3_PATTERNS, "level3")); allMissingFields.push(...checkRequiredFields(entry, REQUIRED_LEVEL3)); }

    validation.checks.boundary_clean = { passed: allViolations.length === 0, violations: allViolations };
    validation.checks.required_fields_complete = { passed: allMissingFields.length === 0, missing: allMissingFields };
    if (allViolations.length > 0) validation.failures.push({ check: "boundary_clean", detail: allViolations });
    if (allMissingFields.length > 0) validation.failures.push({ check: "required_fields_complete", detail: allMissingFields });

    const duplicateL2 = NEW_LEVEL2_ENTRIES.filter((e) => existingL2Slugs.has(e.slug)).map((e) => e.slug);
    const duplicateL3 = NEW_LEVEL3_ENTRIES.filter((e) => existingL3Slugs.has(e.slug)).map((e) => e.slug);
    validation.checks.no_duplicates = { passed: duplicateL2.length === 0 && duplicateL3.length === 0, duplicate_level2: duplicateL2, duplicate_level3: duplicateL3 };
    if (duplicateL2.length > 0 || duplicateL3.length > 0) validation.failures.push({ check: "no_duplicates", detail: { duplicateL2, duplicateL3 } });

    validation.error_count = validation.failures.length;
    validation.overall_status = validation.failures.length === 0 ? "pass" : "fail";

    if (validation.failures.length > 0) { report.overall_status = "fail"; report.error = "Validation failed."; writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation); console.error("Validation failed. No writes performed."); console.error(JSON.stringify(validation.failures, null, 2)); process.exitCode = 1; return; }

    report.actions.push({ action: "validation_passed" });

    if (dryRun) { report.overall_status = "dry_run_ok"; writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation); console.log("DRY RUN — no files written."); console.log("Would add L2:", NEW_LEVEL2_ENTRIES.map((e) => e.slug)); console.log("Would add L3:", NEW_LEVEL3_ENTRIES.map((e) => e.slug)); return; }

    fs.writeFileSync(level2BackupPath, JSON.stringify(level2Data, null, 2) + "\n", "utf8");
    fs.writeFileSync(level3BackupPath, JSON.stringify(level3Data, null, 2) + "\n", "utf8");
    report.actions.push({ action: "backups_written" });

    level2Data.entries = [...(level2Data.entries || []), ...NEW_LEVEL2_ENTRIES];
    level3Data.entries = [...(level3Data.entries || []), ...NEW_LEVEL3_ENTRIES];
    level2Data.meta = { ...level2Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };
    level3Data.meta = { ...level3Data.meta, updated_at: new Date().toISOString().slice(0, 10), build_phase: PHASE_ID };

    writeJson(level2Path, level2Data);
    writeJson(level3Path, level3Data);
    report.actions.push({ action: "entries_appended", level2_added: NEW_LEVEL2_ENTRIES.map((e) => e.slug), level3_added: NEW_LEVEL3_ENTRIES.map((e) => e.slug), level2_total: level2Data.entries.length, level3_total: level3Data.entries.length });
    report.overall_status = "success";
    writeJson(DEFAULT_REPORT_PATH, report);
    writeJson(DEFAULT_VALIDATION_PATH, validation);

    console.log(`Level 2: ${level2Data.entries.length} entries (added ${NEW_LEVEL2_ENTRIES.length})`);
    console.log(`Level 3: ${level3Data.entries.length} entries (added ${NEW_LEVEL3_ENTRIES.length})`);
    console.log(`Report: ${DEFAULT_REPORT_PATH}`);
  } catch (err) {
    report.overall_status = "fail"; report.error = err.message; validation.overall_status = "fail";
    writeJson(DEFAULT_REPORT_PATH, report); writeJson(DEFAULT_VALIDATION_PATH, validation);
    console.error(err.message); process.exitCode = 1;
  }
}

main();
