const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const TODAY = new Date().toISOString().slice(0, 10);

const PHASE_ID = "phase_m5_2_decision_apply";

const MOVE_SLUG = "level2-northeast-placement-and-ashlar-relationship";
const FREEZE_SLUG = "level2-tool-system-measure-force-direction";
const FLAG_SLUG = "level2-reflection-chamber-and-mortality-system";
const MOVE_CATEGORY = "relationships_between_symbols";

const KEEP_UNCHANGED_SLUGS = [
  "level2-obligation-brotherhood-and-work-process",
  "level2-chain-of-office-and-responsibility",
  "level2-lodge-as-learning-structure",
];

const MOVE_RELATED_TOPICS = {
  prior: [],
  companion: [
    "even-gvil",
    "l1-ritual-hatzava-batzafon-mizrach",
    "l1-inner-work-hamaavar-meeven-gvila-leeven-mesutetet",
    "vitriol",
  ],
  deeper: [],
};

const LEVEL2_ONLY_FIELDS = [
  "level2_content_type",
  "level2_type",
  "depth_scope",
  "boundary_guard_passed",
  "observability",
  "relies_on_level1_topics",
];

const FREEZE_REASON = "tool set mismatch and cross-degree contamination";
const FREEZE_DECISION_STATUS = "rejected_pending_rewrite";
const FLAG_VALUE = {
  status: "weak_direct_support",
  note: "Architecturally valid but not directly supported by current notebook sources",
};

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const report = {
    phase: PHASE_ID,
    goal: "Apply validated NotebookLM + M.5 decisions to Level 2 and Level 1 datasets in a controlled, atomic, and reversible way.",
    mode: "controlled_data_alignment",
    executed_at: new Date().toISOString(),
    inputs: {
      level2_path: config.level2Path,
      level1_path: config.level1Path,
      notebooklm_report: config.notebooklmReportPath,
      m5_audit: config.m5AuditPath,
    },
    execution_contract: {
      atomic_write: true,
      backup_required: true,
      preserve_non_target_entries: true,
      no_generation: true,
      no_schema_change: true,
      no_partial_apply: true,
    },
    outputs: {
      updated_level2: config.level2Path,
      updated_level1: config.level1Path,
      backup_level2: config.level2BackupPath,
      backup_level1: config.level1BackupPath,
      report: config.alignmentReportPath,
      applied_changes: config.appliedChangesPath,
    },
    compatibility_adaptations: [],
    validations: {},
    overall_status: "pending",
  };

  const appliedChanges = {
    phase: PHASE_ID,
    applied_at: report.executed_at,
    move_to_level1: [],
    reject_or_freeze: [],
    keep_with_flag: [],
    keep_unchanged_verified: [],
    consistency_updates: [],
    compatibility_adaptations: [],
  };

  try {
    assertFileExists(config.level2Path, "Level 2 input");
    assertFileExists(config.level1Path, "Level 1 input");
    assertFileExists(config.notebooklmReportPath, "NotebookLM report");
    assertFileExists(config.m5AuditPath, "M.5 audit");

    const level2Raw = fs.readFileSync(config.level2Path, "utf8");
    const level1Raw = fs.readFileSync(config.level1Path, "utf8");
    const level2Eol = detectEol(level2Raw);
    const level1Eol = detectEol(level1Raw);

    const level2Original = JSON.parse(level2Raw);
    const level1Original = JSON.parse(level1Raw);
    const level2Data = clone(level2Original);
    const level1Data = clone(level1Original);

    const keepChecks = KEEP_UNCHANGED_SLUGS.map((slug) => {
      const exists = Boolean(findEntry(level2Data, slug));
      return { slug, exists };
    });
    const missingKeep = keepChecks.filter((item) => !item.exists);
    if (missingKeep.length) {
      throw new Error(`Missing keep_unchanged entries: ${missingKeep.map((item) => item.slug).join(", ")}`);
    }
    appliedChanges.keep_unchanged_verified = keepChecks.map((item) => item.slug);

    const moveIndex = level2Data.entries.findIndex((entry) => entry.slug === MOVE_SLUG);
    if (moveIndex < 0) {
      throw new Error(`Move target not found in Level 2: ${MOVE_SLUG}`);
    }
    if (findEntry(level1Data, MOVE_SLUG)) {
      throw new Error(`Move target already exists in Level 1: ${MOVE_SLUG}`);
    }

    const level2Category = level2Data.categories[MOVE_CATEGORY];
    if (!level2Category) {
      throw new Error(`Missing source category in Level 2: ${MOVE_CATEGORY}`);
    }
    if (!level1Data.categories[MOVE_CATEGORY]) {
      level1Data.categories[MOVE_CATEGORY] = clone(level2Category);
      appliedChanges.consistency_updates.push({
        type: "category_added",
        dataset: "level1",
        category: MOVE_CATEGORY,
      });
    }

    const movedEntry = clone(level2Data.entries[moveIndex]);
    level2Data.entries.splice(moveIndex, 1);
    sanitizeMovedEntry(movedEntry);
    level1Data.entries.push(movedEntry);
    appliedChanges.move_to_level1.push({
      slug: MOVE_SLUG,
      from_dataset: "level2",
      to_dataset: "level1",
      degree: movedEntry.degree,
      applies_to_degrees: movedEntry.applies_to_degrees,
      degree_owner: movedEntry.degree_owner,
      category: movedEntry.category,
      removed_fields: LEVEL2_ONLY_FIELDS.filter((field) => Object.prototype.hasOwnProperty.call(level2Original.entries[moveIndex], field)),
      related_topics_strategy: "remapped_to_existing_level1_knowledge_links",
    });

    const frozenEntry = findEntry(level2Data, FREEZE_SLUG);
    if (!frozenEntry) {
      throw new Error(`Freeze target not found in Level 2: ${FREEZE_SLUG}`);
    }
    frozenEntry.visibility_level = "editorial";
    frozenEntry.review_controls = {
      ...(frozenEntry.review_controls || {}),
      phase: PHASE_ID,
      decision_status: FREEZE_DECISION_STATUS,
      exclude_from_navigation: true,
      exclude_from_related_topics: true,
      reason: FREEZE_REASON,
    };
    report.compatibility_adaptations.push({
      slug: FREEZE_SLUG,
      requested_field: "status",
      requested_value: FREEZE_DECISION_STATUS,
      applied_mapping: "review_controls.decision_status",
      reason: "content.schema.json only allows status values draft|reviewed|published",
    });
    appliedChanges.compatibility_adaptations.push({
      slug: FREEZE_SLUG,
      requested_field: "status",
      requested_value: FREEZE_DECISION_STATUS,
      applied_mapping: "review_controls.decision_status",
    });
    appliedChanges.reject_or_freeze.push({
      slug: FREEZE_SLUG,
      preserved_entry: true,
      visibility_level: frozenEntry.visibility_level,
      review_controls: clone(frozenEntry.review_controls),
    });

    const flagEntry = findEntry(level2Data, FLAG_SLUG);
    if (!flagEntry) {
      throw new Error(`Flag target not found in Level 2: ${FLAG_SLUG}`);
    }
    const flagApplyResult = mergeMissingObject(flagEntry, "source_validation", FLAG_VALUE);
    appliedChanges.keep_with_flag.push({
      slug: FLAG_SLUG,
      field: "source_validation",
      added_fields: flagApplyResult.added,
      preserved_existing_fields: flagApplyResult.preserved,
      final_value: clone(flagEntry.source_validation),
    });

    const consistencyTargets = [MOVE_SLUG, FREEZE_SLUG];
    for (const target of consistencyTargets) {
      appliedChanges.consistency_updates.push(
        ...removeReferencesToTarget(level2Data, target, "level2")
      );
      appliedChanges.consistency_updates.push(
        ...removeReferencesToTarget(level1Data, target, "level1")
      );
    }

    level2Data.meta = {
      ...level2Data.meta,
      updated_at: TODAY,
    };
    level1Data.meta = {
      ...level1Data.meta,
      updated_at: TODAY,
    };

    const level2Issues = collectBrokenLocalReferences(level2Data);
    const level1Issues = collectBrokenLocalReferences(level1Data);

    const moveValidation = validateMove(level2Data, level1Data);
    const freezeValidation = validateFreeze(level2Data);
    const flagValidation = validateFlag(level2Data);

    report.validations = {
      level2_valid_json: true,
      level1_valid_json: true,
      no_broken_links: level2Issues.length === 0 && level1Issues.length === 0,
      move_applied_correctly: moveValidation.ok,
      freeze_applied_correctly: freezeValidation.ok,
      flags_added: flagValidation.ok,
      level2_broken_references: level2Issues,
      level1_broken_references: level1Issues,
      move_details: moveValidation,
      freeze_details: freezeValidation,
      flag_details: flagValidation,
    };

    const blockingIssues = [
      ...level2Issues.map((issue) => `level2:${issue.entry_slug}:${issue.kind}:${issue.target}`),
      ...level1Issues.map((issue) => `level1:${issue.entry_slug}:${issue.kind}:${issue.target}`),
      ...(moveValidation.ok ? [] : moveValidation.errors),
      ...(freezeValidation.ok ? [] : freezeValidation.errors),
      ...(flagValidation.ok ? [] : flagValidation.errors),
    ];

    if (blockingIssues.length) {
      throw new Error(`Validation failed after apply: ${blockingIssues.join(" | ")}`);
    }

    const level2Text = stringifyJson(level2Data, level2Eol);
    const level1Text = stringifyJson(level1Data, level1Eol);
    report.overall_status = "pass";
    report.success_criteria = {
      level2_valid: true,
      level1_valid: true,
      no_broken_links: true,
      move_applied_correctly: true,
      freeze_applied_correctly: true,
      flags_added: true,
      overall_status: "pass",
    };
    const reportText = stringifyJson(report, level2Eol);
    const appliedChangesText = stringifyJson(appliedChanges, level2Eol);

    ensureParentDir(config.level2BackupPath);
    ensureParentDir(config.level1BackupPath);
    ensureParentDir(config.alignmentReportPath);
    ensureParentDir(config.appliedChangesPath);

    fs.writeFileSync(config.level2BackupPath, level2Raw, "utf8");
    fs.writeFileSync(config.level1BackupPath, level1Raw, "utf8");

    const snapshots = buildSnapshots([
      { path: config.level2Path, content: level2Text },
      { path: config.level1Path, content: level1Text },
      { path: config.alignmentReportPath, content: reportText },
      { path: config.appliedChangesPath, content: appliedChangesText },
    ]);

    commitWritesWithRollback(snapshots);

    console.log(`Phase M.5.2 apply complete`);
    console.log(`Level 2 updated: ${config.level2Path}`);
    console.log(`Level 1 updated: ${config.level1Path}`);
    console.log(`Alignment report: ${config.alignmentReportPath}`);
    console.log(`Applied changes: ${config.appliedChangesPath}`);
  } catch (error) {
    report.overall_status = "failed";
    report.error = error.message;
    console.error(error.message);
    process.exitCode = 1;
  }
}

