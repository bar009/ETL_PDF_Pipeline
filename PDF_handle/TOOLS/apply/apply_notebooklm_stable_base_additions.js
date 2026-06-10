#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");

function buildDefaults() {
  return {
    artifactIndexInput: "PDF_handle/TOOLS/data/notebooklm_stable_base_additions/index.json",
    artifactReviewPacketInput: "PDF_handle/TOOLS/data/notebooklm_stable_base_review_packet.json",
    stableTopicBaseOutput: "PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json",
    reportOutput: "PDF_handle/TOOLS/data/notebooklm_stable_base_apply_report.json"
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

function normalizeOptionalString(value) {
  const normalized = normalizeString(value);
  return normalized ? normalized : null;
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function validateArtifactDecision(entry, artifactIndex) {
  const artifactId = normalizeOptionalString(entry?.artifact_id);
  const decision = normalizeOptionalString(entry?.decision) || "pending_review";
  const reviewer = normalizeOptionalString(entry?.reviewer);
  const role = normalizeOptionalString(entry?.role) || "stable_base_reviewer";
  const reason = normalizeOptionalString(entry?.reason);
  const reviewedAt = normalizeOptionalString(entry?.reviewed_at) || (decision !== "pending_review" ? new Date().toISOString() : null);
  const errors = [];

  if (!artifactId) {
    errors.push("artifact_id is required.");
  } else if (!artifactIndex.has(artifactId)) {
    errors.push(`artifact_id "${artifactId}" does not exist in the artifact index.`);
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

  return {
    artifactId,
    decision,
    reviewer,
    role,
    reason,
    reviewedAt,
    errors
  };
}

function createStableBaseEntry(artifact, reviewedAt) {
  return {
    stable_base_id: artifact.artifact_id,
    artifact_id: artifact.artifact_id,
    source_candidate_id: artifact.source_ledger_entry.candidate_id,
    candidate_topic: artifact.candidate_snapshot.candidate_topic,
    target_topic_slug: artifact.stable_base_addition.target_topic_slug,
    target_topic_title: artifact.stable_base_addition.target_topic_title,
    target_degree: artifact.stable_base_addition.target_degree,
    addition_type: artifact.stable_base_addition.addition_type,
    base_action: artifact.stable_base_addition.base_action,
    review_lane: artifact.stable_base_addition.review_lane,
    promotion_reason: artifact.promotion_reason,
    provenance: artifact.provenance,
    approval_chain: artifact.approval_chain,
    review_status: artifact.review_status,
    candidate_snapshot: artifact.candidate_snapshot,
    source_ledger_entry: artifact.source_ledger_entry,
    aliases: ensureArray(artifact.source_ledger_entry.related_existing_matches).map((item) => item.title || item.slug).filter(Boolean),
    applied_at: reviewedAt
  };
}

function main() {
  const cliOptions = parseArgs(process.argv.slice(2));
  const options = { ...buildDefaults(), ...cliOptions };
  const resolved = {
    artifactIndexInput: resolveRepoPath(pickOption(options, "artifact-index-input", "artifactIndexInput")),
    artifactReviewPacketInput: resolveRepoPath(pickOption(options, "artifact-review-packet-input", "artifactReviewPacketInput")),
    stableTopicBaseOutput: resolveRepoPath(pickOption(options, "stable-topic-base-output", "stableTopicBaseOutput")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput"))
  };

  const artifactIndexArtifact = readJson(resolved.artifactIndexInput);
  const artifactReviewPacket = readJsonIfExists(resolved.artifactReviewPacketInput, { entries: [] });
  const stableBaseArtifact = readJsonIfExists(resolved.stableTopicBaseOutput, {
    meta: {
      purpose: "Reusable stable topic base built from reviewed NotebookLM promotion artifacts."
    },
    entries: []
  });

  const artifactIndex = new Map(
    ensureArray(artifactIndexArtifact.entries).map((entry) => [normalizeOptionalString(entry?.artifact_id), entry]).filter(([key]) => Boolean(key))
  );
  const artifactDecisions = ensureArray(artifactReviewPacket.entries).map((entry) => validateArtifactDecision(entry, artifactIndex));
  const report = {
    meta: {
      phase: "notebooklm_stable_base_apply",
      generated_at: new Date().toISOString(),
      inputs: {
        artifact_index_input: resolved.artifactIndexInput,
        artifact_review_packet_input: resolved.artifactReviewPacketInput
      }
    },
    summary: {
      approved: 0,
      rejected: 0,
      deferred: 0,
      pending_review: 0,
      applied: 0,
      skipped_conflicts: 0,
      invalid_review_entries: 0
    },
    invalid_review_entries: [],
    conflicts: []
  };
  const existingEntries = ensureArray(stableBaseArtifact.entries);
  const stableBaseById = new Map(existingEntries.map((entry) => [entry.artifact_id, entry]));
  const stableBaseBySlug = new Map(existingEntries.map((entry) => [entry.target_topic_slug, entry]));

  for (const decision of artifactDecisions) {
    if (decision.errors.length > 0) {
      report.summary.invalid_review_entries += 1;
      report.invalid_review_entries.push({
        artifact_id: decision.artifactId,
        errors: decision.errors
      });
      continue;
    }

    if (decision.decision === "pending_review") {
      report.summary.pending_review += 1;
      continue;
    }

    const artifactIndexEntry = artifactIndex.get(decision.artifactId);
    const artifactPath = artifactIndexEntry.file_path;
    const artifact = readJson(artifactPath);
    artifact.approval_chain = ensureArray(artifact.approval_chain);
    artifact.approval_chain.push({
      actor: decision.reviewer,
      role: decision.role,
      decision:
        decision.decision === "approved"
          ? "approved"
          : decision.decision === "deferred"
            ? "deferred"
            : "rejected",
      at: decision.reviewedAt,
      reason: decision.reason
    });

    if (decision.decision === "approved") {
      const slug = artifact.stable_base_addition.target_topic_slug;
      const conflictingEntry = stableBaseBySlug.get(slug);
      if (conflictingEntry && conflictingEntry.artifact_id !== artifact.artifact_id) {
        report.summary.skipped_conflicts += 1;
        report.conflicts.push({
          artifact_id: artifact.artifact_id,
          target_topic_slug: slug,
          conflicting_artifact_id: conflictingEntry.artifact_id
        });
        artifact.review_status = "deferred";
        artifact.promotion_state = "deferred_before_addition";
        artifact.apply_eligibility = {
          eligible: false,
          blocked_by: "slug_conflict",
          next_step: "manual_review"
        };
        artifact.rejection_or_deferral_context = {
          kind: "deferral",
          reason: `Slug conflict with existing stable-base entry ${conflictingEntry.artifact_id}.`,
          owner: decision.reviewer,
          at: decision.reviewedAt
        };
        writeJsonAtomic(artifactPath, artifact);
        continue;
      }

      artifact.review_status = "approved";
      artifact.promotion_state = "approved_for_stable_base_addition";
      artifact.apply_eligibility = {
        eligible: true,
        blocked_by: null,
        next_step: "applied_to_stable_topic_base"
      };
      artifact.rejection_or_deferral_context = null;

      const stableBaseEntry = createStableBaseEntry(artifact, decision.reviewedAt);
      stableBaseById.set(artifact.artifact_id, stableBaseEntry);
      stableBaseBySlug.set(stableBaseEntry.target_topic_slug, stableBaseEntry);
      report.summary.approved += 1;
      report.summary.applied += 1;
    } else if (decision.decision === "deferred") {
      artifact.review_status = "deferred";
      artifact.promotion_state = "deferred_before_addition";
      artifact.apply_eligibility = {
        eligible: false,
        blocked_by: "stable_base_review",
        next_step: "manual_review"
      };
      artifact.rejection_or_deferral_context = {
        kind: "deferral",
        reason: decision.reason,
        owner: decision.reviewer,
        at: decision.reviewedAt
      };
      report.summary.deferred += 1;
    } else if (decision.decision === "rejected") {
      artifact.review_status = "rejected";
      artifact.promotion_state = "rejected_before_addition";
      artifact.apply_eligibility = {
        eligible: false,
        blocked_by: "rejected_in_stable_base_review",
        next_step: "none"
      };
      artifact.rejection_or_deferral_context = {
        kind: "rejection",
        reason: decision.reason,
        owner: decision.reviewer,
        at: decision.reviewedAt
      };
      report.summary.rejected += 1;
    }

    artifactIndexEntry.review_status = artifact.review_status;
    artifactIndexEntry.promotion_state = artifact.promotion_state;
    writeJsonAtomic(artifactPath, artifact);
  }

  const nextStableBase = {
    meta: {
      ...stableBaseArtifact.meta,
      generated_at: new Date().toISOString(),
      purpose: "Reusable stable topic base built from reviewed NotebookLM promotion artifacts."
    },
    entries: Array.from(stableBaseById.values()).sort((left, right) => left.target_topic_slug.localeCompare(right.target_topic_slug))
  };

  writeJsonAtomic(resolved.stableTopicBaseOutput, nextStableBase);
  writeJsonAtomic(resolved.artifactIndexInput, artifactIndexArtifact);
  writeJsonAtomic(resolved.reportOutput, report);

  process.stdout.write(`Stable topic base written: ${resolved.stableTopicBaseOutput}\n`);
  process.stdout.write(`Approved additions applied: ${report.summary.applied}\n`);
  process.stdout.write(`Conflicts skipped: ${report.summary.skipped_conflicts}\n`);
}

main();
