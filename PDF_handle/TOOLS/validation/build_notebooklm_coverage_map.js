/**
 * build_notebooklm_coverage_map.js
 *
 * Reads notebooklm_subjects.md and compares each subject against all existing
 * entries in level1, level2, and level3 JSON files. Outputs a coverage map
 * showing which subjects are covered, partially covered, or not covered.
 *
 * Usage:
 *   node PDF_handle/TOOLS/build_notebooklm_coverage_map.js
 */

const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot, resolveWorkspacePath } = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const SUBJECTS_PATH = path.join(ROOT, "experiments", "notebooklm_validation", "notebooklm_subjects.md");
const SANDBOX_DATA = path.join(getWorkSiteRoot(), "data");
const OUTPUT_JSON = path.join(ROOT, "PDF_handle", "TOOLS", "data", "notebooklm_coverage_map.json");
const OUTPUT_MD = path.join(ROOT, "PDF_handle", "TOOLS", "data", "notebooklm_coverage_map.md");

function loadJson(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = next;
    index += 1;
  }
  return parsed;
}

function resolvePath(value, fallback) {
  if (typeof value === "string" && value.trim()) {
    return resolveWorkspacePath(value.trim());
  }
  return fallback;
}

function resolveConfig(options) {
  return {
    subjectsPath: resolvePath(options.subjects, SUBJECTS_PATH),
    dataRoot: resolvePath(options["data-root"], SANDBOX_DATA),
    outputJson: resolvePath(options.json, OUTPUT_JSON),
    outputMd: resolvePath(options.md, OUTPUT_MD),
  };
}

function parseSubjects(text) {
  const lines = text.split("\n");
  let currentDegree = null;
  let currentBlock = 0;
  const subjects = [];
  const seen = new Set();

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (/הדרגה הראשונה/.test(trimmed)) {
      currentDegree = "level1";
      if (subjects.length > 0 && subjects[subjects.length - 1].degree === "level1") currentBlock++;
      continue;
    }
    if (/הדרגה השנייה/.test(trimmed)) {
      currentDegree = "level2";
      continue;
    }
    if (/הדרגה השלישית/.test(trimmed)) {
      currentDegree = "level3";
      continue;
    }

    if (trimmed === "." || /^זה מושלם/.test(trimmed)) continue;

    // Extract subject: "Hebrew name (English name) - description"
    const match = trimmed.match(/^(.+?)\s*(?:\(([^)]+)\))?\s*[-–—]\s*(.+)$/);
    if (!match) continue;

    const hebrewName = match[1].trim();
    const englishName = (match[2] || "").trim();
    const description = match[3].replace(/\.$/, "").trim();

    // Dedup key
    const key = `${currentDegree}:${hebrewName}`;
    if (seen.has(key)) continue;
    seen.add(key);

    subjects.push({
      hebrew_name: hebrewName,
      english_name: englishName,
      description,
      degree: currentDegree,
    });
  }

  return subjects;
}

function buildSearchIndex(entries, degree) {
  return entries.map((entry) => {
    const searchable = [
      entry.title || "",
      entry.slug || "",
      ...(entry.aliases || []),
      ...(entry.keywords || []),
      entry.short_summary || "",
      ...(entry.source_anchor || []),
    ]
      .join(" ")
      .toLowerCase();

    return { slug: entry.slug, title: entry.title, degree, searchable };
  });
}

