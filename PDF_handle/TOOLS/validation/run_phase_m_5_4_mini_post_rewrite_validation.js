const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PHASE_ID = "phase_m5_4_mini_post_rewrite_validation";
const NEW_SLUG = "level2-tool-system-plumb-square-level";
const FROZEN_SLUG = "level2-tool-system-measure-force-direction";
const RELATIONSHIP_CATEGORY = "relationships_between_symbols";
const OVERLAP_THRESHOLD = 0.35;

const RELATION_MARKERS = [
  "יחס",
  "ביניהם",
  "תלות",
  "הדדית",
  "משלימים",
  "קשר",
  "התאמה",
  "מגדיר",
  "מישור",
  "ציר",
];

const PROCESS_MARKERS = [
  "תהליך",
  "שלב",
  "שלבים",
  "רצף",
  "תחילה",
  "לאחר מכן",
];

const ALLOWED_FC_MARKERS = [
  "אנך",
  "זוויתן",
  "פלס",
  "Plumb",
  "Square",
  "Level",
];

const FORBIDDEN_PATTERNS = [
  { label: "gauge", pattern: /amah-24-etzbaot|gauge|אמת המידה/iu },
  { label: "gavel", pattern: /makevet-ve-izmel|gavel|מקבת/iu },
  { label: "chisel", pattern: /makevet-ve-izmel|chisel|איזמל/iu },
  { label: "later_degree", pattern: /mark[\s-]?master|royal arch|master mason|דרגה שלישית|רב.?בונה/iu },
];

