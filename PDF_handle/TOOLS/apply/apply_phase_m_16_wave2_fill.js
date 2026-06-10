/**
 * apply_phase_m_16_wave2_fill.js
 *
 * Wave 2 topic expansion — adds 6 new Level 2 entries and 3 new Level 3 entries.
 *
 * Level 2 new candidates:
 *   - level2-middle-chamber-as-reward-space
 *   - level2-operative-vs-speculative-framing
 *   - level2-fc-jewels-ear-tongue-breast
 *   - level2-fc-obligation-and-penalty-structure
 *   - level2-shibboleth-as-passage-and-test
 *   - level2-pillar-ornaments-and-globes-system
 *
 * Level 3 new candidates:
 *   - level3-five-points-of-fellowship-value-structure
 *   - level3-three-ruffians-and-gates-dramatic-structure
 *   - level3-distress-signal-and-protection-system
 *
 * Usage:
 *   node PDF_handle/TOOLS/apply_phase_m_16_wave2_fill.js [--dry-run] [--site-root <path>]
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m16_wave2_fill";
const DEFAULT_SITE_ROOT = path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_16_wave2_fill_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_16_wave2_fill_validation.json");

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
    title: "הלשכה האמצעית כמרחב שכר ולמידה",
    slug: "level2-middle-chamber-as-reward-space",
    type: "topic",
    level2_content_type: "structural_framework",
    level2_type: "structure",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "lodge_structure",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "fc_learning_structure",
    parent_topic: null,
    aliases: ["הלשכה האמצעית", "Middle Chamber", "שכר חבר-בונה"],
    keywords: ["לשכה אמצעית", "שכר", "תירס יין שמן", "דרגה 2", "מרחב למידה"],
    related_topics: {
      prior: ["level2-winding-stairs-as-ascent-process"],
      companion: ["level2-geometry-and-letter-g-intellectual-center", "level2-lodge-as-learning-structure"],
      deeper: [],
    },
    short_summary:
      "הלשכה האמצעית היא היעד שאליו מגיע חבר-הבונה בסוף עלייתו במדרגות הלולייניות. כאן מתגלה שהשכר אינו מטבע אלא ידע: תירס, יין ושמן מסמלים הזנה, רענון ושמחה — מה שהלמידה עצמה מעניקה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, הלשכה האמצעית היא חדר פנימי בבית המקדש שאליו נכנסו חברי-הבונים לקבל את שכרם. השכר שולם בתירס (הזנה), יין (רענון) ושמן (שמחה). הבונה שעלה את כל המדרגות הלולייניות מגיע לכאן ומגלה שהפרס על הלמידה הוא מה שלמד.",
      symbolic:
        "בקריאה הסמלית, הלשכה האמצעית מייצגת את ה'יעד הפנימי' של דרגת חבר-בונה. תירס, יין ושמן אינם מזון גשמי אלא שלושה סוגי תשלום רוחני: מה שמזין את הנפש, מה שמרענן את הרוח, ומה שמשמח את הלב. כך 'שכר' מקבל משמעות חדשה: לא גמול חיצוני אלא תוצאה של תהליך.",
      advanced:
        "בקריאה המבנית של דרגה 2, הלשכה האמצעית משלימה את מבנה העלייה שמתחיל במדרגות הלולייניות. 3-5-7 מכינים את הדרך, אך היעד — המרחב שבו השכר ניתן — מגדיר מה פירוש 'ידע' בדרגה זו. הלשכה האמצעית מלמדת שלמידה שלמה מסתיימת לא בציון אלא בשינוי פנימי.",
    },
    full_summary:
      "הלשכה האמצעית (Middle Chamber) היא המרחב הפנימי שבית המקדש בנוי סביבו, ובפולחן הדרגה השנייה היא התחנה שאליה מכוון כל מסע העלייה. לאחר שחבר-הבונה עולה 3 מדרגות (שלבי חיים), 5 מדרגות (חושים וסדרי אדריכלות) ו-7 מדרגות (אמנויות ומדעים), הוא מגיע ללשכה ושם מתקבל שכרו.\n\nהשכר המסורתי של חברי-הבונים ניתן בשלושה מרכיבים: תירס, יין ושמן. תירס מסמל הזנה — את מה שהידע מעניק לגוף החושב. יין מסמל רענון — את מה שהלמידה עושה לרוח העייפה. שמן מסמל שמחה — את השמחה שנמצאת בהבנה עצמה. השלושה יחד מגדירים מודל של שכר שונה מכל מודל כלכלי: כאן הפרס הוא חלק מהתהליך, לא תוספת חיצונית.\n\nמבחינה מבנית, הלשכה האמצעית משלימה את 'מערכת הידע' של הדרגה השנייה: המדרגות הלולייניות מגדירות את המסלול, הגיאומטריה והאות G מגדירות את המרכז השכלי, והלשכה האמצעית מגדירה את ה'שכר' — מה שנותר בידי הלומד בסוף הדרך. ללא הלשכה, העלייה חסרת יעד; ללא המדרגות, הלשכה חסרת משמעות.",
    practical_elements: [
      "לשאול: מה ה'שכר' שקיבלתי מהלמידה — הזנה, רענון, או שמחה?",
      "לחשוב על ההבדל בין שכר חיצוני (ציון, תואר) לבין שכר פנימי (שינוי בתפיסה).",
    ],
    symbolic_meaning:
      "הלשכה האמצעית מסמלת שהלמידה אינה אמצעי אלא מטרה. כשהשכר הוא תירס, יין ושמן — לא כסף — הדרגה מלמדת שהעלייה עצמה היא התשלום. מי שעולה באמת מגלה שמה שחיפש כבר נמצא בו.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא ששכר אמיתי אינו מגיע מבחוץ. תירס, יין ושמן מסמלים שמה שהלמידה נותנת — הזנה, רענון ושמחה — כבר נמצא בתהליך עצמו.",
    tradition_notes: [
      "הלשכה האמצעית מתוארת במלכים א' ו' ובפולחן הדרגה השנייה המסורתי.",
      "שכר תירס, יין ושמן מקורו בלקט הקרבנות המקראי ובהקשר הבנייה החופשית קיבל פרשנות מוסרית.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן דרגה שלישית: הלשכה האמצעית שייכת לחבר-בונה בלבד.",
      "אין לפרש את השכר כתגמול חומרי — הפרשנות הבנייה-חופשית היא סמלית.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0049-flight-of-winding-stairs",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree", "blue-lodge-ritual-reference-guide-2021-section-0049-flight-of-winding-stairs"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-winding-stairs-as-ascent-process", degree: "level2" }, { slug: "level2-geometry-and-letter-g-intellectual-center", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "בנייה אופרטיבית מול עיונית כמסגרת חבר-בונה",
    slug: "level2-operative-vs-speculative-framing",
    type: "topic",
    level2_content_type: "structural_framework",
    level2_type: "relationship",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "concept",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "structural_meaning",
    parent_topic: null,
    aliases: ["אופרטיבית מול עיונית", "Operative vs Speculative", "בנייה חופשית מעשית ועיונית"],
    keywords: ["אופרטיבית", "עיונית", "ספקולטיבית", "בנייה חופשית", "דרגה 2"],
    related_topics: {
      prior: ["level2-tool-system-plumb-square-level"],
      companion: ["level2-from-discipline-to-inner-formation", "level2-geometry-and-letter-g-intellectual-center"],
      deeper: [],
    },
    short_summary:
      "דרגת חבר-הבונה מגדירה את ההבחנה המרכזית בבנייה החופשית: בנייה אופרטיבית (מעשית, פיזית) מול בנייה עיונית (מוסרית, פנימית). לא שתי מערכות נפרדות, אלא שתי קריאות של אותה מלאכה — וההבנה שמה שמבנים בחוץ הוא משל למה שמבנים בפנים.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, בנייה אופרטיבית (Operative Masonry) מתייחסת למלאכת הבנייה הפיזית: חיתוך אבן, הקמת מבנים, שימוש בכלים. בנייה עיונית (Speculative Masonry) לוקחת את אותם כלים ואותם תהליכים ומפרשת אותם כמשל לבניית האדם הפנימי. חבר-הבונה לומד ששישה ימי עבודה אינם רק חוק מלאכה אלא מבנה חיים.",
      symbolic:
        "בקריאה הסמלית, ההבחנה אופרטיבית/עיונית אינה ניגוד אלא שכבות. האנך, הפלס והזוויתן אינם רק כלי מדידה — הם גם כלי חשיבה. כשבנאי אופרטיבי בודק שקיר ישר, בנאי עיוני בודק שחייו ישרים. הדרגה השנייה היא הדרגה שמגלה את הקשר הזה ומבקשת מהלומד לחיות בשתי הקריאות בו-זמנית.",
      advanced:
        "בקריאה המבנית של דרגה 2, ציר האופרטיבי/עיוני הוא עמוד השדרה של הדרגה. כל כלי, כל מבנה, כל תנועה ניתנים לקריאה כפולה. שאלת הליבה היא: כיצד דרגה שנייה הופכת אומנות לפילוסופיה? והתשובה נמצאת בהבנה שהכלים אינם מטפורה — הם אותו דבר בשתי שפות.",
    },
    full_summary:
      "ההבחנה בין בנייה אופרטיבית לבנייה עיונית היא אחד המושגים המכוננים ביותר בבנייה החופשית, והיא מופיעה בגוף הלקטורה של דרגת חבר-הבונה. בנייה אופרטיבית (Operative Masonry) מתייחסת למלאכת הבנייה הממשית — חיתוך אבן, הקמת קירות, שימוש בכלים כמו אנך, פלס וזוויתן לצורך בנייה פיזית. בנייה עיונית (Speculative Masonry) לוקחת את הכלים, התהליכים והמבנים ומפרשת אותם כמשל למוסר, אמונה ובניין הנפש.\n\nמה שמייחד את הגישה הבנייה-חופשית הוא שהיא אינה מבטלת את הצד האופרטיבי. הכלים הם באמת כלים; האבן היא באמת אבן; העבודה היא באמת עבודה. אך בדרגת חבר-הבונה מתגלה שכל אלה ניתנים גם לקריאה שנייה: אנך ששומר על יושר פיזי שומר גם על יושר מוסרי. פלס שמשווה גובה משווה גם אנשים. זוויתן שבודק זוויות בודק גם מעשים.\n\nהמבנה של 'שישה ימי עבודה ויום שביעי למנוחה ולחקר' מחזק את הנקודה: גם מבנה הזמן עצמו הוא אופרטיבי (ששת הימים) ועיוני (השביעי). כך דרגת חבר-הבונה מגלה שהמלאכה והחשיבה אינן שני עולמות אלא שפתיים של אותו דבר.",
    practical_elements: [
      "לבחון כלי או תהליך בשתי קריאות: מה הוא עושה בפועל, ומה הוא מלמד?",
      "לשים לב שהקריאה העיונית לא מבטלת את המעשית — שתיהן שרות יחד.",
    ],
    symbolic_meaning:
      "ציר האופרטיבי/עיוני מסמל שהדרגה השנייה רואה בכל חומר גם רוח. הכלים מסמלים מידות; המבנים מסמלים ערכים; והעבודה מסמלת תהליך פנימי. כשמבינים שאין פער בין השניים, אלא שהם אותו דבר בשתי שפות, מתגלה מה שהדרגה מלמדת.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שאין הבדל בין 'עשייה' ל'חשיבה' — יש רק שני אופנים של קריאה. מי שמבין שהאנך בודק גם קיר וגם חיים, נכנס לדרגת חבר-בונה באמת.",
    tradition_notes: [
      "ההבחנה אופרטיבי/ספקולטיבי היא מרכזית בהגדרת הזהות של הבנייה החופשית המודרנית.",
      "הלקטורה של הדרגה השנייה מפרטת את ההבחנה בצורה מפורשת.",
    ],
    caution_notes: [
      "אין להציג את הבנייה העיונית כ'עדיפה' על האופרטיבית — שתיהן נדרשות.",
      "אין לגלוש לתוכן דרגות מאוחרות יותר.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-tool-system-plumb-square-level", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "אוזן קשבת, לשון מדריכה וחזה נאמן כמערכת חבר-בונה",
    slug: "level2-fc-jewels-ear-tongue-breast",
    type: "topic",
    level2_content_type: "structural_framework",
    level2_type: "system",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "symbol",
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "built",
    category: "moral_framework_expansion",
    parent_topic: null,
    aliases: ["תכשיטי חבר-בונה", "FC Jewels", "אוזן לשון חזה"],
    keywords: ["אוזן קשבת", "לשון מדריכה", "חזה נאמן", "תכשיטים", "דרגה 2"],
    related_topics: {
      prior: ["level2-language-of-recognition-trust-structure"],
      companion: ["level2-obligation-brotherhood-and-work-process", "level2-from-discipline-to-inner-formation"],
      deeper: [],
    },
    short_summary:
      "שלושת ה'תכשיטים' של חבר-הבונה — אוזן קשבת, לשון מדריכה וחזה נאמן — אינם עיטורים אלא מערכת מוסרית: הקשבה, הוראה ושמירת סוד. יחד הם מגדירים מודל של העברת ידע בדרגה השנייה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, שלושת התכשיטים מתארים שלוש חובות. אוזן קשבת — חובת ההקשבה להוראות ולזעקות אח. לשון מדריכה — חובת ההוראה וההדרכה של אחים צעירים. חזה נאמן — חובת שמירת הסוד בלב. שלושתם ביחד מגדירים את מהותו של חבר-בונה: אדם ששומע, מלמד ושומר.",
      symbolic:
        "בקריאה הסמלית, אוזן, לשון וחזה מייצגים שלושה כיוונים של ידע. הידע נכנס (אוזן), יוצא (לשון), ונשמר (חזה). כך השלושה מרכיבים מערכת חיה של 'זרימת ידע' שבה חבר-הבונה הוא לא רק נושא מידע אלא תחנה פעילה: קולט, מעביר ושומר.",
      advanced:
        "בקריאה המבנית של דרגה 2, השאלה היא: כיצד הדרגה מגדירה את תפקיד חבר-הבונה ביחס לידע? התשובה: הוא לא רק לומד — הוא גם מלמד. ולא רק מלמד — הוא גם שומר. מערכת 'אוזן-לשון-חזה' מציבה את חבר-הבונה כצומת בתוך רשת של ידע, לא כקצה.",
    },
    full_summary:
      "בפולחן הדרגה השנייה מוזכרים שלושה 'תכשיטים' (Jewels) ייחודיים לחבר-הבונה, שונים מהתכשיטים הפיזיים של נושאי המשרה: אוזן קשבת (Attentive Ear), לשון מדריכה (Instructive Tongue) וחזה נאמן (Faithful Breast). שלושתם יחד מגדירים מודל של העברת ידע ושמירתו.\n\nהאוזן הקשבת מלמדת שלמידה מתחילה בהקשבה — לא רק לבונה הנכבד המלמד אלא גם לאח הזועק לעזרה. הלשון המדריכה מלמדת שמי שלמד חייב גם ללמד, אך בחכמה ובעדינות ולא בכפייה. החזה הנאמן מלמד שיש ידע שנשמר ולא מועבר — הסודות שנמסרו באמון ושומרים עליהם בלב.\n\nמבנה זה חשוב להבנת דרגה שנייה מפני שהוא מציב את חבר-הבונה לא רק כ'תלמיד משודרג' אלא כ'צומת ידע'. בדרגה ראשונה האדם בעיקר מקבל; בדרגה שנייה הוא גם נותן. ובכל הנתינה יש גבול: לא כל מה שנלמד ניתן להעברה, ולא כל מי ששומע ראוי עדיין לשמוע.",
    practical_elements: [
      "לבחון את עצמי דרך שלושת התכשיטים: האם אני שומע באמת? האם אני מלמד נכון? האם אני שומר?",
      "להבחין בין 'שתיקה מתוך פחד' לבין 'חזה נאמן' — שמירת סוד היא בחירה פעילה, לא חולשה.",
    ],
    symbolic_meaning:
      "שלושת התכשיטים מסמלים שזרימת הידע אינה חד-כיוונית. אוזן = כניסה, לשון = יציאה, חזה = שמירה. כך הידע מקבל מעגל חי: נקלט, מועבר ונשמר. חבר-הבונה הוא הצומת שמחזיק את שלושת הכיוונים בו-זמנית.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שידע אמיתי מחייב שלושה דברים: לשמוע, ללמד ולשמור. מי שרק שומע — פסיבי. מי שרק מלמד — מרוקן. מי שרק שומר — מנותק. חבר-בונה עושה את שלושתם.",
    tradition_notes: [
      "שלושת ה'תכשיטים' מוזכרים בלקטורה של הדרגה השנייה.",
      "ההבחנה בין תכשיטים אישיים לתכשיטים של משרה היא חשובה בפרשנות הבנייה החופשית.",
    ],
    caution_notes: ["אין לבלבל תכשיטים אלה עם תכשיטי נושאי המשרה (Square, Level, Plumb Rule)."],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-language-of-recognition-trust-structure", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "התחייבות חבר-בונה ומבנה העונש",
    slug: "level2-fc-obligation-and-penalty-structure",
    type: "topic",
    level2_content_type: "process_explanation",
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
    category: "moral_framework_expansion",
    parent_topic: null,
    aliases: ["התחייבות דרגה שנייה", "FC obligation", "עונש חבר-בונה"],
    keywords: ["התחייבות", "חיוב", "עונש", "קריעת חזה", "דרגה 2"],
    related_topics: {
      prior: ["level2-obligation-brotherhood-and-work-process"],
      companion: ["level2-language-of-recognition-trust-structure", "level2-fc-jewels-ear-tongue-breast"],
      deeper: [],
    },
    short_summary:
      "ההתחייבות של דרגת חבר-הבונה מעמיקה את זו של דרגה ראשונה: לא עוד חיתוך גרון אלא קריעת חזה — כאילו הלב עצמו נחשף. ההסלמה אינה אלימות אלא משקפת את עומק האמון שניתן ואת הכבדות של ההפרה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, חבר-הבונה נוטל שבועה חמורה יותר מזו של שוליה. העונש הסמלי של דרגה ראשונה היה חיתוך הגרון; כאן העונש הוא קריעת החזה ועקירת הלב. ההסלמה מלמדת שככל שהידע מעמיק, כך המחויבות לשמור עליו מתחזקת.",
      symbolic:
        "בקריאה הסמלית, הגרון (דרגה 1) הוא מקום הדיבור — ולכן עונש על דיבור. החזה (דרגה 2) הוא מקום הלב — ולכן עונש על בגידה רגשית ולא רק מילולית. ההסלמה מלמדת שהסכנה בדרגה שנייה אינה רק גילוי מילולי אלא גילוי של מה שבלב.",
      advanced:
        "בקריאה המבנית של דרגה 2, ההתחייבות מבנית כתהליך של הגברת אמון. כל דרגה מוסיפה שכבה: דרגה ראשונה — שמירת מילה (גרון); דרגה שנייה — שמירת לב (חזה). המבנה מלמד שהמערכת בנויה כסדרה של מעגלי אמון הולכים ומתרחבים.",
    },
    full_summary:
      "ההתחייבות (Obligation) של חבר-הבונה ניתנת כשהמועמד כורע על ברכו הימנית, כאשר זווית הזוויתן מונחת על חזהו הימני החשוף. כבל הגרירה כרוך פעמיים סביב זרועו — 'קשר כפול' של מחויבות. הנוסח כולל שבועה חמורה יותר מדרגה ראשונה, ועונש סמלי של קריעת חזה ועקירת הלב שיינתן כמאכל לנשרי השמיים.\n\nההסלמה מדרגה ראשונה (חיתוך גרון ועקירת לשון) לדרגה שנייה (קריעת חזה ועקירת לב) אינה מקרית. הגרון שייך לדיבור — ולכן עונש הדרגה הראשונה קשור לדליפה מילולית. החזה שייך ללב — ולכן עונש הדרגה השנייה קשור לבגידה עמוקה יותר, של מי שמגלה לא רק מילים אלא אמון.\n\nמבנה ההתחייבות חשוב להבנת הדרגה מפני שהוא מראה שהמעבר מדרגה ראשונה לשנייה אינו רק עניין של ידע נוסף. הוא עניין של מעגל אמון חדש: כבל כפול, ברך שונה, איבר שונה. הסיסטם כולו בנוי על הנחת היסוד שכל שכבת ידע דורשת שכבת אחריות מתאימה.",
    practical_elements: [
      "לשים לב שההסלמה (גרון → חזה) מלמדת שהאחריות גדלה עם הידע — לא הפוך.",
      "לשאול: מה פירוש 'קשר כפול' (כבל פעמיים) ביחסים של אמון ומחויבות?",
    ],
    symbolic_meaning:
      "ההתחייבות מסמלת שהידע ואחריות הם צמד בלתי נפרד. ככל שהמעגל מתרחב (מגרון ללב, מכבל אחד לשניים), כך העומק של האמון והסיכון גדלים. המערכת כולה מסמלת שאין ידע ללא מחיר.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שמחויבות אמיתית מתעמקת עם כל מה שלומדים. כבל כפול אומר: מה שקיבלתי כפול ממה שקיבלתי קודם, ומה שאני חייב גדל בהתאם.",
    tradition_notes: ["ההתחייבות של דרגת חבר-בונה מופיעה בנוסח הפולחן המסורתי.", "העונשים הסמליים משותפים לרוב המסורות אך אינם ממומשים מעולם."],
    caution_notes: ["אין להציג את העונשים כריאליסטיים — הם סמליים בלבד.", "אין לגלוש לתוכן דרגה שלישית."],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree", "duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-obligation-brotherhood-and-work-process", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "שיבולת כמעבר ובחינה",
    slug: "level2-shibboleth-as-passage-and-test",
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
    aliases: ["שיבולת", "Shibboleth", "מילת מעבר חבר-בונה"],
    keywords: ["שיבולת", "מילת מעבר", "אפרים", "יפתח", "דרגה 2", "בחינה"],
    related_topics: {
      prior: ["level2-language-of-recognition-trust-structure"],
      companion: ["level2-jachin-boaz-threshold-and-symbol-structure", "level2-fc-obligation-and-penalty-structure"],
      deeper: [],
    },
    short_summary:
      "שיבולת היא מילת המעבר של דרגת חבר-הבונה, ומשמעותה 'שפע' או 'שיבולת תירס ליד מפל מים'. הסיפור המקראי — שבט אפרים שנכשל בהגיית המילה — מלמד שמעבר אמיתי נבחן לא רק ברצון אלא ביכולת, ושלא כל מי שטוען לזכות אכן ראוי.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, שיבולת היא מילה שמשמשת כמבחן כניסה. בסיפור המקראי, יפתח בדק מי מבני אפרים מנסה לחצות את הירדן על ידי כך שביקש מהם לומר 'שיבולת'. מי שלא הצליח להגות נכון — אמר 'סיבולת' — נתפס כחיצוני. בדרגת חבר-הבונה, שיבולת היא מילת המעבר שנדרשת לעליית המדרגות.",
      symbolic:
        "בקריאה הסמלית, שיבולת היא לא רק סיסמא אלא עיקרון. המבחן אינו 'האם אתה יודע?' אלא 'האם אתה שייך?' — האם הגיית המילה טבעית לך או זרה? שיבולת מסמלת שהמעבר אינו רק ידע אלא זהות: מי שמצליח לעבור הוא מי ש'גדל' לתוך הידע ולא רק שינן אותו.",
      advanced:
        "בקריאה המבנית של דרגה 2, שיבולת פועלת כ'מבחן סף': היא מפרידה בין מי שעולה באמת לבין מי שמתחזה. כך המילה אינה רק חלק מטקס אלא חלק מהמבנה הלימודי של הדרגה — שקיימת בה הבחנה בין מי שהוא בפנים לבין מי שעדיין בחוץ.",
    },
    full_summary:
      "שיבולת (Shibboleth) היא מילת המעבר של דרגת חבר-הבונה, נגזרת מהמילה העברית המציינת שיבולת תבואה או שטף מים. הסיפור המקראי (שופטים י״ב) מספר כיצד יפתח הגלעדי השתמש במילה כמבחן: אנשי שבט אפרים שניסו לחצות את הירדן התבקשו לומר 'שיבולת', ומי שאמר 'סיבולת' נחשף כזר ונהרג.\n\nבבנייה החופשית, הסיפור מקבל משמעות מוסרית: לא כל מי שרוצה לעבור יכול לעבור. המעבר דורש לא רק ידע אלא שייכות — 'הגייה נכונה' שמעידה על כך שהאדם גדל לתוך המערכת ולא רק למד את הסיסמא. שיבולת תירס (שיבולים) ליד מפל מים מסמלת שפע: מי שעובר את המבחן מגיע אל השפע שבצד השני.\n\nמבחינת המבנה הלימודי של דרגת חבר-הבונה, שיבולת משלימה את ה'מערכת הכניסה' שמתחילה ביכין ובועז (סף אדריכלי), עוברת דרך שיבולת (סף מילולי), וממשיכה במדרגות הלולייניות (סף לימודי). כל אחד מהם הוא מבחן מעבר מסוג אחר.",
    practical_elements: [
      "לשאול: מה ה'שיבולת' שלי — מה מבחין בין ידע שטחי לבין שייכות אמיתית?",
      "לשים לב שהמילה 'שפע' (Plenty) היא לא רק פירוש אלא הבטחה: מי שעובר, מגיע לשפע.",
    ],
    symbolic_meaning:
      "שיבולת מסמלת שמעבר אמיתי אינו רק ידע אלא זהות. ההגייה הנכונה מסמלת 'להיות מהמקום הזה', לא רק 'לדעת על המקום הזה'. כך המילה הופכת למבחן שמבדיל בין מי שצמח פנימה לבין מי שעדיין מבחוץ.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שלא כל ידע הוא מעבר. שיבולת מלמדת שיש הבדל בין 'לדעת' ל'להיות' — ושהמעבר הזה לא תמיד גלוי לעין.",
    tradition_notes: ["שיבולת מקורה בשופטים י״ב, 5-6.", "בבנייה החופשית הפכה לסמל למבחן מעבר ושייכות."],
    caution_notes: ["אין להציג את סיפור שיבולת כהצדקה לאלימות — המשמעות הבנייה-חופשית היא מוסרית."],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-language-of-recognition-trust-structure", degree: "level2" }, { slug: "level2-jachin-boaz-threshold-and-symbol-structure", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "כותרות העמודים וגלובוסים כמערכת עיטור ומשמעות",
    slug: "level2-pillar-ornaments-and-globes-system",
    type: "topic",
    level2_content_type: "symbol_relationship_analysis",
    level2_type: "system",
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
    aliases: ["כותרות ועיטורי העמודים", "Pillar Ornaments", "גלובוסים"],
    keywords: ["כותרות", "רשת", "שושן", "רימונים", "גלובוסים", "דרגה 2"],
    related_topics: {
      prior: ["level2-jachin-boaz-threshold-and-symbol-structure"],
      companion: ["level2-floor-frame-and-center-system", "level2-light-placement-and-orientation"],
      deeper: [],
    },
    short_summary:
      "כותרות שני העמודים מעוטרות ברשת (אחדות), שושן (שלום) ורימונים (שפע), ומעליהן מונחים גלובוסים שמימיים וארציים. יחד הם מרכיבים מערכת עיטור שאינה קישוט אלא הצהרה: הלשכה חובקת עולם.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, כותרות העמודים יכין ובועז עוטרו בשלושה סוגי עיטורים. רשת (Network) — סריגה המסמלת אחדות. שושן (Lily-work) — פרח המסמל שלום וטוהר. רימונים (Pomegranates) — פרי שזרעיו הרבים מסמלים שפע. מעל הכותרות מונחים שני גלובוסים: שמימי (גרמי השמיים) וארצי (פני כדור הארץ).",
      symbolic:
        "בקריאה הסמלית, שלושת העיטורים מייצגים שלוש תכונות של קהילה: אחדות (רשת — שמחברת), שלום (שושן — שמרגיע), שפע (רימון — שמזין). הגלובוסים מוסיפים ממד קוסמי: הלשכה אינה מוגבלת למקום אחד אלא חובקת גם שמיים וגם ארץ.",
      advanced:
        "בקריאה המבנית של דרגה 2, העיטורים והגלובוסים הם הרחבה של שני העמודים. אם יכין ובועז אומרים 'ביסוס וכוח', הכותרות אומרות 'אחדות, שלום, שפע' — מה שנצמח בין הביסוס והכוח. והגלובוסים אומרים 'היקף אוניברסלי' — שהמשמעות אינה מקומית אלא כוללת. כך הכניסה למקדש הופכת מדלת למיקרוקוסמוס.",
    },
    full_summary:
      "כותרות שני העמודים (Chapiters) הן חלק בלתי נפרד מהמבנה הסמלי של כניסת חבר-הבונה. הן יצוקות מנחושת ומעוטרות בשלושה סוגי עיטורים. הרשת (Network) מייצגת את הקשר שמחבר בין הבנאים — רשת של אחים. השושן (Lily-work) מייצג שלום וטוהר — המצב שבו הקהילה פועלת בלי מאבק. הרימונים (Pomegranates) מייצגים שפע — בשל שפע זרעיהם, הם מזכירים ששכר העבודה הוא ריבוי של טוב.\n\nמעל הכותרות מונחים שני גלובוסים. הגלובוס השמימי מציג את גרמי השמיים ואת סדר היקום. הגלובוס הארצי מציג את פני כדור הארץ ואת תפוצת הבנייה החופשית בעולם. יחד הם מרחיבים את מרחב הלשכה מחדר פיזי ליקום שלם: מה שנלמד כאן אינו מוגבל למקום הזה.\n\nמבחינת המערכת הסמלית של דרגה שנייה, כותרות העמודים וגלובוסיהם הם מעין 'כתר' על גבי 'בסיס'. העמודים (ביסוס וכוח) הם הבסיס; הכותרות (אחדות, שלום, שפע) הם מה שנצמח; והגלובוסים (שמיים וארץ) הם ההיקף. כל שלושת השכבות ביחד מגדירות את הכניסה כהצהרה: מקום שיש בו יסוד, פירות והיקף עולמי.",
    practical_elements: [
      "לשאול: אילו שלוש תכונות (אחדות, שלום, שפע) נראות בקהילה שלי — ואיזו חסרה?",
      "לשים לב שהגלובוסים הם לא קישוט אלא הצהרה: מה שאנחנו עושים כאן קשור לעולם כולו.",
    ],
    symbolic_meaning:
      "הכותרות מסמלות את הפירות שנצמחים כאשר ביסוס וכוח (יכין ובועז) פועלים יחד: אחדות, שלום ושפע. הגלובוסים מסמלים שהלשכה אינה מוגבלת — שמיים וארץ יחד בתוך מרחב אחד. כך הכניסה הופכת מדלת קטנה לחלון על היקום.",
    candidate_lesson:
      "הלקח של דרגה 2 הוא שמה שמעטר את היסוד חשוב לא פחות מהיסוד עצמו. כותרות ללא עמודים אינן עומדות, אך עמודים ללא כותרות הם רק בטון. הדרגה מלמדת שביסוס צריך גם פריחה.",
    tradition_notes: ["תיאור הכותרות מבוסס על מלכים א' ז' ועל הפרשנות הבנייה-חופשית.", "הגלובוסים מופיעים בפולחן הדרגה השנייה כהרחבה של סמלי העמודים."],
    caution_notes: ["אין לגלוש לפרשנות כרונולוגית של הגלובוסים (שלא היו בזמן שלמה) — זה נושא היסטורי, לא טקסי."],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0023-fellow-craft-or-second-degree",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0042-fellow-craft-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level2-jachin-boaz-threshold-and-symbol-structure", degree: "level2" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },
];

// ─────────────────────────────────────────────────────────
// New Level 3 Entries
// ─────────────────────────────────────────────────────────

const NEW_LEVEL3_ENTRIES = [
  {
    title: "חמש נקודות האחווה כמבנה ערכי",
    slug: "level3-five-points-of-fellowship-value-structure",
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
    category: "relationships_between_symbols",
    parent_topic: null,
    aliases: ["חמש נקודות האחווה", "Five Points of Fellowship", "נקודות הקשר בין רבי-בונים"],
    keywords: ["חמש נקודות", "אחווה", "רגל לרגל", "ברך לברך", "חזה לחזה", "דרגה 3"],
    related_topics: {
      prior: ["level3-raising-and-restoration-process"],
      companion: ["level3-hiram-loss-and-fidelity-system", "level3-charge-and-duty-framework"],
      deeper: [],
    },
    short_summary:
      "חמש נקודות האחווה — רגל לרגל, ברך לברך, חזה לחזה, יד לגב, ולחי ללחי — אינן רק תנוחה טקסית. הן מערכת ערכית שבה כל מגע גופני מקודד חובה מוסרית: ללכת למען אח, להתפלל עבורו, לשמור את סודותיו, לתמוך בו כשנופל ולייעץ בסתר.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, חמש הנקודות הן חמש תנוחות גוף שרב-בונה מבצע בטקס: רגל לרגל (נכונות ללכת ולעזור), ברך לברך (תפילה הדדית), חזה לחזה (שמירת סוד), יד לגב (תמיכה באח שנפל), ולחי ללחי / פה לאוזן (עצה טובה בסתר). כל אחת היא חובה, לא סמל.",
      symbolic:
        "בקריאה הסמלית, חמש הנקודות מייצגות חמישה ערוצים של קשר בין בני אדם. רגל = תנועה; ברך = תפילה; חזה = סוד; יד = הגנה; לחי = דיבור ישיר. הגוף כולו הופך למפה של חובות: כל איבר נושא ערך, כל מגע הוא הבטחה.",
      advanced:
        "בקריאה המבנית של דרגה 3, חמש הנקודות הן המבנה שמגדיר מה 'אחווה' פירושה מעבר למילה. בניגוד לעקרונות כלליים (ידידות, מוסריות, אהבת אחים), כאן כל חובה מגולמת בפעולה פיזית. זה מה שהופך את חמש הנקודות למערכת: לא הצהרה אלא רצף של מעשים שהגוף מבצע.",
    },
    full_summary:
      "חמש נקודות האחווה (Five Points of Fellowship) הן הרגע שבו ההקמה מקבלת משמעות מוסרית. הן מבוצעות כאשר רב-בונה מרים את גוף חירם באחיזת כף רגל האריה, ובמהלך ההרמה הגוף כולו הופך למפה של חובות.\n\nרגל לרגל — נכונות ללכת ולעזור לאח גם מחוץ לדרך השגרה. ברך לברך — להתפלל עבור אח כפי שמתפלל עבור עצמו. חזה לחזה — לשמור את סודותיו עמוק בלב, למעט רצח ובגידה. יד לגב — להגן על שמו הטוב של אח בהיעדרו ולהחזיקו כשנופל. לחי ללחי (או פה לאוזן) — ליתן עצה טובה בסתר לאח שטועה.\n\nהמבנה של חמש הנקודות חשוב מפני שהוא ממיר ערכים מופשטים לפעולות. 'אחווה' היא מילה יפה; אך 'ללכת ברגליך אל אחיך' היא חובה. 'נאמנות' היא ערך; אך 'להחזיק את גבו כשהוא נופל' היא פעולה. חמש הנקודות מלמדות שהדרגה השלישית אינה מסתפקת בהצהרות — היא דורשת גוף שפועל.",
    practical_elements: [
      "לעבור על חמש הנקודות ולשאול: באיזו מהן אני חזק? באיזו חלש?",
      "לשים לב שהנקודות הן חובות הדדיות — לא חד-כיווניות.",
    ],
    symbolic_meaning:
      "חמש נקודות האחווה מסמלות שהגוף כולו הוא כלי של ערכים. כל נקודה — רגל, ברך, חזה, יד, לחי — היא ערוץ של חובה. כאשר הגוף מבצע את המגע, הערך מקבל צורה. כך הדרגה השלישית הופכת את הגוף למפה מוסרית.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שמילים אינן מספיקות: הגוף צריך לפעול. חמש הנקודות מלמדות שכל ערך שנשאר מילה בלבד — לא הושלם. רק כשהרגל הולכת, הברך כורעת, הלב שומר, היד מגנה והפה מייעץ — האחווה חיה.",
    tradition_notes: [
      "חמש נקודות האחווה מופיעות בפולחן הדרגה השלישית ובאחיזת כף רגל האריה.",
      "חלק מהמסורות כוללות שינויים קלים בסדר או בפירוש הנקודות.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן Royal Arch: חמש הנקודות שייכות לדרגה השלישית בלבד.",
      "אין להציג את חמש הנקודות כ'טקס' בלבד — הן חובות מוסריות פעילות.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-raising-and-restoration-process", degree: "level3" }, { slug: "level3-charge-and-duty-framework", degree: "level3" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "שלושת המתנקשים ושלושת השערים כמבנה דרמטי",
    slug: "level3-three-ruffians-and-gates-dramatic-structure",
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
    category: "ritual_dynamics",
    parent_topic: null,
    aliases: ["שלושת הקושרים", "Three Ruffians", "יובילה יובלו יובילום", "שלושת השערים"],
    keywords: ["שלושה מתנקשים", "שערים", "יובילה", "יובלו", "יובילום", "דרגה 3"],
    related_topics: {
      prior: ["level3-hiram-loss-and-fidelity-system"],
      companion: ["level3-raising-and-restoration-process", "level3-five-points-of-fellowship-value-structure"],
      deeper: ["level3-third-degree-tracing-board-map"],
    },
    short_summary:
      "שלושת המתנקשים — יובילה, יובלו ויובילום — תוקפים את חירם בשלושה שערים עם שלושה כלים, בהסלמה הולכת וגוברת. המבנה אינו מקרי: שער דרומי (מד זווית, מכה בגרון), שער מערבי (זוויתן, מכה בחזה), שער מזרחי (קורנס, מכה קטלנית במצח). ההסלמה היא הדרמה של הדרגה.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, שלושת הקושרים (Ruffians) היו חברי-בונה שרצו לקבל את סודות רב-הבונה בטרם עת. הם ארבו לחירם בשלושה שערי המקדש. בשער הדרומי יובילה הכה בגרונו במד זווית. בשער המערבי יובלו הכה בחזהו בזוויתן. בשער המזרחי יובילום הכה את מכת המוות במצחו בקורנס (setting-maul).",
      symbolic:
        "בקריאה הסמלית, ההסלמה גרון-חזה-מצח מקבילה להסלמה דיבור-לב-מחשבה. המתנקש הראשון תוקף את הדיבור (גרון); השני תוקף את הלב (חזה); השלישי תוקף את השכל (מצח). הכלים מתאימים: מד זווית (כלי שוליה), זוויתן (כלי חבר-בונה), קורנס (כלי מלאכה כבד). הבגידה מתעמקת עם כל שלב — מניסיון דחייה קלה ועד רצח.",
      advanced:
        "בקריאה המבנית של דרגה 3, שלושת השערים הם ארכיטקטורה דרמטית: הם מגדירים שלוש נקודות כישלון. בכל שער חירם יכול היה להיכנע ולמסור את הסוד — אך בחר שלא. כל שער מייצג מבחן: מול איום על הדיבור, מול איום על הלב, ומול איום על החיים. שלושתם יחד מגדירים מה פירוש 'נאמנות עד המוות'.",
    },
    full_summary:
      "סיפור שלושת המתנקשים הוא הליבה הדרמטית של דרגת רב-הבונה. שלושה חברי-בונה — יובילה, יובלו ויובילום — קנאו בסודות הרב-בונה ורצו לקבלם לפני שבניית המקדש הושלמה. הם ארבו לחירם בשלושה שערים.\n\nבשער הדרומי, יובילה עצר את חירם ותבע ממנו את סודות הרב-בונה. כשחירם סירב, הוא הכה אותו בגרונו במד זווית של 24 אינץ'. חירם הצליח להימלט. בשער המערבי, יובלו חיכה לו ותבע את אותם הסודות. כשחירם סירב שוב, הוא הוכה בחזהו בזוויתן. חלש ומדמם, חירם ניסה לברוח. בשער המזרחי — השער האחרון — יובילום הנחית את מכת המוות על מצחו של חירם בקורנס עץ.\n\nשלושת השערים, שלושת הכלים ושלושת איברי הגוף מרכיבים מבנה דרמטי שבו כל שלב מעמיק את הבחירה. חירם יכול היה למסור את הסוד בכל רגע ולהציל את חייו. שלוש פעמים הוא בחר שלא. כך המבנה מלמד שנאמנות אינה החלטה חד-פעמית אלא בחירה שחוזרת על עצמה גם כשהמחיר עולה.",
    practical_elements: [
      "לזהות את שלוש ה'שערים' בחיים: מתי נבחנת נאמנות מול דיבור (גרון), מול רגש (חזה), ומול חיים (מצח)?",
      "לשים לב שההסלמה מלמדת: בגידה אמיתית מתחילה קטנה ומתרחבת.",
    ],
    symbolic_meaning:
      "שלושת השערים מסמלים שלוש רמות של מבחן. גרון = מבחן הדיבור; חזה = מבחן הלב; מצח = מבחן הקיום. ושלושת הכלים (מד זווית, זוויתן, קורנס) מסמלים שכלי הבנייה עצמם יכולים להיהפך לכלי הרס כאשר הם בידיים לא נאמנות.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שנאמנות נבחנת שלוש פעמים לפחות. מי שעומד פעם אחת — אמיץ. מי שעומד שלוש — נאמן. שלושת השערים מלמדים שהאמת של הנפש נגלית רק בהסלמה.",
    tradition_notes: [
      "סיפור שלושת המתנקשים הוא חלק מרכזי מדרמת הדרגה השלישית בכל המסורות.",
      "שמות המתנקשים (יובילה, יובלו, יובילום) משתנים בין מסורות שונות.",
    ],
    caution_notes: [
      "אין להציג את הסיפור כהצדקה לאלימות — הוא דרמה סמלית.",
      "אין לגלוש לתיאור Royal Arch: העונש של המתנקשים שייך לדרגה השלישית.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "מקור תומך: duncans-ritual-monitor-1866-section-0030-the-three-steps",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-hiram-loss-and-fidelity-system", degree: "level3" }, { slug: "level3-raising-and-restoration-process", degree: "level3" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },

  {
    title: "אות המצוקה והזעקה כמערכת הגנה",
    slug: "level3-distress-signal-and-protection-system",
    type: "topic",
    level3_content_type: "structural_framework",
    level3_type: "structure",
    depth_scope: "structural_only",
    boundary_guard_passed: true,
    knowledge_type: "ceremony",
    degree: "level3",
    applies_to_degrees: ["level3"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level3",
    product_state: "built",
    category: "symbolic_systems",
    parent_topic: null,
    aliases: ["אות המצוקה הגדול", "Grand Hailing Sign of Distress", "בן האלמנה"],
    keywords: ["אות מצוקה", "זעקה", "בן האלמנה", "הגנה", "אחיזת כף רגל האריה", "דרגה 3"],
    related_topics: {
      prior: ["level3-five-points-of-fellowship-value-structure"],
      companion: ["level3-hiram-loss-and-fidelity-system", "level3-three-ruffians-and-gates-dramatic-structure"],
      deeper: [],
    },
    short_summary:
      "אות המצוקה הגדול — ידיים מורמות לשמיים עם הזעקה 'האם אין עזרה לבן האלמנה?' — הוא מערכת הגנה שמחברת את הדרגה השלישית לפעולה מעשית. לצידו, אחיזת כף רגל האריה מגדירה את כוח ההצלה. יחד הם מלמדים שהדרגה אינה רק זהות אלא חיוב להגנה הדדית.",
    reading_layers: {
      basic:
        "בקריאה הבסיסית, אות המצוקה הוא סימן שרב-בונה משתמש בו בעת סכנת חיים. הוא מרים את ידיו לשמיים וזועק — בקול או בלב — 'הו אלוהי, האם אין עזרה לבן האלמנה?' כל רב-בונה ששומע או רואה את האות חייב לבוא לעזרה, גם במחיר סכנה לעצמו. אחיזת כף רגל האריה (Lion's Paw) היא האחיזה החזקה שבה הוקם גוף חירם.",
      symbolic:
        "בקריאה הסמלית, 'בן האלמנה' מפנה לחירם, שהיה בנה של אישה אלמנה. כל רב-בונה הוא 'בן אלמנה' — כלומר, אדם שנותר ללא הגנה ומבקש עזרה מאחיו. אחיזת כף רגל האריה — אחיזה של שבט יהודה — מסמלת כוח שמצליח במקום שכל אחיזות אחרות נכשלו.",
      advanced:
        "בקריאה המבנית של דרגה 3, אות המצוקה ואחיזת ההצלה מרכיבים יחד מערכת הגנה: צד אחד קורא (הזעקה), צד שני עונה (האחיזה). המערכת מגדירה שהדרגה השלישית אינה רק ידע — היא רשת ביטחון. מי שנכנס לדרגה מקבל לא רק סודות אלא הבטחה: אם תיפול, יבואו.",
    },
    full_summary:
      "אות המצוקה הגדול (Grand Hailing Sign of Distress) הוא האות החמור ביותר בבנייה החופשית. הוא ניתן רק בעת סכנת חיים ממשית, כאשר רב-בונה מרים את ידיו לשמיים ואומר (או חושב): 'אלוהי, האם אין עזרה לבן האלמנה?' כל רב-בונה השומע את הזעקה או רואה את האות חייב לבוא לעזרה, גם אם הדבר כרוך בסכנה — כל עוד הדבר לא יפגע במשפחתו שלו.\n\nהכינוי 'בן האלמנה' מפנה ישירות לחירם אביף, שתואר כ'בנם של אישה אלמנה'. כך כל רב-בונה שמבקש עזרה מזדהה עם חירם — עם מי שנפל בגלל נאמנותו. והתגובה — האחיזה החזקה, אחיזת כף רגל האריה — היא אותה אחיזה שבה הוקם גוף חירם כשכל אחיזות השוליה וחבר-הבונה כשלו. כך הגוף שנפל מוקם שוב.\n\nמבחינת מערכת הדרגה, אות המצוקה הוא ההוכחה שהדרגה השלישית אינה רק ידע מסורתי אלא רשת ביטחון פעילה. חמש נקודות האחווה מגדירות את החובות; אות המצוקה מגדיר מתי הן מופעלות. יחד הם מרכיבים מערכת של הגנה הדדית שהופכת את 'אחווה' ממילה למעשה.",
    practical_elements: [
      "לשאול: מתי הייתי מוכן לבקש עזרה? ומתי הייתי מוכן לתת אותה — גם במחיר?",
      "לשים לב שהזעקה מכוונת גם לאלוהים וגם לאחים — שני מרחבים בו-זמנית.",
    ],
    symbolic_meaning:
      "אות המצוקה מסמל שנאמנות אינה מספיקה אם אין מערכת הצלה. הזעקה היא צד אחד; אחיזת כף רגל האריה היא הצד השני. יחד הם מסמלים שהדרגה אינה ידע בלבד אלא הבטחה: מי שנפל — יקום, מי שזעק — ייענה.",
    candidate_lesson:
      "הלקח של דרגה 3 הוא שאחווה אמיתית נבחנת ברגע המצוקה. אות המצוקה מלמד שהאדם לא לבד — ושמי שנכנס למעגל הזה קיבל לא רק ידע אלא גם הבטחה לעזרה.",
    tradition_notes: [
      "אות המצוקה הוא חלק מהפולחן של דרגה שלישית ומופיע בכל המסורות.",
      "אחיזת כף רגל האריה מקושרת לשבט יהודה ולאחיזה שהצליחה כשכל האחרות כשלו.",
    ],
    caution_notes: [
      "אין לגלוש לתוכן Royal Arch — מערכת ההגנה שייכת לדרגה השלישית.",
      "אין להציג את אות המצוקה כ'טריק' — הוא ניתן רק בסכנת חיים אמיתית.",
    ],
    source_notes: [
      "מקור עיקרי: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
      "מקור תומך: blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
    ],
    language: "he",
    work_id: null, work_title: null, source_kind: "degree_ritual", source_path: null,
    source_anchor: ["blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree"],
    source_heading: null, source_order: null, parallel_entry: null, translation_mode: null,
    knowledge_links: [{ slug: "level3-hiram-loss-and-fidelity-system", degree: "level3" }, { slug: "level3-five-points-of-fellowship-value-structure", degree: "level3" }],
    chapter_toc: null, visibility_level: "internal", sensitivity_level: "standard", tradition_scope: "universal", status: "draft", observability: "visible", relies_on_level1_topics: [],
  },
];

// ─────────────────────────────────────────────────────────
// Utilities (same as wave 1)
// ─────────────────────────────────────────────────────────

function loadJson(filePath) { return JSON.parse(fs.readFileSync(filePath, "utf8")); }
function writeJson(filePath, payload) { fs.mkdirSync(path.dirname(filePath), { recursive: true }); const tmp = filePath + ".tmp"; fs.writeFileSync(tmp, JSON.stringify(payload, null, 2) + "\n", "utf8"); fs.renameSync(tmp, filePath); }
function parseArgs(argv) { const opts = { dryRun: false, siteRoot: DEFAULT_SITE_ROOT }; for (let i = 0; i < argv.length; i++) { if (argv[i] === "--dry-run") opts.dryRun = true; if (argv[i] === "--site-root" && argv[i + 1]) { opts.siteRoot = path.resolve(argv[++i]); } } return opts; }

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
  const level2BackupPath = path.join(siteRoot, "data", "level2.pre_m16_wave2_backup.json");
  const level3BackupPath = path.join(siteRoot, "data", "level3.pre_m16_wave2_backup.json");

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
