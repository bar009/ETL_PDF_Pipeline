#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot } = require("../lib/site_roots");

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const DEFAULT_SITE_ROOT = getWorkSiteRoot();

function buildDefaults(siteRoot) {
  return {
    siteRoot,
    library: path.join(siteRoot, "data", "library.json"),
    level1: path.join(siteRoot, "data", "level1.json"),
    level2: path.join(siteRoot, "data", "level2.json"),
    level3: path.join(siteRoot, "data", "level3.json"),
    seedPacketInput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/seed_packet.json",
    bundleDir: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/staging_bundle",
    reportOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/staging_bundle/report.json"
  };
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const nextValue = argv[index + 1];
    if (!nextValue || nextValue.startsWith("--")) {
      options[key] = true;
      continue;
    }
    options[key] = nextValue;
    index += 1;
  }
  return options;
}

function pickOption(options, ...keys) {
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(options, key) && options[key] !== undefined) {
      return options[key];
    }
  }
  return undefined;
}

function resolveRepoPath(targetPath) {
  if (!targetPath) {
    return null;
  }
  return path.isAbsolute(targetPath) ? path.resolve(targetPath) : path.resolve(repoRoot, targetPath);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function uniqueStrings(values) {
  return Array.from(new Set(ensureArray(values).map((value) => normalizeString(value)).filter(Boolean)));
}

function requireExplicitIsolationFlag(options) {
  const allowed = Boolean(options["allow-isolated-backfill"] || options.allowIsolatedBackfill);
  if (allowed) {
    return;
  }

  throw new Error(
    "Retroactive staging bundle is isolated on purpose. Re-run with --allow-isolated-backfill to confirm this non-canonical review lane."
  );
}

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function utcTimestamp() {
  return new Date().toISOString();
}

function firstCategoryId(dataset) {
  const keys = Object.keys(dataset.categories || {});
  return keys[0] || null;
}

function pickCategoryId(seed, dataset, bestMatchEntry) {
  if (bestMatchEntry && bestMatchEntry.category && dataset.categories?.[bestMatchEntry.category]) {
    return bestMatchEntry.category;
  }
  return firstCategoryId(dataset);
}

function buildDraftEntryPayload(seed, dataset, bestMatchEntry) {
  const categoryId = pickCategoryId(seed, dataset, bestMatchEntry);
  const companionSlugs =
    bestMatchEntry && bestMatchEntry.degree === seed.target_degree && bestMatchEntry.slug
      ? [bestMatchEntry.slug]
      : [];
  const sourceBook = seed.provenance?.source_book || "NotebookLM stable base";
  const sourceSection = seed.provenance?.source_section || seed.target_topic_title;
  const sourceLocation = seed.provenance?.source_location || "";
  const sourceNote = `${sourceBook} | ${sourceSection} | ${sourceLocation || "stable-base seed"} | retroactive backfill`;

  return {
    title: seed.seed_payload.title,
    slug: seed.seed_payload.slug,
    type: "topic",
    degree: seed.target_degree,
    applies_to_degrees: [seed.target_degree],
    category: categoryId,
    parent_topic: null,
    aliases: [],
    keywords: uniqueStrings(seed.seed_payload.keywords),
    related_topics: { prior: [], companion: companionSlugs, deeper: [] },
    short_summary: seed.seed_payload.short_summary || "",
    full_summary: seed.seed_payload.short_summary || "",
    practical_elements: [],
    symbolic_meaning: "",
    candidate_lesson: seed.seed_payload.candidate_lesson || "",
    tradition_notes: [],
    caution_notes: [],
    source_notes: uniqueStrings([
      sourceNote,
      ...ensureArray(seed.seed_payload.source_notes)
    ]),
    language: "en",
    work_id: "notebooklm-retroactive-backfill",
    work_title: "NotebookLM Retroactive Backfill",
    source_kind: "notebooklm-stable-base",
    source_path: "PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json",
    source_anchor: seed.stable_base_id,
    source_heading: seed.target_topic_title,
    source_order: null,
    parallel_entry: null,
    translation_mode: null,
    knowledge_links: [],
    chapter_toc: [],
    visibility_level: "internal",
    sensitivity_level: "standard",
    tradition_scope: "interpretive",
    status: "draft"
  };
}

function cloneDataset(dataset) {
  return JSON.parse(JSON.stringify(dataset));
}

function buildCompanionCandidate(seed, dataset, bestMatchEntry) {
  const draftPayload = buildDraftEntryPayload(seed, dataset, bestMatchEntry);
  return {
    work_id: "notebooklm-retroactive-backfill",
    section_id: seed.seed_id,
    section_title: seed.target_topic_title,
    suggested_degree: seed.target_degree,
    suggested_category: draftPayload.category,
    related_existing_slugs: bestMatchEntry && bestMatchEntry.slug ? [bestMatchEntry.slug] : [],
    source_provenance: `${seed.provenance?.source_book || "NotebookLM"} | ${seed.provenance?.source_section || seed.target_topic_title} | ${seed.provenance?.source_location || "stable-base seed"} | retroactive backfill`,
    confidence_reason: `Built from approved stable-base seed ${seed.stable_base_id}.`,
    draft_entry_payload: draftPayload
  };
}

function appendCompanionPreview(dataset, candidate) {
  const slug = candidate.draft_entry_payload.slug;
  if (ensureArray(dataset.entries).some((entry) => entry.slug === slug)) {
    return false;
  }
  dataset.entries.push(candidate.draft_entry_payload);
  dataset.meta.updated_at = todayDate();
  return true;
}

function main() {
  const cliOptions = parseArgs(process.argv.slice(2));
  requireExplicitIsolationFlag(cliOptions);
  const defaults = buildDefaults(resolveRepoPath(pickOption(cliOptions, "site-root", "siteRoot") || DEFAULT_SITE_ROOT));
  const options = { ...defaults, ...cliOptions };
  const resolved = {
    siteRoot: resolveRepoPath(pickOption(options, "site-root", "siteRoot")),
    library: resolveRepoPath(pickOption(options, "library")),
    level1: resolveRepoPath(pickOption(options, "level1")),
    level2: resolveRepoPath(pickOption(options, "level2")),
    level3: resolveRepoPath(pickOption(options, "level3")),
    seedPacketInput: resolveRepoPath(pickOption(options, "seed-packet-input", "seedPacketInput")),
    bundleDir: resolveRepoPath(pickOption(options, "bundle-dir", "bundleDir")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput"))
  };

  const seedPacket = readJson(resolved.seedPacketInput);
  const library = readJson(resolved.library);
  const level1 = readJson(resolved.level1);
  const level2 = readJson(resolved.level2);
  const level3Exists = resolved.level3 && fs.existsSync(resolved.level3);
  const level3 = level3Exists ? readJson(resolved.level3) : null;

  const previewLibrary = cloneDataset(library);
  const previewLevel1 = cloneDataset(level1);
  const previewLevel2 = cloneDataset(level2);
  const previewLevel3 = level3 ? cloneDataset(level3) : null;

  const datasetMap = {
    library: previewLibrary,
    level1: previewLevel1,
    level2: previewLevel2,
    ...(previewLevel3 ? { level3: previewLevel3 } : {})
  };

  const companionCandidates = [];
  const report = {
    meta: {
      phase: "notebooklm_retroactive_staging_bundle",
      generated_at: utcTimestamp(),
      site_root: resolved.siteRoot,
      seed_packet_input: resolved.seedPacketInput
    },
    summary: {
      seed_count: ensureArray(seedPacket.entries).length,
      candidate_count: 0,
      skipped_existing_slug_count: 0,
      target_degree_counts: {}
    },
    candidates: [],
    skipped: []
  };

  for (const seed of ensureArray(seedPacket.entries)) {
    const dataset = datasetMap[seed.target_degree];
    if (!dataset) {
      report.skipped.push({
        seed_id: seed.seed_id,
        reason: `target dataset ${seed.target_degree} is unavailable`
      });
      continue;
    }

    const bestMatch = seed.best_existing_match || null;
    const bestMatchEntry =
      bestMatch && bestMatch.dataset_id === seed.target_degree
        ? ensureArray(dataset.entries).find((entry) => entry.slug === bestMatch.slug) || null
        : null;
    const candidate = buildCompanionCandidate(seed, dataset, bestMatchEntry);
    const existsAlready = ensureArray(dataset.entries).some((entry) => entry.slug === candidate.draft_entry_payload.slug);
    if (existsAlready) {
      report.summary.skipped_existing_slug_count += 1;
      report.skipped.push({
        seed_id: seed.seed_id,
        reason: `slug ${candidate.draft_entry_payload.slug} already exists in ${seed.target_degree}`
      });
      continue;
    }

    appendCompanionPreview(dataset, candidate);
    companionCandidates.push(candidate);
    report.summary.target_degree_counts[seed.target_degree] =
      (report.summary.target_degree_counts[seed.target_degree] || 0) + 1;
    report.candidates.push({
      seed_id: seed.seed_id,
      slug: candidate.draft_entry_payload.slug,
      title: candidate.draft_entry_payload.title,
      degree: candidate.draft_entry_payload.degree,
      category: candidate.draft_entry_payload.category,
      related_existing_slugs: candidate.related_existing_slugs
    });
  }

  report.summary.candidate_count = companionCandidates.length;

  const bundleDir = ensureDir(resolved.bundleDir);
  const emptyLibraryPatch = { created_at: utcTimestamp(), degree: "library", category_added: false, entries: [] };
  const emptyDegreePatch = (degree) => ({ created_at: utcTimestamp(), degree, operations: [] });
  const workManifest = {
    created_at: utcTimestamp(),
    works: ensureArray(seedPacket.entries).map((seed) => ({
      work_id: "notebooklm-retroactive-backfill",
      section_id: seed.seed_id,
      section_title: seed.target_topic_title,
      target_degree: seed.target_degree,
      target_slug: seed.target_topic_slug,
      source_candidate_id: seed.source_candidate_id
    }))
  };

  writeJsonAtomic(path.join(bundleDir, "work_manifest.generated.json"), workManifest);
  writeJsonAtomic(path.join(bundleDir, "library.patch.json"), emptyLibraryPatch);
  writeJsonAtomic(path.join(bundleDir, "level1.patch.json"), emptyDegreePatch("level1"));
  writeJsonAtomic(path.join(bundleDir, "level2.patch.json"), emptyDegreePatch("level2"));
  if (previewLevel3) {
    writeJsonAtomic(path.join(bundleDir, "level3.patch.json"), emptyDegreePatch("level3"));
  }
  writeJsonAtomic(path.join(bundleDir, "companion_candidates.json"), companionCandidates);
  writeJsonAtomic(path.join(bundleDir, "library.candidate.json"), previewLibrary);
  writeJsonAtomic(path.join(bundleDir, "level1.candidate.json"), previewLevel1);
  writeJsonAtomic(path.join(bundleDir, "level2.candidate.json"), previewLevel2);
  if (previewLevel3) {
    writeJsonAtomic(path.join(bundleDir, "level3.candidate.json"), previewLevel3);
  }
  writeJsonAtomic(resolved.reportOutput, report);

  process.stdout.write(`Retroactive staging bundle written: ${bundleDir}\n`);
  process.stdout.write(`Companion candidates written: ${companionCandidates.length}\n`);
  process.stdout.write(`Report written: ${resolved.reportOutput}\n`);
}

main();
