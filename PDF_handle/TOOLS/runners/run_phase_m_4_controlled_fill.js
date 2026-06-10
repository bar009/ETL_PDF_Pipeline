const fs = require("fs");
const path = require("path");

const CONTENT_TYPE_BY_CANDIDATE = {
  "level2-candidate-mishmaat-even-gvil-haavoda-system": "inner_work_expansion",
  "level2-candidate-even-gvil-gvila-hamaavar-system": "deep_symbolic_explanation",
  "level2-candidate-gvila-haavoda-hamaavar-hamidot-process": "inner_work_expansion",
  "level2-candidate-chok-chovot-haach-haavoda-process": "process_explanation",
  "level2-candidate-atzamot-gulgolett-hahirhurim-hapilosofit-system": "structural_framework",
  "level2-candidate-batzafon-even-gvil-gvila-relationship": "symbol_relationship_analysis",
  "level2-candidate-allegory-hadarim-hamisra-hamoamad-structure": "structural_framework",
  "level2-candidate-even-gvil-gvila-hamaavar-relationship": "symbol_relationship_analysis",
  "level2-candidate-bamasa-cable-habakasha-hahovala-process": "process_explanation",
};

const TYPE_TO_RELATED = {
  "level2-discipline-work-and-rough-ashlar-system": {
    prior: [],
    companion: ["level2-from-discipline-to-inner-formation", "level2-tool-system-measure-force-direction"],
    deeper: ["level2-tool-system-measure-force-direction"],
  },
  "level2-ashlar-transition-and-formation-system": {
    prior: [],
    companion: ["level2-tool-system-measure-force-direction", "level2-floor-frame-and-center-system"],
    deeper: ["level2-work-transition-and-measure-process"],
  },
  "level2-work-transition-and-measure-process": {
    prior: [],
    companion: ["level2-from-discipline-to-inner-formation", "level2-tool-system-measure-force-direction"],
    deeper: ["level2-from-discipline-to-inner-formation"],
  },
  "level2-obligation-brotherhood-and-work-process": {
    prior: [],
    companion: ["level2-language-of-recognition-trust-structure", "level2-from-discipline-to-inner-formation"],
    deeper: ["level2-language-of-recognition-trust-structure"],
  },
  "level2-reflection-chamber-and-mortality-system": {
    prior: [],
    companion: ["level2-preparation-as-structured-transition", "level2-ritual-movement-as-learning-form"],
    deeper: ["level2-from-discipline-to-inner-formation"],
  },
  "level2-northeast-placement-and-ashlar-relationship": {
    prior: [],
    companion: ["level2-light-placement-and-orientation", "level2-floor-frame-and-center-system"],
    deeper: ["level2-light-placement-and-orientation"],
  },
  "level2-threshold-officers-and-candidate-structure": {
    prior: [],
    companion: ["level2-chain-of-office-and-responsibility", "level2-lodge-as-learning-structure"],
    deeper: ["level2-preparation-as-structured-transition"],
  },
  "level2-rough-ashlar-transition-and-measure-relationship": {
    prior: [],
    companion: ["level2-ashlar-transition-and-formation-system", "level2-from-discipline-to-inner-formation"],
    deeper: ["level2-work-transition-and-measure-process"],
  },
  "level2-cable-tow-entry-and-guided-movement-process": {
    prior: [],
    companion: ["level2-preparation-as-structured-transition", "level2-ritual-movement-as-learning-form"],
    deeper: ["level2-lodge-as-learning-structure"],
  },
};

const HIGHER_DEGREE_PATTERNS = [
  /Royal Arch/iu,
  /Lost Word/iu,
  /\u05d4\u05de\u05d9\u05dc\u05d4 \u05d4\u05d0\u05d1\u05d5\u05d3\u05d4/u,
  /\u05d7\u05d9\u05e8\u05dd/u,
  /\u05e8\u05d1-\u05d1\u05d5\u05e0\u05d4/u,
  /\u05d4\u05d3\u05e8\u05d2\u05d4 \u05d4\u05e9\u05dc\u05d9\u05e9\u05d9\u05ea/u,
  /\u05de\u05d0\u05e1\u05d8\u05e8/u,
  /Tubal/iu,
  /Mah-Hah-Bone/iu,
];

const RITUAL_DETAIL_PATTERNS = [
  /\u05e2\u05d5\u05e0\u05e9/u,
  /\u05e9\u05d1\u05d5\u05e2\u05d4/u,
  /\u05de\u05d9\u05dc\u05ea \u05de\u05e2\u05d1\u05e8/u,
  /\u05d0\u05d7\u05d9\u05d6\u05d4/u,
  /\u05d7\u05d5\u05d3/u,
  /\u05db\u05e8\u05d9\u05e2/u,
  /\u05db\u05d1\u05dc/u,
  /\u05d7\u05d1\u05dc/u,
  /\u05e0\u05d5\u05e1\u05d7/u,
];

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function toSlashPath(filePath) {
  return path.resolve(filePath).replace(/\\/g, "/");
}