function normalize(str) {
  return str
    .toLowerCase()
    .replace(/[\u0591-\u05C7]/g, "") // remove Hebrew diacritics
    .replace(/[-–—_]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function scoreCoverage(subject, searchIndex) {
  const heNorm = normalize(subject.hebrew_name);
  const enNorm = normalize(subject.english_name);
  const descNorm = normalize(subject.description);

  // Extract key terms (Hebrew words > 2 chars, English words > 3 chars)
  const heTerms = heNorm.split(" ").filter((w) => w.length > 2);
  const enTerms = enNorm.split(" ").filter((w) => w.length > 3);
  const descTerms = descNorm
    .split(" ")
    .filter((w) => w.length > 2)
    .slice(0, 6);

  let bestMatch = null;
  let bestScore = 0;

  for (const indexed of searchIndex) {
    const norm = normalize(indexed.searchable);
    let score = 0;

    // Hebrew name exact match in searchable
    if (norm.includes(heNorm)) score += 10;

    // English name match
    if (enNorm && norm.includes(enNorm)) score += 8;

    // Hebrew term matches
    for (const term of heTerms) {
      if (norm.includes(term)) score += 3;
    }

    // English term matches
    for (const term of enTerms) {
      if (norm.includes(term)) score += 2;
    }

    // Description term matches (weaker signal)
    for (const term of descTerms) {
      if (norm.includes(term)) score += 1;
    }

    if (score > bestScore) {
      bestScore = score;
      bestMatch = { slug: indexed.slug, title: indexed.title, degree: indexed.degree };
    }
  }

  return { bestMatch, bestScore };
}

function classifyCoverage(score) {
  if (score >= 12) return "covered";
  if (score >= 6) return "partially_covered";
  return "not_covered";
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const subjectsText = fs.readFileSync(config.subjectsPath, "utf8");
  const subjects = parseSubjects(subjectsText);

  // Load all datasets
  const level1 = loadJson(path.join(config.dataRoot, "level1.json"));
  const level2 = loadJson(path.join(config.dataRoot, "level2.json"));
  const level3 = loadJson(path.join(config.dataRoot, "level3.json"));

  // Build search index from all levels
  const searchIndex = [
    ...buildSearchIndex(level1?.entries || [], "level1"),
    ...buildSearchIndex(level2?.entries || [], "level2"),
    ...buildSearchIndex(level3?.entries || [], "level3"),
  ];

  // Score each subject
  const results = subjects.map((subject) => {
    const { bestMatch, bestScore } = scoreCoverage(subject, searchIndex);
    const status = classifyCoverage(bestScore);
    return {
      ...subject,
      status,
      score: bestScore,
      best_match: bestMatch,
    };
  });

  // Summary stats
  const byDegree = {};
  const byStatus = { covered: 0, partially_covered: 0, not_covered: 0 };

  for (const r of results) {
    if (!byDegree[r.degree]) byDegree[r.degree] = { covered: 0, partially_covered: 0, not_covered: 0, total: 0 };
    byDegree[r.degree][r.status]++;
    byDegree[r.degree].total++;
    byStatus[r.status]++;
  }

  const output = {
    phase: "notebooklm_coverage_map",
    generated_at: new Date().toISOString(),
    inputs: {
      subjects_path: config.subjectsPath,
      sandbox_data: config.dataRoot,
    },
    summary: {
      total_unique_subjects: results.length,
      ...byStatus,
      coverage_pct: Math.round(((byStatus.covered + byStatus.partially_covered) / results.length) * 100),
      by_degree: byDegree,
    },
    subjects: results,
  };

  fs.mkdirSync(path.dirname(config.outputJson), { recursive: true });
  fs.writeFileSync(config.outputJson, JSON.stringify(output, null, 2) + "\n", "utf8");

  // Generate markdown summary
  const md = [];
  md.push("# NotebookLM Coverage Map");
  md.push(`\nGenerated: ${output.generated_at}`);
  md.push(`\n## Summary`);
  md.push(`- Total unique subjects: ${output.summary.total_unique_subjects}`);
  md.push(`- Covered: ${byStatus.covered}`);
  md.push(`- Partially covered: ${byStatus.partially_covered}`);
  md.push(`- Not covered: ${byStatus.not_covered}`);
  md.push(`- Coverage: ${output.summary.coverage_pct}%`);

  for (const [deg, stats] of Object.entries(byDegree)) {
    md.push(`\n### ${deg}`);
    md.push(`- Total: ${stats.total} | Covered: ${stats.covered} | Partial: ${stats.partially_covered} | Not covered: ${stats.not_covered}`);
  }

  md.push(`\n## Not Covered Subjects\n`);
  const notCovered = results.filter((r) => r.status === "not_covered");
  for (const r of notCovered) {
    md.push(`- **${r.hebrew_name}** (${r.degree}) — ${r.english_name || "N/A"}`);
  }

  md.push(`\n## Partially Covered Subjects\n`);
  const partial = results.filter((r) => r.status === "partially_covered");
  for (const r of partial) {
    md.push(`- **${r.hebrew_name}** (${r.degree}) → ${r.best_match?.slug || "?"} (score: ${r.score})`);
  }

  fs.writeFileSync(config.outputMd, md.join("\n") + "\n", "utf8");

  console.log(`Subjects: ${results.length}`);
  console.log(`Covered: ${byStatus.covered} | Partial: ${byStatus.partially_covered} | Not covered: ${byStatus.not_covered}`);
  console.log(`Coverage: ${output.summary.coverage_pct}%`);
  console.log(`JSON: ${config.outputJson}`);
  console.log(`MD: ${config.outputMd}`);
}

main();
