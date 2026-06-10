const fs = require("fs");
const path = require("path");
const {
  getDatedPublishedSiteRoot,
  getLiveSiteRoot,
  getReleaseIdSlug,
  inferReleaseLine,
} = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m11_finalize_site_release";
const DEFAULT_SOURCE_SITE_ROOT = getLiveSiteRoot({ requireRuntimeAssets: true });
const DEFAULT_RELEASE_ID = inferReleaseLine(DEFAULT_SOURCE_SITE_ROOT);
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_11_finalize_site_release_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_11_finalize_site_release_validation.json");

const ROOT_INCLUDE = [
  "index.html",
  "css",
  "js",
  "data",
  "favicon.svg",
  "og-image.svg",
];

const DATA_INCLUDE = [
  "content.schema.json",
  "degrees.json",
  "level1.json",
  "level2.json",
  "level3.json",
  "library.json",
  "library_manifest.json",
  "improvments.txt",
];

const ROOT_EXCLUDE_HINTS = [
  ".obsidian",
  "output_md",
  "exports",
  "new_content",
  "PRODUCT_CONTRACT_v0.3.0.md",
  "Untitled.base",
];

const DATA_EXCLUDE_HINTS = [
  "README-content.md",
  "entry.template.json",
  "degrees.pre_m10_backup.json",
  "level1.pre_m5_2_backup.json",
  "level2.pre_m5_2_backup.json",
  "level2.pre_m5_3_backup.json",
];

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();

  const report = {
    phase: PHASE_ID,
    goal: "Create a clean runtime-only site release from the current sandbox site.",
    mode: "controlled_clean_release_packaging",
    executed_at: executedAt,
    inputs: {
      source_site_root: config.sourceSiteRoot,
      release_id: config.releaseId,
      release_qualifier: config.releaseQualifier || null,
      target_name_mode: config.targetNameMode,
      target_site_root: config.targetSiteRoot,
    },
    execution_contract: {
      atomic_write: true,
      runtime_only_copy: true,
      preserve_existing_releases: true,
      no_schema_change: true,
    },
    packaging_rules: {
      root_include: ROOT_INCLUDE,
      data_include: DATA_INCLUDE,
      root_exclude_hints: ROOT_EXCLUDE_HINTS,
      data_exclude_hints: DATA_EXCLUDE_HINTS,
    },
    outputs: {
      release_site_root: config.targetSiteRoot,
      manifest: path.join(config.targetSiteRoot, "release_manifest.json"),
      report: config.reportPath,
      validation: config.validationPath,
      expected_smoke_report: config.smokeReportPath,
    },
    actions: [],
    overall_status: "pending",
  };

  const validation = {
    phase: PHASE_ID,
    executed_at: executedAt,
    source_site_root: config.sourceSiteRoot,
    target_site_root: config.targetSiteRoot,
    checks: {},
    failures: [],
    error_count: 0,
    overall_status: "pending",
  };

  try {
    assertDirExists(config.sourceSiteRoot, "Source site root");
    assertDirExists(path.join(config.sourceSiteRoot, "data"), "Source data root");
    assertDirExists(path.join(config.sourceSiteRoot, "js"), "Source js root");
    assertDirExists(path.join(config.sourceSiteRoot, "css"), "Source css root");

    if (fs.existsSync(config.targetSiteRoot)) {
      throw new Error(`Target release root already exists: ${config.targetSiteRoot}`);
    }

    const tempTargetRoot = `${config.targetSiteRoot}.tmp-${Date.now()}`;
    if (fs.existsSync(tempTargetRoot)) {
      throw new Error(`Temporary target already exists: ${tempTargetRoot}`);
    }

    fs.mkdirSync(tempTargetRoot, { recursive: true });
    copyRuntimeRoot(config.sourceSiteRoot, tempTargetRoot, report);
    copyRuntimeData(config.sourceSiteRoot, tempTargetRoot, report);

    const manifest = buildManifest(config, executedAt);
    fs.writeFileSync(path.join(tempTargetRoot, "release_manifest.json"), stringifyJson(manifest), "utf8");
    report.actions.push({
      type: "write_release_manifest",
      target: path.join(config.targetSiteRoot, "release_manifest.json"),
    });

    validation.checks.runtime_root_only = buildCheck(
      hasOnlyExpectedEntries(tempTargetRoot, [...ROOT_INCLUDE, "release_manifest.json"]),
      hasOnlyExpectedEntries(tempTargetRoot, [...ROOT_INCLUDE, "release_manifest.json"])
        ? "Release root contains only runtime assets and manifest."
        : "Release root still contains extra working files.",
      {
        actual_root_entries: fs.readdirSync(tempTargetRoot).sort(),
      }
    );

    validation.checks.runtime_data_only = buildCheck(
      hasOnlyExpectedEntries(path.join(tempTargetRoot, "data"), getExpectedDataEntries(config.sourceSiteRoot)),
      hasOnlyExpectedEntries(path.join(tempTargetRoot, "data"), getExpectedDataEntries(config.sourceSiteRoot))
        ? "Release data root contains only runtime data files."
        : "Release data root still contains extra backup or authoring files.",
      {
        actual_data_entries: fs.readdirSync(path.join(tempTargetRoot, "data")).sort(),
      }
    );

    const parseIssues = collectJsonParseIssues(tempTargetRoot);
    validation.checks.json_parse_valid = buildCheck(
      parseIssues.length === 0,
      parseIssues.length === 0
        ? "All shipped JSON files parse correctly."
        : "Some shipped JSON files failed to parse.",
      { issues: parseIssues }
    );

    const parity = compareRuntimeData(config.sourceSiteRoot, tempTargetRoot);
    validation.checks.runtime_data_matches_source = buildCheck(
      parity.pass,
      parity.pass
        ? "Release runtime data matches the sandbox source for all shipped data files."
        : "Release runtime data differs from the sandbox source.",
      parity
    );

    const excludedIssues = collectExcludedArtifacts(tempTargetRoot);
    validation.checks.no_excluded_artifacts_shipped = buildCheck(
      excludedIssues.length === 0,
      excludedIssues.length === 0
        ? "No excluded working artifacts were shipped."
        : "Excluded working artifacts are still present in the release.",
      { issues: excludedIssues }
    );

    const failures = Object.entries(validation.checks)
      .filter(([, value]) => !value.pass)
      .map(([name, value]) => ({ check: name, detail: value.detail }));

    validation.failures = failures;
    validation.error_count = failures.length;
    validation.overall_status = failures.length === 0 ? "pass" : "fail";

    if (validation.overall_status !== "pass") {
      throw new Error("Phase M.11 validation failed. Temporary release was left in place for inspection.");
    }

    fs.renameSync(tempTargetRoot, config.targetSiteRoot);
    report.actions.push({
      type: "clean_release_created",
      target: config.targetSiteRoot,
    });
    report.overall_status = "pass";
    report.success_criteria = {
      clean_runtime_release_created: true,
      validation_pass: true,
      overall_status: "pass",
    };

    writeOutputs(config, report, validation);

    console.log(`Clean release created: ${config.targetSiteRoot}`);
    console.log(`Finalize report: ${config.reportPath}`);
    console.log(`Finalize validation: ${config.validationPath}`);
  } catch (error) {
    report.overall_status = "fail";
    report.error = error.message;
    validation.overall_status = "fail";
    if (validation.error_count === 0) {
      validation.failures = [{ check: "execution", detail: error.message }];
      validation.error_count = 1;
    }
    writeOutputs(config, report, validation);
    console.error(error.message);
    process.exitCode = 1;
  }
}

