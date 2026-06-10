const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const TODAY = new Date().toISOString().slice(0, 10);
const PHASE_ID = "phase_m12_post_refill_cleanup";
const TARGET_LEVEL2_SLUG = "level2-discipline-work-and-rough-ashlar-system";
const DEFAULT_SITE_ROOT = path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00");
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_12_post_refill_cleanup_report.json");

const SANITIZED_ENTRY_FIELDS = {
  full_summary:
    "הערך נשען על המשמעות המשולבת של כלי התלמיד, משמעת טקסית מול משמעת פנימית ומהי העבודה בדרגה הראשונה כדי להציג את העבודה הפנימית כמערכת אחת ולא כסדרה של מסרים נפרדים. הציר הראשון הוא משמעת חיצונית מול פנימית: הסדר הטקסי נותן מסגרת, אך רק קליטה פנימית הופכת אותו להרגל יציב. הציר השני הוא עבודה כמאמץ מול עבודה כצורה: לא די ברצון טוב, אלא צריך מבנה שיחזיק את המאמץ לאורך זמן. הציר השלישי הוא חומר גלם מול אפשרות עיבוד: אבן הגוויל מזכירה שהאדם מתחיל כחומר פתוח, לא כצורה גמורה. כך מתברר שמשמעת, עבודה ואבן הגוויל אינן שלוש שפות שונות אלא מערכת אחת, מכלול אחד של התהוות פנימית.\n\nההתקדמות בדרגה השנייה נקראת כאן כהתקדמות מדורגת מאבן גסה אל צורה מעובדת יותר. העבודה איננה רק תנופה של מאמץ, אלא תרגול עקבי שנשמר בתוך מסגרת. המשמעת איננה תחליף לעבודה, אלא התנאי שמאפשר לה להישאר מדודה; ואבן הגוויל איננה רק נקודת פתיחה, אלא תזכורת לכך שכל בניין מתחיל מחומר שדורש עיבוד. לכן הקריאה של דרגה 2 מדגישה יחס יציב בין סדר, מלאכה וחומר גלם, ומתמקדת בעבודה ניתנת לתרגול ובהתקדמות מדורגת.",
  practical_elements: [
    "לקרוא מצב של קושי דרך שלושת הצירים: משמעת, עבודה וחומר גלם.",
    "לבחון היכן נדרש יותר סדר, היכן נדרש יותר עמל, והיכן חומר הגלם עדיין לא עובד.",
    "לקשור בין מאמץ חוזר, מדידה ושיפור עקבי במקום לצפות לשינוי מיידי."
  ],
  symbolic_meaning:
    "המשמעות הסמלית כאן נוצרת מן הקשר בין מסגרת, מלאכה וחומר. אבן הגוויל מסמלת אפשרות לא מעובדת, המשמעת שומרת על גבול ועל קצב, והעבודה הופכת את האפשרות לצורה. המעבר מאבן גסה למסותתת מדגיש שהשינוי נבנה דרך עיבוד חוזר, לא דרך קפיצה אחת. לכן הסמל איננו רק האדם בתחילתו, אלא המערכת שמלמדת כיצד התחלה נעשית בניין.",
  candidate_lesson:
    "הלקח של דרגה 2 הוא שלא די לדבר על תיקון; צריך להבין את המערכת שמאפשרת אותו. כאשר המשמעת נשארת רק בחוץ, העבודה נחלשת, וכאשר העבודה נשארת ללא צורה, חומר הגלם נשאר כפי שהיה. לימוד בוגר יותר מתחיל כאשר שלושת החלקים פועלים יחד, כך שההתקדמות נעשית עקבית, מדודה ויציבה.",
  tradition_notes: [
    "הערך נשען על המשמעות המשולבת של כלי התלמיד, משמעת טקסית מול משמעת פנימית, מהי העבודה בדרגה הראשונה ואבן גוויל (Rough Ashlar) מן הדרגה הראשונה, וקורא אותם יחד כמבנה של דרגה שנייה.",
    "המעבר מאבן גסה לאבן מעובדת נקרא כאן כסימון של התקדמות מדורגת בעבודה ובהרגל.",
    "הדגש נשאר על קריאה מבנית של עבודה, מסגרת וחומר גלם בתוך גבול הדרגה."
  ]
};

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();

  const report = {
    phase: PHASE_ID,
    executed_at: executedAt,
    site_root: config.siteRoot,
    target_level2_slug: TARGET_LEVEL2_SLUG,
    outputs: {
      backup_level2: config.level2BackupPath,
      backup_library: config.libraryBackupPath,
      report: config.reportPath
    },
    changes: {
      level2_entry_sanitized: false,
      hidden_library_links_removed: 0,
      touched_library_entries: 0
    },
    hidden_link_cleanup: {
      hidden_degree_targets: {},
      removed_links: []
    },
    overall_status: "pending"
  };

  try {
    const level2Raw = fs.readFileSync(config.level2Path, "utf8");
    const libraryRaw = fs.readFileSync(config.libraryPath, "utf8");
    const level1Data = JSON.parse(fs.readFileSync(config.level1Path, "utf8"));
    const level2Data = JSON.parse(level2Raw);
    const libraryData = JSON.parse(libraryRaw);
    const level3Data = fs.existsSync(config.level3Path)
      ? JSON.parse(fs.readFileSync(config.level3Path, "utf8"))
      : null;

    const level2Next = clone(level2Data);
    const libraryNext = clone(libraryData);

    const targetEntry = level2Next.entries.find((entry) => entry.slug === TARGET_LEVEL2_SLUG);
    if (!targetEntry) {
      throw new Error(`Target Level 2 entry not found: ${TARGET_LEVEL2_SLUG}`);
    }

    Object.assign(targetEntry, clone(SANITIZED_ENTRY_FIELDS));
    level2Next.meta = {
      ...level2Next.meta,
      updated_at: TODAY
    };
    report.changes.level2_entry_sanitized = true;

    const hiddenTargets = buildHiddenTargets({
      level1: level1Data,
      level2: level2Data,
      level3: level3Data
    });

    report.hidden_link_cleanup.hidden_degree_targets = Object.fromEntries(
      Object.entries(hiddenTargets).map(([degree, slugs]) => [degree, Array.from(slugs).sort()])
    );

    const removedLinks = [];
    let touchedEntries = 0;

    for (const entry of libraryNext.entries) {
      if (!Array.isArray(entry.knowledge_links) || entry.knowledge_links.length === 0) {
        continue;
      }

      const nextLinks = [];
      let removedForEntry = 0;

      for (const link of entry.knowledge_links) {
        const hiddenSet = hiddenTargets[link.degree];
        if (hiddenSet && hiddenSet.has(link.slug)) {
          removedLinks.push({
            entry_slug: entry.slug,
            entry_title: entry.title,
            target_degree: link.degree,
            target_slug: link.slug
          });
          removedForEntry += 1;
          continue;
        }
        nextLinks.push(link);
      }

      if (removedForEntry > 0) {
        entry.knowledge_links = nextLinks;
        touchedEntries += 1;
      }
    }

    libraryNext.meta = {
      ...libraryNext.meta,
      updated_at: TODAY
    };

    report.changes.hidden_library_links_removed = removedLinks.length;
    report.changes.touched_library_entries = touchedEntries;
    report.hidden_link_cleanup.removed_links = removedLinks;

    ensureParentDir(config.level2BackupPath);
    ensureParentDir(config.libraryBackupPath);
    ensureParentDir(config.reportPath);

    fs.copyFileSync(config.level2Path, config.level2BackupPath);
    fs.copyFileSync(config.libraryPath, config.libraryBackupPath);

    atomicWriteJson(config.level2Path, level2Next, detectEol(level2Raw));
    atomicWriteJson(config.libraryPath, libraryNext, detectEol(libraryRaw));

    report.overall_status = "pass";
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");

    console.log(`Phase M.12 cleanup applied: ${config.siteRoot}`);
    console.log(`Level 2 backup: ${config.level2BackupPath}`);
    console.log(`Library backup: ${config.libraryBackupPath}`);
    console.log(`Hidden library links removed: ${removedLinks.length}`);
    console.log(`Cleanup report: ${config.reportPath}`);
  } catch (error) {
    report.overall_status = "fail";
    report.error = error.message;
    ensureParentDir(config.reportPath);
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
    console.error(error.message);
    process.exitCode = 1;
  }
}

