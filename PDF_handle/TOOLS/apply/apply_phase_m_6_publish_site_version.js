const fs = require("fs");
const path = require("path");
const {
  getDatedPublishedSiteRoot,
  getLiveSiteRoot,
  getPublishedSitesRoot,
  getWorkSiteRoot,
  inferReleaseLine,
} = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m6_publish_site_version";
const DEFAULT_SANDBOX_SITE_ROOT = getWorkSiteRoot({ requireRuntimeAssets: true });
const DEFAULT_CURRENT_PUBLISHED_ROOT = getLiveSiteRoot({ requireRuntimeAssets: true });
const DEFAULT_RELEASE_ID = inferReleaseLine(DEFAULT_SANDBOX_SITE_ROOT);
const DEFAULT_RELEASE_QUALIFIER = "m6";
const DEFAULT_REPORT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_6_published_promotion_report.json");
const DEFAULT_VALIDATION_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_6_published_validation.json");
const REQUIRED_DATASET_FILES = ["level1.json", "level2.json", "library.json"];
const OPTIONAL_DATASET_FILES = ["level3.json"];

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();

  const report = {
    phase: PHASE_ID,
    goal: "Promote the current sandbox site into a new published site version with full parity validation.",
    mode: "controlled_site_version_promotion",
    executed_at: executedAt,
    inputs: {
      sandbox_site_root: config.sandboxSiteRoot,
      current_published_root: config.currentPublishedRoot,
      release_id: config.releaseId,
      release_qualifier: config.releaseQualifier || null,
      target_name_mode: config.targetNameMode,
      target_site_root: config.targetSiteRoot,
    },
    execution_contract: {
      atomic_write: true,
      backup_required: false,
      no_generation_inside_site: true,
      no_schema_change: true,
      full_site_copy: true,
      preserve_existing_published_root: true,
    },
    outputs: {
      new_published_site_root: config.targetSiteRoot,
      report: config.reportPath,
      validation: config.validationPath,
    },
    actions: [],
    overall_status: "pending",
  };

  const validation = {
    phase: PHASE_ID,
    executed_at: executedAt,
    source_site_root: config.sandboxSiteRoot,
    target_site_root: config.targetSiteRoot,
    checks: {},
    failures: [],
    error_count: 0,
    overall_status: "pending",
  };

  try {
    assertDirExists(config.sandboxSiteRoot, "Sandbox site root");
    assertDirExists(path.join(config.sandboxSiteRoot, "data"), "Sandbox data root");
    assertDirExists(path.join(config.sandboxSiteRoot, "js"), "Sandbox js root");

    if (fs.existsSync(config.targetSiteRoot)) {
      throw new Error(`Target published site root already exists: ${config.targetSiteRoot}`);
    }

    const tempTargetRoot = `${config.targetSiteRoot}.tmp-${Date.now()}`;
    if (fs.existsSync(tempTargetRoot)) {
      throw new Error(`Temporary target already exists: ${tempTargetRoot}`);
    }

    report.actions.push({
      type: "copy_site_root",
      from: config.sandboxSiteRoot,
      to: config.targetSiteRoot,
      method: "copy_to_temp_then_rename",
    });

    fs.cpSync(config.sandboxSiteRoot, tempTargetRoot, {
      recursive: true,
      force: false,
      errorOnExist: true,
    });

    const sourceRoot = loadSiteRoot(config.sandboxSiteRoot);
    const targetRoot = loadSiteRoot(tempTargetRoot);

    validation.checks.json_parse_valid = buildCheck(
      true,
      "Sandbox and promoted site JSON files parse correctly."
    );

    validation.checks.full_site_structure_present = buildCheck(
      hasExpectedSiteStructure(tempTargetRoot),
      hasExpectedSiteStructure(tempTargetRoot)
        ? "Target site root contains the expected site structure."
        : "Target site root is missing required top-level site structure.",
      {
        top_level_entries: fs.readdirSync(tempTargetRoot).sort(),
      }
    );

    const parity = compareSiteData(sourceRoot, targetRoot);
    validation.checks.published_matches_sandbox = buildCheck(
      parity.pass,
      parity.pass
        ? "Promoted site data matches sandbox data exactly."
        : "Promoted site data does not match sandbox data.",
      parity
    );

    const brokenRelatedTopics = collectBrokenRelatedTopics(targetRoot);
    validation.checks.no_broken_related_topics = buildCheck(
      brokenRelatedTopics.length === 0,
      brokenRelatedTopics.length === 0
        ? "No broken related_topics references detected in promoted site."
        : "Broken related_topics references detected in promoted site.",
      {
        issues: brokenRelatedTopics,
      }
    );

    const brokenKnowledgeLinks = collectBrokenKnowledgeLinks(targetRoot);
    validation.checks.no_broken_knowledge_links = buildCheck(
      brokenKnowledgeLinks.length === 0,
      brokenKnowledgeLinks.length === 0
        ? "No broken knowledge_links detected in promoted site."
        : "Broken knowledge_links detected in promoted site.",
      {
        issues: brokenKnowledgeLinks,
      }
    );

    const level2BoundaryIssues = collectDegreeLaneIntegrityIssues(targetRoot);
    validation.checks.boundary_guard_integrity = buildCheck(
      level2BoundaryIssues.length === 0,
      level2BoundaryIssues.length === 0
        ? "All degree-lane entries keep boundary_guard_passed and degree metadata intact."
        : "Boundary integrity issues detected in promoted degree-lane data.",
      {
        issues: level2BoundaryIssues,
      }
    );

    const runtimeVisibilityIssues = collectRuntimeVisibilityIssues(targetRoot);
    validation.checks.frozen_entries_not_exposed = buildCheck(
      runtimeVisibilityIssues.length === 0,
      runtimeVisibilityIssues.length === 0
        ? "Editorial and superseded entries remain hidden in promoted runtime."
        : "Promoted runtime still exposes editorial or superseded entries.",
      {
        issues: runtimeVisibilityIssues,
      }
    );

    const failures = Object.entries(validation.checks)
      .filter(([, value]) => !value.pass)
      .map(([name, value]) => ({
        check: name,
        detail: value.detail,
      }));

    validation.failures = failures;
    validation.error_count = failures.length;
    validation.overall_status = failures.length === 0 ? "pass" : "fail";

    if (validation.overall_status !== "pass") {
      throw new Error("Phase M.6 validation failed. Temporary published site copy was left in place for inspection.");
    }

    fs.renameSync(tempTargetRoot, config.targetSiteRoot);

    report.actions.push({
      type: "publish_site_version_created",
      target: config.targetSiteRoot,
    });

    report.success_criteria = {
      published_matches_sandbox: true,
      validation_pass: true,
      overall_status: "pass",
    };
    report.overall_status = "pass";

    ensureParentDir(config.reportPath);
    ensureParentDir(config.validationPath);
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
    fs.writeFileSync(config.validationPath, stringifyJson(validation), "utf8");

    console.log(`New published site created: ${config.targetSiteRoot}`);
    console.log(`Promotion report: ${config.reportPath}`);
    console.log(`Promotion validation: ${config.validationPath}`);
  } catch (error) {
    report.overall_status = "fail";
    report.error = error.message;
    validation.overall_status = "fail";
    if (validation.error_count === 0) {
      validation.failures = [{ check: "execution", detail: error.message }];
      validation.error_count = 1;
    }
    ensureParentDir(config.reportPath);
    ensureParentDir(config.validationPath);
    fs.writeFileSync(config.reportPath, stringifyJson(report), "utf8");
    fs.writeFileSync(config.validationPath, stringifyJson(validation), "utf8");
    console.error(error.message);
    process.exitCode = 1;
  }
}