function buildManifest(config, executedAt) {
  const counts = readRuntimeCounts(config.sourceSiteRoot);
  return {
    release_id: config.releaseId,
    published_snapshot_name: path.basename(config.targetSiteRoot),
    released_at: getLocalDateString(),
    scope: counts.level3 > 0 ? "full_level3_clean_release" : "broad_clean_release",
    included_lanes: [
      "level1",
      "level2",
      ...(counts.level3 > 0 ? ["level3"] : []),
      "library",
    ],
    deferred_lanes: ["royal_arch"],
    entry_counts: counts,
    packaging: {
      source_site_root: path.relative(ROOT, config.sourceSiteRoot).replace(/\\/g, "/"),
      runtime_only_copy: true,
      excluded_root_artifacts: ROOT_EXCLUDE_HINTS,
      excluded_data_artifacts: DATA_EXCLUDE_HINTS,
    },
    validation: {
      finalize_report: path.relative(ROOT, config.reportPath).replace(/\\/g, "/"),
      finalize_validation: path.relative(ROOT, config.validationPath).replace(/\\/g, "/"),
      expected_smoke_report: path.relative(ROOT, config.smokeReportPath).replace(/\\/g, "/"),
    },
    notes: [
      "This release strips authoring clutter, backup files, and working directories from the published package.",
      "Runtime data remains identical to the sandbox source for the shipped files.",
    ],
  };
}

