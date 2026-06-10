#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot } = require("../lib/site_roots");

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const DEFAULT_SITE_ROOT = getWorkSiteRoot();
const STOPWORDS = new Set([
  "the",
  "and",
  "of",
  "for",
  "with",
  "from",
  "into",
  "meaning",
  "origin",
  "two",
  "a",
  "an"
]);

function buildDefaults(siteRoot) {
  return {
    siteRoot,
    library: path.join(siteRoot, "data", "library.json"),
    level1: path.join(siteRoot, "data", "level1.json"),
    level2: path.join(siteRoot, "data", "level2.json"),
    level3: path.join(siteRoot, "data", "level3.json"),
    stableTopicBaseInput: "PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json",
    proposalOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/queue.json",
    reviewPacketOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/review_packet.json",
    reportOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/report.json"
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
  return path.isAbsolute(targetPath) ? targetPath : path.resolve(repoRoot, targetPath);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readJsonIfExists(filePath, fallbackValue) {
  if (!filePath || !fs.existsSync(filePath)) {
    return fallbackValue;
  }
  return readJson(filePath);
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function normalizeText(value) {
  return normalizeString(value)
    .toLowerCase()
    .replace(/[^a-z0-9\u0590-\u05ff\s]+/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenize(value) {
  return Array.from(
    new Set(
      normalizeText(value)
        .split(" ")
        .filter((token) => token && token.length >= 3 && !STOPWORDS.has(token))
    )
  );
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function requireExplicitIsolationFlag(options) {
  const allowed = Boolean(options["allow-isolated-backfill"] || options.allowIsolatedBackfill);
  if (allowed) {
    return;
  }

  throw new Error(
    "Retroactive backfill lane is isolated on purpose. Re-run with --allow-isolated-backfill to confirm this non-canonical review lane."
  );
}

function stableBaseText(entry) {
  return [
    entry.target_topic_title,
    entry.candidate_topic,
    ensureArray(entry.aliases).join(" "),
    entry.candidate_snapshot?.candidate_title_hint,
    entry.candidate_snapshot?.why_new,
    entry.candidate_snapshot?.core_question,
    ensureArray(entry.candidate_snapshot?.evidence).map((item) => item.detail).join(" ")
  ].join(" ");
}

function siteEntryText(entry) {
  return [
    entry.slug,
    entry.title,
    entry.short_summary,
    entry.full_summary,
    entry.source_heading,
    entry.work_title,
    ensureArray(entry.keywords).join(" "),
    ensureArray(entry.aliases).join(" "),
    ensureArray(entry.source_notes).join(" ")
  ].join(" ");
}

function getDatasetEntries(filePath, datasetId) {
  const payload = readJsonIfExists(filePath, { entries: [] });
  return ensureArray(payload.entries).map((entry) => ({
    dataset_id: datasetId,
    entry
  }));
}

function scoreMatch(stableEntry, siteRecord) {
  const stableTokens = tokenize(stableBaseText(stableEntry));
  const siteText = normalizeText(siteEntryText(siteRecord.entry));
  const siteTokens = new Set(tokenize(siteText));
  if (stableTokens.length === 0 || siteTokens.size === 0) {
    return null;
  }

  let tokenHits = 0;
  for (const token of stableTokens) {
    if (siteTokens.has(token)) {
      tokenHits += 1;
    }
  }

  const titleExact = normalizeText(stableEntry.target_topic_title) === normalizeText(siteRecord.entry.title);
  const slugExact = normalizeText(stableEntry.target_topic_slug) === normalizeText(siteRecord.entry.slug);
  const sourceBookMatch =
    normalizeText(stableEntry.provenance?.source_book) &&
    normalizeText(stableEntry.provenance?.source_book) === normalizeText(siteRecord.entry.work_title);
  const ratio = tokenHits / stableTokens.length;
  const score =
    ratio
    + (titleExact ? 0.8 : 0)
    + (slugExact ? 0.8 : 0)
    + (sourceBookMatch ? 0.15 : 0)
    + (siteRecord.dataset_id === stableEntry.target_degree ? 0.1 : 0);

  return {
    dataset_id: siteRecord.dataset_id,
    slug: siteRecord.entry.slug,
    title: siteRecord.entry.title,
    degree: siteRecord.entry.degree || siteRecord.dataset_id,
    status: siteRecord.entry.status || null,
    overlap_ratio: Number(ratio.toFixed(3)),
    score: Number(score.toFixed(3)),
    title_exact: titleExact,
    slug_exact: slugExact,
    source_book_match: Boolean(sourceBookMatch)
  };
}

function classifyProposal(stableEntry, topMatches, availableDatasets) {
  const targetDataset = stableEntry.target_degree;
  const exactMatch = topMatches.find((item) => item.title_exact || item.slug_exact);
  if (exactMatch) {
    return {
      coverage_status: "already_present",
      recommended_action: "skip_existing_coverage",
      rationale: `Exact coverage already exists in ${exactMatch.dataset_id} as ${exactMatch.slug}.`,
      blocked_by: []
    };
  }

  if (!availableDatasets.has(targetDataset)) {
    return {
      coverage_status: "blocked_missing_dataset",
      recommended_action: "defer_until_target_dataset_exists",
      rationale: `Target dataset ${targetDataset} is missing at the selected site root.`,
      blocked_by: ["missing_target_dataset"]
    };
  }

  const sameDegreeMatch = topMatches.find((item) => item.dataset_id === targetDataset);
  if (sameDegreeMatch && sameDegreeMatch.score >= 0.58) {
    return {
      coverage_status: "existing_entry_needs_enrichment",
      recommended_action: "expand_existing_entry",
      rationale: `Strong same-degree overlap suggests enriching ${sameDegreeMatch.slug} instead of opening a separate topic immediately.`,
      blocked_by: []
    };
  }

  if (sameDegreeMatch && sameDegreeMatch.score >= 0.32) {
    return {
      coverage_status: "adjacent_existing_entry",
      recommended_action: "attach_companion_relation_candidate",
      rationale: `Moderate same-degree overlap suggests a relation-first backfill proposal linked to ${sameDegreeMatch.slug}.`,
      blocked_by: []
    };
  }

  return {
    coverage_status: "new_backfill_seed",
    recommended_action: "seed_new_entry_from_stable_base",
    rationale: "No strong same-degree coverage exists yet, so this topic should enter retroactive backfill as a new staged seed.",
    blocked_by: []
  };
}

function buildProposal(stableEntry, allSiteRecords, availableDatasets) {
  const matches = allSiteRecords
    .map((siteRecord) => scoreMatch(stableEntry, siteRecord))
    .filter(Boolean)
    .sort((left, right) => right.score - left.score || left.slug.localeCompare(right.slug))
    .slice(0, 5);

  const classification = classifyProposal(stableEntry, matches, availableDatasets);
  return {
    proposal_id: `retro-backfill-${stableEntry.target_topic_slug}`,
    stable_base_id: stableEntry.stable_base_id,
    artifact_id: stableEntry.artifact_id,
    target_topic_slug: stableEntry.target_topic_slug,
    target_topic_title: stableEntry.target_topic_title,
    target_degree: stableEntry.target_degree,
    source_candidate_id: stableEntry.source_candidate_id,
    coverage_status: classification.coverage_status,
    recommended_action: classification.recommended_action,
    target_dataset: stableEntry.target_degree,
    rationale: classification.rationale,
    blocked_by: classification.blocked_by,
    provenance: stableEntry.provenance || {},
    stable_base_summary: {
      candidate_topic: stableEntry.candidate_topic,
      candidate_title_hint: stableEntry.candidate_snapshot?.candidate_title_hint || null,
      why_new: stableEntry.candidate_snapshot?.why_new || null,
      core_question: stableEntry.candidate_snapshot?.core_question || null
    },
    candidate_matches: matches
  };
}

function buildReviewPacket(proposals) {
  return {
    meta: {
      phase: "notebooklm_retroactive_backfill_review",
      generated_at: new Date().toISOString(),
      purpose: "Operator review packet for retroactive backfill proposals derived from the stable topic base."
    },
    entries: proposals.map((proposal) => ({
      proposal_id: proposal.proposal_id,
      stable_base_id: proposal.stable_base_id,
      target_topic_slug: proposal.target_topic_slug,
      target_topic_title: proposal.target_topic_title,
      target_degree: proposal.target_degree,
      recommended_action: proposal.recommended_action,
      decision: "pending_review",
      reviewer: null,
      role: null,
      reason: null,
      reviewed_at: null
    }))
  };
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
    stableTopicBaseInput: resolveRepoPath(pickOption(options, "stable-topic-base-input", "stableTopicBaseInput")),
    proposalOutput: resolveRepoPath(pickOption(options, "proposal-output", "proposalOutput")),
    reviewPacketOutput: resolveRepoPath(pickOption(options, "review-packet-output", "reviewPacketOutput")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput"))
  };

  const stableBase = readJsonIfExists(resolved.stableTopicBaseInput, { entries: [] });
  const allSiteRecords = [
    ...getDatasetEntries(resolved.library, "library"),
    ...getDatasetEntries(resolved.level1, "level1"),
    ...getDatasetEntries(resolved.level2, "level2"),
    ...getDatasetEntries(resolved.level3, "level3")
  ];
  const availableDatasets = new Set(
    [
      ["library", resolved.library],
      ["level1", resolved.level1],
      ["level2", resolved.level2],
      ["level3", resolved.level3]
    ]
      .filter(([, filePath]) => filePath && fs.existsSync(filePath))
      .map(([datasetId]) => datasetId)
  );

  const proposals = ensureArray(stableBase.entries).map((entry) => buildProposal(entry, allSiteRecords, availableDatasets));
  const reviewPacket = buildReviewPacket(proposals);
  const report = {
    meta: {
      phase: "notebooklm_retroactive_backfill_queue",
      generated_at: new Date().toISOString(),
      site_root: resolved.siteRoot,
      stable_topic_base_input: resolved.stableTopicBaseInput
    },
    summary: {
      stable_base_entry_count: ensureArray(stableBase.entries).length,
      proposal_count: proposals.length,
      already_present_count: proposals.filter((item) => item.coverage_status === "already_present").length,
      enrichment_candidate_count: proposals.filter((item) => item.recommended_action === "expand_existing_entry").length,
      relation_candidate_count: proposals.filter((item) => item.recommended_action === "attach_companion_relation_candidate").length,
      new_seed_count: proposals.filter((item) => item.recommended_action === "seed_new_entry_from_stable_base").length,
      blocked_count: proposals.filter((item) => item.coverage_status === "blocked_missing_dataset").length
    },
    top_priority: proposals
      .filter((item) => item.coverage_status !== "already_present" && item.coverage_status !== "blocked_missing_dataset")
      .slice(0, 5)
      .map((item) => ({
        proposal_id: item.proposal_id,
        recommended_action: item.recommended_action,
        target_topic_title: item.target_topic_title
      }))
  };

  writeJsonAtomic(resolved.proposalOutput, {
    meta: {
      phase: "notebooklm_retroactive_backfill_queue",
      generated_at: new Date().toISOString(),
      inputs: {
        site_root: resolved.siteRoot,
        stable_topic_base_input: resolved.stableTopicBaseInput,
        library_path: resolved.library,
        level1_path: resolved.level1,
        level2_path: resolved.level2,
        level3_path: resolved.level3
      }
    },
    proposals
  });
  writeJsonAtomic(resolved.reviewPacketOutput, reviewPacket);
  writeJsonAtomic(resolved.reportOutput, report);

  process.stdout.write(`Retroactive backfill queue written: ${resolved.proposalOutput}\n`);
  process.stdout.write(`Retroactive backfill review packet written: ${resolved.reviewPacketOutput}\n`);
  process.stdout.write(`Retroactive backfill report written: ${resolved.reportOutput}\n`);
  process.stdout.write(`Stable base entries analyzed: ${ensureArray(stableBase.entries).length}\n`);
  process.stdout.write(`Backfill proposals created: ${proposals.length}\n`);
}

main();