const STOPWORDS = new Set([
  "את",
  "של",
  "על",
  "עם",
  "בלי",
  "גם",
  "כך",
  "לא",
  "זה",
  "זו",
  "או",
  "אל",
  "מן",
  "מה",
  "איך",
  "אבל",
  "כדי",
  "אחד",
  "אחת",
  "שני",
  "שלושתם",
  "דרגה",
  "level2",
  "topic",
  "entry",
  "system",
  "relationship",
  "symbol",
  "analysis",
  "structural",
  "reading",
  "tools",
  "tool",
]);

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();

  const report = {
    phase: PHASE_ID,
    goal: "Validate the new FC tool entry and confirm the frozen predecessor no longer affects canonical Level 2 behavior.",
    mode: "read_only_targeted_validation",
    executed_at: executedAt,
    inputs: {
      level2_path: config.level2Path,
      new_slug: NEW_SLUG,
      frozen_slug: FROZEN_SLUG,
      rewrite_report: config.rewriteReportPath,
      rewrite_validation: config.rewriteValidationPath,
      runtime_render_path: config.renderPath,
    },
    upstream_context: {},
    checks: {},
    overlap_analysis: {},
    runtime_navigation_analysis: {},
    errors: [],
    error_count: 0,
    overall_status: "pending",
  };

  try {
    assertFileExists(config.level2Path, "Level 2 input");
    assertFileExists(config.rewriteReportPath, "Rewrite report");
    assertFileExists(config.rewriteValidationPath, "Rewrite validation");
    assertFileExists(config.renderPath, "Sandbox render runtime");

    const level2Raw = fs.readFileSync(config.level2Path, "utf8");
    const reportRaw = fs.readFileSync(config.rewriteReportPath, "utf8");
    const validationRaw = fs.readFileSync(config.rewriteValidationPath, "utf8");
    const renderRaw = fs.readFileSync(config.renderPath, "utf8");

    const level2Data = JSON.parse(level2Raw);
    const rewriteReport = JSON.parse(reportRaw);
    const rewriteValidation = JSON.parse(validationRaw);

    const newEntry = findEntry(level2Data, NEW_SLUG);
    const frozenEntry = findEntry(level2Data, FROZEN_SLUG);
    const brokenLocalReferences = collectBrokenLocalReferences(level2Data);

    report.upstream_context = {
      rewrite_report_status: rewriteReport.overall_status || "unknown",
      rewrite_validation_status: rewriteValidation.overall_status || "unknown",
      rewrite_stage_3_identity: Boolean(rewriteValidation.stage_3_identity_check?.pass),
      rewrite_stage_4_boundary: Boolean(rewriteValidation.stage_4_boundary_check?.pass),
      rewrite_stage_5_apply_gate: Boolean(rewriteValidation.stage_5_apply_gate?.pass),
    };

    report.checks.new_entry_exists = buildCheck(
      Boolean(newEntry),
      newEntry
        ? `Found ${NEW_SLUG} in level2.json.`
        : `Missing ${NEW_SLUG} in level2.json.`
    );

    report.checks.new_entry_type_integrity = validateTypeIntegrity(newEntry, rewriteValidation);
    report.checks.new_entry_category_fit = validateCategoryFit(newEntry);
    report.checks.new_entry_boundary_stability = validateBoundaryStability(newEntry, rewriteValidation);
    report.checks.new_entry_source_alignment = validateSourceAlignment(newEntry);
    report.checks.new_entry_graph_integrity = validateEntryGraph(level2Data, newEntry);
    report.checks.frozen_entry_hidden_from_runtime_navigation = validateFrozenRuntimeState(frozenEntry, renderRaw);
    report.checks.frozen_entry_has_superseded_by = validateSupersededBy(frozenEntry);
    report.checks.no_broken_local_references = buildCheck(
      brokenLocalReferences.length === 0,
      brokenLocalReferences.length === 0
        ? "No broken local references detected in current Level 2 graph."
        : "Broken local references detected.",
      { broken_references: brokenLocalReferences }
    );

    const overlapAnalysis = analyzeOverlap(level2Data, newEntry);
    report.overlap_analysis = overlapAnalysis;
    report.checks.no_high_overlap_with_existing_relationship_entries = buildCheck(
      overlapAnalysis.max_similarity < OVERLAP_THRESHOLD,
      overlapAnalysis.max_similarity < OVERLAP_THRESHOLD
        ? `Maximum relationship overlap ${overlapAnalysis.max_similarity.toFixed(3)} is below threshold ${OVERLAP_THRESHOLD}.`
        : `Maximum relationship overlap ${overlapAnalysis.max_similarity.toFixed(3)} exceeds threshold ${OVERLAP_THRESHOLD}.`,
      {
        threshold: OVERLAP_THRESHOLD,
        compared_entries: overlapAnalysis.compared_entries,
        top_matches: overlapAnalysis.top_matches,
      }
    );

    const failingChecks = Object.entries(report.checks)
      .filter(([, value]) => !value.pass)
      .map(([name, value]) => ({
        check: name,
        detail: value.detail,
      }));

    report.errors = failingChecks;
    report.error_count = failingChecks.length;
    report.overall_status = failingChecks.length === 0 ? "pass" : "fail";

    const eol = detectEol(level2Raw);
    ensureParentDir(config.outputPath);
    fs.writeFileSync(config.outputPath, stringifyJson(report, eol), "utf8");

    console.log(`Phase M.5.4 validation report: ${config.outputPath}`);
    console.log(`Overall status: ${report.overall_status}`);
    console.log(`Error count: ${report.error_count}`);
  } catch (error) {
    report.overall_status = "fail";
    report.errors = [{ check: "execution", detail: error.message }];
    report.error_count = 1;

    ensureParentDir(config.outputPath);
    fs.writeFileSync(config.outputPath, stringifyJson(report), "utf8");

    console.error(error.message);
    process.exitCode = 1;
  }
}