function readRuntimeCounts(siteRoot) {
  const dataRoot = path.join(siteRoot, "data");
  const counts = {};
  for (const name of ["level1", "level2", "level3", "library"]) {
    const filePath = path.join(dataRoot, `${name}.json`);
    if (!fs.existsSync(filePath)) continue;
    const payload = readJsonFile(filePath);
    counts[name] = Array.isArray(payload.entries) ? payload.entries.length : 0;
  }
  return counts;
}

function copyRuntimeRoot(sourceRoot, targetRoot, report) {
  for (const name of ROOT_INCLUDE) {
    if (name === "data") continue;
    const sourcePath = path.join(sourceRoot, name);
    if (!fs.existsSync(sourcePath)) continue;
    const targetPath = path.join(targetRoot, name);
    fs.cpSync(sourcePath, targetPath, {
      recursive: true,
      force: false,
      errorOnExist: true,
    });
    report.actions.push({
      type: "copy_runtime_root_entry",
      name,
      from: sourcePath,
      to: targetPath,
    });
  }
}

function copyRuntimeData(sourceRoot, targetRoot, report) {
  const sourceDataRoot = path.join(sourceRoot, "data");
  const targetDataRoot = path.join(targetRoot, "data");
  fs.mkdirSync(targetDataRoot, { recursive: true });

  for (const name of getExpectedDataEntries(sourceRoot)) {
    const sourcePath = path.join(sourceDataRoot, name);
    if (!fs.existsSync(sourcePath)) continue;
    const targetPath = path.join(targetDataRoot, name);
    fs.copyFileSync(sourcePath, targetPath);
    report.actions.push({
      type: "copy_runtime_data_file",
      name,
      from: sourcePath,
      to: targetPath,
    });
  }
}

function compareRuntimeData(sourceRoot, targetRoot) {
  const comparisons = {};
  let diffCount = 0;

  for (const name of getExpectedDataEntries(sourceRoot)) {
    const sourcePath = path.join(sourceRoot, "data", name);
    const targetPath = path.join(targetRoot, "data", name);
    const sourceRaw = fs.readFileSync(sourcePath, "utf8");
    const targetRaw = fs.readFileSync(targetPath, "utf8");
    const matches = sourceRaw === targetRaw;
    comparisons[name] = { matches };
    if (!matches) diffCount += 1;
  }

  return {
    pass: diffCount === 0,
    files: comparisons,
  };
}

function collectJsonParseIssues(siteRoot) {
  const issues = [];
  const dataRoot = path.join(siteRoot, "data");
  for (const name of fs.readdirSync(dataRoot)) {
    if (!name.endsWith(".json")) continue;
    const filePath = path.join(dataRoot, name);
    try {
      readJsonFile(filePath);
    } catch (error) {
      issues.push({
        file: filePath,
        error: error.message,
      });
    }
  }

  const manifestPath = path.join(siteRoot, "release_manifest.json");
  try {
    readJsonFile(manifestPath);
  } catch (error) {
    issues.push({
      file: manifestPath,
      error: error.message,
    });
  }

  return issues;
}

