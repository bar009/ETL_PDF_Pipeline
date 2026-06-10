#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const options = {
    workIds: [],
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--staging-dir") {
      options.stagingDir = argv[++index];
    } else if (arg === "--site-root") {
      options.siteRoot = argv[++index];
    } else if (arg === "--output") {
      options.output = argv[++index];
    } else if (arg === "--report") {
      options.report = argv[++index];
    } else if (arg === "--work-id") {
      options.workIds.push(argv[++index]);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!options.stagingDir || !options.siteRoot || !options.output || !options.report) {
    throw new Error(
      "Usage: node build_refill_queue_from_step5_staging.js --staging-dir <dir> --site-root <site-root> --output <queue.json> --report <report.json> [--work-id <id> ...]"
    );
  }
  return options;
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

function uniqueStrings(values) {
  const seen = new Set();
  const ordered = [];
  for (const value of values) {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    ordered.push(text);
  }
  return ordered;
}

function defaultWorkIds() {
  return [
    "commentary-on-the-second-degree",
    "deeper-meaning-of-fc-degree",
  ];
}

function buildSectionLookup(workManifest) {
  const byKey = new Map();
  for (const work of workManifest.works || []) {
    for (const section of work.sections || []) {
      byKey.set(`${work.work_id}::${section.section_id}`, {
        workId: work.work_id,
        workTitle: work.work_title,
        chapterSlug: section.chapter_slug,
        sectionTitle: section.title,
        sourceOrder: section.source_order,
        strongMatches: section.strong_matches || [],
      });
    }
  }
  return byKey;
}

function groupLevel2Operations(level2Patch, allowedWorkIds) {
  const grouped = new Map();
  for (const operation of level2Patch.operations || []) {
    if (!allowedWorkIds.has(operation.work_id)) {
      continue;
    }
    if (!grouped.has(operation.slug)) {
      grouped.set(operation.slug, []);
    }
    grouped.get(operation.slug).push(operation);
  }
  return grouped;
}

function buildCandidateSources(operations, sectionLookup, libraryData) {
  const libraryEntryBySlug = new Map((libraryData.entries || []).map((entry) => [entry.slug, entry]));
  const grouped = new Map();
  for (const operation of operations) {
    const section = sectionLookup.get(`${operation.work_id}::${operation.section_id}`);
    if (!section || !section.chapterSlug) {
      continue;
    }
    const key = section.chapterSlug;
    if (!grouped.has(key)) {
      grouped.set(key, {
        slug: section.chapterSlug,
        title: section.sectionTitle,
        work_id: section.workId,
        work_title: section.workTitle,
        source_heading: section.sectionTitle,
        source_order: section.sourceOrder,
        score: 0,
        reasons: [],
        confidence: "medium",
        section_ids: [],
      });
    }
    const row = grouped.get(key);
    row.score += 20;
    row.reasons.push("step5-strong-match");
    row.reasons.push(`matched-target:${operation.slug}`);
    row.section_ids.push(operation.section_id);
  }

  const candidates = [];
  for (const row of grouped.values()) {
    const libraryEntry = libraryEntryBySlug.get(row.slug);
    if (!libraryEntry) {
      continue;
    }
    candidates.push({
      slug: row.slug,
      title: libraryEntry.title || row.title,
      work_id: row.work_id,
      work_title: row.work_title,
      source_heading: libraryEntry.source_heading || row.source_heading,
      source_order: libraryEntry.source_order || row.source_order,
      score: row.score,
      reasons: uniqueStrings(row.reasons),
      confidence: row.score >= 40 ? "high" : "medium",
      section_ids: uniqueStrings(row.section_ids),
    });
  }

  candidates.sort((left, right) => {
    if (right.score !== left.score) {
      return right.score - left.score;
    }
    return String(left.slug).localeCompare(String(right.slug));
  });
  return candidates;
}

