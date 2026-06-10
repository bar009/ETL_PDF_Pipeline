const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot } = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m10_level3_build";
const DEFAULT_SITE_ROOT = getWorkSiteRoot();
const DEFAULT_DEGREES_PATH = path.join(DEFAULT_SITE_ROOT, "data", "degrees.json");
const DEFAULT_LEVEL3_PATH = path.join(DEFAULT_SITE_ROOT, "data", "level3.json");
const DEFAULT_LEVEL3_BACKUP_PATH = path.join(DEFAULT_SITE_ROOT, "data", "level3.pre_m10_backup.json");
const DEFAULT_DEGREES_BACKUP_PATH = path.join(DEFAULT_SITE_ROOT, "data", "degrees.pre_m10_backup.json");
const DEFAULT_SEED_SPEC_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "level3_boundary_seed_spec.json");
const DEFAULT_GOLDSET_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "level3_boundary_goldset_seed.json");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_10_level3_build_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_10_level3_build_validation.json");

const REQUIRED_LEVEL3_FIELDS = [
  "title",
  "slug",
  "type",
  "degree",
  "applies_to_degrees",
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
  "knowledge_links",
  "chapter_toc",
  "visibility_level",
  "sensitivity_level",
  "tradition_scope",
  "status",
  "degree_owner",
  "boundary_guard_passed",
];

const FORBIDDEN_LEVEL3_PATTERNS = [
  { label: "royal_arch", pattern: /royal arch|קשת מלכותית|רויאל ארץ׳/iu },
  { label: "return_from_babylon", pattern: /babylon|בבל/iu },
  { label: "hidden_vault", pattern: /vault|קמרון|אוצר נסתר/iu },
];

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();

  const report = {
    phase: PHASE_ID,
    goal: "Create the first native Level 3 runtime lane from the approved seed boundary and goldset.",
    mode: "controlled_level3_build",
    executed_at: executedAt,
    inputs: {
      site_root: config.siteRoot,
      degrees_path: config.degreesPath,
      level3_path: config.level3Path,
      seed_spec: config.seedSpecPath,
      goldset_seed: config.goldsetPath,
    },
    outputs: {
      updated_degrees: config.degreesPath,
      updated_level3: config.level3Path,
      degrees_backup: config.degreesBackupPath,
      level3_backup: config.level3BackupPath,
      report: config.reportPath,
      validation: config.validationPath,
    },
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
    assertFileExists(config.degreesPath, "degrees.json");
    assertFileExists(config.libraryPath, "library.json");
    assertFileExists(config.seedSpecPath, "level3 seed spec");
    assertFileExists(config.goldsetPath, "level3 goldset");

    const degreesRaw = fs.readFileSync(config.degreesPath, "utf8");
    const existingLevel3Raw = fs.existsSync(config.level3Path)
      ? fs.readFileSync(config.level3Path, "utf8")
      : null;

    const degrees = JSON.parse(degreesRaw);
    const library = JSON.parse(fs.readFileSync(config.libraryPath, "utf8"));
    const seedSpec = JSON.parse(fs.readFileSync(config.seedSpecPath, "utf8"));
    const goldsetSeed = JSON.parse(fs.readFileSync(config.goldsetPath, "utf8"));
    const libraryLookup = new Set((library.entries || []).map((entry) => `library:${entry.slug}`));

    const level3Data = buildLevel3Dataset({
      seedSpec,
      goldsetSeed,
      libraryLookup,
    });

    const updatedDegrees = {
      ...degrees,
      level3: buildLevel3RegistryRecord(degrees.level2?.passwordHash || null),
    };

    const validationIssues = [];

    validation.checks.seed_spec_ready = buildCheck(
      seedSpec?.meta?.status === "seed_ready_not_approved" || seedSpec?.meta?.status === "seed_ready_approved",
      "Level 3 boundary seed spec was found and parsed.",
      {
        candidate_count: Array.isArray(seedSpec?.native_anchor_candidates) ? seedSpec.native_anchor_candidates.length : 0,
      }
    );
    validation.checks.goldset_seed_ready = buildCheck(
      Array.isArray(goldsetSeed?.positive_examples) && goldsetSeed.positive_examples.length >= 3,
      "Level 3 goldset seed was found and parsed.",
      {
        positive_example_count: Array.isArray(goldsetSeed?.positive_examples) ? goldsetSeed.positive_examples.length : 0,
      }
    );

    validationIssues.push(...validateLevel3Dataset(level3Data, libraryLookup));
    validationIssues.push(...validateLevel3Registry(updatedDegrees.level3));

    validation.checks.level3_dataset_valid = buildCheck(
      validationIssues.length === 0,
      validationIssues.length === 0
        ? "Level 3 dataset satisfies the controlled-build contract."
        : "Level 3 dataset validation detected issues.",
      {
        issues: validationIssues,
      }
    );

    ensureParentDir(config.degreesBackupPath);
    if (fs.existsSync(config.level3Path)) {
      ensureParentDir(config.level3BackupPath);
      fs.writeFileSync(config.level3BackupPath, existingLevel3Raw, "utf8");
      report.actions.push({
        type: "backup_level3",
        path: config.level3BackupPath,
      });
    }
    fs.writeFileSync(config.degreesBackupPath, degreesRaw, "utf8");
    report.actions.push({
      type: "backup_degrees",
      path: config.degreesBackupPath,
    });

    const failingChecks = Object.values(validation.checks).filter((check) => !check.pass);
    validation.failures = validationIssues.map((issue) => ({
      check: issue.check,
      detail: issue.detail,
    }));
    validation.error_count = failingChecks.length + validation.failures.length;
    if (validation.error_count > 0) {
      validation.overall_status = "fail";
      throw new Error("Level 3 build validation failed before write.");
    }

    writeJsonAtomic(config.level3Path, level3Data);
    writeJsonAtomic(config.degreesPath, updatedDegrees);

    report.actions.push({
      type: "write_level3_dataset",
      path: config.level3Path,
      entry_count: level3Data.entries.length,
      category_count: Object.keys(level3Data.categories).length,
    });
    report.actions.push({
      type: "update_degree_registry",
      path: config.degreesPath,
      level3_access_mode: updatedDegrees.level3.access_mode,
    });

    validation.checks.json_roundtrip_valid = buildCheck(
      Boolean(JSON.parse(fs.readFileSync(config.level3Path, "utf8")))
        && Boolean(JSON.parse(fs.readFileSync(config.degreesPath, "utf8"))),
      "Written Level 3 and degrees files parse successfully."
    );

    validation.overall_status = "pass";
    report.overall_status = "pass";

    ensureParentDir(config.reportPath);
    ensureParentDir(config.validationPath);
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
    fs.writeFileSync(config.validationPath, stringifyJson(validation), "utf8");

    console.log(`Level 3 built: ${config.level3Path}`);
    console.log(`Degrees updated: ${config.degreesPath}`);
    console.log(`Build report: ${config.reportPath}`);
    console.log(`Build validation: ${config.validationPath}`);
  } catch (error) {
    validation.overall_status = "fail";
    if (validation.failures.length === 0) {
      validation.failures = [{ check: "execution", detail: error.message }];
      validation.error_count = 1;
    }
    report.overall_status = "fail";
    report.error = error.message;
    ensureParentDir(config.reportPath);
    ensureParentDir(config.validationPath);
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
    fs.writeFileSync(config.validationPath, stringifyJson(validation), "utf8");
    console.error(error.message);
    process.exitCode = 1;
  }
}