function resolveConfig(options) {
  const sandboxSiteRoot = resolvePathOption(options["sandbox-site-root"], DEFAULT_SANDBOX_SITE_ROOT);
  const currentPublishedRoot = resolvePathOption(options["current-published-root"], DEFAULT_CURRENT_PUBLISHED_ROOT);
  const versionName = typeof options["version-name"] === "string" ? options["version-name"].trim() : "";
  const explicitTargetSiteRoot = typeof options["target-site-root"] === "string" && options["target-site-root"].trim()
    ? resolvePathOption(options["target-site-root"], options["target-site-root"])
    : "";
  const targetNameMode = versionName
    ? "legacy-explicit-version-name"
    : explicitTargetSiteRoot
      ? "explicit-target-site-root"
      : "contract-derived";
  const releaseIdSeed = explicitTargetSiteRoot || versionName || sandboxSiteRoot;
  const releaseId = resolveReleaseIdOption(options["release-id"], releaseIdSeed);
  const releaseQualifier = resolveReleaseQualifier(
    options["release-qualifier"],
    targetNameMode === "contract-derived" ? DEFAULT_RELEASE_QUALIFIER : ""
  );
  const derivedTargetSiteRoot = explicitTargetSiteRoot
    || (versionName
      ? path.join(getPublishedSitesRoot(), versionName)
      : getDatedPublishedSiteRoot({
        releaseId,
        sourceSiteRoot: sandboxSiteRoot,
        qualifier: releaseQualifier,
      }));

  return {
    sandboxSiteRoot,
    currentPublishedRoot,
    releaseId,
    releaseQualifier,
    targetNameMode,
    targetSiteRoot: resolvePathOption(options["target-site-root"], derivedTargetSiteRoot),
    reportPath: resolvePathOption(options.report, DEFAULT_REPORT_PATH),
    validationPath: resolvePathOption(options.validation, DEFAULT_VALIDATION_PATH),
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

function loadSiteRoot(siteRoot) {
  const datasets = {};
  const entryLookup = new Map();

  for (const fileName of resolveDatasetFiles(siteRoot)) {
    const fullPath = path.join(siteRoot, "data", fileName);
      const dataset = readJsonFile(fullPath);
    const datasetName = path.basename(fileName, ".json");
    datasets[datasetName] = dataset;

    const degree = dataset.meta?.degree || datasetName;
    for (const entry of dataset.entries) {
      entryLookup.set(makeNodeKey(degree, entry.slug), entry);
    }
  }

  return {
    siteRoot,
    dataRoot: path.join(siteRoot, "data"),
    renderPath: path.join(siteRoot, "js", "render.js"),
    renderRaw: fs.readFileSync(path.join(siteRoot, "js", "render.js"), "utf8"),
    datasets,
    entryLookup,
  };
}

function hasExpectedSiteStructure(siteRoot) {
  return ["css", "data", "js", "index.html"].every((name) => fs.existsSync(path.join(siteRoot, name)));
}

function compareSiteData(sourceRoot, targetRoot) {
  const datasets = {};
  let totalDiffCount = 0;

  for (const datasetName of Object.keys(sourceRoot.datasets)) {
    const sourceNormalized = normalizeObject(sourceRoot.datasets[datasetName]);
    const targetNormalized = normalizeObject(targetRoot.datasets[datasetName]);
    const sourceEntries = sourceRoot.datasets[datasetName].entries.map((entry) => entry.slug).sort();
    const targetEntries = targetRoot.datasets[datasetName].entries.map((entry) => entry.slug).sort();

    const missingInTarget = sourceEntries.filter((slug) => !targetEntries.includes(slug));
    const extraInTarget = targetEntries.filter((slug) => !sourceEntries.includes(slug));
    const matches = JSON.stringify(sourceNormalized) === JSON.stringify(targetNormalized);

    datasets[datasetName] = {
      matches,
      source_count: sourceEntries.length,
      target_count: targetEntries.length,
      missing_in_target: missingInTarget,
      extra_in_target: extraInTarget,
    };

    if (!matches || missingInTarget.length > 0 || extraInTarget.length > 0) {
      totalDiffCount += 1;
    }
  }

  return {
    pass: totalDiffCount === 0,
    datasets,
  };
}

function collectBrokenRelatedTopics(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const slugs = new Set(dataset.entries.map((entry) => entry.slug));
    for (const entry of dataset.entries) {
      for (const slug of flattenRelatedTopics(entry.related_topics)) {
        if (!slugs.has(slug)) {
          issues.push({
            dataset: datasetName,
            entry_slug: entry.slug,
            kind: "related_topics",
            target: slug,
          });
        }
      }
      if (entry.parent_topic && !slugs.has(entry.parent_topic)) {
        issues.push({
          dataset: datasetName,
          entry_slug: entry.slug,
          kind: "parent_topic",
          target: entry.parent_topic,
        });
      }
      if (entry.parallel_entry && !slugs.has(entry.parallel_entry)) {
        issues.push({
          dataset: datasetName,
          entry_slug: entry.slug,
          kind: "parallel_entry",
          target: entry.parallel_entry,
        });
      }
    }
  }
  return issues;
}

function collectBrokenKnowledgeLinks(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    for (const entry of dataset.entries) {
      for (const link of entry.knowledge_links || []) {
        if (!root.entryLookup.has(makeNodeKey(link.degree, link.slug))) {
          issues.push({
            dataset: datasetName,
            entry_slug: entry.slug,
            target_degree: link.degree,
            target_slug: link.slug,
          });
        }
      }
    }
  }
  return issues;
}