function validateTypeIntegrity(entry, rewriteValidation) {
  if (!entry) {
    return buildCheck(false, "New entry missing; cannot validate type integrity.");
  }

  const text = gatherEntryText(entry);
  const relationHits = RELATION_MARKERS.filter((marker) => text.includes(marker));
  const processHits = PROCESS_MARKERS.filter((marker) => text.includes(marker));
  const identityStagePass = Boolean(rewriteValidation.stage_3_identity_check?.pass);

  const pass = entry.level2_type === "relationship"
    && entry.level2_content_type === "symbol_relationship_analysis"
    && entry.type === "topic"
    && entry.category === RELATIONSHIP_CATEGORY
    && relationHits.length >= 4
    && processHits.length <= 1
    && identityStagePass;

  return buildCheck(
    pass,
    pass
      ? "Entry still reads as a relationship lane and preserves the M.5.3 identity gate."
      : "Entry no longer satisfies the relationship identity gate.",
    {
      declared_type: entry.level2_type,
      level2_content_type: entry.level2_content_type,
      relation_marker_hits: relationHits,
      process_marker_hits: processHits,
      rewrite_stage_3_identity_pass: identityStagePass,
    }
  );
}

function validateCategoryFit(entry) {
  if (!entry) {
    return buildCheck(false, "New entry missing; cannot validate category fit.");
  }

  const pass = entry.category === RELATIONSHIP_CATEGORY;
  return buildCheck(
    pass,
    pass
      ? "Entry remains in relationships_between_symbols."
      : `Entry category drifted to ${entry.category || "<missing>"}.`,
    { category: entry.category || null }
  );
}

function validateBoundaryStability(entry, rewriteValidation) {
  if (!entry) {
    return buildCheck(false, "New entry missing; cannot validate boundary stability.");
  }

  const serialized = JSON.stringify(entry);
  const boundaryStagePass = Boolean(rewriteValidation.stage_4_boundary_check?.pass);
  const forbiddenHits = FORBIDDEN_PATTERNS
    .filter((rule) => rule.pattern.test(serialized))
    .map((rule) => rule.label);

  const pass = entry.boundary_guard_passed === true
    && entry.degree === "level2"
    && sameArray(entry.applies_to_degrees, ["level2"])
    && entry.degree_owner === "level2"
    && entry.depth_scope === "structural_only"
    && entry.partition_role === "core_degree_content"
    && entry.observability?.is_distinct_from_level1 === true
    && entry.observability?.introduces_new_structure === true
    && forbiddenHits.length === 0
    && boundaryStagePass;

  return buildCheck(
    pass,
    pass
      ? "Boundary discipline remains stable and Level 2 ownership is intact."
      : "Boundary stability check failed.",
    {
      boundary_guard_passed: entry.boundary_guard_passed === true,
      degree: entry.degree,
      applies_to_degrees: entry.applies_to_degrees,
      degree_owner: entry.degree_owner,
      depth_scope: entry.depth_scope,
      partition_role: entry.partition_role,
      forbidden_hits: forbiddenHits,
      rewrite_stage_4_boundary_pass: boundaryStagePass,
    }
  );
}

function validateSourceAlignment(entry) {
  if (!entry) {
    return buildCheck(false, "New entry missing; cannot validate source alignment.");
  }

  const serialized = JSON.stringify(entry);
  const allowedHits = ALLOWED_FC_MARKERS.filter((marker) => serialized.includes(marker));
  const forbiddenHits = FORBIDDEN_PATTERNS
    .filter((rule) => rule.pattern.test(serialized))
    .map((rule) => rule.label);
  const knowledgeLinkDegrees = (entry.knowledge_links || []).map((link) => link.degree);

  const pass = allowedHits.length >= 3
    && forbiddenHits.length === 0
    && (entry.knowledge_links || []).length > 0
    && knowledgeLinkDegrees.every((degree) => degree === "library")
    && Array.isArray(entry.relies_on_level1_topics)
    && entry.relies_on_level1_topics.length === 0;

  return buildCheck(
    pass,
    pass
      ? "Entry remains FC-only and grounded on library support without Level 1 carry-over."
      : "Source alignment drifted away from the FC-only rewrite contract.",
    {
      allowed_marker_hits: allowedHits,
      forbidden_hits: forbiddenHits,
      knowledge_link_degrees: knowledgeLinkDegrees,
      relies_on_level1_topics: entry.relies_on_level1_topics,
      normalized_alignment: pass ? "fc_only" : "not_fc_only",
    }
  );
}

