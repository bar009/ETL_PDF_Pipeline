#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");

function buildDefaults() {
  return {
    queueInput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_queue.json",
    ledgerInput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json",
    reviewPacketInput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_review_packet.json",
    ledgerOutput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json",
    artifactDir: "PDF_handle/TOOLS/data/notebooklm_stable_base_additions/artifacts",
    artifactIndexOutput: "PDF_handle/TOOLS/data/notebooklm_stable_base_additions/index.json",
    artifactReviewPacketOutput: "PDF_handle/TOOLS/data/notebooklm_stable_base_review_packet.json",
    reportOutput: "PDF_handle/TOOLS/data/notebooklm_stable_base_additions_report.json"
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

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeString(value) {
  return String(value ?? "").trim();
}

function normalizeOptionalString(value) {
  const normalized = normalizeString(value);
  return normalized ? normalized : null;
}

function slugify(value) {
  return normalizeString(value)
    .toLowerCase()
    .replace(/^[a-z0-9]+-candidate-/, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

function humanizeCandidateTopic(value) {
  const cleaned = normalizeString(value).replace(/^[a-z0-9]+-candidate-/, "");
  if (!cleaned) {
    return "Untitled promoted candidate";
  }
  return cleaned
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

function getNotebooklmCandidates(queueArtifact) {
  return ensureArray(queueArtifact?.lanes?.notebooklm_intake_candidates);
}

function buildCandidateIndex(queueArtifact) {
  const items = getNotebooklmCandidates(queueArtifact);
  return new Map(
    items.map((item) => [
      normalizeOptionalString(item?.provenance?.candidate_id) || normalizeOptionalString(item?.queue_id),
      item
    ]).filter(([key]) => Boolean(key))
  );
}

function buildLedgerIndex(ledgerArtifact) {
  return new Map(
    ensureArray(ledgerArtifact?.entries).map((entry) => [normalizeOptionalString(entry?.candidate_id), entry]).filter(([key]) => Boolean(key))
  );
}

function validateReviewDecision(entry, candidateIndex) {
  const candidateId = normalizeOptionalString(entry?.candidate_id);
  const decision = normalizeOptionalString(entry?.decision) || "pending_review";
  const reviewer = normalizeOptionalString(entry?.reviewer);
  const role = normalizeOptionalString(entry?.role) || "promotion_reviewer";
  const reason = normalizeOptionalString(entry?.reason);
  const reviewedAt = normalizeOptionalString(entry?.reviewed_at) || (decision !== "pending_review" ? new Date().toISOString() : null);
  const errors = [];

  if (!candidateId) {
    errors.push("candidate_id is required.");
  } else if (!candidateIndex.has(candidateId)) {
    errors.push(`candidate_id "${candidateId}" does not exist in the current NotebookLM queue.`);
  }

  if (!["pending_review", "promoted", "rejected", "deferred"].includes(decision)) {
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
    candidateId,
    decision,
    reviewer,
    role,
    reason,
    reviewedAt,
    proposedTargetSlug: normalizeOptionalString(entry?.proposed_target_slug),
    proposedTargetTitle: normalizeOptionalString(entry?.proposed_target_title),
    proposedTargetDegree: normalizeOptionalString(entry?.proposed_target_degree),
    additionType: normalizeOptionalString(entry?.addition_type) || "new_topic",
    baseAction: normalizeOptionalString(entry?.base_action) || "add",
    errors
  };
}

function buildUpdatedLedgerEntry(baseEntry, candidate, decisionResult) {
  const updated = {
    ...baseEntry,
    candidate_id: decisionResult.candidateId,
    candidate_topic: candidate.candidate_topic,
    source_provenance: baseEntry?.source_provenance || {
      notebook_source: candidate?.provenance?.source || "notebooklm_intake",
      notebook_packet_id: candidate?.provenance?.candidate_id || candidate?.queue_id,
      intake_location: candidate?.provenance?.intake_location || null,
      source_anchor: candidate?.source_anchor || null
    },
    degree_hint: candidate.degree_hint,
    related_existing_matches: ensureArray(candidate.catalog_matches)
  };

  if (decisionResult.decision === "pending_review") {
    updated.review_state = baseEntry?.review_state || "pending_review";
    updated.final_state = null;
    updated.final_reason = null;
    updated.gate_owner = baseEntry?.gate_owner || "queue_normalization";
    updated.reviewed_at = null;
    return updated;
  }

  updated.review_state = "reviewed";
  updated.final_state = decisionResult.decision;
  updated.final_reason = decisionResult.reason;
  updated.gate_owner = `${decisionResult.role}:${decisionResult.reviewer}`;
  updated.reviewed_at = decisionResult.reviewedAt;
  return updated;
}

function buildArtifact(candidate, ledgerEntry, decisionResult) {
  const targetTopicSlug = decisionResult.proposedTargetSlug || slugify(candidate.candidate_topic || candidate.queue_id || "promoted-topic");
  const targetTopicTitle = decisionResult.proposedTargetTitle || candidate.candidate_title_hint || humanizeCandidateTopic(candidate.candidate_topic);
  const targetDegree = decisionResult.proposedTargetDegree || candidate.degree_hint || "research";
  const artifactId = `stable-base-${decisionResult.candidateId}`;
  const sourceAnchor = isPlainObject(candidate.source_anchor) ? candidate.source_anchor : {};

  return {
    artifact_id: artifactId,
    source_ledger_entry: {
      candidate_id: ledgerEntry.candidate_id,
      final_state: ledgerEntry.final_state,
      final_reason: ledgerEntry.final_reason,
      gate_owner: ledgerEntry.gate_owner,
      reviewed_at: ledgerEntry.reviewed_at,
      related_existing_matches: ensureArray(ledgerEntry.related_existing_matches)
    },
    promotion_state: "ready_for_stable_base_review",
    candidate_snapshot: {
      candidate_topic: candidate.candidate_topic,
      candidate_title_hint: candidate.candidate_title_hint,
      degree_hint: candidate.degree_hint,
      topic_type: candidate.suggested_type || "topic",
      why_new: candidate.why_new,
      core_question: candidate.core_question,
      source_anchor: candidate.source_anchor || null,
      evidence: ensureArray(candidate.evidence),
      existing_matches: ensureArray(candidate.existing_matches),
      risk_flags: ensureArray(candidate.risk_flags)
    },
    stable_base_addition: {
      target_topic_slug: targetTopicSlug,
      target_topic_title: targetTopicTitle,
      target_degree: targetDegree,
      addition_type: decisionResult.additionType,
      base_action: decisionResult.baseAction,
      review_lane: "stable_base_review"
    },
    provenance: {
      notebook_source: candidate?.provenance?.source || "notebooklm_intake",
      notebook_packet_id: candidate?.provenance?.candidate_id || candidate?.queue_id,
      discovery_lane: "phase_m8_topic_discovery",
      promotion_ledger_id: ledgerEntry.candidate_id,
      source_book: sourceAnchor.book || null,
      source_section: sourceAnchor.section || null,
      source_location: sourceAnchor.location || null
    },
    review_status: "reviewable",
    promotion_reason: decisionResult.reason,
    approval_chain: [
      {
        actor: decisionResult.reviewer,
        role: decisionResult.role,
        decision: "approved",
        at: decisionResult.reviewedAt,
        reason: decisionResult.reason
      }
    ],
    apply_eligibility: {
      eligible: false,
      blocked_by: "stable_base_review",
      next_step: "stable_base_review"
    },
    rejection_or_deferral_context: null
  };
}

function buildArtifactIndexEntries(artifactDir, artifacts) {
  return artifacts.map((artifact) => ({
    artifact_id: artifact.artifact_id,
    candidate_id: artifact.source_ledger_entry.candidate_id,
    file_path: path.join(artifactDir, `${artifact.artifact_id}.json`),
    target_topic_slug: artifact.stable_base_addition.target_topic_slug,
    target_topic_title: artifact.stable_base_addition.target_topic_title,
    target_degree: artifact.stable_base_addition.target_degree,
    review_status: artifact.review_status,
    promotion_state: artifact.promotion_state
  }));
}

function buildArtifactReviewPacket(indexEntries) {
  return {
    meta: {
      phase: "notebooklm_stable_base_review",
      generated_at: new Date().toISOString(),
      purpose: "Review packet for approving or rejecting stable-base addition artifacts."
    },
    entries: indexEntries.map((entry) => ({
      artifact_id: entry.artifact_id,
      candidate_id: entry.candidate_id,
      target_topic_slug: entry.target_topic_slug,
      target_topic_title: entry.target_topic_title,
      target_degree: entry.target_degree,
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
  const options = { ...buildDefaults(), ...cliOptions };
  const resolved = {
    queueInput: resolveRepoPath(pickOption(options, "queue-input", "queueInput")),
    ledgerInput: resolveRepoPath(pickOption(options, "ledger-input", "ledgerInput")),
    reviewPacketInput: resolveRepoPath(pickOption(options, "review-packet-input", "reviewPacketInput")),
    ledgerOutput: resolveRepoPath(pickOption(options, "ledger-output", "ledgerOutput")),
    artifactDir: resolveRepoPath(pickOption(options, "artifact-dir", "artifactDir")),
    artifactIndexOutput: resolveRepoPath(pickOption(options, "artifact-index-output", "artifactIndexOutput")),
    artifactReviewPacketOutput: resolveRepoPath(pickOption(options, "artifact-review-packet-output", "artifactReviewPacketOutput")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput"))
  };

  const queueArtifact = readJson(resolved.queueInput);
  const ledgerArtifact = readJsonIfExists(resolved.ledgerInput, { entries: [] });
  const reviewPacket = readJsonIfExists(resolved.reviewPacketInput, { entries: [] });
  const candidateIndex = buildCandidateIndex(queueArtifact);
  const ledgerIndex = buildLedgerIndex(ledgerArtifact);
  const updatedLedgerEntries = [];
  const artifacts = [];
  const report = {
    meta: {
      phase: "notebooklm_stable_base_additions_build",
      generated_at: new Date().toISOString(),
      inputs: {
        queue_input: resolved.queueInput,
        ledger_input: resolved.ledgerInput,
        review_packet_input: resolved.reviewPacketInput
      }
    },
    summary: {
      reviewed_candidates: 0,
      promoted_candidates: 0,
      rejected_candidates: 0,
      deferred_candidates: 0,
      pending_candidates: 0,
      artifacts_written: 0,
      invalid_review_entries: 0
    },
    invalid_review_entries: []
  };

  const reviewResults = ensureArray(reviewPacket.entries).map((entry) => validateReviewDecision(entry, candidateIndex));
  const reviewMap = new Map(reviewResults.filter((result) => result.candidateId).map((result) => [result.candidateId, result]));

  for (const result of reviewResults) {
    if (result.errors.length > 0) {
      report.summary.invalid_review_entries += 1;
      report.invalid_review_entries.push({
        candidate_id: result.candidateId,
        errors: result.errors
      });
    }
  }

  for (const [candidateId, candidate] of candidateIndex.entries()) {
    const baseLedgerEntry = ledgerIndex.get(candidateId) || {};
    const decisionResult = reviewMap.get(candidateId) || {
      candidateId,
      decision: "pending_review",
      reviewer: null,
      role: "promotion_reviewer",
      reason: null,
      reviewedAt: null,
      proposedTargetSlug: null,
      proposedTargetTitle: null,
      proposedTargetDegree: null,
      additionType: "new_topic",
      baseAction: "add",
      errors: []
    };
    const updatedLedgerEntry = buildUpdatedLedgerEntry(baseLedgerEntry, candidate, decisionResult);
    updatedLedgerEntries.push(updatedLedgerEntry);

    if (decisionResult.errors.length > 0) {
      continue;
    }

    if (decisionResult.decision === "pending_review") {
      report.summary.pending_candidates += 1;
      continue;
    }

    report.summary.reviewed_candidates += 1;
    if (decisionResult.decision === "promoted") {
      artifacts.push(buildArtifact(candidate, updatedLedgerEntry, decisionResult));
      report.summary.promoted_candidates += 1;
    } else if (decisionResult.decision === "rejected") {
      report.summary.rejected_candidates += 1;
    } else if (decisionResult.decision === "deferred") {
      report.summary.deferred_candidates += 1;
    }
  }

  const updatedLedger = {
    meta: {
      ...ledgerArtifact.meta,
      generated_at: new Date().toISOString(),
      review_packet_path: resolved.reviewPacketInput
    },
    summary: {
      candidate_count: updatedLedgerEntries.length,
      promoted_count: updatedLedgerEntries.filter((entry) => entry.final_state === "promoted").length,
      rejected_count: updatedLedgerEntries.filter((entry) => entry.final_state === "rejected").length,
      deferred_count: updatedLedgerEntries.filter((entry) => entry.final_state === "deferred").length,
      pending_review_count: updatedLedgerEntries.filter((entry) => !entry.final_state).length
    },
    entries: updatedLedgerEntries
  };

  const artifactIndexEntries = buildArtifactIndexEntries(resolved.artifactDir, artifacts);
  const artifactIndex = {
    meta: {
      phase: "notebooklm_stable_base_additions",
      generated_at: new Date().toISOString(),
      source_ledger_path: resolved.ledgerOutput
    },
    entries: artifactIndexEntries
  };
  const artifactReviewPacket = buildArtifactReviewPacket(artifactIndexEntries);

  for (const artifact of artifacts) {
    writeJsonAtomic(path.join(resolved.artifactDir, `${artifact.artifact_id}.json`), artifact);
  }

  report.summary.artifacts_written = artifacts.length;

  writeJsonAtomic(resolved.ledgerOutput, updatedLedger);
  writeJsonAtomic(resolved.artifactIndexOutput, artifactIndex);
  writeJsonAtomic(resolved.artifactReviewPacketOutput, artifactReviewPacket);
  writeJsonAtomic(resolved.reportOutput, report);

  process.stdout.write(`NotebookLM ledger updated: ${resolved.ledgerOutput}\n`);
  process.stdout.write(`Stable-base artifacts written: ${artifacts.length}\n`);
  process.stdout.write(`Artifact index written: ${resolved.artifactIndexOutput}\n`);
  process.stdout.write(`Artifact review packet written: ${resolved.artifactReviewPacketOutput}\n`);
}

main();