function collectDegreeLaneIntegrityIssues(root) {
  const issues = [];
  for (const datasetName of ["level2", "level3"]) {
    const dataset = root.datasets[datasetName];
    if (!dataset) continue;
    for (const entry of dataset.entries) {
      const degreeOk = entry.degree === datasetName;
      const appliesOk = Array.isArray(entry.applies_to_degrees) && entry.applies_to_degrees.length === 1 && entry.applies_to_degrees[0] === datasetName;
      const ownerOk = entry.degree_owner === datasetName;
      const boundaryOk = entry.boundary_guard_passed === true;

      if (!degreeOk || !appliesOk || !ownerOk || !boundaryOk) {
        issues.push({
          dataset: datasetName,
          slug: entry.slug,
          degree: entry.degree,
          applies_to_degrees: entry.applies_to_degrees,
          degree_owner: entry.degree_owner || null,
          boundary_guard_passed: entry.boundary_guard_passed === true,
        });
      }
    }
  }
  return issues;
}

function resolveDatasetFiles(siteRoot) {
  const files = [...REQUIRED_DATASET_FILES];
  for (const fileName of OPTIONAL_DATASET_FILES) {
    if (fs.existsSync(path.join(siteRoot, "data", fileName))) {
      files.push(fileName);
    }
  }
  return files;
}