function collectExcludedArtifacts(siteRoot) {
  const issues = [];
  for (const name of ROOT_EXCLUDE_HINTS) {
    if (fs.existsSync(path.join(siteRoot, name))) {
      issues.push({ kind: "root", name });
    }
  }
  for (const name of DATA_EXCLUDE_HINTS) {
    if (fs.existsSync(path.join(siteRoot, "data", name))) {
      issues.push({ kind: "data", name });
    }
  }
  for (const name of fs.readdirSync(path.join(siteRoot, "data"))) {
    if (/\.pre_.*\.json$/i.test(name)) {
      issues.push({ kind: "data", name });
    }
  }
  return issues;
}

function getExpectedDataEntries(sourceRoot) {
  return DATA_INCLUDE.filter((name) => fs.existsSync(path.join(sourceRoot, "data", name)));
}

function hasOnlyExpectedEntries(dirPath, expectedNames) {
  const actual = fs.readdirSync(dirPath).sort();
  const expected = [...expectedNames].sort();
  return JSON.stringify(actual) === JSON.stringify(expected);
}

function writeOutputs(config, report, validation) {
  ensureParentDir(config.reportPath);
  ensureParentDir(config.validationPath);
  fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
  fs.writeFileSync(config.validationPath, stringifyJson(validation), "utf8");
}

function buildCheck(pass, detail, extra = {}) {
  return {
    pass,
    detail,
    ...extra,
  };
}

function readJsonFile(filePath) {
  const raw = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
  return JSON.parse(raw);
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
  const sourceSiteRoot = resolvePathOption(options["source-site-root"], DEFAULT_SOURCE_SITE_ROOT);
  const explicitTargetSiteRoot = typeof options["target-site-root"] === "string" && options["target-site-root"].trim()
    ? resolvePathOption(options["target-site-root"], options["target-site-root"])
    : "";
  const targetNameMode = explicitTargetSiteRoot ? "explicit-target-site-root" : "contract-derived";
  const releaseIdSeed = explicitTargetSiteRoot || sourceSiteRoot;
  const releaseId = resolveReleaseIdOption(options["release-id"], releaseIdSeed);
  const releaseQualifier = resolveReleaseQualifier(options["release-qualifier"], "");
  const targetSiteRoot = explicitTargetSiteRoot || getDatedPublishedSiteRoot({
    releaseId,
    sourceSiteRoot,
    qualifier: releaseQualifier,
  });
  const defaultSmokeReportPath = path.join(
    ROOT,
    "PDF_handle",
    "TOOLS",
    "data",
    `phase_m_7_full_system_smoke_report_${getReleaseIdSlug({ releaseId, sourceSiteRoot })}.json`
  );

  return {
    sourceSiteRoot,
    releaseId,
    releaseQualifier,
    targetNameMode,
    targetSiteRoot: resolvePathOption(options["target-site-root"], targetSiteRoot),
    reportPath: resolvePathOption(options.report, DEFAULT_REPORT_PATH),
    validationPath: resolvePathOption(options.validation, DEFAULT_VALIDATION_PATH),
    smokeReportPath: resolvePathOption(options["smoke-report"], defaultSmokeReportPath),
  };
}

function resolveReleaseIdOption(value, fallbackSource) {
  const explicit = typeof value === "string" ? value.trim() : "";
  if (explicit) {
    const match = explicit.match(/^v?(\d+\.\d+(?:\.\d+)?)/i);
    return match ? match[1] : explicit.replace(/^v/i, "");
  }

  return inferReleaseLine(fallbackSource);
}

function resolveReleaseQualifier(value, fallback) {
  const chosen = typeof value === "string" && value.trim() ? value.trim() : fallback;
  return String(chosen || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9.-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function resolvePathOption(value, fallback) {
  const target = value || fallback;
  return path.isAbsolute(target) ? target : path.resolve(ROOT, target);
}

function assertDirExists(dirPath, label) {
  if (!fs.existsSync(dirPath) || !fs.statSync(dirPath).isDirectory()) {
    throw new Error(`${label} not found: ${dirPath}`);
  }
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function stringifyJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

function getLocalDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

main();