function validateEntryGraph(dataset, entry) {
  if (!entry) {
    return buildCheck(false, "New entry missing; cannot validate graph integrity.");
  }

  const entryBySlug = new Map(dataset.entries.map((item) => [item.slug, item]));
  const issues = [];

  for (const slug of flattenRelatedTopics(entry.related_topics)) {
    if (!entryBySlug.has(slug)) {
      issues.push({ kind: "related_topics", target: slug });
    }
  }

  if (entry.parent_topic && !entryBySlug.has(entry.parent_topic)) {
    issues.push({ kind: "parent_topic", target: entry.parent_topic });
  }

  if (entry.parallel_entry && !entryBySlug.has(entry.parallel_entry)) {
    issues.push({ kind: "parallel_entry", target: entry.parallel_entry });
  }

  for (const link of entry.knowledge_links || []) {
    if (link.degree === dataset.meta.degree && !entryBySlug.has(link.slug)) {
      issues.push({ kind: "knowledge_links", target: link.slug });
    }
    if (link.slug === FROZEN_SLUG) {
      issues.push({ kind: "knowledge_links", target: link.slug, reason: "must_not_reference_frozen_entry" });
    }
  }

  const pass = issues.length === 0;
  return buildCheck(
    pass,
    pass
      ? "Entry-specific related topics and knowledge links resolve cleanly."
      : "Entry graph integrity failed.",
    { issues }
  );
}