function collectRuntimeVisibilityIssues(root) {
  const issues = [];
  if (!hasRuntimeHiddenGuard(root.renderRaw)) {
    issues.push({
      kind: "missing_render_guard",
      render_path: root.renderPath,
    });
  }

  const hiddenKeys = new Set();
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const degree = dataset.meta?.degree || datasetName;
    for (const entry of dataset.entries) {
      if (isEditoriallyHidden(entry)) {
        hiddenKeys.add(makeNodeKey(degree, entry.slug));
      }
      if (entry.review_controls?.superseded_by) {
        const supersedingKey = makeNodeKey(degree, entry.review_controls.superseded_by);
        if (!root.entryLookup.has(supersedingKey)) {
          issues.push({
            kind: "missing_superseding_entry",
            dataset: datasetName,
            slug: entry.slug,
            superseded_by: entry.review_controls.superseded_by,
          });
        }
      }
    }
  }

  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const degree = dataset.meta?.degree || datasetName;
    for (const entry of dataset.entries) {
      if (entry.type === "category" || isEditoriallyHidden(entry)) continue;
      const outgoing = resolveOutgoingTargets(degree, entry);
      for (const target of outgoing) {
        if (!hiddenKeys.has(target)) continue;
        const [targetDegree, targetSlug] = target.split(":");
        issues.push({
          kind: "visible_entry_references_hidden_entry",
          dataset: datasetName,
          entry_slug: entry.slug,
          target_degree: targetDegree,
          target_slug: targetSlug,
        });
      }
    }
  }

  return issues;
}

function resolveOutgoingTargets(degree, entry) {
  const outgoing = [];
  for (const slug of flattenRelatedTopics(entry.related_topics)) {
    outgoing.push(makeNodeKey(degree, slug));
  }
  if (entry.parent_topic) {
    outgoing.push(makeNodeKey(degree, entry.parent_topic));
  }
  if (entry.parallel_entry) {
    outgoing.push(makeNodeKey(degree, entry.parallel_entry));
  }
  for (const link of entry.knowledge_links || []) {
    outgoing.push(makeNodeKey(link.degree, link.slug));
  }
  return outgoing;
}

function hasRuntimeHiddenGuard(renderRaw) {
  return /if\s*\(!entry\s*\|\|\s*!shouldListEntry\(entry,\s*degreeData\)\)\s*return;/.test(renderRaw)
    && /function shouldListEntry\(entry,\s*degreeData,\s*referenceEntry = null\)\s*\{[\s\S]*?isEntryEditoriallyHidden\(entry,\s*referenceEntry\)/.test(renderRaw)
    && /function isEntryEditoriallyHidden\(entry,\s*referenceEntry = null\)\s*\{[\s\S]*?entry\.review_controls\.exclude_from_navigation[\s\S]*?entry\.review_controls\.exclude_from_related_topics/.test(renderRaw);
}

function isEditoriallyHidden(entry) {
  return entry.visibility_level === "editorial" && Boolean(entry.review_controls?.exclude_from_navigation);
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

function normalizeObject(value) {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeObject(item));
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  const normalized = {};
  for (const key of Object.keys(value).sort()) {
    normalized[key] = normalizeObject(value[key]);
  }
  return normalized;
}

function buildCheck(pass, detail, extra = {}) {
  return {
    pass,
    detail,
    ...extra,
  };
}

function makeNodeKey(degree, slug) {
  return `${degree}:${slug}`;
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

main();
