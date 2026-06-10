const fs = require("fs");
const path = require("path");
const { getLiveSiteRoot, getWorkSiteRoot } = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m7_full_system_smoke";
const REQUIRED_DATASET_FILES = ["level1.json", "level2.json", "library.json"];
const OPTIONAL_DATASET_FILES = ["level3.json"];
const DEGREE_DATASETS = new Set(["level1", "level2", "level3"]);
const SANDBOX_DATA_ROOT = path.join(getWorkSiteRoot({ requireRuntimeAssets: true }), "data");
const PUBLISHED_PRIMARY_DATA_ROOT = path.join(getLiveSiteRoot({ requireRuntimeAssets: true }), "data");
const OUTPUT_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_7_full_system_smoke_report.json");

const CONTAMINATION_PATTERNS = {
  level1: [
    { label: "royal_arch", pattern: /royal arch|רויאל ארץ׳|קשת מלכותית/iu },
    { label: "mark_master", pattern: /mark[\s-]?master|מרק מאסטר/iu },
    { label: "master_mason", pattern: /master mason|מאסטר מייסון|רב.?בונה/iu },
    { label: "third_degree", pattern: /third degree|degree 3|level3|דרגה שלישית/iu },
  ],
  level2: [
    { label: "royal_arch", pattern: /royal arch|רויאל ארץ׳|קשת מלכותית/iu },
    { label: "mark_master", pattern: /mark[\s-]?master|מרק מאסטר/iu },
    { label: "master_mason", pattern: /master mason|מאסטר מייסון|רב.?בונה/iu },
    { label: "third_degree", pattern: /third degree|degree 3|level3|דרגה שלישית/iu },
  ],
  level3: [
    { label: "royal_arch", pattern: /royal arch|רויאל ארץ׳|קשת מלכותית/iu },
    { label: "mark_master", pattern: /mark[\s-]?master|מרק מאסטר/iu },
  ],
};

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const report = {
    phase: PHASE_ID,
    goal: "Run full system readiness and integrity validation across sandbox and published roots.",
    mode: "read_only_full_system_validation",
    executed_at: new Date().toISOString(),
    inputs: {
      sandbox: [],
      published: [],
    },
    resolved_paths: {
      sandbox_data_root: config.sandboxDataRoot,
      published_data_root: config.publishedDataRoot,
      output_report: config.outputPath,
    },
    path_adaptations: config.pathAdaptations,
    root_summary: {},
    checks: {},
    failures: [],
    error_count: 0,
    critical_failures: 0,
    overall_status: "pending",
  };

  try {
    const sandboxRoot = loadRoot("sandbox", config.sandboxDataRoot);
    const publishedRoot = loadRoot("published", config.publishedDataRoot);
    report.inputs.sandbox = sandboxRoot.parsedFiles.map((item) => path.basename(item.file));
    report.inputs.published = publishedRoot.parsedFiles.map((item) => `published/${path.basename(item.file)}`);
    report.root_summary = buildRootSummary([sandboxRoot, publishedRoot]);

    report.checks.all_files_parse_valid = buildCheck(
      true,
      "All requested JSON files parsed successfully.",
      {
        critical: true,
        parsed_files: [
          ...sandboxRoot.parsedFiles,
          ...publishedRoot.parsedFiles,
        ],
      }
    );

    const level2Parity = compareDatasets(sandboxRoot.datasets.level2, publishedRoot.datasets.level2);
    report.checks.sandbox_vs_published_match_for_level2 = buildCheck(
      level2Parity.pass,
      level2Parity.pass
        ? "Sandbox and published Level 2 datasets are identical."
        : "Sandbox and published Level 2 datasets do not match.",
      {
        critical: true,
        sandbox_count: sandboxRoot.datasets.level2.entries.length,
        published_count: publishedRoot.datasets.level2.entries.length,
        missing_in_published: level2Parity.onlyInSandbox,
        missing_in_sandbox: level2Parity.onlyInPublished,
        changed_entries: level2Parity.changedEntries,
      }
    );

    if (sandboxRoot.datasets.level3 && publishedRoot.datasets.level3) {
      const level3Parity = compareDatasets(sandboxRoot.datasets.level3, publishedRoot.datasets.level3);
      report.checks.sandbox_vs_published_match_for_level3 = buildCheck(
        level3Parity.pass,
        level3Parity.pass
          ? "Sandbox and published Level 3 datasets are identical."
          : "Sandbox and published Level 3 datasets do not match.",
        {
          critical: true,
          sandbox_count: sandboxRoot.datasets.level3.entries.length,
          published_count: publishedRoot.datasets.level3.entries.length,
          missing_in_published: level3Parity.onlyInSandbox,
          missing_in_sandbox: level3Parity.onlyInPublished,
          changed_entries: level3Parity.changedEntries,
        }
      );
    } else {
      report.checks.sandbox_vs_published_match_for_level3 = buildCheck(
        !sandboxRoot.datasets.level3 && !publishedRoot.datasets.level3,
        !sandboxRoot.datasets.level3 && !publishedRoot.datasets.level3
          ? "Level 3 parity check skipped because neither root contains a Level 3 runtime file."
          : "Level 3 exists in only one root.",
        {
          critical: true,
          sandbox_has_level3: Boolean(sandboxRoot.datasets.level3),
          published_has_level3: Boolean(publishedRoot.datasets.level3),
        }
      );
    }

    const crossRootDiffs = collectCrossRootDiffs(sandboxRoot, publishedRoot);
    report.checks.no_missing_entries = buildCheck(
      crossRootDiffs.totalDiffCount === 0,
      crossRootDiffs.totalDiffCount === 0
        ? "No missing entries between sandbox and published roots."
        : "Missing or extra entries detected between sandbox and published roots.",
      {
        critical: true,
        datasets: crossRootDiffs.datasets,
      }
    );

    const brokenRelatedTopics = [
      ...collectBrokenRelatedTopics(sandboxRoot),
      ...collectBrokenRelatedTopics(publishedRoot),
    ];
    report.checks.no_broken_related_topics = buildCheck(
      brokenRelatedTopics.length === 0,
      brokenRelatedTopics.length === 0
        ? "No broken related_topics references detected."
        : "Broken related_topics references detected.",
      {
        critical: true,
        issues: brokenRelatedTopics,
      }
    );

    const brokenKnowledgeLinks = [
      ...collectBrokenKnowledgeLinks(sandboxRoot),
      ...collectBrokenKnowledgeLinks(publishedRoot),
    ];
    report.checks.no_broken_knowledge_links = buildCheck(
      brokenKnowledgeLinks.length === 0,
      brokenKnowledgeLinks.length === 0
        ? "No broken knowledge_links detected."
        : "Broken knowledge_links detected.",
      {
        critical: true,
        issues: brokenKnowledgeLinks,
      }
    );

    const isolatedNodes = [
      ...collectIsolatedNodes(sandboxRoot),
      ...collectIsolatedNodes(publishedRoot),
    ];
    report.checks.no_isolated_nodes = buildCheck(
      isolatedNodes.length === 0,
      isolatedNodes.length === 0
        ? "No isolated visible nodes detected."
        : "Isolated visible nodes detected.",
      {
        critical: false,
        issues: isolatedNodes,
      }
    );

    const runtimeVisibility = validateRuntimeVisibility([sandboxRoot, publishedRoot]);
    report.checks.editorial_entries_hidden = runtimeVisibility.editorialEntriesHidden;
    report.checks.superseded_entries_not_used = runtimeVisibility.supersededEntriesNotUsed;

    const degreeIssues = [
      ...collectDegreeIssues(sandboxRoot),
      ...collectDegreeIssues(publishedRoot),
    ];
    report.checks.entries_in_correct_degree = buildCheck(
      degreeIssues.length === 0,
      degreeIssues.length === 0
        ? "All entries stay in their declared dataset degree."
        : "Entries found in the wrong degree dataset.",
      {
        critical: false,
        issues: degreeIssues,
      }
    );

    const contaminationIssues = [
      ...collectHigherDegreeContamination(sandboxRoot),
      ...collectHigherDegreeContamination(publishedRoot),
    ];
    report.checks.no_cross_degree_contamination = buildCheck(
      contaminationIssues.length === 0,
      contaminationIssues.length === 0
        ? "No higher-degree contamination markers detected in visible Level 1/Level 2 entries."
        : "Higher-degree contamination markers detected in visible degree entries.",
      {
        critical: false,
        issues: contaminationIssues,
      }
    );

    const degreeOwnerIssues = [
      ...collectDegreeOwnerIssues(sandboxRoot),
      ...collectDegreeOwnerIssues(publishedRoot),
    ];
    report.checks.degree_owner_correct = buildCheck(
      degreeOwnerIssues.length === 0,
      degreeOwnerIssues.length === 0
        ? "degree_owner values are consistent where the schema uses them."
        : "degree_owner mismatches detected.",
      {
        critical: false,
        issues: degreeOwnerIssues,
        note: "Library entries without degree_owner are ignored; degree lanes require exact match.",
      }
    );

    const appliesIssues = [
      ...collectAppliesToDegreesIssues(sandboxRoot),
      ...collectAppliesToDegreesIssues(publishedRoot),
    ];
    report.checks.applies_to_degrees_correct = buildCheck(
      appliesIssues.length === 0,
      appliesIssues.length === 0
        ? "applies_to_degrees includes the owning dataset degree on all entries."
        : "applies_to_degrees inconsistencies detected.",
      {
        critical: false,
        issues: appliesIssues,
      }
    );

    const failingChecks = Object.entries(report.checks)
      .filter(([, value]) => !value.pass)
      .map(([name, value]) => ({
        check: name,
        detail: value.detail,
        critical: Boolean(value.critical),
      }));

    report.failures = failingChecks;
    report.error_count = failingChecks.length;
    report.critical_failures = failingChecks.filter((failure) => failure.critical).length;
    report.overall_status = failingChecks.length === 0 ? "pass" : "fail";

    ensureParentDir(config.outputPath);
    fs.writeFileSync(config.outputPath, stringifyJson(report), "utf8");

    console.log(`Phase M.7 report written: ${config.outputPath}`);
    console.log(`Overall status: ${report.overall_status}`);
    console.log(`Error count: ${report.error_count}`);
    console.log(`Critical failures: ${report.critical_failures}`);
  } catch (error) {
    report.failures = [{ check: "execution", detail: error.message, critical: true }];
    report.error_count = 1;
    report.critical_failures = 1;
    report.overall_status = "fail";
    ensureParentDir(config.outputPath);
    fs.writeFileSync(config.outputPath, stringifyJson(report), "utf8");
    console.error(error.message);
    process.exitCode = 1;
  }
}