function buildQueueItem(entry, operations, candidateSources) {
  const workIds = uniqueStrings(operations.map((item) => item.work_id));
  const sectionIds = uniqueStrings(operations.map((item) => item.section_id));
  return {
    degree: "level2",
    slug: entry.slug,
    title: entry.title,
    type: entry.type,
    status: entry.status,
    category: entry.category,
    parent_topic: entry.parent_topic,
    importance_bucket: candidateSources.length >= 4 ? "high" : "medium",
    classification: "step5_mapped",
    reasons: [
      "step5 strong matches were found after lookup expansion",
      "candidate sources come from dedicated Fellow Craft books",
      "heuristic run produced evidence links but no new human-readable content blocks",
    ],
    selected_operation_count: operations.length,
    candidate_library_source_count: candidateSources.length,
    candidate_library_sources: candidateSources,
    candidate_work_ids: workIds,
    candidate_section_slugs: candidateSources.map((item) => item.slug),
    matched_section_ids: sectionIds,
    recommended_next_action:
      "Run targeted_refill_from_audit with provider-backed content generation for this entry using the selected FC sources.",
  };
}

function buildReport(queue, workIds, outputPath) {
  const byWork = {};
  for (const item of queue) {
    for (const workId of item.candidate_work_ids || []) {
      byWork[workId] = (byWork[workId] || 0) + 1;
    }
  }
  return {
    created_at: new Date().toISOString(),
    mode: "step5-staging-to-refill-queue",
    output: outputPath,
    selected_work_ids: Array.from(workIds),
    queue_count: queue.length,
    by_work: byWork,
    target_slugs: queue.map((item) => item.slug),
    top_targets: queue.slice(0, 10).map((item) => ({
      slug: item.slug,
      selected_operation_count: item.selected_operation_count,
      candidate_library_source_count: item.candidate_library_source_count,
      candidate_work_ids: item.candidate_work_ids,
    })),
  };
}

function main() {
  const options = parseArgs(process.argv);
  const stagingDir = path.resolve(options.stagingDir);
  const siteRoot = path.resolve(options.siteRoot);
  const outputPath = path.resolve(options.output);
  const reportPath = path.resolve(options.report);

  const workIds = new Set(options.workIds.length ? options.workIds : defaultWorkIds());
  const workManifest = loadJson(path.join(stagingDir, "work_manifest.generated.json"));
  const level2Patch = loadJson(path.join(stagingDir, "level2.patch.json"));
  const level2Data = loadJson(path.join(siteRoot, "data", "level2.json"));
  const siteLibraryData = loadJson(path.join(siteRoot, "data", "library.json"));
  const stagedLibraryCandidate = loadJson(path.join(stagingDir, "library.candidate.json"));
  const mergedLibraryData = {
    entries: [],
  };
  const mergedLibraryBySlug = new Map();
  for (const entry of [...(siteLibraryData.entries || []), ...(stagedLibraryCandidate.entries || [])]) {
    if (!entry || !entry.slug) {
      continue;
    }
    mergedLibraryBySlug.set(entry.slug, entry);
  }
  mergedLibraryData.entries = Array.from(mergedLibraryBySlug.values());

  const entryBySlug = new Map((level2Data.entries || []).map((entry) => [entry.slug, entry]));
  const sectionLookup = buildSectionLookup(workManifest);
  const grouped = groupLevel2Operations(level2Patch, workIds);

  const queue = [];
  for (const [slug, operations] of grouped.entries()) {
    const entry = entryBySlug.get(slug);
    if (!entry) {
      continue;
    }
    const candidateSources = buildCandidateSources(operations, sectionLookup, mergedLibraryData);
    if (!candidateSources.length) {
      continue;
    }
    queue.push(buildQueueItem(entry, operations, candidateSources));
  }

  queue.sort((left, right) => {
    if (right.selected_operation_count !== left.selected_operation_count) {
      return right.selected_operation_count - left.selected_operation_count;
    }
    return String(left.slug).localeCompare(String(right.slug));
  });

  const report = buildReport(queue, workIds, outputPath);
  writeJson(outputPath, queue);
  writeJson(reportPath, report);
  process.stdout.write(`Queue written: ${outputPath}\n`);
  process.stdout.write(`Report written: ${reportPath}\n`);
  process.stdout.write(`Targets: ${queue.length}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
}
