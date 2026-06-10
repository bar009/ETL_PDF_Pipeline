#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");

function buildDefaults() {
  return {
    proposalInput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/queue.json",
    reviewPacketInput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/review_packet.json",
    stableTopicBaseInput: "PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json",
    seedPacketOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/seed_packet.json",
    reportOutput: "PDF_handle/TOOLS/data/notebooklm_retroactive_backfill/seed_report.json"
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

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function requireExplicitIsolationFlag(options) {
  const allowed = Boolean(options["allow-isolated-backfill"] || options.allowIsolatedBackfill);
  if (allowed) {
    return;
  }

  throw new Error(
    "Retroactive backfill seed build is isolated on purpose. Re-run with --allow-isolated-backfill to confirm this non-canonical review lane."
  );
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function normalizeOptionalString(value) {
  const normalized = normalizeString(value);
  return normalized ? normalized : null;
}

function tokenizeKeywords(...values) {
  return Array.from(
    new Set(
      values
        .flatMap((value) =>
          normalizeString(value)
            .toLowerCase()
            .replace(/[^a-z0-9\u0590-\u05ff\s]+/gi, " ")
            .split(/\s+/)
        )
        .filter((token) => token && token.length >= 4)
    )
  ).slice(0, 12);
}

function buildReviewDecision(entry) {
  const proposalId = normalizeOptionalString(entry?.proposal_id);
  const decision = normalizeOptionalString(entry?.decision) || "pending_review";
  const reviewer = normalizeOptionalString(entry?.reviewer);
  const role = normalizeOptionalString(entry?.role) || "retro_backfill_reviewer";
  const reason = normalizeOptionalString(entry?.reason);
  const reviewedAt = normalizeOptionalString(entry?.reviewed_at) || (decision !== "pending_review" ? new Date().toISOString() : null);
  const errors = [];

  if (!proposalId) {
    errors.push("proposal_id is required.");
  }
  if (!["pending_review", "approved", "deferred", "rejected"].includes(decision)) {
    errors.push(`decision "${decision}" is not supported.`);
  }
  if (decision !== "pending_review") {
    if (!reviewer) {
      errors.push(`reviewer is required when decision is "${decision}".`);
    }
    if (!reason) {
      errors.push(`reason is required when decision is "${decision}".`);
    }
  }

  return { proposalId, decision, reviewer, role, reason, reviewedAt, errors };
}

function buildSeedEntry(proposal, stableBaseEntry, decision) {
  const bestMatch = ensureArray(proposal.candidate_matches)[0] || null;
  const candidateSnapshot = stableBaseEntry?.candidate_snapshot || {};
  const baseSummary = proposal.stable_base_summary || {};

  return {
    seed_id: `retro-seed-${proposal.target_topic_slug}`,
    proposal_id: proposal.proposal_id,
    stable_base_id: proposal.stable_base_id,
    recommended_action: proposal.recommended_action,
    target_dataset: proposal.target_dataset,
    target_topic_slug: proposal.target_topic_slug,
    target_topic_title: proposal.target_topic_title,
    target_degree: proposal.target_degree,
    mutation_mode:
      proposal.recommended_action === "expand_existing_entry"
        ? "enrich_existing_entry"
        : proposal.recommended_action === "attach_companion_relation_candidate"
          ? "relation_candidate"
          : "new_entry_seed",
    source_candidate_id: proposal.source_candidate_id,
    provenance: proposal.provenance,
    approval: {
      reviewer: decision.reviewer,
      role: decision.role,
      reason: decision.reason,
      reviewed_at: decision.reviewedAt
    },
    best_existing_match: bestMatch
      ? {
          dataset_id: bestMatch.dataset_id,
          slug: bestMatch.slug,
          title: bestMatch.title,
          score: bestMatch.score
        }
      : null,
    seed_payload: {
      title: proposal.target_topic_title,
      slug: proposal.target_topic_slug,
      degree: proposal.target_degree,
      keywords: tokenizeKeywords(
        proposal.target_topic_title,
        baseSummary.candidate_title_hint,
        baseSummary.candidate_topic
      ),
      short_summary: baseSummary.why_new || "",
      candidate_lesson: baseSummary.core_question || "",
      source_notes: [
        `NotebookLM stable-base provenance: ${proposal.provenance?.source_book || "unknown source"} / ${proposal.provenance?.source_section || "unknown section"}`,
        `Retroactive backfill rationale: ${proposal.rationale}`
      ],
      supporting_evidence: ensureArray(candidateSnapshot.evidence).slice(0, 3),
      relation_target_slug:
        proposal.recommended_action === "attach_companion_relation_candidate" && bestMatch
          ? bestMatch.slug
          : null,
      enrich_target_slug:
        proposal.recommended_action === "expand_existing_entry" && bestMatch
          ? bestMatch.slug
          : null
    }
  };
}

function main() {
  const cliOptions = parseArgs(process.argv.slice(2));
  requireExplicitIsolationFlag(cliOptions);
  const options = { ...buildDefaults(), ...cliOptions };
  const resolved = {
    proposalInput: resolveRepoPath(pickOption(options, "proposal-input", "proposalInput")),
    reviewPacketInput: resolveRepoPath(pickOption(options, "review-packet-input", "reviewPacketInput")),
    stableTopicBaseInput: resolveRepoPath(pickOption(options, "stable-topic-base-input", "stableTopicBaseInput")),
    seedPacketOutput: resolveRepoPath(pickOption(options, "seed-packet-output", "seedPacketOutput")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput"))
  };

  const proposalArtifact = readJson(resolved.proposalInput);
  const reviewPacket = readJsonIfExists(resolved.reviewPacketInput, { entries: [] });
  const stableBase = readJsonIfExists(resolved.stableTopicBaseInput, { entries: [] });
  const proposalIndex = new Map(ensureArray(proposalArtifact.proposals).map((item) => [item.proposal_id, item]));
  const stableBaseIndex = new Map(ensureArray(stableBase.entries).map((item) => [item.stable_base_id, item]));

  const decisions = ensureArray(reviewPacket.entries).map((entry) => buildReviewDecision(entry));
  const seeds = [];
  const report = {
    meta: {
      phase: "notebooklm_retroactive_backfill_seed_build",
      generated_at: new Date().toISOString(),
      inputs: {
        proposal_input: resolved.proposalInput,
        review_packet_input: resolved.reviewPacketInput,
        stable_topic_base_input: resolved.stableTopicBaseInput
      }
    },
    summary: {
      proposal_count: ensureArray(proposalArtifact.proposals).length,
      approved_count: 0,
      deferred_count: 0,
      rejected_count: 0,
      pending_count: 0,
      invalid_review_entries: 0,
      seed_count: 0
    },
    invalid_review_entries: []
  };

  for (const decision of decisions) {
    const proposal = proposalIndex.get(decision.proposalId);
    if (!proposal) {
      report.summary.invalid_review_entries += 1;
      report.invalid_review_entries.push({
        proposal_id: decision.proposalId,
        errors: ["proposal_id does not exist in the current retroactive backfill queue."]
      });
      continue;
    }
    if (decision.errors.length > 0) {
      report.summary.invalid_review_entries += 1;
      report.invalid_review_entries.push({
        proposal_id: decision.proposalId,
        errors: decision.errors
      });
      continue;
    }

    if (decision.decision === "pending_review") {
      report.summary.pending_count += 1;
      continue;
    }
    if (decision.decision === "deferred") {
      report.summary.deferred_count += 1;
      continue;
    }
    if (decision.decision === "rejected") {
      report.summary.rejected_count += 1;
      continue;
    }

    const stableBaseEntry = stableBaseIndex.get(proposal.stable_base_id);
    seeds.push(buildSeedEntry(proposal, stableBaseEntry, decision));
    report.summary.approved_count += 1;
  }

  report.summary.seed_count = seeds.length;

  const seedPacket = {
    meta: {
      phase: "notebooklm_retroactive_backfill_seed_packet",
      generated_at: new Date().toISOString(),
      purpose: "Approved retroactive backfill seeds derived from stable-base proposals; still reviewable and not auto-applied."
    },
    entries: seeds
  };

  writeJsonAtomic(resolved.seedPacketOutput, seedPacket);
  writeJsonAtomic(resolved.reportOutput, report);

  process.stdout.write(`Retroactive backfill seed packet written: ${resolved.seedPacketOutput}\n`);
  process.stdout.write(`Approved seeds built: ${seeds.length}\n`);
}

main();