function resolveConfig(options) {
  return {
    sandboxDataRoot: resolvePathOption(options.sandbox, SANDBOX_DATA_ROOT),
    publishedDataRoot: resolvePathOption(options.published, PUBLISHED_PRIMARY_DATA_ROOT),
    outputPath: resolvePathOption(options.output, OUTPUT_PATH),
    pathAdaptations: [],
  };
}

function loadRoot(label, dataRoot) {
  if (!fs.existsSync(dataRoot)) {
    throw new Error(`Data root not found for ${label}: ${dataRoot}`);
  }

  const datasets = {};
  const parsedFiles = [];
  for (const fileName of resolveDatasetFiles(dataRoot)) {
    const fullPath = path.join(dataRoot, fileName);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Missing dataset file for ${label}: ${fullPath}`);
    }
    const raw = readJsonFile(fullPath);
    const parsed = JSON.parse(raw);
    datasets[path.basename(fileName, ".json")] = parsed;
    parsedFiles.push({
      root: label,
      file: fullPath,
      entry_count: Array.isArray(parsed.entries) ? parsed.entries.length : 0,
      degree: parsed.meta?.degree || path.basename(fileName, ".json"),
    });
  }

  const renderPath = path.join(path.dirname(dataRoot), "js", "render.js");
  const renderRaw = fs.existsSync(renderPath) ? fs.readFileSync(renderPath, "utf8") : "";
  const entryLookup = buildEntryLookup(datasets);

  return {
    label,
    dataRoot,
    renderPath,
    renderRaw,
    datasets,
    parsedFiles,
    entryLookup,
  };
}

function readJsonFile(filePath) {
  return fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
}

function buildRootSummary(roots) {
  const summary = {};
  for (const root of roots) {
    summary[root.label] = {};
    for (const [datasetName, dataset] of Object.entries(root.datasets)) {
      const hiddenCount = dataset.entries.filter((entry) => isEditoriallyHidden(entry)).length;
      const supersededCount = dataset.entries.filter((entry) => Boolean(entry.review_controls?.superseded_by)).length;
      summary[root.label][datasetName] = {
        degree: dataset.meta?.degree || datasetName,
        entry_count: Array.isArray(dataset.entries) ? dataset.entries.length : 0,
        hidden_editorial_count: hiddenCount,
        superseded_count: supersededCount,
      };
    }
  }
  return summary;
}

function compareDatasets(left, right) {
  const leftBySlug = new Map(left.entries.map((entry) => [entry.slug, normalizeObject(entry)]));
  const rightBySlug = new Map(right.entries.map((entry) => [entry.slug, normalizeObject(entry)]));
  const leftSlugs = [...leftBySlug.keys()].sort();
  const rightSlugs = [...rightBySlug.keys()].sort();
  const onlyInLeft = leftSlugs.filter((slug) => !rightBySlug.has(slug));
  const onlyInRight = rightSlugs.filter((slug) => !leftBySlug.has(slug));

  const changedEntries = [];
  for (const slug of leftSlugs) {
    if (!rightBySlug.has(slug)) continue;
    const leftSerialized = JSON.stringify(leftBySlug.get(slug));
    const rightSerialized = JSON.stringify(rightBySlug.get(slug));
    if (leftSerialized !== rightSerialized) {
      changedEntries.push(slug);
    }
  }

  return {
    pass: onlyInLeft.length === 0 && onlyInRight.length === 0 && changedEntries.length === 0,
    onlyInSandbox: onlyInLeft,
    onlyInPublished: onlyInRight,
    changedEntries,
  };
}

function collectCrossRootDiffs(sandboxRoot, publishedRoot) {
  const datasets = {};
  let totalDiffCount = 0;

  const datasetNames = new Set([
    ...Object.keys(sandboxRoot.datasets),
    ...Object.keys(publishedRoot.datasets),
  ]);

  for (const datasetName of datasetNames) {
    const sandboxEntries = sandboxRoot.datasets[datasetName]?.entries || [];
    const publishedEntries = publishedRoot.datasets[datasetName]?.entries || [];
    const sandboxSlugs = new Set(sandboxEntries.map((entry) => entry.slug));
    const publishedSlugs = new Set(publishedEntries.map((entry) => entry.slug));
    const missingInPublished = [...sandboxSlugs].filter((slug) => !publishedSlugs.has(slug)).sort();
    const missingInSandbox = [...publishedSlugs].filter((slug) => !sandboxSlugs.has(slug)).sort();

    totalDiffCount += missingInPublished.length + missingInSandbox.length;
    datasets[datasetName] = {
      missing_in_published: missingInPublished,
      missing_in_sandbox: missingInSandbox,
    };
  }

  return { totalDiffCount, datasets };
}

function collectBrokenRelatedTopics(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const slugs = new Set(dataset.entries.map((entry) => entry.slug));
    for (const entry of dataset.entries) {
      for (const slug of flattenRelatedTopics(entry.related_topics)) {
        if (!slugs.has(slug)) {
          issues.push({
            root: root.label,
            dataset: datasetName,
            entry_slug: entry.slug,
            kind: "related_topics",
            target: slug,
          });
        }
      }
      if (entry.parent_topic && !slugs.has(entry.parent_topic)) {
        issues.push({
          root: root.label,
          dataset: datasetName,
          entry_slug: entry.slug,
          kind: "parent_topic",
          target: entry.parent_topic,
        });
      }
      if (entry.parallel_entry && !slugs.has(entry.parallel_entry)) {
        issues.push({
          root: root.label,
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
            root: root.label,
            dataset: datasetName,
            entry_slug: entry.slug,
            kind: "knowledge_links",
            target_degree: link.degree,
            target_slug: link.slug,
          });
        }
      }
    }
  }
  return issues;
}

function collectIsolatedNodes(root) {
  const nodes = [];
  const incomingCounts = new Map();

  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    for (const entry of dataset.entries) {
      if (entry.type === "category" || isEditoriallyHidden(entry)) {
        continue;
      }

      const nodeKey = makeNodeKey(dataset.meta.degree, entry.slug);
      const outgoing = resolveOutgoingTargets(root, datasetName, dataset, entry)
        .filter((target) => root.entryLookup.has(target));

      nodes.push({
        root: root.label,
        dataset: datasetName,
        degree: dataset.meta.degree,
        slug: entry.slug,
        key: nodeKey,
        outgoing,
      });
      incomingCounts.set(nodeKey, 0);
    }
  }

  for (const node of nodes) {
    for (const target of node.outgoing) {
      if (incomingCounts.has(target)) {
        incomingCounts.set(target, incomingCounts.get(target) + 1);
      }
    }
  }

  return nodes
    .filter((node) => node.outgoing.length === 0 && incomingCounts.get(node.key) === 0)
    .map((node) => ({
      root: node.root,
      dataset: node.dataset,
      degree: node.degree,
      slug: node.slug,
    }));
}

function validateRuntimeVisibility(roots) {
  const editorialIssues = [];
  const supersededIssues = [];

  for (const root of roots) {
    const renderGuardPass = hasRuntimeHiddenGuard(root.renderRaw);
    const editorialEntries = [];
    const supersededEntries = [];

    for (const [datasetName, dataset] of Object.entries(root.datasets)) {
      for (const entry of dataset.entries) {
        if (isEditoriallyHidden(entry)) {
          editorialEntries.push({
            root: root.label,
            dataset: datasetName,
            slug: entry.slug,
            visibility_level: entry.visibility_level || null,
            exclude_from_navigation: Boolean(entry.review_controls?.exclude_from_navigation),
          });
        }
        if (entry.review_controls?.superseded_by) {
          supersededEntries.push({
            root: root.label,
            dataset: datasetName,
            slug: entry.slug,
            superseded_by: entry.review_controls.superseded_by,
          });
        }
      }
    }

    if (editorialEntries.length > 0 && !renderGuardPass) {
      editorialIssues.push({
        root: root.label,
        kind: "missing_render_guard",
        render_path: root.renderPath,
        entry_count: editorialEntries.length,
      });
    }

    for (const superseded of supersededEntries) {
      const supersedingKey = makeNodeKey(root.datasets[superseded.dataset].meta.degree, superseded.superseded_by);
      if (!root.entryLookup.has(supersedingKey)) {
        supersededIssues.push({
          root: superseded.root,
          dataset: superseded.dataset,
          slug: superseded.slug,
          kind: "missing_superseding_entry",
          superseded_by: superseded.superseded_by,
        });
      }
    }

    supersededIssues.push(...collectVisibleReferencesToHiddenEntries(root));
  }

  return {
    editorialEntriesHidden: buildCheck(
      editorialIssues.length === 0,
      editorialIssues.length === 0
        ? "Editorial entries are protected by runtime visibility guards."
        : "Editorial entries are not fully protected by runtime visibility guards.",
      {
        critical: true,
        issues: editorialIssues,
      }
    ),
    supersededEntriesNotUsed: buildCheck(
      supersededIssues.length === 0,
      supersededIssues.length === 0
        ? "Superseded editorial entries are not used by canonical visible nodes."
        : "Visible entries still reference hidden or superseded entries.",
      {
        critical: true,
        issues: supersededIssues,
      }
    ),
  };
}

function collectVisibleReferencesToHiddenEntries(root) {
  const issues = [];
  const hiddenKeys = new Set();

  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    for (const entry of dataset.entries) {
      if (isEditoriallyHidden(entry)) {
        hiddenKeys.add(makeNodeKey(dataset.meta.degree, entry.slug));
      }
    }
  }

  if (hiddenKeys.size === 0) {
    return issues;
  }

  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    for (const entry of dataset.entries) {
      if (entry.type === "category" || isEditoriallyHidden(entry)) continue;
      const outgoing = resolveOutgoingTargets(root, datasetName, dataset, entry);
      for (const target of outgoing) {
        if (!hiddenKeys.has(target)) continue;
        const [targetDegree, targetSlug] = target.split(":");
        issues.push({
          root: root.label,
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

function collectDegreeIssues(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const expectedDegree = dataset.meta.degree || datasetName;
    for (const entry of dataset.entries) {
      if (entry.degree !== expectedDegree) {
        issues.push({
          root: root.label,
          dataset: datasetName,
          slug: entry.slug,
          expected_degree: expectedDegree,
          actual_degree: entry.degree,
        });
      }
    }
  }
  return issues;
}

function collectHigherDegreeContamination(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    if (!DEGREE_DATASETS.has(datasetName)) continue;
    const patterns = CONTAMINATION_PATTERNS[datasetName] || [];
    if (patterns.length === 0) continue;
    for (const entry of dataset.entries) {
      if (entry.type === "category" || isEditoriallyHidden(entry)) continue;
      const text = gatherEntryText(entry);
      const hits = patterns
        .filter((rule) => rule.pattern.test(text))
        .map((rule) => rule.label);
      if (hits.length > 0) {
        issues.push({
          root: root.label,
          dataset: datasetName,
          slug: entry.slug,
          hits,
        });
      }
    }
  }
  return issues;
}

function resolveDatasetFiles(dataRoot) {
  const files = [...REQUIRED_DATASET_FILES];
  for (const fileName of OPTIONAL_DATASET_FILES) {
    if (fs.existsSync(path.join(dataRoot, fileName))) {
      files.push(fileName);
    }
  }
  return files;
}

function collectDegreeOwnerIssues(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const expectedDegreeOwner = dataset.meta.degree || datasetName;
    for (const entry of dataset.entries) {
      if (DEGREE_DATASETS.has(datasetName)) {
        if (entry.degree_owner !== expectedDegreeOwner) {
          issues.push({
            root: root.label,
            dataset: datasetName,
            slug: entry.slug,
            expected_degree_owner: expectedDegreeOwner,
            actual_degree_owner: entry.degree_owner || null,
          });
        }
        continue;
      }

      if (entry.degree_owner !== undefined && entry.degree_owner !== null && entry.degree_owner !== expectedDegreeOwner) {
        issues.push({
          root: root.label,
          dataset: datasetName,
          slug: entry.slug,
          expected_degree_owner: expectedDegreeOwner,
          actual_degree_owner: entry.degree_owner,
        });
      }
    }
  }
  return issues;
}

function collectAppliesToDegreesIssues(root) {
  const issues = [];
  for (const [datasetName, dataset] of Object.entries(root.datasets)) {
    const expectedDegree = dataset.meta.degree || datasetName;
    for (const entry of dataset.entries) {
      if (!Array.isArray(entry.applies_to_degrees) || !entry.applies_to_degrees.includes(expectedDegree)) {
        issues.push({
          root: root.label,
          dataset: datasetName,
          slug: entry.slug,
          applies_to_degrees: entry.applies_to_degrees || null,
          expected_degree: expectedDegree,
        });
      }
    }
  }
  return issues;
}

function resolveOutgoingTargets(root, datasetName, dataset, entry) {
  const outgoing = [];
  const degree = dataset.meta.degree || datasetName;

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

function buildEntryLookup(datasets) {
  const lookup = new Map();
  for (const [datasetName, dataset] of Object.entries(datasets)) {
    const degree = dataset.meta.degree || datasetName;
    for (const entry of dataset.entries) {
      lookup.set(makeNodeKey(degree, entry.slug), entry);
    }
  }
  return lookup;
}

function hasRuntimeHiddenGuard(renderRaw) {
  if (!renderRaw) return false;
  return /if\s*\(!entry\s*\|\|\s*!shouldListEntry\(entry,\s*degreeData\)\)\s*return;/.test(renderRaw)
    && /function shouldListEntry\(entry,\s*degreeData,\s*referenceEntry = null\)\s*\{[\s\S]*?isEntryEditoriallyHidden\(entry,\s*referenceEntry\)/.test(renderRaw)
    && /function isEntryEditoriallyHidden\(entry,\s*referenceEntry = null\)\s*\{[\s\S]*?entry\.review_controls\.exclude_from_navigation[\s\S]*?entry\.review_controls\.exclude_from_related_topics/.test(renderRaw);
}

function isEditoriallyHidden(entry) {
  if (!entry || entry.visibility_level !== "editorial") {
    return false;
  }
  return Boolean(entry.review_controls?.exclude_from_navigation);
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

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function stringifyJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

main();