function buildLevel3Dataset({ seedSpec, goldsetSeed, libraryLookup }) {
  const meta = {
    degree: "level3",
    title: "דרגה 3 - רב בונה",
    updated_at: new Date().toISOString().slice(0, 10),
    product_state: "built",
    build_phase: "phase_m10",
    calibration_phase: "phase_m8_1",
    source_seed_status: seedSpec?.meta?.status || null,
    source_goldset_status: goldsetSeed?.status || null,
  };

  const categories = {
    symbolic_systems: {
      id: "symbolic_systems",
      title: "מערכות סמליות",
      symbol: "✶",
      description: "מערכות הסמל של הדרגה השלישית: חירם, אובדן, נאמנות, זיכרון והיעדר שאיננו מתבטל.",
      parent_category: null,
    },
    ritual_dynamics: {
      id: "ritual_dynamics",
      title: "דינמיקה טקסית",
      symbol: "↟",
      description: "תנועה דרגתית של מעבר, נפילה, הקמה והשבה, כפי שהיא נקראת בדרגה השלישית.",
      parent_category: null,
    },
    relationships_between_symbols: {
      id: "relationships_between_symbols",
      title: "קשרים בין סמלים",
      symbol: "⚱",
      description: "יחסים בין קבר, שיטה, זיכרון, המשכיות ותקווה שאינה תלויה בהסבר משלים מדרגות סמוכות.",
      parent_category: null,
    },
  };

  const entries = [
    {
      title: "חירם, האובדן והנאמנות כמערכת דרגה שלישית",
      slug: "level3-hiram-loss-and-fidelity-system",
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
      category: "symbolic_systems",
      parent_topic: null,
      aliases: [
        "מערכת חירם והאובדן",
        "Hiram Loss Fidelity",
      ],
      keywords: [
        "חירם",
        "אובדן",
        "נאמנות",
        "רב בונה",
        "דרגה 3",
        "Master Mason",
      ],
      related_topics: {
        prior: [],
        companion: [
          "level3-raising-and-restoration-process",
          "level3-acacia-grave-and-immortality-relationship",
        ],
        deeper: [],
      },
      short_summary: "הדרגה השלישית נקראת כאן כמערכת אחת של חירם, אובדן ונאמנות. לא מדובר באגדה נפרדת, אלא במבנה שבו אובדן הסוד, נאמנות לאמון, והמשך העמידה תחת לחץ מגדירים יחד את זהות הדרגה.",
      reading_layers: {
        basic: "בקריאה הבסיסית, חירם איננו רק דמות סיפורית אלא מרכז שמסביבו מסתדרים אובדן ונאמנות. האובדן יוצר חלל אמיתי, והנאמנות מגדירה כיצד עומדים מולו מבלי לבטל אותו.",
        symbolic: "בקריאה הסמלית, חירם, האובדן והנאמנות פועלים כמערכת אחת. הדמות מסמלת תפקיד שנשמר, האובדן מסמן היעדר שלא נסגר בקלות, והנאמנות שומרת על שלמות גם כאשר אין פתרון מיידי.",
        advanced: "בקריאה המבנית של דרגה 3, המשמעות איננה בשחזור דרמטי בלבד אלא במערכת של זהות: חירם מגדיר מוקד, האובדן מונע סגירה שטחית, והנאמנות מחזיקה את המערכת מבלי לברוח להשלמה מדרגות מאוחרות יותר.",
      },
      full_summary: "הדרגה השלישית בונה את זהותה סביב מערכת חירם, האובדן והנאמנות. חירם פועל כאן לא רק כגיבור זיכרון, אלא כמרכז של אחריות ושל אמון שנשמר גם כאשר מופעל עליו לחץ. מכאן נולד האובדן: לא כאירוע מקרי בלבד, אלא כהיעדר ממשי שנשאר כחלק מן הדרגה. המערכת הזו חשובה מפני שהיא מלמדת שהעמידה הנאמנה איננה מתבטלת רק מפני שהמחיר כבד, וגם שאובדן איננו בהכרח כישלון של המסגרת אלא חלק מן האמת שהיא נושאת.\n\nבמקום לקרוא את הסיפור כאגדה על העבר, הקריאה של דרגה 3 רואה כאן מערכת חיה. חירם מייצב תפקיד של נאמנות לאמון; האובדן יוצר ריק שאי אפשר לסגור בסיסמא פשוטה; והנאמנות מסרבת להחליף אמת בעמידה נוחה. לכן שלושת הרכיבים אינם שלושה נושאים נפרדים אלא מערכת אחת של משמעות. הדמות בונה את המרכז, האובדן שומר על חומרת הדרגה, והנאמנות מגדירה כיצד אפשר להישאר בתוך הדרמה מבלי לעוות את משמעותה.\n\nזהו ערך system מובהק מפני שהמשמעות לא יושבת ברכיב יחיד. אם מדגישים רק את חירם, מאבדים את עומק האובדן; אם מדגישים רק אובדן, מאבדים את אופייה המוסרי של הדרגה; ואם מדגישים רק נאמנות, מאבדים את המחיר ואת הריק שבלעדיהם אין דרגה שלישית. המערכת השלמה מלמדת שהדרגה נבנית סביב אמת שאיננה נמסרת בזול ואיננה מתמלאת על ידי השלמה חיצונית.",
      practical_elements: [
        "לקרוא כל דיון בדרגה השלישית דרך שלושת הצירים: מי נושא את האמון, מה בדיוק אבד, ואיזו נאמנות נשמרת גם בלי סגירה מלאה.",
        "להבחין בין עמידה נאמנה מול חסר לבין ניסיון מהיר מדי לבטל את החסר באמצעות השלמה חיצונית.",
      ],
      symbolic_meaning: "המשמעות הסמלית של הערך נוצרת מן המתח שבין מרכז לאובדן. חירם מסמל מוקד של אמון, האובדן מסמל היעדר שאי אפשר להחליק, והנאמנות מסמלת שלמות שאינה נשברת רק מפני שאין פתרון מיידי. יחד הם מגדירים את שפת הדרגה השלישית.",
      candidate_lesson: "הלקח של הדרגה השלישית הוא שלא כל אמת נמדדת לפי מה שנשאר ביד, אלא גם לפי מה שלא נבגד. כאשר אובדן ונאמנות נקראים יחד, אפשר להבין ששלמות פנימית נבחנת גם ברגע שבו מה שמבוקש אינו ניתן להשבה מיידית.",
      tradition_notes: [
        "הערך נשען על חומר Master Mason ברור מן הספרייה בלבד.",
        "המערכת נשארת בתוך תחום הדרגה השלישית ואינה נפתרת באמצעות Royal Arch או מסגרות appendant.",
      ],
      caution_notes: [
        "אין להחליק את האובדן לכדי תקציר עלילתי בלבד.",
        "אין לערב כאן recovery-of-the-word, hidden vault או שמות מדרגות סמוכות.",
      ],
      source_notes: [
        "Phase M.10 Level 3 native build from approved Level 3 seed boundary and goldset.",
        "Seed topic: level3-candidate-hiram-loss-and-fidelity-system.",
        "Primary library anchors: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree, blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason, textbook-freemasonry-tracing-boards-en.",
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
      knowledge_links: [
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason", degree: "library" },
        { slug: "textbook-freemasonry-tracing-boards-en", degree: "library" },
      ],
      chapter_toc: [
        "פתיחה קצרה",
        "מערכת חירם, האובדן והנאמנות",
        "קשרים",
        "מסקנה לימודית",
      ],
      visibility_level: "internal",
      sensitivity_level: "guarded",
      tradition_scope: "interpretive",
      status: "draft",
      observability: {
        is_distinct_from_level2: true,
        depth_level: "level3",
        relies_on_level1_topics: false,
        introduces_new_structure: true,
        native_degree_identity: true,
      },
      relies_on_level1_topics: [],
    },
    {
      title: "הקמה, השבה והשלמה כתהליך דרגה שלישית",
      slug: "level3-raising-and-restoration-process",
      type: "topic",
      level3_content_type: "process_explanation",
      level3_type: "process",
      depth_scope: "structural_only",
      boundary_guard_passed: true,
      knowledge_type: "ritual",
      degree: "level3",
      applies_to_degrees: ["level3"],
      content_scope: "degree_specific",
      partition_role: "core_degree_content",
      degree_owner: "level3",
      product_state: "built",
      category: "ritual_dynamics",
      parent_topic: null,
      aliases: [
        "תהליך ההקמה",
        "Raising and Restoration",
      ],
      keywords: [
        "הקמה",
        "השבה",
        "השלמה",
        "דרגה שלישית",
        "Raising",
        "Master Mason",
      ],
      related_topics: {
        prior: [
          "level3-hiram-loss-and-fidelity-system",
        ],
        companion: [
          "level3-acacia-grave-and-immortality-relationship",
        ],
        deeper: [],
      },
      short_summary: "בדרגה השלישית ההקמה נקראת כתהליך של השבה מתוך אובדן, לא כרגע בודד של פתרון. זהו רצף שבו נפילה, היעדר, פעולה טקסית והשבה חלקית יוצרים יחד הבנה של השלמה שאינה מבטלת את מה שאבד.",
      reading_layers: {
        basic: "בקריאה הבסיסית, ההקמה היא תהליך ולא מחווה אחת. יש נפילה, יש היעדר, יש פעולה שמגיבה להיעדר, ויש השבה שמאפשרת מעבר חדש.",
        symbolic: "בקריאה הסמלית, ההקמה מייצרת תנועה מן הקטיעה אל אפשרות של עמידה מחודשת. היא אינה מחזירה את הכול כפי שהיה, אלא בונה צורת המשך שנושאת איתה גם את סימן האובדן.",
        advanced: "בקריאה המבנית של דרגה 3, זהו process מובהק: האובדן מקדים, הפעולה הטקסית מגיבה אליו, וההשבה מסיימת שלב מבלי לטעון שהחסר בוטל לגמרי. לכן הדרגה השלישית מלמדת תהליך של restoration, לא סגירה מלאכותית.",
      },
      full_summary: "ההקמה בדרגה השלישית איננה נקראת כאן כרגע מרהיב בלבד, אלא כתהליך שלם. תחילה נוצר אובדן שאין להכחישו; אחר כך מתבהר שאין אפשרות פשוטה לשוב למצב הקודם; ורק לאחר מכן מופיעה פעולה טקסית שמאפשרת השבה. מכאן נולדת משמעות של restoration: לא החזרת המצב בדיוק כפי שהיה, אלא בניית אפשרות חדשה לעמידה, לזיכרון ולהמשך.\n\nהערך מדגיש שהשלמה בדרגה השלישית איננה זהה למחיקה של האובדן. אם הנפילה הייתה רק תחנת ביניים טכנית, לא היה צורך בדרגה שלישית. אם ההשבה הייתה שיחזור מלא, לא היה נשאר מקום לעומק הטקסי של זיכרון, נאמנות ותקווה. לכן התהליך של הדרגה נע בין שלושה מוקדים: היעדר, פעולה, והשבה. רק הרצף ביניהם יוצר את המשמעות.\n\nזהו ערך process מפני שהדגש איננו על סמל יחיד ולא על מערכת של דמויות בלבד, אלא על סדר מהלכים. האובדן פותח, ההקמה פועלת, וההשבה חותמת מעבר. אבל החתימה איננה מחזירה את הדרגה למקום נטול כאב; היא מלמדת כיצד ניתן לעבור דרך קטיעה מבלי להישאר קפואים בתוכה. זוהי שלמות מסוג אחר: שלמות שנבנית דרך ההכרה בחסר ולא דרך הכחשתו.",
      practical_elements: [
        "לקרוא את הדרגה השלישית דרך שלושה שלבים: אובדן, פעולה משיבה, ועמידה מחודשת שאינה מוחקת את מה שחסר.",
        "להבחין בין restoration פנימי של הדרגה לבין הבטחה של השלמה ממסגרות סמוכות שאינן חלק מ־Level 3 native.",
      ],
      symbolic_meaning: "המשמעות הסמלית של ההקמה היא שמעבר אמיתי איננו קורה למרות האובדן אלא דרכו. ההיעדר יוצר את עומק התהליך, הפעולה נותנת לו צורה, וההשבה מעניקה אפשרות של עמידה מחודשת שאינה מתיימרת לבטל את מה שאבד.",
      candidate_lesson: "הלקח הוא שהשבה איננה תמיד החזרת הדבר המקורי, אלא לפעמים יצירת יכולת חדשה לשאת אמת, זיכרון ואחריות. הדרגה השלישית מלמדת שהשלמה עמוקה יותר נבנית מתוך הכרה בחסר ולא מתוך קיצור דרך.",
      tradition_notes: [
        "הערך נשען על חומר raising ברור מן הספרייה בלבד.",
        "הקריאה נשארת בתוך המסגרת של דרגה שלישית native ואינה גולשת ל־Royal Arch או למסלולים משלים.",
      ],
      caution_notes: [
        "אין להפוך את הערך לרצף של פרטי טקס מפורטים.",
        "אין לערב כאן השבת מילה, שמות נסתרים או vault motifs שאינם native לדרגה השלישית.",
      ],
      source_notes: [
        "Phase M.10 Level 3 native build from approved Level 3 seed boundary and goldset.",
        "Seed topic: level3-candidate-raising-and-restoration-process.",
        "Primary library anchors: blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree, blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason, textbook-freemasonry-tracing-boards-en.",
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
      knowledge_links: [
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason", degree: "library" },
        { slug: "textbook-freemasonry-tracing-boards-en", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service", degree: "library" },
      ],
      chapter_toc: [
        "פתיחה קצרה",
        "האובדן קודם להשבה",
        "תהליך ההקמה",
        "מסקנה לימודית",
      ],
      visibility_level: "internal",
      sensitivity_level: "guarded",
      tradition_scope: "interpretive",
      status: "draft",
      observability: {
        is_distinct_from_level2: true,
        depth_level: "level3",
        relies_on_level1_topics: false,
        introduces_new_structure: true,
        native_degree_identity: true,
      },
      relies_on_level1_topics: [],
    },
    {
      title: "ענף השיטה, הקבר והאלמוות כיחס סמלי",
      slug: "level3-acacia-grave-and-immortality-relationship",
      type: "topic",
      level3_content_type: "symbol_relationship_analysis",
      level3_type: "relationship",
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
      aliases: [
        "השיטה והקבר",
        "Acacia Grave Immortality",
      ],
      keywords: [
        "שיטה",
        "קבר",
        "אלמוות",
        "המשכיות",
        "דרגה 3",
        "Master Mason",
      ],
      related_topics: {
        prior: [
          "level3-hiram-loss-and-fidelity-system",
        ],
        companion: [
          "level3-raising-and-restoration-process",
        ],
        deeper: [],
      },
      short_summary: "בדרגה השלישית ענף השיטה, הקבר והאלמוות אינם שלושה סמלים מבודדים אלא יחס אחד. הקבר מסמן גבול, השיטה מסמנת המשכיות בתוך הגבול, והאלמוות מגדיר את הקריאה של מה שאיננו נחתם במוות בלבד.",
      reading_layers: {
        basic: "בקריאה הבסיסית, הקבר מציב את גבול החיים הגלוי, השיטה מצביעה על המשך שאינו נעלם עם הקבורה, והאלמוות נותן לשני הסמלים יחד כיוון שאינו רק אבל.",
        symbolic: "בקריאה הסמלית, השיטה אינה קישוט לקבר אלא סימן שמגדיר מחדש את הקבר עצמו. הקבר בלי השיטה היה רק סיום; השיטה בלי הקבר הייתה סמל כללי מדי; והאלמוות הוא המשמעות שנוצרת מן המפגש ביניהם.",
        advanced: "בקריאה המבנית של דרגה 3, זהו relationship מובהק: הקבר, השיטה והאלמוות מפרשים זה את זה. המשמעות איננה בהדרכת לוויה טכנית, אלא ביחס בין גבול, זיכרון, המשך ותקווה דרגתית.",
      },
      full_summary: "הקבר בדרגה השלישית מסמן את הגבול שמולו האדם נעצר. הוא איננו רק סמל של סוף ביולוגי, אלא מקום שבו השפה הטקסית נבחנת: האם כל משמעות נסגרת בקו הזה, או שמופיע יחס אחר. ענף השיטה נכנס בדיוק בנקודה זו. הוא איננו תוספת חיצונית לקבר, אלא סימן שמכריח לקרוא את הקבר מחדש. הקבר חדל להיות רק סיום, והשיטה מסמנת שבתוך מקום הגבול נשמרת גם אפשרות של המשך.\n\nמכאן נולדת הקריאה של אלמוות. לא כהכרזה מופשטת שנזרקת מעל הסמלים, אלא כמשמעות שנבנית מן היחס ביניהם. הקבר מעניק את הכובד, השיטה מעניקה את סימן ההמשכיות, והאלמוות הוא השם שהדרגה נותנת למשמעות הזאת. לכן אין לקרוא את שלושת הסמלים בנפרד. רק כאשר הקבר והשיטה מוחזקים יחד, אפשר להבין מדוע הדרגה השלישית מדברת על יותר מאשר מוות בלבד.\n\nהערך שומר גם על גבול חשוב: הוא איננו הופך את דרגה 3 למסגרת של מנהגי הלוויה בלבד. שירות הקבורה והטקסים ליד הקבר יכולים לשמש עוגנים, אבל הלב של הערך הוא הקשר בין הסמלים. זהו ערך relationship מפני שהמשמעות נולדת מן ההדדיות: הקבר מחריף את הצורך בסימן, השיטה מגדירה את אופי ההמשך, והאלמוות נותן לשניהם שפה שאינה רק זיכרון פסיבי.",
      practical_elements: [
        "לשאול בכל קריאה של הדרגה השלישית: מהו הגבול שהקבר מציב, מה מסמן ענף השיטה בתוך הגבול הזה, ואיזו צורת המשכיות הדרגה מאפשרת לקרוא.",
        "להבחין בין ערך סמלי native של קבר-שיטה-אלמוות לבין הוראות קבורה טכניות או הרחבות מאוחרות יותר.",
      ],
      symbolic_meaning: "המשמעות הסמלית של הערך נוצרת מן היחס בין גבול לבין המשכיות. הקבר מסמל את המקום שבו הכול יכול היה להסתיים, השיטה מסמלת שהסיום איננו המילה האחרונה, והאלמוות הוא שם היחס שנוצר ביניהם. יחד הם מעניקים לדרגה השלישית את שפת התקווה שלה.",
      candidate_lesson: "הלקח של הדרגה השלישית הוא שהתקווה אינה נולדת מהכחשת הקבר, אלא מן הדרך שבה הסמל נשמר גם מולו. ענף השיטה איננו מבטל את הכובד, אלא מלמד לקרוא בתוכו המשכיות, זיכרון ואמון במה שאיננו חומרי בלבד.",
      tradition_notes: [
        "הערך נשען על עוגני ספרייה של דרגה שלישית, במיוחד Tracing Boards, Burial Service ו־Ceremonies at the Grave.",
        "השימוש במקורות הקבורה כאן נשאר כסיוע לקריאת יחסי הסמלים, לא כיצירת lane של funeral administration.",
      ],
      caution_notes: [
        "אין להפוך את הערך למדריך טקס קבורה.",
        "אין לערב כאן hidden-name, vault או Royal Arch motifs.",
      ],
      source_notes: [
        "Phase M.10 Level 3 native build from approved Level 3 seed boundary and goldset.",
        "Seed topic: level3-candidate-acacia-grave-and-immortality-relationship.",
        "Primary library anchors: textbook-freemasonry-tracing-boards-en, blue-lodge-ritual-reference-guide-2021-section-0077-burial-service, blue-lodge-ritual-reference-guide-2021-section-0078-ceremonies-at-the-grave.",
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
      knowledge_links: [
        { slug: "textbook-freemasonry-tracing-boards-en", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0078-ceremonies-at-the-grave", degree: "library" },
        { slug: "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree", degree: "library" },
      ],
      chapter_toc: [
        "פתיחה קצרה",
        "הקבר כגבול",
        "השיטה כסימן המשך",
        "מסקנה לימודית",
      ],
      visibility_level: "internal",
      sensitivity_level: "guarded",
      tradition_scope: "interpretive",
      status: "draft",
      observability: {
        is_distinct_from_level2: true,
        depth_level: "level3",
        relies_on_level1_topics: false,
        introduces_new_structure: true,
        native_degree_identity: true,
      },
      relies_on_level1_topics: [],
    },
  ];

  for (const entry of entries) {
    for (const link of entry.knowledge_links) {
      if (!libraryLookup.has(`${link.degree}:${link.slug}`)) {
        throw new Error(`Missing library anchor while building Level 3: ${link.degree}:${link.slug}`);
      }
    }
  }

  return { meta, categories, entries };
}

function buildLevel3RegistryRecord(level2PasswordHash) {
  return {
    title: "דרגה 3 – רב בונה",
    color: "#6b2c2c",
    symbol: "✶",
    access_mode: "password",
    passwordHash: level2PasswordHash,
    password_policy: "temporary_same_as_level2_until_dedicated_level3_password_is_set",
  };
}

function validateLevel3Dataset(level3Data, libraryLookup) {
  const issues = [];
  if (level3Data?.meta?.degree !== "level3") {
    issues.push({
      check: "meta_degree",
      detail: "level3.json meta.degree must equal level3.",
    });
  }
  if (!Array.isArray(level3Data?.entries) || level3Data.entries.length !== 3) {
    issues.push({
      check: "entry_count",
      detail: "Level 3 build must contain exactly 3 native anchor entries in this phase.",
    });
  }

  const entrySlugs = new Set((level3Data.entries || []).map((entry) => entry.slug));
  for (const entry of level3Data.entries || []) {
    for (const field of REQUIRED_LEVEL3_FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(entry, field)) {
        issues.push({
          check: "missing_field",
          detail: `Entry ${entry.slug} is missing required field ${field}`,
        });
      }
    }
    if (entry.degree !== "level3") {
      issues.push({
        check: "degree",
        detail: `Entry ${entry.slug} does not declare degree=level3`,
      });
    }
    if (entry.degree_owner !== "level3") {
      issues.push({
        check: "degree_owner",
        detail: `Entry ${entry.slug} does not declare degree_owner=level3`,
      });
    }
    if (JSON.stringify(entry.applies_to_degrees) !== JSON.stringify(["level3"])) {
      issues.push({
        check: "applies_to_degrees",
        detail: `Entry ${entry.slug} must apply only to level3 in this build.`,
      });
    }
    if (entry.product_state !== "built") {
      issues.push({
        check: "product_state",
        detail: `Entry ${entry.slug} must declare product_state=built.`,
      });
    }
    if (entry.boundary_guard_passed !== true) {
      issues.push({
        check: "boundary_guard_passed",
        detail: `Entry ${entry.slug} must declare boundary_guard_passed=true.`,
      });
    }

    for (const target of flattenRelatedTopics(entry.related_topics)) {
      if (!entrySlugs.has(target)) {
        issues.push({
          check: "broken_local_reference",
          detail: `Entry ${entry.slug} references missing local slug ${target}`,
        });
      }
    }

    for (const link of entry.knowledge_links || []) {
      if (link.degree !== "library") {
        issues.push({
          check: "knowledge_link_degree",
          detail: `Entry ${entry.slug} must link only to library anchors in Phase M.10.`,
        });
      } else if (!libraryLookup.has(`${link.degree}:${link.slug}`)) {
        issues.push({
          check: "knowledge_link_missing",
          detail: `Entry ${entry.slug} points to missing library anchor ${link.slug}`,
        });
      }
    }

    const text = gatherEntryText(entry);
    for (const rule of FORBIDDEN_LEVEL3_PATTERNS) {
      if (rule.pattern.test(text)) {
        issues.push({
          check: "forbidden_basis",
          detail: `Entry ${entry.slug} contains forbidden Level 3 basis marker: ${rule.label}`,
        });
      }
    }
  }

  return issues;
}

function validateLevel3Registry(record) {
  const issues = [];
  if (!record || typeof record !== "object") {
    issues.push({
      check: "level3_registry",
      detail: "Level 3 degree registry record was not created.",
    });
    return issues;
  }
  if (record.access_mode !== "password") {
    issues.push({
      check: "level3_access_mode",
      detail: "Level 3 should remain a password-protected lane.",
    });
  }
  if (!record.passwordHash) {
    issues.push({
      check: "level3_password_hash",
      detail: "Level 3 passwordHash is empty; a temporary gate is still required.",
    });
  }
  return issues;
}

function gatherEntryText(entry) {
  return [
    entry.title,
    entry.short_summary,
    entry.full_summary,
    entry.symbolic_meaning,
    entry.candidate_lesson,
  ]
    .filter((value) => typeof value === "string" && value.trim())
    .join(" ");
}

function flattenRelatedTopics(relatedTopics) {
  if (Array.isArray(relatedTopics)) {
    return relatedTopics.filter(Boolean);
  }
  if (!relatedTopics || typeof relatedTopics !== "object") {
    return [];
  }
  return [
    ...(Array.isArray(relatedTopics.prior) ? relatedTopics.prior : []),
    ...(Array.isArray(relatedTopics.companion) ? relatedTopics.companion : []),
    ...(Array.isArray(relatedTopics.deeper) ? relatedTopics.deeper : []),
  ].filter(Boolean);
}

function parseArgs(args) {
  const parsed = {};
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = args[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = next;
    index += 1;
  }
  return parsed;
}

function resolveConfig(options) {
  const siteRoot = resolvePathOption(options["site-root"], DEFAULT_SITE_ROOT);
  const dataRoot = path.join(siteRoot, "data");
  return {
    siteRoot,
    dataRoot,
    libraryPath: resolvePathOption(options.library, path.join(dataRoot, "library.json")),
    degreesPath: resolvePathOption(options.degrees, DEFAULT_DEGREES_PATH),
    level3Path: resolvePathOption(options.level3, DEFAULT_LEVEL3_PATH),
    level3BackupPath: resolvePathOption(options["level3-backup"], DEFAULT_LEVEL3_BACKUP_PATH),
    degreesBackupPath: resolvePathOption(options["degrees-backup"], DEFAULT_DEGREES_BACKUP_PATH),
    seedSpecPath: resolvePathOption(options["seed-spec"], DEFAULT_SEED_SPEC_PATH),
    goldsetPath: resolvePathOption(options.goldset, DEFAULT_GOLDSET_PATH),
    reportPath: resolvePathOption(options.report, DEFAULT_REPORT_PATH),
    validationPath: resolvePathOption(options.validation, DEFAULT_VALIDATION_PATH),
  };
}

function resolvePathOption(value, fallback) {
  const target = value || fallback;
  return path.isAbsolute(target) ? target : path.resolve(ROOT, target);
}

function buildCheck(pass, detail, extra = {}) {
  return {
    pass,
    detail,
    ...extra,
  };
}

function assertFileExists(filePath, label) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath}`);
  }
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function writeJsonAtomic(filePath, payload) {
  ensureParentDir(filePath);
  const tempPath = `${filePath}.tmp-${Date.now()}`;
  fs.writeFileSync(tempPath, stringifyJson(payload), "utf8");
  fs.renameSync(tempPath, filePath);
}

function stringifyJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}
main();