function resolveConfig(options) {
  const latestAudit = findLatestAuditReport();
  return {
    level2Path: resolvePathOption(
      options.level2,
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "data", "level2.json")
    ),
    level1Path: resolvePathOption(
      options.level1,
      path.join(ROOT, "0.3", "data", "level1.json")
    ),
    notebooklmReportPath: resolvePathOption(
      options["notebooklm-report"],
      path.join(ROOT, "experiments", "notebooklm_validation", "runs", "2026-03-20", "notebooklm_level2_queue_report_19-37-35Z.md")
    ),
    m5AuditPath: resolvePathOption(options["m5-audit"], latestAudit),
    level2BackupPath: resolvePathOption(
      options["level2-backup"],
      path.join(ROOT, "sandbox_sites", "phase-h-2026-03-20T00-52-47+00-00", "data", "level2.pre_m5_2_backup.json")
    ),
    level1BackupPath: resolvePathOption(
      options["level1-backup"],
      path.join(ROOT, "0.3", "data", "level1.pre_m5_2_backup.json")
    ),
    alignmentReportPath: resolvePathOption(
      options["alignment-report"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_2_alignment_report.json")
    ),
    appliedChangesPath: resolvePathOption(
      options["applied-changes"],
      path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_5_2_applied_changes.json")
    ),
  };
}