function buildHiddenTargets(datasets) {
  const result = {};
  for (const [degree, data] of Object.entries(datasets)) {
    if (!data || !Array.isArray(data.entries)) {
      continue;
    }

    const hidden = new Set();
    for (const entry of data.entries) {
      const review = entry.review_controls || {};
      const isHidden =
        entry.visibility_level === "editorial" ||
        review.exclude_from_navigation === true ||
        review.exclude_from_related_topics === true ||
        (typeof review.decision_status === "string" && review.decision_status.includes("rejected"));
      if (isHidden) {
        hidden.add(entry.slug);
      }
    }

    if (hidden.size > 0) {
      result[degree] = hidden;
    }
  }
  return result;
}

function resolveConfig(options) {
  const siteRoot = resolvePathOption(options["site-root"], DEFAULT_SITE_ROOT);
  const dataRoot = path.join(siteRoot, "data");
  return {
    siteRoot,
    level1Path: path.join(dataRoot, "level1.json"),
    level2Path: path.join(dataRoot, "level2.json"),
    level3Path: path.join(dataRoot, "level3.json"),
    libraryPath: path.join(dataRoot, "library.json"),
    level2BackupPath: path.join(dataRoot, "level2.pre_m12_post_refill_cleanup.json"),
    libraryBackupPath: path.join(dataRoot, "library.pre_m12_post_refill_cleanup.json"),
    reportPath: resolvePathOption(options.report, DEFAULT_REPORT_PATH)
  };
}

function resolvePathOption(value, fallback) {
  if (typeof value === "string" && value.trim()) {
    return path.resolve(ROOT, value.trim());
  }
  return fallback;
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
      continue;
    }
    options[key] = next;
    index += 1;
  }
  return options;
}

function atomicWriteJson(targetPath, data, eol) {
  const tempPath = `${targetPath}.tmp-${Date.now()}`;
  fs.writeFileSync(tempPath, stringifyJson(data, eol), "utf8");
  fs.renameSync(tempPath, targetPath);
}

function stringifyJson(value, eol = "\n") {
  return `${JSON.stringify(value, null, 2).replace(/\n/g, eol)}${eol}`;
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function detectEol(text) {
  return text.includes("\r\n") ? "\r\n" : "\n";
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

main();