function validateFrozenRuntimeState(entry, renderRaw) {
  if (!entry) {
    return buildCheck(false, "Frozen entry missing; cannot validate runtime hiding.");
  }

  const dataPass = entry.visibility_level === "editorial"
    && entry.review_controls?.decision_status === "rejected_pending_rewrite"
    && entry.review_controls?.exclude_from_navigation === true
    && entry.review_controls?.exclude_from_related_topics === true;

  const renderPass = /if\s*\(!entry\s*\|\|\s*!shouldListEntry\(entry,\s*degreeData\)\)\s*return;/.test(renderRaw)
    && /function shouldListEntry\(entry,\s*degreeData,\s*referenceEntry = null\)\s*\{[\s\S]*?isEntryEditoriallyHidden\(entry,\s*referenceEntry\)/.test(renderRaw)
    && /function isEntryEditoriallyHidden\(entry,\s*referenceEntry = null\)\s*\{[\s\S]*?entry\.review_controls\.exclude_from_navigation[\s\S]*?entry\.review_controls\.exclude_from_related_topics/.test(renderRaw);

  const pass = dataPass && renderPass;
  return buildCheck(
    pass,
    pass
      ? "Frozen predecessor is gated out of canonical runtime navigation."
      : "Frozen predecessor is not fully gated out of runtime navigation.",
    {
      visibility_level: entry.visibility_level,
      decision_status: entry.review_controls?.decision_status || null,
      exclude_from_navigation: Boolean(entry.review_controls?.exclude_from_navigation),
      exclude_from_related_topics: Boolean(entry.review_controls?.exclude_from_related_topics),
      render_guard_detected: renderPass,
    }
  );
}

function validateSupersededBy(entry) {
  if (!entry) {
    return buildCheck(false, "Frozen entry missing; cannot validate superseded_by.");
  }

  const pass = entry.review_controls?.superseded_by === NEW_SLUG;
  return buildCheck(
    pass,
    pass
      ? `Frozen predecessor is correctly superseded by ${NEW_SLUG}.`
      : "Frozen predecessor is missing superseded_by linkage.",
    {
      superseded_by: entry.review_controls?.superseded_by || null,
      superseded_in_phase: entry.review_controls?.superseded_in_phase || null,
    }
  );
}

function analyzeOverlap(dataset, newEntry) {
  if (!newEntry) {
    return {
      compared_entries: 0,
      max_similarity: 1,
      top_matches: [],
    };
  }

  const newTokens = buildTokenSet(gatherEntryText(newEntry));
  const comparisons = dataset.entries
    .filter((entry) => entry.slug !== NEW_SLUG && entry.level2_type === "relationship")
    .map((entry) => ({
      slug: entry.slug,
      similarity: jaccardSimilarity(newTokens, buildTokenSet(gatherEntryText(entry))),
      category: entry.category || null,
    }))
    .sort((a, b) => b.similarity - a.similarity);

  return {
    compared_entries: comparisons.length,
    max_similarity: comparisons[0]?.similarity || 0,
    threshold: OVERLAP_THRESHOLD,
    top_matches: comparisons.slice(0, 5),
  };
}

function collectBrokenLocalReferences(dataset) {
  const entryBySlug = new Map(dataset.entries.map((entry) => [entry.slug, entry]));
  const issues = [];

  for (const entry of dataset.entries) {
    for (const slug of flattenRelatedTopics(entry.related_topics)) {
      if (!entryBySlug.has(slug)) {
        issues.push({
          entry_slug: entry.slug,
          kind: "related_topics",
          target: slug,
        });
      }
    }

    if (entry.parent_topic && !entryBySlug.has(entry.parent_topic)) {
      issues.push({
        entry_slug: entry.slug,
        kind: "parent_topic",
        target: entry.parent_topic,
      });
    }

    if (entry.parallel_entry && !entryBySlug.has(entry.parallel_entry)) {
      issues.push({
        entry_slug: entry.slug,
        kind: "parallel_entry",
        target: entry.parallel_entry,
      });
    }

    for (const link of entry.knowledge_links || []) {
      if (link.degree === dataset.meta.degree && !entryBySlug.has(link.slug)) {
        issues.push({
          entry_slug: entry.slug,
          kind: "knowledge_links",
          target: link.slug,
        });
      }
    }
  }

  return issues;
}

function buildTokenSet(text) {
  const normalized = text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 3 && !STOPWORDS.has(token));

  return new Set(normalized);
}

function jaccardSimilarity(left, right) {
  if (!left.size && !right.size) return 1;
  let intersection = 0;
  for (const token of left) {
    if (right.has(token)) {
      intersection += 1;
    }
  }
  const union = new Set([...left, ...right]).size;
  return union === 0 ? 0 : intersection / union;
}

function gatherEntryText(entry) {
  if (!entry) return "";
  return [
    entry.title,
    entry.short_summary,
    entry.reading_layers?.basic,
    entry.reading_layers?.symbolic,
    entry.reading_layers?.advanced,
    entry.full_summary,
    entry.symbolic_meaning,
    entry.candidate_lesson,
    ...(entry.tradition_notes || []),
    ...(entry.caution_notes || []),
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

function findEntry(dataset, slug) {
  return dataset.entries.find((entry) => entry.slug === slug);
}

function buildCheck(pass, detail, extra = {}) {
  return {
    pass,
    detail,
    ...extra,
  };
}

function sameArray(left, right) {
  return JSON.stringify(left || []) === JSON.stringify(right || []);
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
  return {
    level2Path: resolvePathOption(
      options.level2,
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "data", "level2.json")
    ),
    rewriteReportPath: resolvePathOption(
      options["rewrite-report"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_3_rewrite_report.json")
    ),
    rewriteValidationPath: resolvePathOption(
      options["rewrite-validation"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_3_rewrite_validation.json")
    ),
    renderPath: resolvePathOption(
      options.render,
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "js", "render.js")
    ),
    outputPath: resolvePathOption(
      options.output,
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_4_mini_validation_report.json")
    ),
  };
}

function resolvePathOption(value, fallback) {
  const target = value || fallback;
  return path.isAbsolute(target) ? target : path.resolve(ROOT, target);
}

function assertFileExists(filePath, label) {
  if (!filePath || !fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath || "<missing>"}`);
  }
}

function detectEol(text) {
  return text.includes("\r\n") ? "\r\n" : "\n";
}

function stringifyJson(value, eol = "\n") {
  return `${JSON.stringify(value, null, 2)}\n`.replace(/\n/g, eol);
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

main();