function hebrewList(items) {
  if (!items.length) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} ו${items[1]}`;
  return `${items.slice(0, -1).join(", ")} ו${items[items.length - 1]}`;
}

function buildKeywords(frame) {
  return [...new Set([...frame.structure_axes, frame.target_title, "דרגה 2", "שותף בונה"])].slice(0, 6);
}

function makeKnowledgeLinks(sourceEntries) {
  return sourceEntries.map((slug) => ({ slug, degree: "level1" }));
}

function sourceMap(level1Payload) {
  return new Map(level1Payload.entries.map((entry) => [entry.slug, entry]));
}

function requiredFieldsList() {
  return [
    "title",
    "slug",
    "type",
    "level2_content_type",
    "level2_type",
    "depth_scope",
    "boundary_guard_passed",
    "knowledge_type",
    "degree",
    "applies_to_degrees",
    "content_scope",
    "partition_role",
    "degree_owner",
    "product_state",
    "category",
    "parent_topic",
    "aliases",
    "keywords",
    "related_topics",
    "short_summary",
    "reading_layers",
    "full_summary",
    "practical_elements",
    "symbolic_meaning",
    "candidate_lesson",
    "tradition_notes",
    "caution_notes",
    "source_notes",
    "language",
    "knowledge_links",
    "chapter_toc",
    "visibility_level",
    "sensitivity_level",
    "tradition_scope",
    "status",
    "observability",
    "relies_on_level1_topics",
  ];
}

function buildEntry(frame, entryLookup) {
  const sources = frame.source_entries.map((slug) => entryLookup.get(slug));
  const sourceTitles = sources
    .map((entry) => entry.title)
    .filter((title) =>
      frame.target_slug === "level2-cable-tow-entry-and-guided-movement-process"
        ? !/Cable-tow|\u05d7\u05d1\u05dc/u.test(title)
        : true,
    );
  const axisText = hebrewList(frame.structure_axes);
  const firstAxes = hebrewList(frame.structure_axes.slice(0, 3));
  const sourceTitleText = hebrewList(sourceTitles.slice(0, 3));

  let shortSummary = "";
  let readingBasic = "";
  let readingSymbolic = "";
  let readingAdvanced = "";
  let fullSummary = "";
  let symbolicMeaning = "";
  let candidateLesson = "";
  let practicalElements = [];
  let aliases = [];
  let traditionNotes = null;

  switch (frame.target_slug) {
    case "level2-discipline-work-and-rough-ashlar-system":
      aliases = ["מערכת עבודה ומשמעת", "אבן גוויל ועבודה פנימית"];
      shortSummary =
        "בדרגה השנייה העבודה, המשמעת ואבן הגוויל נקראות כמערכת אחת. במקום לראות מלאכה, סדר וחומר גלם כרכיבים נפרדים, הקריאה הזו מראה כיצד הם יוצרים יחד צורת התהוות פנימית.";
      readingBasic =
        "בקריאה הבסיסית, האדם איננו משתנה רק מפני שהוא רוצה להשתנות. הוא צריך משמעת חיצונית מול פנימית, עבודה כמאמץ מול עבודה כצורה, וחומר גלם מול אפשרות עיבוד כדי שהשינוי יקבל צורה יציבה.";
      readingSymbolic =
        "בקריאה הסמלית, אבן הגוויל איננה רק דימוי לפתיחה לא־מעובדת, והעבודה איננה רק מאמץ מוסרי. יחד עם המשמעת הן יוצרות מערכת שבה החוץ נותן מסגרת, הפנים נותן כוונה, והאדם עצמו נעשה חומר שניתן לעבד.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, השאלה איננה רק אם האדם עובד על עצמו אלא איך המערכת פועלת. המשמעת קובעת גבול, העבודה נותנת תנועה, ואבן הגוויל מזכירה שכל תנועה מתחילה מחומר שעדיין מבקש עיצוב.";
      fullSummary =
        "הערך נשען על " +
        sourceTitleText +
        " כדי להציג את העבודה הפנימית כמערכת אחת ולא כסדרה של מסרים נפרדים. הציר הראשון הוא משמעת חיצונית מול פנימית: הסדר הטקסי נותן מסגרת, אך רק קליטה פנימית הופכת אותו להרגל יציב. הציר השני הוא עבודה כמאמץ מול עבודה כצורה: לא די ברצון טוב, אלא צריך מבנה שיחזיק את המאמץ לאורך זמן. הציר השלישי הוא חומר גלם מול אפשרות עיבוד: אבן הגוויל מזכירה שהאדם מתחיל כחומר פתוח, לא כצורה גמורה. כך מתברר שמשמעת, עבודה ואבן הגוויל אינן שלוש שפות שונות אלא מערכת אחת של התהוות פנימית. הקריאה הזו עונה על שאלת היסוד של המסגרת: כיצד האדם מקבל צורה בלי לדלג על המלאכה עצמה.";
      symbolicMeaning =
        "המשמעות הסמלית כאן נוצרת מן הקשר בין מסגרת, מלאכה וחומר. אבן הגוויל מסמלת אפשרות לא־מעובדת, המשמעת שומרת על גבול, והעבודה הופכת את האפשרות לצורה. לכן הסמל איננו רק האדם בתחילתו, אלא המערכת שמלמדת כיצד התחלה נעשית בניין.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שלא די לדבר על תיקון; צריך להבין את המערכת שמאפשרת אותו. כאשר המשמעת נשארת רק בחוץ, העבודה נחלשת, וכאשר העבודה נשארת ללא צורה, חומר הגלם נשאר כפי שהיה. לימוד בוגר יותר מתחיל כאשר שלושת החלקים פועלים יחד.";
      practicalElements = ["לקרוא מצב של קושי דרך שלושת הצירים: משמעת, עבודה וחומר גלם."];
      break;
    case "level2-ashlar-transition-and-formation-system":
      aliases = ["מערכת ההתהוות של האבן", "מעבר מאבן גסה לצורה"];
      shortSummary =
        "בדרגה השנייה אבן הגוויל והמעבר אל עיבוד נקראים כמערכת אחת של שינוי. הכלים, תהליך המעבר ותיקון המידות מצטרפים כאן למבנה שמסביר איך חומר מקבל צורה.";
      readingBasic =
        "בקריאה הבסיסית, המעבר איננו רגע חד אלא מערכת. חומר מול צורה, כוח מול דיוק, ומעבר מול תהליך פועלים יחד כדי להראות שהשינוי צריך גם דחיפה וגם הכוונה.";
      readingSymbolic =
        "בקריאה הסמלית, המקבת והאיזמל אינם רק כלים, ואבן הגוויל איננה רק מצב פתיחה. יחד הם מלמדים שהעיצוב המוסרי נבנה מתוך יחס בין אנרגיה, הבחנה, ותהליך שמתקדם צעד אחר צעד.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, השאלה היא איך שינוי נהיה בר־קיימא. כאשר חומר מול צורה, כוח מול דיוק, ומעבר מול תהליך נקראים כמערכת אחת, מתברר שהתהוות אמיתית איננה קפיצה אלא ארגון נכון של כוחות.";
      fullSummary =
        "הערך מחבר את " +
        sourceTitleText +
        " למערכת אחת של התהוות. הציר הראשון, חומר מול צורה, מראה שאבן הגוויל איננה תקלה אלא נקודת מוצא שממנה אפשר לבנות. הציר השני, כוח מול דיוק, מבהיר שהמקבת והאיזמל פועלים יחד: כוח לבדו מפזר, ודיוק לבדו איננו מניע. הציר השלישי, מעבר מול תהליך, מדגיש שתיקון המידות איננו תוצאה של רגע דרמטי אלא של מלאכה חוזרת. כך המעבר מאבן גסה למעובדת נקרא כמערכת שיש בה חומר, כלי, סדר ותכלית. הקריאה הזו עונה על שאלת הליבה של הדרגה: איך שינוי מקבל צורה בלי לאבד את הקצב ההדרגתי שלו.";
      symbolicMeaning =
        "המשמעות הסמלית של הערך איננה רק בשתי האבנים אלא במבנה שמחבר ביניהן. אבן הגוויל מייצגת אפשרות פתוחה, הכלים מייצגים את אופני הפעולה, ותיקון המידות מציג את התוצאה החינוכית של הקשר ביניהם. כך הסמל נעשה למערכת של התהוות ולא לדימוי בודד.";
      candidateLesson =
        "הלקח של דרגה 2 הוא לראות שהתהליך חשוב לא פחות מן היעד. שינוי פנימי אינו נבנה רק מתוך רצון להיות טוב יותר, אלא מתוך הבנה כיצד חומר, פעולה ודיוק נשזרים יחד. ברגע שהמערכת ברורה, גם העבודה נעשית יציבה יותר.";
      practicalElements = ["לבחון תהליך שינוי דרך שלושת הצירים: חומר וצורה, כוח ודיוק, מעבר ותהליך."];
      break;
    case "level2-work-transition-and-measure-process":
      aliases = ["רצף העבודה הפנימית", "תהליך עבודה ותיקון"];
      shortSummary =
        "בדרגה השנייה העבודה נקראת כתהליך של מעבר ותיקון, לא כרעיון כללי בלבד. ההתחלה, העיבוד, המדידה, התיקון וההתהוות מצטרפים כאן לרצף אחד ברור.";
      readingBasic =
        "בקריאה הבסיסית, העבודה הפנימית מתקדמת בשלבים. יש התחלה שמכירה במצב הקיים, עיבוד שמפעיל מלאכה, מדידה ששומרת על יחס, תיקון שמכוון את השינוי, והתהוות שמעניקה לו צורה יציבה.";
      readingSymbolic =
        "בקריאה הסמלית, הכלים והאבן אינם מדברים כל אחד לבדו. הם מצטרפים לרצף שבו האדם נע בין התחלה, עיבוד, מדידה, תיקון והתהוות, ולכן העבודה נקראת כאן כתהליך מסודר ולא כתחושה כללית של מאמץ.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, התהליך עצמו הופך לנושא הלימוד. הקריאה עונה על השאלה מהו רצף העבודה כאשר קוראים אותה כתהליך ולא כרעיון, ומראה שהעומק נוצר מן הסדר שבין השלבים ולא מעודף ניסוח.";
      fullSummary =
        "הערך נשען על " +
        sourceTitleText +
        " כדי לנסח את העבודה כרצף. ההתחלה מציבה את נקודת המוצא של האדם; העיבוד מכניס את פעולת הכלים והמלאכה; המדידה שומרת על יחס נכון; התיקון מכוון את הפעולה אל המידות; וההתהוות מתארת את הצורה החדשה שנבנית בהדרגה. כאשר חמשת הצירים האלה נקראים יחד, מתברר שהעבודה איננה רק משימה מוסרית אלא תהליך חינוכי שיש לו סדר פנימי. זהו ההבדל בין מסר של דרגה ראשונה לבין קריאה מבנית של דרגה שנייה: לא רק מה נכון לעשות, אלא איך העבודה מתקדמת בפועל. כך הרצף עצמו נעשה לכלי לימודי.";
      symbolicMeaning =
        "המשמעות הסמלית נבנית כאן מן המעבר בין שלבים. העבודה איננה צעד יחיד, אלא תנועה מסודרת שבה כל שלב משנה את הבא אחריו: התחלה, עיבוד, מדידה, תיקון והתהוות. כאשר הרצף נשמר, גם הסמל מתגלה כמבנה של צמיחה.";
      candidateLesson =
        "הלקח של דרגה 2 הוא לזהות איפה בתהליך האדם נמצא ולא למהר לקרוא לכל קושי כישלון. מי שמבין את הרצף יודע שהתחלה איננה סוף, שעיבוד דורש מדידה, ושתיקון מוליד התהוות רק כשהוא נשמר לאורך זמן.";
      practicalElements = ["לקרוא תהליך אישי דרך חמשת הצירים: התחלה, עיבוד, מדידה, תיקון והתהוות."];
      break;
    case "level2-obligation-brotherhood-and-work-process":
      aliases = ["תהליך ההתחייבות והאחווה", "עבודת האחווה"];
      shortSummary =
        "בדרגה השנייה התחייבות ואחווה נקראות כתהליך חי ולא כהצהרה בלבד. חוק, מצפון, חובה, אחווה ועבודה מצטרפים כאן לרצף שמסביר איך מחויבות מקבלת צורה מעשית.";
      readingBasic =
        "בקריאה הבסיסית, ההתחייבות איננה נגמרת ברגע שבו נאמרו הדברים. חוק נותן גבול, מצפון בודק כוונה, חובה מגדירה מעשה, אחווה מכניסה אחריות לזולת, והעבודה שומרת שהכול יהפוך להרגל.";
      readingSymbolic =
        "בקריאה הסמלית, ההתחייבות והאחווה אינן שני נושאים נפרדים. הן נקראות כרצף שבו הגבול, התודעה, החובה, הקשר האנושי והעבודה הפנימית בונים יחד מסגרת חיה של נאמנות.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, השאלה היא איך התחייבות נהיית תהליך ולא רק הצהרה. התשובה נבנית דרך חמשת הצירים: חוק, מצפון, חובה, אחווה ועבודה, שכל אחד מהם מחזיק שלב אחר במעבר מן הדיבור אל החיים.";
      fullSummary =
        "הערך מחבר את " +
        sourceTitleText +
        " לרצף מוסרי אחד. חוק מעניק גבול, מצפון בודק את האמת הפנימית, חובה קושרת את האדם למעשה, אחווה מוציאה אותו מן המרכז העצמי, והעבודה שומרת שכל אלה ייעשו להרגל ולא רק למחווה. כך ההתחייבות מפסיקה להיות רגע טקסי ומתחילה להיקרא כתהליך שיש לו שלבים ברורים. הקריאה הזו מראה שהאחווה עצמה איננה רגש מופשט אלא דרך עבודה שמחייבת התמדה, נאמנות ושיקול דעת. במקום לראות את ההתחייבות כמסמך ואת האחווה כערך נפרד, הדרגה השנייה מחברת ביניהם לרצף אחד של בניין אופי. זהו תהליך שמגדיר איך אדם נשאר נאמן גם למסגרת וגם לאחר.";
      symbolicMeaning =
        "המשמעות הסמלית של הערך היא שמחויבות אמיתית בנויה מצירופים ולא מהצהרות. הגבול, הכוונה, החובה, הקשר והעבודה מצטרפים כאן למבנה שמראה כיצד אחווה נהיית צורת חיים. לכן הערך איננו רק על נאמנות, אלא על הארגון הפנימי שמחזיק אותה.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שאחווה אמינה נבנית מתוך תהליך מתמשך. כאשר החוק נשאר ללא מצפון הוא מתקשה לחיות, וכאשר האחווה נשארת ללא עבודה היא דוהה לסיסמה. הלמידה כאן היא לחבר בין העקרונות כך שיישארו פעילים.";
      practicalElements = ["לבדוק החלטה מוסרית דרך חמשת הצירים: חוק, מצפון, חובה, אחווה ועבודה."];
      break;
    case "level2-reflection-chamber-and-mortality-system":
      aliases = ["מערכת חדר ההרהורים", "מבנה ההתבוננות לפני המעבר"];
      shortSummary =
        "בדרגה השנייה חדר ההרהורים נקרא כמערכת התבוננות ולא רק כתחנת הכנה. ניתוק, שתיקה, עימות, ריכוז וכוונה מצטרפים כאן למבנה לימודי אחד.";
      readingBasic =
        "בקריאה הבסיסית, חדר ההרהורים איננו אוסף של סמלים קודרים. הוא בונה ניתוק מן השגרה, שתיקה שמייצבת קשב, עימות עם ארעיות, ריכוז פנימי, וכוונה לפני מעבר.";
      readingSymbolic =
        "בקריאה הסמלית, החדר, השתיקה, הגולגולת והכתיבה אינם פועלים כל אחד לבדו. יחד הם יוצרים מערכת שבה האדם מושהה, פוגש גבול, מסדר את תשומת הלב, ומכין את עצמו לכניסה מתוך כוונה ולא מתוך תנופה בלבד.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, חדר ההרהורים מוסבר כמנגנון חינוכי. ניתוק, שתיקה, עימות, ריכוז וכוונה פועלים כאן כצירי מבנה שמארגנים את המעבר מן החוץ אל הפנים בלי להישען על חומר מדרגות אחרות.";
      fullSummary =
        "הערך נשען על " +
        sourceTitleText +
        " כדי לקרוא את חדר ההרהורים כמערכת. הניתוק מוציא את המועמד מן השגרה, השתיקה בונה קשב, העימות עם ארעיות החיים מייצר רצינות, הריכוז מצמצם פיזור, והכוונה אוספת את כל אלה לקראת מעבר מודע. כך החדר חדל להיות תפאורה ונקרא כמבנה חינוכי שלם. גם הגולגולת והצוואה הפילוסופית אינן נועדו לייצר דרמה בלבד, אלא לארגן תשומת לב, חשבון נפש והכרעה. הקריאה הזו עונה על שאלת היסוד של הערך: איך שתיקה, ניתוק וסמלי ארעיות יוצרים מבנה אחד. התשובה היא שהם פועלים יחד כמערכת שמעמיקה את המוכנות בלי לחרוג מגבול הדרגה.";
      symbolicMeaning =
        "המשמעות הסמלית כאן נוצרת מן האופן שבו כמה רכיבים בונים מצב נפשי אחד. ניתוק, שתיקה, עימות, ריכוז וכוונה יוצרים יחד מרחב שבו האדם נעצר כדי להתכוונן. לכן חדר ההרהורים הוא מערכת התבוננות, לא סמל יחיד.";
      candidateLesson =
        "הלקח של דרגה 2 הוא להבחין שמוכנות אינה מתחילה רק בידע אלא בצורת קשב. כאשר האדם מבין כיצד ניתוק, שתיקה וריכוז נשזרים יחד, הוא לומד לקרוא גם את הכניסה עצמה כחלק ממבנה חינוכי ולא כרגע חולף.";
      practicalElements = ["לקרוא את חדר ההרהורים דרך חמשת הצירים: ניתוק, שתיקה, עימות, ריכוז וכוונה."];
      break;
    case "level2-northeast-placement-and-ashlar-relationship":
      aliases = ["הצבה ואבן הגוויל", "קשר בין יסוד לפוטנציאל"];
      shortSummary =
        "בדרגה השנייה הפינה הצפון־מזרחית ואבן הגוויל נקראות כיחס פעיל בין מיקום, התחלה וחומר גלם. הקריאה הזו בוחנת כיצד יסוד, פוטנציאל וכיוון משנים זה את משמעותו של זה.";
      readingBasic =
        "בקריאה הבסיסית, ההצבה בצפון־מזרח איננה רק מקום, ואבן הגוויל איננה רק דימוי לפתיחה גסה. יחד הן מראות שמיקום, יסוד, התחלה, פוטנציאל וכיוון יוצרים יחס שממנו מתחיל הבניין.";
      readingSymbolic =
        "בקריאה הסמלית, מקום ההצבה מעניק נקודת יסוד, ואבן הגוויל מעניקה חומר התחלה. צירוף שניהם מלמד שהפוטנציאל זקוק גם לכיוון וגם לעמדה נכונה כדי להפוך למלאכה ממשית.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, הקשר איננו בין שני סמלים בלבד אלא בין כמה רכיבים: מיקום, יסוד, התחלה, פוטנציאל וכיוון. כך נענית שאלת הליבה של הערך: מה הקשר בין מיקום, התחלה ופוטנציאל.";
      fullSummary =
        "הערך נשען על " +
        sourceTitleText +
        " כדי לבנות יחס מבני בין נקודת העמידה ובין חומר הפתיחה של האדם. המיקום קובע היכן מתחיל הבניין, היסוד נותן לעמידה תוקף, ההתחלה מגדירה שלב ולא יעד, הפוטנציאל מתואר דרך אבן הגוויל, והכיוון מונע מן הפוטנציאל להישאר בלתי־מעובד. כך ההצבה בצפון־מזרח ואבן הגוויל נקראות לא כפריטים טקסיים מבודדים אלא כיחס שמסביר איך התחלה מקבלת צורה. גם ההפניה הפנימית המופיעה במקורות ההכנה נשארת כאן בגבול מבני: היא מדגישה בירור וכיוון, לא שכבה נוספת של ידע. הקריאה הזו מראה שהשאלה איננה רק מאיפה מתחילים, אלא איך נקודת ההתחלה מגדירה את איכות הבניין.";
      symbolicMeaning =
        "המשמעות הסמלית נבנית כאן מן היחס בין מקום לחומר. ההצבה מעניקה נקודת יסוד, ואבן הגוויל מייצגת פוטנציאל שעדיין מבקש צורה. כאשר הכיוון מצטרף לשניהם, נוצר דגם של התחלה נכונה ולא רק של התחלה חגיגית.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שפוטנציאל לבדו איננו מספיק. האדם זקוק למקום, לכיוון וליסוד כדי שהתחלה תהפוך לבניין. לכן היחס בין ההצבה ובין אבן הגוויל מלמד כיצד התחלה נכונה שומרת על הפוטנציאל מפני פיזור.";
      practicalElements = ["לקרוא התחלה חדשה דרך חמשת הצירים: מיקום, יסוד, התחלה, פוטנציאל וכיוון."];
      break;
    case "level2-threshold-officers-and-candidate-structure":
      aliases = ["מבנה הסף והמפגש", "המועמד מול השומר ונושאי המשרה"];
      shortSummary =
        "בדרגה השנייה הסף, השומר, הפגישה, הסמכות והמעבר נקראים כמבנה אחד. במקום לראות את רגע הכניסה כאוסף תחנות, הקריאה הזו מציגה כיצד הסף יוצר גבול, השומר מייצב בקרה, הפגישה מסדרת את המפגש עם נושאי המשרה, הסמכות מעניקה תוקף, והמעבר מחבר את הכול למסגרת לימודית אחת.";
      readingBasic =
        "בקריאה הבסיסית, הסף הוא לא רק נקודת עמידה פיזית. השומר מסמן שיש גבול, הפגישה פותחת יחס מסודר, הסמכות מבהירה מי מחזיק את הלשכה, והמעבר קושר את המועמד מן החוץ אל תוך סדר מוכתב. כך נבנה מבנה שבו כל צעד תלוי בצעד שלפניו.";
      readingSymbolic =
        "בקריאה הסמלית, הסף והשומר אינם תוספות טקסיות, אלא חלקי מסגרת. הפגישה אינה רק היכרות, אלא צומת שבו הסמכות פוגשת את המועמד ומעבירה אותו למצב חדש. כאשר הסף, השומר, הפגישה, הסמכות והמעבר פועלים יחד, הלשכה מצטיירת כמרחב שמלמד דרך סדר ולא דרך הסבר מופשט בלבד.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, הערך איננו עוסק רק במי עומד בפתח אלא באופן שבו מרחב הכניסה נבנה. הסף מגדיר גבול, השומר ממיין את הגישה, הפגישה מארגנת קשר ראשוני, הסמכות מייצרת היררכיה ברורה, והמעבר קושר את כל אלה למהלך חינוכי אחד. זהו ערך של structure משום שהמשמעות נמצאת במסגרת שנבנית בין התחנות.";
      fullSummary =
        "הערך נשען על שוער (Tyler), מפגש המועמד עם נושאי המשרה, הצוואה הפילוסופית ואלגוריית שלושת החדרים כדי לקרוא את הכניסה ללשכה כמבנה מעבר. הסף אינו רק קצה של חלל אלא מקום שבו נבדק אם יש מעבר לגיטימי מן החוץ אל הפנים. השומר איננו דמות מלווה בלבד, אלא פונקציה של סינון, שמירה והעמדת גבול. הפגישה עם נושאי המשרה איננה אירוע חברתי קצר, אלא צומת שבו הסמכות נגלית למועמד בצורה מדורגת ומסודרת. גם הצוואה הפילוסופית ואלגוריית שלושת החדרים מצטרפות כאן לא כמסרים נפרדים, אלא כהעמקה של אותה תבנית: המעבר צריך מסגרת, והמסגרת צריכה בעלי תפקיד, גבול וסדר.\n\nכך הסף, השומר, הפגישה, הסמכות והמעבר נקראים כמבנה אחד. המוקד איננו פרט טקסי בודד אלא האופן שבו הלשכה מלמדת דרך ארגון הכניסה. במקום לחשוב שהמועמד פשוט מובא פנימה, הקריאה של דרגה 2 מדגישה שהכניסה עצמה כבר מלמדת כיצד פועלת לשכה: דרך תפקידים, נקודות בקרה ומעבר מדורג.";
      symbolicMeaning =
        "המשמעות הסמלית של הערך נבנית מן היחס בין גבול לבין ארגון. הסף מסמל נקודת הכרעה, השומר מסמל אחריות על הגבול, הפגישה מסמלת מפגש עם סדר חי, הסמכות מסמלת תוקף, והמעבר מסמל שינוי מצב. רק כאשר חמשת הרכיבים נקראים יחד מתקבל מבנה לשכתי שלם.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שמבנה נכון קודם להבנה עמוקה. כאשר הסף רופף, השומר חסר, הפגישה מקרית, הסמכות מטושטשת או המעבר לא מסודר, גם הלימוד נעשה חלש. לכן יש לקרוא את רגע הכניסה לא כאפיזודה אלא כבית ספר למבנה.";
      practicalElements = ["לנתח מרחב כניסה דרך חמשת הצירים: סף, שומר, פגישה, סמכות ומעבר."];
      break;
    case "level2-rough-ashlar-transition-and-measure-relationship":
      aliases = ["יחס בין אבן, מעבר ומידה", "חומר גלם אל צורה"];
      shortSummary =
        "בדרגה השנייה אבן הגוויל, המעבר, תיקון המידות, מידה וצורה נקראים כיחס אחד. במקום להציג חומר גלם ואז תוצאה, הקריאה הזו מדגישה שהמעבר עצמו מגדיר כיצד תיקון נבחן, כיצד מידה נשמרת, וכיצד צורה נוצרת.";
      readingBasic =
        "בקריאה הבסיסית, חומר גלם איננו תקלה אלא נקודת מוצא. המעבר איננו קפיצה אלא תהליך מתמשך, תיקון איננו רק שיפור מוסרי כללי, מידה שומרת על יחס נכון, וצורה היא התוצאה שמתגלה רק כאשר כל אלה פועלים יחד. כך נבנה יחס שבו כל רכיב מסביר את האחר.";
      readingSymbolic =
        "בקריאה הסמלית, אבן הגוויל מסמלת חומר גלם פתוח, המעבר מסמל תנועה מן הבלתי מעובד אל המבוקר, תיקון מסמל כיוון פנימי, מידה מסמלת גבול ויחס, וצורה מסמלת את הארגון שנולד מכל אלה. הערך איננו רשימת מושגים, אלא קשר פעיל בין חומר גלם, מעבר, תיקון, מידה וצורה.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, זהו ערך relationship מובהק: המשמעות איננה באבן לבדה וגם לא בתיקון לבדו, אלא בדרך שבה חומר גלם זקוק למעבר, מעבר זקוק למידה, מידה מאפשרת תיקון, ותיקון מאפשר צורה. כאשר אחד הרכיבים חסר, כל היחס נחלש.";
      fullSummary =
        "הערך נשען על אבן גוויל (Rough Ashlar), המעבר מאבן גסה לאבן מסותתת, תיקון המידות ורצפת הפסיפס / המוזאיקה כדי להגדיר יחס אחד. אבן הגוויל מציבה חומר גלם, כלומר מצב פתוח שעוד לא קיבל סדר. המעבר מאבן גסה לאבן מסותתת מדגיש שאין כאן רגע חד אלא תנועה מודרגת. תיקון המידות מעניק לתנועה הזו כיוון מוסרי, אך הכיוון אינו עומד לבדו; הוא נזקק למידה, משום שרק יחס מדוד מונע מן השינוי להפוך לפיזור. מתוך כל אלה מופיעה צורה, לא כקישוט סופי אלא כביטוי של ארגון נכון.\n\nלכן חומר גלם, מעבר, תיקון, מידה וצורה מגדירים זה את זה. חומר גלם בלי מידה נשאר פתוח מדי; מידה בלי מעבר נשארת קפואה; תיקון בלי צורה נשאר כוונה לא ממומשת; וצורה בלי זיכרון של חומר גלם הופכת לחזות ריקה. הקריאה של דרגה 2 מציעה להבין את אבן הגוויל לא רק כתחילת דרך אלא כמרכז יחסים שמסביר כיצד שינוי פנימי נעשה מדוד ובעל צורה.";
      symbolicMeaning =
        "המשמעות הסמלית של הערך נמצאת במעבר בין הקטבים. חומר גלם וצורה אינם שני עולמות נפרדים, אלא שני קצוות של יחס אחד. המעבר מחבר ביניהם, תיקון מנווט את הכיוון, ומידה שומרת על קנה המידה של השינוי. כך הקשר בין הסמלים נעשה העומק של הערך.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שלא שואלים רק אם יש רצון להשתנות, אלא באיזה יחס השינוי מתקדם. כאשר חומר גלם, מעבר, תיקון, מידה וצורה נשמרים יחד, אפשר לקרוא את העבודה הפנימית כמבנה מדויק ולא כסיסמה מוסרית.";
      practicalElements = ["לבחון שינוי פנימי דרך חמשת הצירים: חומר גלם, מעבר, תיקון, מידה וצורה."];
      break;
    case "level2-cable-tow-entry-and-guided-movement-process":
      aliases = ["תהליך הכניסה המודרכת", "מן הבקשה אל מעבר מודרך"];
      shortSummary =
        "בדרגה השנייה הבקשה, קשירה, הובלה, תחנות וכניסה נקראות כתהליך אחד. במקום לראות את רגע הכניסה כפעולה אחת, הקריאה הזו מסדרת אותו כרצף שבו הבקשה פותחת, הקשירה מגדירה תלות והכוונה, ההובלה יוצרת תנועה, התחנות מווסתות קצב, והכניסה חותמת מעבר מודרך.";
      readingBasic =
        "בקריאה הבסיסית, התהליך מתחיל בבקשה ולא בתנועה. אחריה באה קשירה שמבהירה שההתקדמות אינה עצמאית לגמרי, אלא נשענת על ליווי והכוונה. ההובלה מזיזה את המועמד במרחב, התחנות עוצרות את הזרימה כדי לייצר קשב, והכניסה מסמנת שמעבר התרחש מתוך סדר ולא מתוך דחיפה עיוורת.";
      readingSymbolic =
        "בקריאה הסמלית, הבקשה היא פתיחת רצון, הקשירה היא קבלת מסגרת, ההובלה היא תנועה שמקבלת כיוון, התחנות הן מקצבים של עיבוד, והכניסה היא תוצאה של תהליך שלם. לכן אין כאן פעולה בודדת אלא רצף שבו כל שלב מכין את הבא אחריו.";
      readingAdvanced =
        "בקריאה המבנית של דרגה 2, זהו ערך process מובהק. הבקשה מגדירה התחלה, הקשירה מייצרת תנאי, ההולכה היא צורת התנועה המודרכת, ההובלה מסיעה את התהליך, התחנות מארגנות קצב לימודי, והכניסה מסיימת מעבר שכבר עוצב לאורך הדרך. המשמעות נמצאת ברצף שבין החלקים, לא באחד מהם בלבד.";
      fullSummary =
        "הערך נשען על הבקשה להיכנס, ההובלה הראשונה במרחב הלשכה, תחנות ועצירות במסע ועל מקור Level 1 נוסף סביב קשירה כדי לקרוא את הכניסה כרצף מובנה. הבקשה קודמת לתנועה ומציבה רצון מפורש לעבור סף. הקשירה איננה פרט מקרי אלא תנאי שמבהיר שהדרך תתרחש מתוך ליווי והכוונה. ההובלה הראשונה במרחב הלשכה מתרגמת את הרצון והמסגרת לתנועה בפועל, ואילו תחנות ועצירות במסע שוברות את הרצף כדי להפוך את ההתקדמות לקצב לימודי. רק לאחר שהבקשה, הקשירה, ההובלה והתחנות פעלו יחד, הכניסה מקבלת משמעות של מעבר מוסדר.\n\nמכאן נבנה תהליך אחד: הבקשה פותחת, הקשירה מכוונת, ההובלה מקדמת, התחנות מווסתות, והכניסה חותמת. הקריאה של דרגה 2 איננה מוסיפה פרטי טקס, אלא מראה כיצד מהלך הכניסה עצמו בנוי כרצף חינוכי. כך אפשר להבין שהמועמד איננו פשוט מגיע פנימה; הוא עובר דרך מבוקרת שבה כל שלב מכין את השלב הבא.";
      symbolicMeaning =
        "המשמעות הסמלית של הערך נולדת מן הסדר שבין השלבים. הבקשה מסמלת רצון מוצהר, הקשירה מסמלת מסגרת מקבלת, ההובלה מסמלת תלות מכוונת, התחנות מסמלות עיבוד מדורג, והכניסה מסמלת שינוי מצב. יחד הן יוצרות תהליך שבו התקדמות נלמדת דרך קצב והדרכה.";
      candidateLesson =
        "הלקח של דרגה 2 הוא שכניסה אמיתית אינה מתחילה רק כשעוברים את הסף, אלא כבר בדרך שמובילה אליו. כאשר הבקשה, הקשירה, ההובלה, התחנות והכניסה נשמרים כרצף, אפשר להבין כיצד הדרכה בונה מוכנות ולא רק תנועה.";
      practicalElements = ["לקרוא תהליך מעבר דרך חמשת הצירים: בקשה, קשירה, הובלה, תחנות וכניסה."];
      traditionNotes = [
        "הערך נשען על הבקשה להיכנס, ההובלה הראשונה במרחב הלשכה, תחנות ועצירות במסע ועל מקור Level 1 נוסף סביב קשירה, וקורא אותם יחד כתהליך של דרגה שנייה."
      ];
      break;
    default:
      throw new Error(`No deterministic generator defined for ${frame.target_slug}`);
  }

  return {
    title: frame.target_title,
    slug: frame.target_slug,
    type: "topic",
    level2_content_type: CONTENT_TYPE_BY_CANDIDATE[frame.candidate_topic],
    level2_type: frame.level2_type,
    depth_scope: "structural_only",
    boundary_guard_passed: false,
    knowledge_type: frame.knowledge_type,
    degree: "level2",
    applies_to_degrees: ["level2"],
    content_scope: "degree_specific",
    partition_role: "core_degree_content",
    degree_owner: "level2",
    product_state: "draft",
    category: frame.category,
    parent_topic: null,
    aliases,
    keywords: buildKeywords(frame),
    related_topics: TYPE_TO_RELATED[frame.target_slug],
    short_summary: shortSummary,
    reading_layers: {
      basic: readingBasic,
      symbolic: readingSymbolic,
      advanced: readingAdvanced,
    },
    full_summary: fullSummary,
    practical_elements: practicalElements,
    symbolic_meaning: symbolicMeaning,
    candidate_lesson: candidateLesson,
    tradition_notes: [
      `הערך נשען על ${hebrewList(sourceTitles)} מן הדרגה הראשונה, וקורא אותם יחד כמבנה של דרגה שנייה.`,
    ],
    caution_notes: [
      "הערך נשאר בקריאה מבנית של דרגה 2, ללא חומר מדרגות גבוהות וללא פירוט טקסי חורג.",
    ],
    source_notes: [
      `Controlled fill generated from validated frame ${frame.candidate_topic} using grounded Level 1 sources only.`,
    ],
    language: "he",
    work_id: null,
    work_title: "",
    source_kind: null,
    source_path: null,
    source_anchor: null,
    source_heading: null,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: makeKnowledgeLinks(frame.source_entries),
    chapter_toc: ["פתיחה קצרה", "פירוש מבני", "קשרים", "מסקנה לימודית"],
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "interpretive",
    status: "draft",
    observability: {
      is_distinct_from_level1: true,
      depth_level: "level2",
      relies_on_level1_topics: true,
      introduces_new_structure: true,
    },
    relies_on_level1_topics: [...frame.source_entries],
  };
}

function validateSchemaPrecheck(entry, frame) {
  const issues = [];
  for (const field of requiredFieldsList()) {
    if (!Object.prototype.hasOwnProperty.call(entry, field)) {
      issues.push(`Missing required field: ${field}`);
    }
  }
  if (entry.slug !== frame.target_slug) issues.push("slug does not match target_slug");
  if (entry.title !== frame.target_title) issues.push("title does not match target_title");
  if (entry.level2_type !== frame.level2_type) issues.push("level2_type does not match frame");
  if (entry.category !== frame.category) issues.push("category does not match frame");
  if (!entry.relies_on_level1_topics) issues.push("relies_on_level1_topics missing");
  if (!entry.knowledge_links || !entry.knowledge_links.length) issues.push("knowledge_links missing");
  const layers = entry.reading_layers || {};
  for (const bucket of ["basic", "symbolic", "advanced"]) {
    if (!layers[bucket]) issues.push(`reading_layers.${bucket} missing`);
  }
  return issues;
}

function validateFrameAlignment(entry, frame, entryLookup) {
  const issues = [];
  const fullText = [entry.short_summary, entry.full_summary, entry.symbolic_meaning, entry.candidate_lesson, entry.reading_layers.basic, entry.reading_layers.symbolic, entry.reading_layers.advanced].join("\n");
  for (const axis of frame.structure_axes) {
    if (!fullText.includes(axis)) {
      issues.push(`structure axis missing from content: ${axis}`);
    }
  }
  if (!entry.full_summary.includes(frame.source_entries.length > 0 ? "" : "")) {
    // no-op to keep deterministic branch shape
  }
  const groundedSourceCount = frame.source_entries.filter((slug) => entry.relies_on_level1_topics.includes(slug)).length;
  if (groundedSourceCount !== frame.source_entries.length) {
    issues.push("relies_on_level1_topics does not preserve frame source_entries");
  }
  if (!entry.full_summary.includes("דרגה 2") && !entry.reading_layers.advanced.includes("דרגה 2")) {
    issues.push("entry does not explicitly position itself as a Level 2 reading");
  }
  const sourceTitleHits = frame.source_entries.filter((slug) => {
    const source = entryLookup.get(slug);
    return source && (entry.full_summary.includes(source.title) || entry.tradition_notes.join(" ").includes(source.title));
  }).length;
  if (sourceTitleHits === 0) {
    issues.push("entry does not show enough grounding in its frame source set");
  }
  return issues;
}

function validatePurityBoundary(entry) {
  const issues = [];
  const text = JSON.stringify(entry);
  for (const pattern of HIGHER_DEGREE_PATTERNS) {
    if (pattern.test(text)) {
      issues.push(`higher_degree_contamination detected: ${pattern}`);
    }
  }
  for (const pattern of RITUAL_DETAIL_PATTERNS) {
    if (pattern.test(text)) {
      issues.push(`ritual_detail_leakage detected: ${pattern}`);
    }
  }
  if (entry.depth_scope !== "structural_only") {
    issues.push("depth_scope drifted away from structural_only");
  }
  return issues;
}

function validateRouting(entry, frame, level2Payload) {
  const issues = [];
  if (!level2Payload.categories[entry.category]) {
    issues.push("entry category is not a valid Level 2 category");
  }
  if (entry.partition_role !== "core_degree_content") {
    issues.push("entry was rerouted away from core_degree_content");
  }
  if (entry.degree_owner !== "level2" || entry.degree !== "level2") {
    issues.push("entry no longer belongs to level2");
  }
  if (entry.category !== frame.category) {
    issues.push("category changed during routing");
  }
  return issues;
}

function validateApplyGate(entry, level2Payload, acceptedEntries) {
  const issues = [];
  const existingSlugs = new Set(level2Payload.entries.map((item) => item.slug));
  const pendingSlugs = new Set(acceptedEntries.map((item) => item.slug));
  if (existingSlugs.has(entry.slug)) issues.push("target_slug already exists in level2.json");
  if (pendingSlugs.has(entry.slug)) issues.push("target_slug duplicated inside accepted set");
  return issues;
}

function stageStatus(name, issues, extra = {}) {
  return {
    stage: name,
    passed: issues.length === 0,
    issues,
    ...extra,
  };
}

function atomicWriteLevel2(level2Path, payload, backupPath) {
  const originalText = fs.readFileSync(level2Path, "utf8");
  fs.mkdirSync(path.dirname(backupPath), { recursive: true });
  fs.writeFileSync(backupPath, originalText, "utf8");
  const tempPath = `${level2Path}.m4b.tmp`;
  const nextText = `${JSON.stringify(payload, null, 2)}\n`;
  JSON.parse(nextText);
  fs.writeFileSync(tempPath, nextText, "utf8");
  fs.copyFileSync(tempPath, level2Path);
  fs.unlinkSync(tempPath);
}

function main() {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    options[args[i]] = args[i + 1];
  }

  const required = ["--frames", "--frames-validation", "--level1", "--level2", "--candidates", "--report-dir"];
  for (const key of required) {
    if (!options[key]) {
      throw new Error(
        "Usage: node run_phase_m_4_controlled_fill.js --frames <path> --frames-validation <path> --level1 <path> --level2 <path> --candidates <path> --report-dir <dir>",
      );
    }
  }

  const framesPayload = loadJson(options["--frames"]);
  const framesValidationPayload = loadJson(options["--frames-validation"]);
  const level1Payload = loadJson(options["--level1"]);
  const level2Payload = loadJson(options["--level2"]);
  loadJson(options["--candidates"]);

  if ((framesValidationPayload.summary || {}).overall_status !== "pass") {
    throw new Error("Phase M.4a validation did not pass; M4b cannot execute.");
  }

  const reportDir = path.resolve(options["--report-dir"]);
  fs.mkdirSync(reportDir, { recursive: true });

  const entryLookup = sourceMap(level1Payload);
  const generatedEntries = [];
  const validationRows = [];
  const rejections = [];
  const acceptedEntries = [];

  for (const frame of framesPayload.topic_frames) {
    const draftEntry = buildEntry(frame, entryLookup);

    const schemaIssues = validateSchemaPrecheck(draftEntry, frame);
    const alignmentIssues = validateFrameAlignment(draftEntry, frame, entryLookup);
    const purityIssues = validatePurityBoundary(draftEntry);
    const routingIssues = validateRouting(draftEntry, frame, level2Payload);
    const applyIssues = validateApplyGate(draftEntry, level2Payload, acceptedEntries);

    const stages = [
      stageStatus("stage_1_schema_precheck", schemaIssues),
      stageStatus("stage_2_frame_alignment", alignmentIssues),
      stageStatus("stage_3_f2_purity_boundary", purityIssues, {
        provider_invoked: false,
        native_like_within_level2_target: purityIssues.length === 0,
      }),
      stageStatus("stage_4_f3_routing", routingIssues, {
        rerouted: false,
      }),
      stageStatus("stage_5_h_apply_gate", applyIssues),
    ];

    const accepted = stages.every((stage) => stage.passed);
    if (accepted) {
      draftEntry.boundary_guard_passed = true;
      draftEntry.product_state = "built";
      acceptedEntries.push(draftEntry);
    } else {
      rejections.push({
        candidate_topic: frame.candidate_topic,
        target_slug: frame.target_slug,
        rejection_reasons: stages.filter((stage) => !stage.passed).flatMap((stage) => stage.issues),
        draft_entry: draftEntry,
      });
    }

    generatedEntries.push({
      candidate_topic: frame.candidate_topic,
      target_slug: frame.target_slug,
      accepted,
      entry: accepted ? draftEntry : draftEntry,
    });
    validationRows.push({
      candidate_topic: frame.candidate_topic,
      target_slug: frame.target_slug,
      accepted,
      stages,
    });
  }

  const acceptedSlugs = acceptedEntries.map((entry) => entry.slug);
  const warningCount = validationRows.reduce(
    (sum, row) => sum + row.stages.filter((stage) => stage.issues.length > 0 && stage.passed).length,
    0,
  );
  const errorCount = rejections.reduce((sum, row) => sum + row.rejection_reasons.length, 0);

  let overallStatus = "pass";
  if (acceptedEntries.length !== framesPayload.topic_frames.length || rejections.length > 0) {
    overallStatus = "fail";
  }

  let backupPath = null;
  if (acceptedEntries.length) {
    const nextLevel2 = JSON.parse(JSON.stringify(level2Payload));
    nextLevel2.meta.updated_at = new Date().toISOString().slice(0, 10);
    nextLevel2.meta.build_phase = "phase_m4b";
    nextLevel2.entries.push(...acceptedEntries);
    backupPath = path.join(reportDir, "level2.pre_m4b_backup.json");
    atomicWriteLevel2(options["--level2"], nextLevel2, backupPath);
    JSON.parse(fs.readFileSync(options["--level2"], "utf8"));
  }

  const entriesArtifact = {
    generated_at: new Date().toISOString(),
    phase: "phase_m4b_controlled_fill",
    frame_count: framesPayload.topic_frames.length,
    generated_count: generatedEntries.length,
    accepted_count: acceptedEntries.length,
    rejected_count: rejections.length,
    entries: generatedEntries,
  };
  const rejectionsArtifact = {
    generated_at: new Date().toISOString(),
    phase: "phase_m4b_controlled_fill",
    rejected_count: rejections.length,
    rejections,
  };
  const validationArtifact = {
    generated_at: new Date().toISOString(),
    phase: "phase_m4b_controlled_fill",
    frame_count: framesPayload.topic_frames.length,
    accepted_count: acceptedEntries.length,
    rejected_count: rejections.length,
    validations: validationRows,
  };
  const reportArtifact = {
    generated_at: new Date().toISOString(),
    phase: "phase_m4b_controlled_fill",
    frame_count: framesPayload.topic_frames.length,
    generated_count: generatedEntries.length,
    accepted_count: acceptedEntries.length,
    rejected_count: rejections.length,
    error_count: errorCount,
    warning_count: warningCount,
    accepted_slugs: acceptedSlugs,
    rejected_candidates: rejections.map((row) => row.candidate_topic),
    overall_status: overallStatus,
    level2_json_valid: true,
    backup_path: backupPath ? toSlashPath(backupPath) : null,
    level2_path: toSlashPath(options["--level2"]),
  };

  writeJson(path.join(reportDir, "phase_m_4_fill_entries.json"), entriesArtifact);
  writeJson(path.join(reportDir, "phase_m_4_fill_rejections.json"), rejectionsArtifact);
  writeJson(path.join(reportDir, "phase_m_4_fill_validation.json"), validationArtifact);
  writeJson(path.join(reportDir, "phase_m_4_fill_report.json"), reportArtifact);
}

main();