function parseArgs(args) {
  const parsed = {};
  for (let i = 0; i < args.length; i += 1) {
    const token = args[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = args[i + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = next;
    i += 1;
  }
  return parsed;
}

function resolvePathOption(value, fallback) {
  const target = value || fallback;
  if (!target) {
    throw new Error("Missing required path configuration");
  }
  return path.isAbsolute(target) ? target : path.resolve(ROOT, target);
}

function findLatestAuditReport() {
  const reportRoot = path.join(ROOT, "PDF_handle", "TOOLS", "reports", "phase_m_5_post_fill_audit");
  if (!fs.existsSync(reportRoot)) return null;

  const candidates = [];
  for (const child of fs.readdirSync(reportRoot, { withFileTypes: true })) {
    if (!child.isDirectory()) continue;
    const candidate = path.join(reportRoot, child.name, "phase_m_5_post_fill_audit.json");
    if (!fs.existsSync(candidate)) continue;
    const stat = fs.statSync(candidate);
    candidates.push({ path: candidate, mtimeMs: stat.mtimeMs });
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0]?.path || null;
}

function sanitizeMovedEntry(entry) {
  for (const field of LEVEL2_ONLY_FIELDS) {
    delete entry[field];
  }
  entry.degree = "level1";
  entry.applies_to_degrees = ["level1"];
  entry.degree_owner = "level1";
  entry.category = MOVE_CATEGORY;
  entry.partition_role = "core_degree_content";
  entry.related_topics = clone(MOVE_RELATED_TOPICS);
}

function removeReferencesToTarget(dataset, targetSlug, datasetName) {
  const updates = [];
  for (const entry of dataset.entries) {
    if (entry.slug === targetSlug) continue;

    const relatedTopics = entry.related_topics;
    if (relatedTopics && typeof relatedTopics === "object" && !Array.isArray(relatedTopics)) {
      for (const bucket of ["prior", "companion", "deeper"]) {
        const original = Array.isArray(relatedTopics[bucket]) ? relatedTopics[bucket] : [];
        const filtered = original.filter((slug) => slug !== targetSlug);
        if (filtered.length !== original.length) {
          entry.related_topics[bucket] = filtered;
          updates.push({
            dataset: datasetName,
            slug: entry.slug,
            target: targetSlug,
            kind: `related_topics.${bucket}`,
            removed_count: original.length - filtered.length,
          });
        }
      }
    } else if (Array.isArray(relatedTopics)) {
      const filtered = relatedTopics.filter((slug) => slug !== targetSlug);
      if (filtered.length !== relatedTopics.length) {
        entry.related_topics = filtered;
        updates.push({
          dataset: datasetName,
          slug: entry.slug,
          target: targetSlug,
          kind: "related_topics",
          removed_count: relatedTopics.length - filtered.length,
        });
      }
    }

    if (entry.parent_topic === targetSlug) {
      entry.parent_topic = null;
      updates.push({
        dataset: datasetName,
        slug: entry.slug,
        target: targetSlug,
        kind: "parent_topic",
        removed_count: 1,
      });
    }

    if (entry.parallel_entry === targetSlug) {
      entry.parallel_entry = null;
      updates.push({
        dataset: datasetName,
        slug: entry.slug,
        target: targetSlug,
        kind: "parallel_entry",
        removed_count: 1,
      });
    }

    if (Array.isArray(entry.knowledge_links)) {
      const originalLinks = entry.knowledge_links;
      const filteredLinks = originalLinks.filter(
        (link) => !(link && link.degree === dataset.meta.degree && link.slug === targetSlug)
      );
      if (filteredLinks.length !== originalLinks.length) {
        entry.knowledge_links = filteredLinks;
        updates.push({
          dataset: datasetName,
          slug: entry.slug,
          target: targetSlug,
          kind: "knowledge_links",
          removed_count: originalLinks.length - filteredLinks.length,
        });
      }
    }
  }
  return updates;
}

function collectBrokenLocalReferences(dataset) {
  const entryBySlug = new Map(dataset.entries.map((entry) => [entry.slug, entry]));
  const issues = [];

  for (const entry of dataset.entries) {
    const related = flattenRelatedTopics(entry.related_topics);
    for (const target of related) {
      if (!entryBySlug.has(target)) {
        issues.push({
          entry_slug: entry.slug,
          kind: "related_topics",
          target,
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

function validateMove(level2Data, level1Data) {
  const errors = [];
  const level2Entry = findEntry(level2Data, MOVE_SLUG);
  const level1Entry = findEntry(level1Data, MOVE_SLUG);

  if (level2Entry) {
    errors.push(`move target still present in level2: ${MOVE_SLUG}`);
  }
  if (!level1Entry) {
    errors.push(`move target missing from level1: ${MOVE_SLUG}`);
  } else {
    if (level1Entry.degree !== "level1") errors.push(`move target degree not updated`);
    if (JSON.stringify(level1Entry.applies_to_degrees) !== JSON.stringify(["level1"])) {
      errors.push(`move target applies_to_degrees not updated`);
    }
    if (level1Entry.degree_owner !== "level1") errors.push(`move target degree_owner not updated`);
    if (level1Entry.category !== MOVE_CATEGORY) errors.push(`move target category not updated`);
    if (level1Entry.partition_role !== "core_degree_content") {
      errors.push(`move target partition_role not updated`);
    }
    for (const field of LEVEL2_ONLY_FIELDS) {
      if (Object.prototype.hasOwnProperty.call(level1Entry, field)) {
        errors.push(`move target still has level2-only field: ${field}`);
      }
    }
  }

  return {
    ok: errors.length === 0,
    errors,
  };
}

function validateFreeze(level2Data) {
  const errors = [];
  const frozenEntry = findEntry(level2Data, FREEZE_SLUG);
  if (!frozenEntry) {
    errors.push(`freeze target missing from level2: ${FREEZE_SLUG}`);
    return { ok: false, errors };
  }
  if (frozenEntry.visibility_level !== "editorial") {
    errors.push(`freeze target visibility_level not set to editorial`);
  }
  if (frozenEntry.review_controls?.decision_status !== FREEZE_DECISION_STATUS) {
    errors.push(`freeze target decision_status missing`);
  }
  if (!frozenEntry.review_controls?.exclude_from_navigation) {
    errors.push(`freeze target exclude_from_navigation missing`);
  }
  if (!frozenEntry.review_controls?.exclude_from_related_topics) {
    errors.push(`freeze target exclude_from_related_topics missing`);
  }

  const referrers = [];
  for (const entry of level2Data.entries) {
    if (entry.slug === FREEZE_SLUG) continue;
    if (flattenRelatedTopics(entry.related_topics).includes(FREEZE_SLUG)) {
      referrers.push(entry.slug);
    }
    if (entry.parent_topic === FREEZE_SLUG) {
      referrers.push(entry.slug);
    }
    if (entry.parallel_entry === FREEZE_SLUG) {
      referrers.push(entry.slug);
    }
    if ((entry.knowledge_links || []).some((link) => link.degree === level2Data.meta.degree && link.slug === FREEZE_SLUG)) {
      referrers.push(entry.slug);
    }
  }
  if (referrers.length) {
    errors.push(`freeze target still referenced by: ${referrers.join(", ")}`);
  }

  return {
    ok: errors.length === 0,
    errors,
  };
}

function validateFlag(level2Data) {
  const errors = [];
  const flagEntry = findEntry(level2Data, FLAG_SLUG);
  if (!flagEntry) {
    errors.push(`flag target missing from level2: ${FLAG_SLUG}`);
    return { ok: false, errors };
  }
  if (!flagEntry.source_validation) {
    errors.push(`source_validation not present on flag target`);
  } else {
    if (!flagEntry.source_validation.status) {
      errors.push(`source_validation.status missing`);
    }
    if (!flagEntry.source_validation.note) {
      errors.push(`source_validation.note missing`);
    }
  }
  return {
    ok: errors.length === 0,
    errors,
  };
}

function mergeMissingObject(entry, fieldName, additions) {
  const target = entry[fieldName] && typeof entry[fieldName] === "object" && !Array.isArray(entry[fieldName])
    ? { ...entry[fieldName] }
    : {};
  const added = [];
  const preserved = [];

  for (const [key, value] of Object.entries(additions)) {
    if (target[key] === undefined) {
      target[key] = value;
      added.push(key);
    } else {
      preserved.push(key);
    }
  }

  entry[fieldName] = target;
  return { added, preserved };
}

function flattenRelatedTopics(relatedTopics) {
  if (Array.isArray(relatedTopics)) return relatedTopics.filter(Boolean);
  if (!relatedTopics || typeof relatedTopics !== "object") return [];
  return [
    ...(Array.isArray(relatedTopics.prior) ? relatedTopics.prior : []),
    ...(Array.isArray(relatedTopics.companion) ? relatedTopics.companion : []),
    ...(Array.isArray(relatedTopics.deeper) ? relatedTopics.deeper : []),
  ].filter(Boolean);
}

function buildSnapshots(writes) {
  return writes.map((write) => {
    const exists = fs.existsSync(write.path);
    return {
      ...write,
      previousExists: exists,
      previousContent: exists ? fs.readFileSync(write.path, "utf8") : null,
    };
  });
}

function commitWritesWithRollback(snapshots) {
  const applied = [];
  try {
    for (const snapshot of snapshots) {
      ensureParentDir(snapshot.path);
      fs.writeFileSync(snapshot.path, snapshot.content, "utf8");
      applied.push(snapshot);
    }
  } catch (error) {
    for (let index = applied.length - 1; index >= 0; index -= 1) {
      const snapshot = applied[index];
      if (snapshot.previousExists) {
        fs.writeFileSync(snapshot.path, snapshot.previousContent, "utf8");
      } else if (fs.existsSync(snapshot.path)) {
        fs.unlinkSync(snapshot.path);
      }
    }
    throw error;
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

function findEntry(dataset, slug) {
  return dataset.entries.find((entry) => entry.slug === slug);
}

function assertFileExists(filePath, label) {
  if (!filePath || !fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath || "<missing>"}`);
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

main();
