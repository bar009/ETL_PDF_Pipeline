#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot } = require("../lib/site_roots");

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const DEFAULT_DISCOVERY_SITE_ROOT = getWorkSiteRoot();

function buildDefaults(siteRoot) {
  return {
  siteRoot,
  level1: path.join(siteRoot, "data", "level1.json"),
  level2: path.join(siteRoot, "data", "level2.json"),
  library: path.join(siteRoot, "data", "library.json"),
  level2Candidates: "PDF_handle/TOOLS/data/level2_topic_candidates.json",
  level2Frames: "PDF_handle/TOOLS/data/phase_m_4_topic_frames.json",
  futureEntryRoot: "PDF_handle/preservation/future_entries",
  notebooklmIntake: "experiments/notebooklm_validation/discovery_mindmap_intake.json",
  stableTopicBase: "PDF_handle/TOOLS/data/notebooklm_stable_topic_base.json",
  queueOutput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_queue.json",
  reportOutput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_report.json",
  ledgerOutput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_ledger.json",
  reviewPacketOutput: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_review_packet.json"
  };
}

const level3ThemeSpecs = [
  {
    candidate_topic: "level3-candidate-hiram-loss-and-fidelity-system",
    candidate_title_hint: "System cluster: Hiram / loss / fidelity / the broken word",
    suggested_type: "system",
    category_hint: "symbolic_systems",
    core_question: "How do Hiram, loss, and fidelity form a native Level 3 system rather than a loose legend recap?",
    why_new:
      "This is the clearest native Master Mason cluster in the current library, and it should become one of the first Level 3 boundary anchors.",
    requiredSignals: [["hiram"], ["master_mason", "third_degree", "sublime_degree"]],
    signals: [
      { label: "hiram", pattern: /\bhiram\b/i, weight: 4 },
      { label: "master_mason", pattern: /master mason/i, weight: 3 },
      { label: "third_degree", pattern: /third degree/i, weight: 3 },
      { label: "lost_word", pattern: /lost word/i, weight: 3 },
      { label: "fidelity", pattern: /fidelity/i, weight: 2 },
      { label: "sublime_degree", pattern: /sublime degree/i, weight: 2 }
    ]
  },
  {
    candidate_topic: "level3-candidate-raising-and-restoration-process",
    candidate_title_hint: "Process cluster: raising / restoration / completion",
    suggested_type: "process",
    category_hint: "ritual_dynamics",
    core_question: "How does raising operate as a process of restoration and completion in the third degree?",
    why_new:
      "The library already contains enough Master Mason and raising language to define a native Level 3 process lane before writing any canonical entries.",
    requiredSignals: [["raising", "raised"], ["master_mason", "third_degree", "sublime_degree"]],
    signals: [
      { label: "raising", pattern: /\braising\b/i, weight: 4 },
      { label: "raised", pattern: /\braised\b/i, weight: 3 },
      { label: "restoration", pattern: /restoration|restore|recovery/i, weight: 2 },
      { label: "completion", pattern: /completion|complete/i, weight: 2 },
      { label: "master_mason", pattern: /master mason/i, weight: 3 },
      { label: "third_degree", pattern: /third degree/i, weight: 3 },
      { label: "sublime_degree", pattern: /sublime degree/i, weight: 2 }
    ]
  },
  {
    candidate_topic: "level3-candidate-acacia-grave-and-immortality-relationship",
    candidate_title_hint: "Relationship cluster: acacia / grave / burial / immortality",
    suggested_type: "relationship",
    category_hint: "relationships_between_symbols",
    core_question: "How do acacia, grave, and burial motifs define each other inside a native Level 3 relationship frame?",
    why_new:
      "The acacia-grave-burial motif is a stable degree-3 symbol relationship and gives Level 3 a cleaner anchor than vague 'higher degree' material.",
    requiredSignals: [["acacia", "sprig"], ["grave", "burial"]],
    signals: [
      { label: "acacia", pattern: /\bacacia\b/i, weight: 4 },
      { label: "sprig", pattern: /\bsprig\b/i, weight: 3 },
      { label: "grave", pattern: /\bgrave\b/i, weight: 4 },
      { label: "burial", pattern: /\bburial\b/i, weight: 3 },
      { label: "immortality", pattern: /immortality|resurrection|life everlasting/i, weight: 2 },
      { label: "master_mason", pattern: /master mason/i, weight: 2 }
    ]
  }
];

const nativeLevel3MetadataAnchorPattern = /master mason|third degree|raising|sublime degree|tracing boards|grave|burial/i;
const NOTEBOOKLM_ALLOWED_DEGREE_HINTS = new Set(["level1", "level2", "level3", "research", "unknown"]);
const NOTEBOOKLM_ALLOWED_PRIORITY = new Set(["high", "medium", "low", "info"]);
const NOTEBOOKLM_ALLOWED_READINESS = new Set([
  "ready_for_triage",
  "needs_manual_triage",
  "needs_more_evidence",
  "defer"
]);
const NOTEBOOKLM_ALLOWED_NEXT_GATES = new Set([
  "dedupe_before_frame",
  "evidence_review",
  "degree_review",
  "human_approval",
  "defer_for_later"
]);
const NOTEBOOKLM_ALLOWED_CONFIDENCE = new Set(["high", "medium", "low"]);
const NOTEBOOKLM_ALLOWED_TOPIC_TYPES = new Set(["topic", "subtopic", "bridge", "question", "motif", "practice", "review"]);
const NOTEBOOKLM_ALLOWED_RISK_FLAGS = new Set([
  "too_broad",
  "duplicate_risk",
  "degree_ambiguous",
  "weak_evidence",
  "cross_degree_leakage",
  "needs_human_review"
]);
const NOTEBOOKLM_ALLOWED_RELATIONSHIPS = new Set([
  "same_topic",
  "near_duplicate",
  "broader_parent",
  "narrower_child",
  "related",
  "no_match"
]);
const NOTEBOOKLM_ALLOWED_EVIDENCE_KINDS = new Set([
  "quote",
  "summary",
  "recurrence",
  "cross_reference",
  "title_match",
  "section_match"
]);

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

function addUnique(target, value) {
  if (!target.includes(value)) {
    target.push(value);
  }
}

function createNotebooklmIntakeArtifact({ queueId, candidateTopic, reason, sourceAnchor, validationErrors, validationWarnings }) {
  return {
    queue_id: queueId,
    lane: "research",
    candidate_family: "notebooklm_mindmap",
    candidate_topic: candidateTopic,
    candidate_title_hint: candidateTopic,
    degree_hint: "unknown",
    category_hint: null,
    suggested_type: "review",
    priority: "info",
    readiness: "rejected_invalid_intake",
    is_actionable: false,
    next_gate: "fix_intake_then_resubmit",
    confidence: "low",
    why_new: reason,
    core_question: "What needs to be corrected in the NotebookLM intake packet before it can be reviewed?",
    source_anchor: sourceAnchor,
    provenance: {
      source: "notebooklm_intake",
      intake_location: sourceAnchor.location,
      source_book: sourceAnchor.book,
      source_section: sourceAnchor.section
    },
    evidence: [
      {
        kind: "summary",
        detail: reason,
        location: sourceAnchor.location
      }
    ],
    existing_matches: [],
    risk_flags: ["needs_human_review"],
    queue_status: "rejected_invalid_intake",
    queue_reason: reason,
    queue_ready: false,
    validation_status: "invalid",
    validation_errors: validationErrors,
    validation_warnings: validationWarnings
  };
}

function normalizeContractEnum(value, allowedValues, fallback, warnings, fieldName) {
  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    return fallback;
  }
  if (allowedValues.has(normalized)) {
    return normalized;
  }
  addUnique(warnings, `${fieldName} "${normalized}" is not supported; downgraded to "${fallback}".`);
  return fallback;
}

function validateSourceAnchor(candidate, errors, warnings) {
  const sourceAnchor = isPlainObject(candidate.source_anchor) ? candidate.source_anchor : null;
  const normalized = {
    book: normalizeOptionalString(sourceAnchor?.book),
    section: normalizeOptionalString(sourceAnchor?.section),
    quote: normalizeOptionalString(sourceAnchor?.quote),
    location: normalizeOptionalString(sourceAnchor?.location)
  };

  if (!sourceAnchor) {
    errors.push("source_anchor must be an object with book, section, quote, and location.");
  }

  for (const field of ["book", "section", "quote", "location"]) {
    if (!normalized[field]) {
      errors.push(`source_anchor.${field} is required.`);
    }
  }

  if (normalized.quote && normalized.quote.length > 240) {
    addUnique(warnings, "source_anchor.quote is long; keep it short enough for review.");
  }

  return normalized;
}

function validateEvidence(candidate, errors, warnings) {
  if (!Array.isArray(candidate.evidence) || candidate.evidence.length === 0) {
    errors.push("evidence must be a non-empty array.");
    return [];
  }

  return candidate.evidence.map((item, index) => {
    if (!isPlainObject(item)) {
      errors.push(`evidence[${index}] must be an object.`);
      return null;
    }

    const kind = normalizeOptionalString(item.kind);
    const detail = normalizeOptionalString(item.detail);
    const location = normalizeOptionalString(item.location);

    if (!kind || !NOTEBOOKLM_ALLOWED_EVIDENCE_KINDS.has(kind)) {
      errors.push(`evidence[${index}].kind must be one of: ${Array.from(NOTEBOOKLM_ALLOWED_EVIDENCE_KINDS).join(", ")}.`);
    }
    if (!detail) {
      errors.push(`evidence[${index}].detail is required.`);
    }
    if (!location) {
      errors.push(`evidence[${index}].location is required.`);
    }

    if (detail && detail.length > 500) {
      addUnique(warnings, `evidence[${index}].detail is long; keep evidence concise.`);
    }

    return {
      kind: kind || "summary",
      detail: detail || "",
      location: location || ""
    };
  }).filter(Boolean);
}

function validateExistingMatches(candidate, errors) {
  if (!Array.isArray(candidate.existing_matches)) {
    errors.push("existing_matches must be an array.");
    return [];
  }

  return candidate.existing_matches.map((item, index) => {
    if (!isPlainObject(item)) {
      errors.push(`existing_matches[${index}] must be an object.`);
      return null;
    }

    const slug = normalizeOptionalString(item.slug);
    const degree = normalizeOptionalString(item.degree);
    const title = normalizeOptionalString(item.title);
    const relationship = normalizeOptionalString(item.relationship);

    if (!slug) {
      errors.push(`existing_matches[${index}].slug is required.`);
    }
    if (!degree) {
      errors.push(`existing_matches[${index}].degree is required.`);
    }
    if (!title) {
      errors.push(`existing_matches[${index}].title is required.`);
    }
    if (!relationship || !NOTEBOOKLM_ALLOWED_RELATIONSHIPS.has(relationship)) {
      errors.push(
        `existing_matches[${index}].relationship must be one of: ${Array.from(NOTEBOOKLM_ALLOWED_RELATIONSHIPS).join(", ")}.`
      );
    }

    return {
      slug: slug || "",
      degree: degree || "",
      title: title || "",
      relationship: relationship || "related"
    };
  }).filter(Boolean);
}

function validateRiskFlags(candidate, errors, warnings) {
  if (!Array.isArray(candidate.risk_flags)) {
    errors.push("risk_flags must be an array.");
    return [];
  }

  const flags = [];
  for (const flag of candidate.risk_flags) {
    const normalized = normalizeOptionalString(flag);
    if (!normalized) {
      continue;
    }
    if (!NOTEBOOKLM_ALLOWED_RISK_FLAGS.has(normalized)) {
      addUnique(warnings, `risk flag "${normalized}" is not supported and was dropped.`);
      continue;
    }
    addUnique(flags, normalized);
  }
  return flags;
}

function validateNotebooklmCandidate(candidate, index, notebooklmIntakePath, catalogIndex) {
  const queueId = normalizeOptionalString(candidate?.candidate_id) || `notebooklm-${String(index + 1).padStart(2, "0")}`;
  const candidateTopic = normalizeOptionalString(candidate?.candidate_topic) || queueId;
  const sourceLocation = `${notebooklmIntakePath}#candidate-${index + 1}`;

  if (!isPlainObject(candidate)) {
    return {
      item: createNotebooklmIntakeArtifact({
        queueId,
        candidateTopic,
        reason: "NotebookLM candidate is not an object.",
        sourceAnchor: {
          book: path.basename(notebooklmIntakePath),
          section: "intake",
          quote: "invalid candidate",
          location: sourceLocation
        },
        validationErrors: ["candidate must be an object."],
        validationWarnings: []
      }),
      valid: false
    };
  }

  const errors = [];
  const warnings = [];
  const sourceAnchor = validateSourceAnchor(candidate, errors, warnings);
  const evidence = validateEvidence(candidate, errors, warnings);
  const existingMatches = validateExistingMatches(candidate, errors);
  const riskFlags = validateRiskFlags(candidate, errors, warnings);

  const candidateTitleHint = normalizeOptionalString(candidate.candidate_title_hint);
  const whyNew = normalizeOptionalString(candidate.why_new);
  const coreQuestion = normalizeOptionalString(candidate.core_question);
  const categoryHint = normalizeOptionalString(candidate.category_hint);
  const topicType = normalizeContractEnum(candidate.topic_type, NOTEBOOKLM_ALLOWED_TOPIC_TYPES, "topic", warnings, "topic_type");
  const priority = normalizeContractEnum(candidate.priority, NOTEBOOKLM_ALLOWED_PRIORITY, "info", warnings, "priority");
  const readiness = normalizeContractEnum(candidate.readiness, NOTEBOOKLM_ALLOWED_READINESS, "needs_manual_triage", warnings, "readiness");
  const nextGate = normalizeContractEnum(candidate.next_gate, NOTEBOOKLM_ALLOWED_NEXT_GATES, "dedupe_before_frame", warnings, "next_gate");
  const confidence = normalizeContractEnum(candidate.confidence, NOTEBOOKLM_ALLOWED_CONFIDENCE, "low", warnings, "confidence");
  const degreeHint = normalizeContractEnum(candidate.degree_hint, NOTEBOOKLM_ALLOWED_DEGREE_HINTS, "unknown", warnings, "degree_hint");
  const isActionable = Boolean(candidate.is_actionable);

  if (!candidateTitleHint) {
    errors.push("candidate_title_hint is required.");
  }
  if (!whyNew) {
    errors.push("why_new is required.");
  }
  if (!coreQuestion) {
    errors.push("core_question is required.");
  }
  if (typeof candidate.is_actionable !== "boolean") {
    errors.push("is_actionable must be a boolean.");
  }
  if (!normalizeOptionalString(candidate.candidate_id)) {
    errors.push("candidate_id is required.");
  }
  if (!normalizeOptionalString(candidate.candidate_topic)) {
    errors.push("candidate_topic is required.");
  }

  const validationStatus = errors.length > 0 ? "invalid" : "valid";
  const normalizedReadiness = validationStatus === "valid" ? readiness : "rejected_invalid_intake";
  const normalizedNextGate = validationStatus === "valid" ? nextGate : "fix_intake_then_resubmit";
  const normalizedIsActionable = validationStatus === "valid" && isActionable && readiness === "ready_for_triage";
  const validationErrors = errors.slice();
  const validationWarnings = warnings.slice();
  if (validationStatus === "valid" && readiness !== "ready_for_triage" && isActionable) {
    addUnique(validationWarnings, "is_actionable is true, but readiness is not ready_for_triage.");
  }

  const evaluated = validationStatus === "valid" ? evaluateNotebooklmNovelty(candidate, catalogIndex) : null;
  const queueStatus = evaluated ? evaluated.queueStatus : "rejected_invalid_intake";
  const queueReason = evaluated ? evaluated.queueReason : "Invalid intake prevented queue promotion.";
  const dedupeStatus = evaluated ? evaluated.dedupeStatus : "invalid";
  const provenance = {
    source: "notebooklm_intake",
    intake_location: notebooklmIntakePath,
    candidate_index: index + 1,
    candidate_id: queueId,
    source_anchor: sourceAnchor
  };
  const finalRiskFlags = evaluated ? evaluated.riskFlags : riskFlags;
  return {
    item: {
      queue_id: queueId,
      lane: degreeHint,
      candidate_family: "notebooklm_mindmap",
      candidate_topic: candidateTopic,
      candidate_title_hint: candidateTitleHint || candidateTopic,
      degree_hint: degreeHint,
      category_hint: categoryHint,
      suggested_type: topicType,
      priority,
      readiness: normalizedReadiness,
      is_actionable: normalizedIsActionable,
      next_gate: normalizedNextGate,
      confidence,
      why_new: whyNew || "",
      core_question: coreQuestion || "",
      source_anchor: sourceAnchor,
      evidence,
      existing_matches: existingMatches,
      risk_flags: finalRiskFlags,
      provenance,
      dedupe_status: dedupeStatus,
      queue_status: queueStatus,
      queue_reason: queueReason,
      catalog_matches: evaluated ? evaluated.matches : [],
      novelty_score: evaluated ? evaluated.noveltyScore : 0,
      queue_ready: evaluated ? evaluated.queueStatus === "queue_ready" : false,
      validation_status: validationStatus,
      validation_errors: validationErrors,
      validation_warnings: validationWarnings
    },
    valid: validationStatus === "valid"
  };
}

function tokenizeDiscoveryText(value) {
  return normalizeText(value)
    .split(" ")
    .map((item) => item.trim())
    .filter(Boolean);
}

function jaccardSimilarity(leftTokens, rightTokens) {
  if (!leftTokens.size || !rightTokens.size) {
    return 0;
  }
  let shared = 0;
  for (const token of leftTokens) {
    if (rightTokens.has(token)) {
      shared += 1;
    }
  }
  const union = new Set([...leftTokens, ...rightTokens]).size;
  return union === 0 ? 0 : shared / union;
}

function buildNotebooklmCandidateText(candidate) {
  const sourceAnchor = candidate.source_anchor || {};
  const evidenceText = Array.isArray(candidate.evidence)
    ? candidate.evidence.map((item) => [item?.kind, item?.detail, item?.location].filter(Boolean).join(" ")).join(" ")
    : "";

  return [
    candidate.candidate_id,
    candidate.candidate_topic,
    candidate.candidate_title_hint,
    candidate.degree_hint,
    candidate.category_hint,
    candidate.topic_type,
    candidate.priority,
    candidate.readiness,
    candidate.why_new,
    candidate.core_question,
    sourceAnchor.book,
    sourceAnchor.section,
    sourceAnchor.quote,
    sourceAnchor.location,
    evidenceText
  ]
    .filter(Boolean)
    .join(" ");
}

function buildCatalogIndex(entries) {
  return entries
    .map((entry) => {
      const metadataText = entryMetadataText(entry);
      const bodyText = entryText(entry);
      return {
        entry,
        metadataText,
        bodyText,
        metadataTokens: new Set(tokenizeDiscoveryText(metadataText)),
        bodyTokens: new Set(tokenizeDiscoveryText(bodyText)),
        titleText: normalizeText(entry.title),
        slugText: normalizeText(entry.slug)
      };
    })
    .filter((item) => item.metadataText || item.bodyText);
}

function buildStableBaseCatalogEntries(stableBasePath) {
  const stableBase = readJsonIfExists(stableBasePath, { entries: [] });
  if (!stableBase || !Array.isArray(stableBase.entries)) {
    return [];
  }

  return stableBase.entries.map((entry) => ({
    slug: entry.target_topic_slug || entry.slug || entry.stable_base_id || "",
    title: entry.target_topic_title || entry.title || entry.candidate_topic || "",
    degree: entry.target_degree || entry.degree || "unknown",
    short_summary: entry.promotion_reason || "",
    full_summary: [entry?.candidate_snapshot?.why_new, entry?.candidate_snapshot?.core_question].filter(Boolean).join(" "),
    source_heading: entry?.provenance?.source_section || entry?.candidate_snapshot?.source_anchor?.section || "",
    work_title: entry?.provenance?.source_book || entry?.candidate_snapshot?.source_anchor?.book || "",
    keywords: [entry.candidate_topic, entry?.candidate_snapshot?.topic_type, entry.addition_type].filter(Boolean),
    aliases: Array.isArray(entry.aliases) ? entry.aliases : [],
    source_notes: [
      entry.stable_base_id || entry.artifact_id || "",
      entry?.provenance?.notebook_packet_id || "",
      entry?.provenance?.notebook_source || ""
    ].filter(Boolean)
  }));
}

function classifyCatalogRelationship(score, candidateText, catalogItem) {
  const exactTopicMatch =
    Boolean(candidateText) &&
    (candidateText === catalogItem.titleText ||
      candidateText === catalogItem.slugText ||
      candidateText.includes(catalogItem.titleText) ||
      catalogItem.titleText.includes(candidateText));

  if (exactTopicMatch || score >= 0.7) {
    return "same_topic";
  }
  if (score >= 0.45) {
    return "near_duplicate";
  }
  if (score >= 0.25) {
    return "related";
  }
  return "no_match";
}

function evaluateNotebooklmNovelty(candidate, catalogIndex) {
  const candidateText = normalizeText(buildNotebooklmCandidateText(candidate));
  const candidateTokens = new Set(tokenizeDiscoveryText(candidateText));
  const degreeHint = normalizeOptionalString(candidate.degree_hint) || "unknown";
  const confidenceHint = normalizeOptionalString(candidate.confidence) || "low";
  const topicText = normalizeText([candidate.candidate_topic, candidate.candidate_title_hint].filter(Boolean).join(" "));
  const topicTokens = new Set(tokenizeDiscoveryText(topicText));
  const matches = [];

  for (const catalogItem of catalogIndex) {
    const metadataScore = jaccardSimilarity(candidateTokens, catalogItem.metadataTokens);
    const bodyScore = jaccardSimilarity(candidateTokens, catalogItem.bodyTokens);
    const topicScore = jaccardSimilarity(topicTokens, catalogItem.metadataTokens);
    const score = Number(Math.max(metadataScore * 0.7 + bodyScore * 0.3, topicScore).toFixed(3));
    const relationship = classifyCatalogRelationship(score, topicText, catalogItem);

    if (relationship === "no_match" && score < 0.18) {
      continue;
    }

    const reasonParts = [];
    if (metadataScore >= 0.18) {
      reasonParts.push("metadata overlap");
    }
    if (bodyScore >= 0.18) {
      reasonParts.push("body overlap");
    }
    if (topicScore >= 0.18) {
      reasonParts.push("topic overlap");
    }
    if (!reasonParts.length && relationship !== "no_match") {
      reasonParts.push("strong lexical proximity");
    }

    matches.push({
      slug: catalogItem.entry.slug || "",
      degree: catalogItem.entry.degree || catalogItem.entry.lane || "unknown",
      title: catalogItem.entry.title || "",
      relationship,
      score,
      reason: reasonParts.join(", ")
    });
  }

  matches.sort((left, right) => right.score - left.score || left.slug.localeCompare(right.slug));
  const topMatches = matches.slice(0, 5);
  const bestMatch = topMatches[0] || null;
  const sameTopicMatch = topMatches.find((item) => item.relationship === "same_topic") || null;
  const nearDuplicateMatch = topMatches.find((item) => item.relationship === "near_duplicate") || null;
  const declaredMatches = Array.isArray(candidate.existing_matches) ? candidate.existing_matches : [];
  const declaredDuplicateMatch = declaredMatches.find((item) => {
    const relationship = normalizeOptionalString(item?.relationship);
    return relationship === "same_topic" || relationship === "near_duplicate";
  });
  const candidateDegree = normalizeOptionalString(candidate.degree_hint) || "unknown";

  let dedupeStatus = "unique";
  if (sameTopicMatch) {
    dedupeStatus = "same_topic";
  } else if (nearDuplicateMatch) {
    dedupeStatus = "near_duplicate";
  } else if (bestMatch && bestMatch.relationship === "related") {
    dedupeStatus = "related";
  }

  if (declaredDuplicateMatch) {
    const declaredRelationship = normalizeOptionalString(declaredDuplicateMatch.relationship);
    if (declaredRelationship === "same_topic") {
      dedupeStatus = "same_topic";
    } else if (dedupeStatus === "unique") {
      dedupeStatus = "near_duplicate";
    }
  }

  const duplicateLabel =
    (sameTopicMatch && (sameTopicMatch.title || sameTopicMatch.slug)) ||
    (declaredDuplicateMatch && (declaredDuplicateMatch.title || declaredDuplicateMatch.slug)) ||
    topicText ||
    candidate.candidate_topic ||
    candidate.candidate_id ||
    "existing topic";
  const nearDuplicateLabel =
    (nearDuplicateMatch && (nearDuplicateMatch.title || nearDuplicateMatch.slug)) ||
    (declaredDuplicateMatch && (declaredDuplicateMatch.title || declaredDuplicateMatch.slug)) ||
    topicText ||
    candidate.candidate_topic ||
    candidate.candidate_id ||
    "existing topic";

  const degreeAmbiguous =
    candidateDegree === "unknown" ||
    Boolean(bestMatch && bestMatch.relationship !== "same_topic" && bestMatch.score >= 0.45 && bestMatch.degree && bestMatch.degree !== candidateDegree);

  let queueStatus = "queue_ready";
  let queueReason = "Grounded, unique, and ready for triage.";
  let readiness = normalizeOptionalString(candidate.readiness) || "needs_manual_triage";
  let isActionable = Boolean(candidate.is_actionable);
  const riskFlags = Array.isArray(candidate.risk_flags) ? [...candidate.risk_flags] : [];

  if (dedupeStatus === "same_topic") {
    queueStatus = "deferred_duplicate";
    queueReason = `Duplicate of existing topic: ${duplicateLabel}.`;
    readiness = "defer";
    isActionable = false;
    addUnique(riskFlags, "duplicate_risk");
    addUnique(riskFlags, "needs_human_review");
  } else if (dedupeStatus === "near_duplicate") {
    queueStatus = "deferred_near_duplicate";
    queueReason = `Near-duplicate of existing topic: ${nearDuplicateLabel}.`;
    readiness = "needs_manual_triage";
    isActionable = false;
    addUnique(riskFlags, "duplicate_risk");
    addUnique(riskFlags, "needs_human_review");
  } else if (candidate.readiness === "needs_more_evidence") {
    queueStatus = "deferred_weak_evidence";
    queueReason = "Candidate needs more evidence before queue promotion.";
    readiness = "defer";
    isActionable = false;
    addUnique(riskFlags, "weak_evidence");
  } else if (candidate.readiness === "defer") {
    queueStatus = "deferred_by_intake";
    queueReason = "Candidate was explicitly deferred at intake.";
    isActionable = false;
  } else if (degreeAmbiguous) {
    queueStatus = "needs_degree_review";
    queueReason = "Candidate has an ambiguous or unsupported degree hint.";
    readiness = "needs_manual_triage";
    isActionable = false;
    addUnique(riskFlags, "degree_ambiguous");
    addUnique(riskFlags, "needs_human_review");
  } else if (confidenceHint === "low" || (bestMatch && bestMatch.relationship === "related" && bestMatch.score < 0.3)) {
    queueStatus = "deferred_weak_evidence";
    queueReason = "Candidate is grounded but still too weak or broad for queue promotion.";
    readiness = "needs_manual_triage";
    isActionable = false;
    addUnique(riskFlags, "weak_evidence");
    addUnique(riskFlags, "needs_human_review");
  } else if (!isActionable || readiness !== "ready_for_triage") {
    queueStatus = "needs_manual_triage";
    queueReason = "Candidate is valid but not ready for queue promotion yet.";
    isActionable = false;
  }

  if (candidateDegree !== "level1" && candidateDegree !== "level2" && candidateDegree !== "level3" && candidateDegree !== "research" && candidateDegree !== "unknown") {
    addUnique(riskFlags, "degree_ambiguous");
    isActionable = false;
    if (queueStatus === "queue_ready") {
      queueStatus = "needs_degree_review";
      queueReason = "Candidate degree hint is not supported.";
    }
  }

  return {
    dedupeStatus,
    queueStatus,
    queueReason,
    readiness,
    isActionable,
    riskFlags,
    matches: topMatches,
    bestMatch,
    degreeAmbiguous,
    noveltyScore: bestMatch ? bestMatch.score : 0
  };
}
function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, filePath);
}

function buildNotebooklmLedger(notebooklmLane, reviewPacketPath) {
  return {
    meta: {
      phase: "phase_m8_topic_discovery",
      generated_at: new Date().toISOString(),
      purpose: "Auditable lifecycle ledger for NotebookLM discovery candidates.",
      review_packet_path: reviewPacketPath
    },
    summary: {
      candidate_count: notebooklmLane.items.length,
      valid_candidate_count: notebooklmLane.summary.valid_candidate_count,
      invalid_candidate_count: notebooklmLane.summary.invalid_candidate_count,
      queue_ready_count: notebooklmLane.summary.queue_ready_count
    },
    entries: notebooklmLane.items.map((item) => ({
      candidate_id: item.provenance?.candidate_id || item.queue_id,
      candidate_topic: item.candidate_topic,
      source_provenance: {
        notebook_source: item.provenance?.source || "notebooklm_intake",
        notebook_packet_id: item.provenance?.candidate_id || item.queue_id,
        intake_location: item.provenance?.intake_location || null,
        source_anchor: item.source_anchor || null
      },
      degree_hint: item.degree_hint,
      review_state:
        item.validation_status !== "valid"
          ? "invalid_intake"
          : item.queue_status === "queue_ready"
            ? "ready_for_review"
            : "triage_required",
      final_state: null,
      final_reason: null,
      gate_owner: "queue_normalization",
      reviewed_at: null,
      related_existing_matches: Array.isArray(item.catalog_matches) ? item.catalog_matches : [],
      queue_status: item.queue_status,
      queue_reason: item.queue_reason,
      validation_status: item.validation_status,
      validation_errors: Array.isArray(item.validation_errors) ? item.validation_errors : [],
      risk_flags: Array.isArray(item.risk_flags) ? item.risk_flags : []
    }))
  };
}

function buildNotebooklmReviewPacket(notebooklmLane, ledgerPath) {
  return {
    meta: {
      phase: "phase_m8_topic_discovery_review",
      generated_at: new Date().toISOString(),
      purpose: "Operator review packet for final NotebookLM promotion decisions.",
      source_ledger_path: ledgerPath
    },
    entries: notebooklmLane.items
      .filter((item) => item.validation_status === "valid")
      .map((item) => ({
        candidate_id: item.provenance?.candidate_id || item.queue_id,
        candidate_topic: item.candidate_topic,
        candidate_title_hint: item.candidate_title_hint,
        degree_hint: item.degree_hint,
        queue_status: item.queue_status,
        queue_reason: item.queue_reason,
        recommended_decision: item.queue_status === "queue_ready" ? "promoted" : "deferred",
        decision: "pending_review",
        reviewer: null,
        role: null,
        reason: null,
        reviewed_at: null,
        proposed_target_slug: null,
        proposed_target_title: null,
        proposed_target_degree: null,
        addition_type: "new_topic",
        base_action: "add"
      }))
  };
}

function collectJsonFiles(rootDir) {
  const files = [];
  if (!fs.existsSync(rootDir)) {
    return files;
  }

  for (const entry of fs.readdirSync(rootDir, { withFileTypes: true })) {
    const fullPath = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectJsonFiles(fullPath));
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".json")) {
      files.push(fullPath);
    }
  }

  return files;
}

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\u0590-\u05ff\s]+/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function entryText(entry) {
  return normalizeText(
    [
      entry.slug,
      entry.title,
      entry.short_summary,
      entry.full_summary,
      entry.source_heading,
      entry.work_title,
      Array.isArray(entry.keywords) ? entry.keywords.join(" ") : "",
      Array.isArray(entry.aliases) ? entry.aliases.join(" ") : "",
      Array.isArray(entry.source_notes) ? entry.source_notes.join(" ") : ""
    ].join(" ")
  );
}

function entryMetadataText(entry) {
  return normalizeText(
    [
      entry.slug,
      entry.title,
      entry.source_heading,
      entry.work_title,
      Array.isArray(entry.keywords) ? entry.keywords.join(" ") : ""
    ].join(" ")
  );
}

function isBlockedForNativeLevel3(entry) {
  const haystack = normalizeText(
    [
      entry.slug,
      entry.title,
      entry.short_summary,
      entry.full_summary,
      entry.source_heading,
      entry.work_title
    ].join(" ")
  );

  const blockedPatterns = [
    /royal arch/i,
    /appendant/i,
    /most excellent master/i,
    /\bsixth degree\b/i,
    /\b18th degree\b/i,
    /rose croix/i,
    /including the royal arch degree/i,
    /return from babylon/i,
    /hidden vault/i
  ];

  return blockedPatterns.some((pattern) => pattern.test(haystack));
}

function entryMap(entries) {
  return new Map(entries.map((entry) => [entry.slug, entry]));
}

function isRuntimeHidden(entry) {
  const controls = entry.review_controls || {};
  return entry.visibility_level === "editorial" || controls.exclude_from_navigation === true;
}

function isFrozen(entry) {
  const controls = entry.review_controls || {};
  return controls.decision_status === "rejected_pending_rewrite";
}

function scoreToConfidence(supportingEntryCount, distinctSignalCount) {
  if (supportingEntryCount >= 6 && distinctSignalCount >= 4) {
    return "high";
  }
  if (supportingEntryCount >= 3 && distinctSignalCount >= 3) {
    return "medium";
  }
  return "low";
}

function overlapRisk(maxOverlap) {
  if (maxOverlap >= 0.4) {
    return "high";
  }
  if (maxOverlap >= 0.2) {
    return "medium";
  }
  return "low";
}

function getPriorityFromRank(rank) {
  if (rank <= 3) {
    return "high";
  }
  if (rank <= 8) {
    return "medium";
  }
  return "low";
}

function buildLevel2Lane({ level1Entries, level2Entries, level2Candidates, level2Frames }) {
  const level1BySlug = entryMap(level1Entries);
  const level2BySlug = entryMap(level2Entries);
  const frameByCandidate = new Map(
    (level2Frames.topic_frames || []).map((frame) => [frame.candidate_topic, frame])
  );

  const items = (level2Candidates.candidates || []).map((candidate) => {
    const frame = frameByCandidate.get(candidate.candidate_topic) || null;
    const targetSlug = frame ? frame.target_slug : null;

    let resolutionStatus = "candidate_not_framed";
    let nextGate = "frame_before_fill";
    let isActionable = true;

    if (frame && level2BySlug.has(targetSlug)) {
      const targetEntry = level2BySlug.get(targetSlug);
      if (isFrozen(targetEntry)) {
        resolutionStatus = "built_but_hidden";
        nextGate = "review_superseded_or_rewrite";
        isActionable = false;
      } else if (isRuntimeHidden(targetEntry)) {
        resolutionStatus = "built_hidden_from_runtime";
        nextGate = "hold";
        isActionable = false;
      } else {
        resolutionStatus = "already_built_in_level2";
        nextGate = "hold";
        isActionable = false;
      }
    } else if (frame && level1BySlug.has(targetSlug)) {
      resolutionStatus = "moved_to_level1";
      nextGate = "do_not_rebuild_in_level2";
      isActionable = false;
    } else if (frame) {
      resolutionStatus = "framed_not_built";
      nextGate = "ready_for_f2_f3_fill";
    }

    const maxOverlap = Number(candidate.overlap_with_existing_level2?.max_jaccard || 0);

    return {
      queue_id: `level2-${candidate.rank.toString().padStart(2, "0")}-${candidate.candidate_topic}`,
      lane: "level2",
      candidate_family: "graph_reuse",
      candidate_topic: candidate.candidate_topic,
      candidate_title_hint: candidate.candidate_title_hint,
      target_slug_hint: targetSlug,
      target_title_hint: frame ? frame.target_title : null,
      degree_hint: "level2",
      category_hint: frame ? frame.category : null,
      suggested_type: frame ? frame.level2_type : candidate.suggested_type,
      confidence: candidate.confidence,
      priority: isActionable ? getPriorityFromRank(candidate.rank) : "info",
      rank: candidate.rank,
      readiness: resolutionStatus,
      is_actionable: isActionable,
      next_gate: nextGate,
      overlap_risk: overlapRisk(maxOverlap),
      overlap_with_existing_level2: candidate.overlap_with_existing_level2 || null,
      source_anchor: {
        based_on_entries: candidate.based_on_entries || [],
        discovery_sources: candidate.discovery_sources || [],
        basis_categories: candidate.basis_categories || []
      },
      why_new: candidate.reason,
      knowledge_goal: frame ? frame.knowledge_goal : null,
      core_question: frame ? frame.core_question : null,
      structure_axes: frame ? frame.structure_axes || [] : [],
      score: candidate.score
    };
  });

  return {
    items,
    summary: {
      total_candidates: items.length,
      actionable_count: items.filter((item) => item.is_actionable).length,
      already_built_count: items.filter((item) => item.readiness === "already_built_in_level2").length,
      moved_to_level1_count: items.filter((item) => item.readiness === "moved_to_level1").length,
      framed_not_built_count: items.filter((item) => item.readiness === "framed_not_built").length,
      not_framed_count: items.filter((item) => item.readiness === "candidate_not_framed").length,
      hidden_or_frozen_count: items.filter(
        (item) => item.readiness === "built_hidden_from_runtime" || item.readiness === "built_but_hidden"
      ).length,
      top_actionable: items
        .filter((item) => item.is_actionable)
        .sort((left, right) => left.rank - right.rank)
        .slice(0, 3)
        .map((item) => item.candidate_topic)
    }
  };
}

function buildLevel3Lane(libraryEntries) {
  const sourceEntries = libraryEntries.filter(
    (entry) => !["category", "hub", "book"].includes(entry.type) && !isBlockedForNativeLevel3(entry)
  );
  const candidateItems = [];

  for (const spec of level3ThemeSpecs) {
    const matchedEntries = [];

    for (const entry of sourceEntries) {
      const metadataHaystack = entryMetadataText(entry);
      const bodyHaystack = entryText(entry);
      if (!bodyHaystack) {
        continue;
      }

      let score = 0;
      let metadataScore = 0;
      const metadataAnchorMatched = nativeLevel3MetadataAnchorPattern.test(metadataHaystack);
      const matchedSignals = [];
      for (const signal of spec.signals) {
        if (signal.pattern.test(metadataHaystack)) {
          score += signal.weight * 2;
          metadataScore += signal.weight;
          matchedSignals.push(signal.label);
          continue;
        }

        if (signal.pattern.test(bodyHaystack)) {
          score += signal.weight;
          matchedSignals.push(signal.label);
        }
      }

      if (metadataAnchorMatched) {
        metadataScore += 1;
      }

      if (score === 0 || metadataScore === 0) {
        continue;
      }

      matchedEntries.push({
        slug: entry.slug,
        title: entry.title,
        type: entry.type,
        work_title: entry.work_title || "",
        source_heading: entry.source_heading || "",
        score,
        metadata_score: metadataScore,
        matched_signals: matchedSignals
      });
    }

    matchedEntries.sort((left, right) => right.score - left.score || left.slug.localeCompare(right.slug));

    const limitedEntries = matchedEntries.slice(0, 12);
    const distinctSignals = new Set(limitedEntries.flatMap((entry) => entry.matched_signals));
    const meetsRequiredSignals = spec.requiredSignals.every((group) =>
      group.some((label) => distinctSignals.has(label))
    );

    if (!meetsRequiredSignals || limitedEntries.length < 2) {
      continue;
    }

    candidateItems.push({
      queue_id: spec.candidate_topic,
      lane: "level3",
      candidate_family: "native_library_seed",
      candidate_topic: spec.candidate_topic,
      candidate_title_hint: spec.candidate_title_hint,
      degree_hint: "level3",
      category_hint: spec.category_hint,
      suggested_type: spec.suggested_type,
      priority: "high",
      readiness: "native_seed_discovery_only",
      is_actionable: true,
      next_gate: "level3_boundary_spec_before_frame",
      confidence: scoreToConfidence(limitedEntries.length, distinctSignals.size),
      why_new: spec.why_new,
      core_question: spec.core_question,
      source_alignment: "library_native_degree3_only",
      blocked_by: [
        "no_level3_scope_spec_finalized",
        "no_level3_category_set_approved",
        "no_level3_runtime_lane"
      ],
      support: {
        supporting_entry_count: limitedEntries.length,
        distinct_signal_count: distinctSignals.size,
        distinct_signals: Array.from(distinctSignals).sort()
      },
      source_anchor: {
        evidence_entries: limitedEntries
      },
      overlap_risk: "low",
      max_overlap_with_other_level3_candidates: 0
    });
  }

  for (let index = 0; index < candidateItems.length; index += 1) {
    const item = candidateItems[index];
    const sourceSlugs = new Set(item.source_anchor.evidence_entries.map((entry) => entry.slug));
    let maxOverlap = 0;

    for (let inner = 0; inner < candidateItems.length; inner += 1) {
      if (index === inner) {
        continue;
      }

      const otherSlugs = new Set(candidateItems[inner].source_anchor.evidence_entries.map((entry) => entry.slug));
      const shared = Array.from(sourceSlugs).filter((slug) => otherSlugs.has(slug)).length;
      const union = new Set([...sourceSlugs, ...otherSlugs]).size;
      const ratio = union === 0 ? 0 : Number((shared / union).toFixed(3));
      if (ratio > maxOverlap) {
        maxOverlap = ratio;
      }
    }

    item.max_overlap_with_other_level3_candidates = maxOverlap;
    item.overlap_risk = overlapRisk(maxOverlap);
  }

  return {
    items: candidateItems,
    summary: {
      total_candidates: candidateItems.length,
      total_support_entries: candidateItems.reduce(
        (sum, item) => sum + item.source_anchor.evidence_entries.length,
        0
      ),
      top_candidates: candidateItems.map((item) => item.candidate_topic),
      build_ready: false
    }
  };
}

function classifyFutureEntryLabel(label) {
  if (/royal_arch/i.test(label)) {
    return {
      queue_kind: "royal_arch_future_queue",
      recommended_lane: "royal_arch",
      reason: "Royal Arch content should live in its own adjacent lane and must not be mixed into native Level 3."
    };
  }

  if (/biblical/i.test(label)) {
    return {
      queue_kind: "research_queue",
      recommended_lane: "library_or_research",
      reason: "Biblical-symbolic material needs a separate boundary review before degree ownership is assigned."
    };
  }

  return {
    queue_kind: "research_queue",
    recommended_lane: "library_or_manual_review",
    reason: "The future-entry queue does not map safely into a native Level 2 or Level 3 lane yet."
  };
}

function summarizePreservationLane(items) {
  return {
    queue_count: items.length,
    total_units: items.reduce((sum, item) => sum + (item.source_anchor?.unit_count || 0), 0),
    labels: items.map((item) => item.candidate_topic)
  };
}

function buildBlockedLane(futureEntryRoot) {
  const files = collectJsonFiles(futureEntryRoot);
  const grouped = new Map();

  for (const filePath of files) {
    const payload = readJson(filePath);
    const label = payload.future_entry_label || "unlabeled_future_entry";
    if (!grouped.has(label)) {
      grouped.set(label, []);
    }
    grouped.get(label).push(payload);
  }

  const items = Array.from(grouped.entries())
    .sort(([leftLabel], [rightLabel]) => leftLabel.localeCompare(rightLabel))
    .map(([label, payloads]) => {
      const classification = classifyFutureEntryLabel(label);
      const sourceEntries = Array.from(
        new Set(payloads.map((payload) => payload.source_entry_slug).filter(Boolean))
      ).sort();

      return {
        queue_id: `blocked-${label}`,
        lane: "blocked_higher_degree",
        candidate_family: "preservation_future_entries",
        candidate_topic: label,
        candidate_title_hint: label.replace(/_/g, " "),
        degree_hint: null,
        category_hint: null,
        suggested_type: "research_queue",
        priority: "info",
        readiness: "blocked_pending_boundary_review",
        is_actionable: false,
        next_gate: "keep_outside_native_degree_lanes",
        queue_kind: classification.queue_kind,
        recommended_lane: classification.recommended_lane,
        why_new: classification.reason,
        source_anchor: {
          unit_count: payloads.length,
          sample_review_units: payloads.slice(0, 5).map((payload) => payload.review_unit_id),
          source_entry_slugs: sourceEntries.slice(0, 12)
        }
      };
    });

  return {
    items,
    summary: summarizePreservationLane(items)
  };
}

function splitPreservationLanes(futureLane) {
  const royalArchItems = futureLane.items.filter((item) => item.recommended_lane === "royal_arch");
  const blockedItems = futureLane.items.filter((item) => item.recommended_lane !== "royal_arch");

  return {
    royalArchLane: {
      items: royalArchItems,
      summary: summarizePreservationLane(royalArchItems)
    },
    blockedLane: {
      items: blockedItems,
      summary: summarizePreservationLane(blockedItems)
    }
  };
}

function buildNotebooklmLane(notebooklmIntakePath, catalogIndex) {
  if (!fs.existsSync(notebooklmIntakePath)) {
    const invalidItem = createNotebooklmIntakeArtifact({
      queueId: "notebooklm-intake-missing",
      candidateTopic: "notebooklm-intake-missing",
      reason: `NotebookLM intake file not found at ${notebooklmIntakePath}.`,
      sourceAnchor: {
        book: path.basename(notebooklmIntakePath),
        section: "intake",
        quote: "missing intake file",
        location: notebooklmIntakePath
      },
      validationErrors: ["NotebookLM intake file does not exist."],
      validationWarnings: []
    });
    return {
      items: [invalidItem],
      summary: {
        intake_status: "intake_missing",
        candidate_count: 1,
        valid_candidate_count: 0,
        invalid_candidate_count: 1,
        actionable_count: 0,
        deferred_count: 0,
        rejected_count: 1,
        top_actionable: []
      }
    };
  }

  let intake;
  try {
    intake = readJson(notebooklmIntakePath);
  } catch (error) {
    const invalidItem = createNotebooklmIntakeArtifact({
      queueId: "notebooklm-intake-invalid-json",
      candidateTopic: "notebooklm-intake-invalid-json",
      reason: `NotebookLM intake file could not be parsed: ${error.message}`,
      sourceAnchor: {
        book: path.basename(notebooklmIntakePath),
        section: "intake",
        quote: "invalid JSON",
        location: notebooklmIntakePath
      },
      validationErrors: [error.message],
      validationWarnings: []
    });
    return {
      items: [invalidItem],
      summary: {
        intake_status: "intake_invalid_json",
        candidate_count: 1,
        valid_candidate_count: 0,
        invalid_candidate_count: 1,
        actionable_count: 0,
        deferred_count: 0,
        rejected_count: 1,
        top_actionable: []
      }
    };
  }

  if (!isPlainObject(intake)) {
    const invalidItem = createNotebooklmIntakeArtifact({
      queueId: "notebooklm-intake-invalid-shape",
      candidateTopic: "notebooklm-intake-invalid-shape",
      reason: "NotebookLM intake root must be a JSON object.",
      sourceAnchor: {
        book: path.basename(notebooklmIntakePath),
        section: "intake",
        quote: "invalid intake shape",
        location: notebooklmIntakePath
      },
      validationErrors: ["NotebookLM intake root is not an object."],
      validationWarnings: []
    });
    return {
      items: [invalidItem],
      summary: {
        intake_status: "intake_invalid_shape",
        candidate_count: 1,
        valid_candidate_count: 0,
        invalid_candidate_count: 1,
        actionable_count: 0,
        deferred_count: 0,
        rejected_count: 1,
        top_actionable: []
      }
    };
  }

  if (!Array.isArray(intake.candidates)) {
    const invalidItem = createNotebooklmIntakeArtifact({
      queueId: "notebooklm-intake-missing-candidates",
      candidateTopic: "notebooklm-intake-missing-candidates",
      reason: "NotebookLM intake must include a candidates array.",
      sourceAnchor: {
        book: path.basename(notebooklmIntakePath),
        section: "intake",
        quote: "missing candidates array",
        location: notebooklmIntakePath
      },
      validationErrors: ["NotebookLM intake.candidates is missing or not an array."],
      validationWarnings: []
    });
    return {
      items: [invalidItem],
      summary: {
        intake_status: "intake_missing_candidates",
        candidate_count: 1,
        valid_candidate_count: 0,
        invalid_candidate_count: 1,
        actionable_count: 0,
        deferred_count: 0,
        rejected_count: 1,
        top_actionable: []
      }
    };
  }

  const validatedCandidates = intake.candidates.map((candidate, index) =>
    validateNotebooklmCandidate(candidate, index, notebooklmIntakePath, catalogIndex)
  );
  const items = validatedCandidates.map((entry) => entry.item);
  const validCount = validatedCandidates.filter((entry) => entry.valid).length;
  const invalidCount = items.length - validCount;
  const actionableItems = items.filter((item) => item.is_actionable && item.validation_status === "valid" && item.queue_ready);
  const queueStatusCounts = items.reduce((counts, item) => {
    const key = item.queue_status || "unknown";
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});

  return {
    items,
    summary: {
      intake_status: "intake_loaded",
      candidate_count: items.length,
      valid_candidate_count: validCount,
      invalid_candidate_count: invalidCount,
        actionable_count: actionableItems.length,
        deferred_count: items.filter((item) => item.readiness === "defer").length,
        rejected_count: items.filter((item) => item.readiness === "rejected_invalid_intake").length,
        duplicate_count: items.filter((item) => item.dedupe_status === "same_topic").length,
        near_duplicate_count: items.filter((item) => item.dedupe_status === "near_duplicate").length,
        queue_ready_count: items.filter((item) => item.queue_status === "queue_ready").length,
        queue_status_counts: queueStatusCounts,
        top_actionable: actionableItems
        .sort((left, right) => {
          const priorityOrder = { high: 0, medium: 1, low: 2, info: 3 };
          const leftPriority = priorityOrder[left.priority] ?? 9;
          const rightPriority = priorityOrder[right.priority] ?? 9;
          if (leftPriority !== rightPriority) {
            return leftPriority - rightPriority;
          }
          return left.queue_id.localeCompare(right.queue_id);
        })
        .slice(0, 3)
        .map((item) => item.candidate_topic)
    }
  };
}

function buildMergedActionQueue(level2Lane, level3Lane, notebooklmLane) {
  const actionableItems = [
    ...level2Lane.items.filter((item) => item.is_actionable),
    ...level3Lane.items.filter((item) => item.is_actionable),
    ...notebooklmLane.items.filter(
      (item) => item.is_actionable && item.validation_status === "valid" && item.queue_status === "queue_ready"
    )
  ];

  const priorityOrder = { high: 0, medium: 1, low: 2, info: 3 };
  actionableItems.sort((left, right) => {
    const leftPriority = priorityOrder[left.priority] ?? 9;
    const rightPriority = priorityOrder[right.priority] ?? 9;
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }

    const leftRank = typeof left.rank === "number" ? left.rank : 999;
    const rightRank = typeof right.rank === "number" ? right.rank : 999;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }

    return left.queue_id.localeCompare(right.queue_id);
  });

  return actionableItems;
}

function buildReport({ inputs, level2Lane, level3Lane, royalArchLane, blockedLane, notebooklmLane, mergedQueue }) {
  const level2OpenCount = level2Lane.summary.actionable_count;
  const saturationState = level2OpenCount >= 8 ? "high" : level2OpenCount >= 4 ? "medium" : "low";

  return {
    meta: {
      phase: "phase_m8_topic_discovery",
      generated_at: new Date().toISOString(),
      mode: "read_only_discovery_queue",
      inputs
    },
    summary: {
      level2: level2Lane.summary,
      level3: level3Lane.summary,
      royal_arch_future_lane: royalArchLane.summary,
      blocked_higher_degree: blockedLane.summary,
      notebooklm: notebooklmLane.summary,
      merged_action_queue_count: mergedQueue.length
    },
    saturation_and_stop_rules: {
      level2_discovery_pressure: saturationState,
      stop_rules: [
        {
          rule: "Do not open another broad Level 2 discovery round while more than 8 Level 2 candidates remain actionable.",
          status: saturationState === "high" ? "triggered" : "clear"
        },
        {
          rule: "Keep Level 3 in discovery mode until its scope spec, category set, and runtime lane exist.",
          status: "enforced"
        },
        {
          rule: "Keep Royal Arch in its own adjacent lane and outside native Level 3 build decisions.",
          status: royalArchLane.items.length > 0
            ? "enforced"
            : "clear"
        },
        {
          rule: "Normalize NotebookLM mindmap output through intake JSON before using it in planning.",
          status:
            notebooklmLane.summary.candidate_count > 0
              ? "active"
              : notebooklmLane.summary.intake_status === "intake_loaded"
                ? "intake_ready"
                : "template_ready"
        }
      ]
    },
    next_actions: [
      {
        step: "Level 2 triage",
        recommendation:
          "Work only the top 3 actionable Level 2 candidates before another large discovery pass.",
        candidates: level2Lane.summary.top_actionable
      },
      {
        step: "Level 3 boundary build",
        recommendation:
          "Use the native library-backed Level 3 candidates as the starting boundary set, not the Royal Arch adjacent lane.",
        candidates: level3Lane.summary.top_candidates
      },
      {
        step: "Royal Arch adjacent lane",
        recommendation:
          "Treat Royal Arch as its own future lane seed, not as blocked Level 3 residue.",
        candidates: royalArchLane.summary.labels
      },
      {
        step: "NotebookLM expansion",
        recommendation:
          "Use the discovery mindmap prompt template and intake JSON to add only atomic candidate topics with one clear question each.",
        candidates: []
      }
    ],
    overall_status: "pass"
  };
}

function main() {
  const cliOptions = parseArgs(process.argv.slice(2));
  const defaultPaths = buildDefaults(resolveRepoPath(pickOption(cliOptions, "site-root", "siteRoot") || DEFAULT_DISCOVERY_SITE_ROOT));
  const options = { ...defaultPaths, ...cliOptions };
  const resolved = {
    siteRoot: resolveRepoPath(pickOption(options, "site-root", "siteRoot")),
    level1: resolveRepoPath(pickOption(options, "level1")),
    level2: resolveRepoPath(pickOption(options, "level2")),
    library: resolveRepoPath(pickOption(options, "library")),
    level2Candidates: resolveRepoPath(pickOption(options, "level2-candidates", "level2Candidates")),
    level2Frames: resolveRepoPath(pickOption(options, "level2-frames", "level2Frames")),
    futureEntryRoot: resolveRepoPath(pickOption(options, "future-entry-root", "futureEntryRoot")),
    notebooklmIntake: resolveRepoPath(pickOption(options, "notebooklm-intake", "notebooklmIntake")),
    stableTopicBase: resolveRepoPath(pickOption(options, "stable-topic-base", "stableTopicBase")),
    queueOutput: resolveRepoPath(pickOption(options, "queue-output", "queueOutput")),
    reportOutput: resolveRepoPath(pickOption(options, "report-output", "reportOutput")),
    ledgerOutput: resolveRepoPath(pickOption(options, "ledger-output", "ledgerOutput")),
    reviewPacketOutput: resolveRepoPath(pickOption(options, "review-packet-output", "reviewPacketOutput"))
  };

  const level1 = readJson(resolved.level1);
  const level2 = readJson(resolved.level2);
  const library = readJson(resolved.library);
  const level2Candidates = readJson(resolved.level2Candidates);
  const level2Frames = readJson(resolved.level2Frames);
  const stableBaseEntries = buildStableBaseCatalogEntries(resolved.stableTopicBase);
  const catalogEntries = [...(level1.entries || []), ...(level2.entries || []), ...(library.entries || []), ...stableBaseEntries];
  const catalogIndex = buildCatalogIndex(catalogEntries);

  const level2Lane = buildLevel2Lane({
    level1Entries: level1.entries || [],
    level2Entries: level2.entries || [],
    level2Candidates,
    level2Frames
  });
  const level3Lane = buildLevel3Lane(library.entries || []);
  const futureLane = buildBlockedLane(resolved.futureEntryRoot);
  const { royalArchLane, blockedLane } = splitPreservationLanes(futureLane);
  const notebooklmLane = buildNotebooklmLane(resolved.notebooklmIntake, catalogIndex);
  const mergedQueue = buildMergedActionQueue(level2Lane, level3Lane, notebooklmLane);

  const queueArtifact = {
    meta: {
      phase: "phase_m8_topic_discovery",
      generated_at: new Date().toISOString(),
      mode: "read_only_discovery_queue",
      inputs: {
        site_root: resolved.siteRoot,
        level1_path: resolved.level1,
        level2_path: resolved.level2,
        library_path: resolved.library,
        level2_candidates_path: resolved.level2Candidates,
        level2_frames_path: resolved.level2Frames,
        future_entry_root: resolved.futureEntryRoot,
        notebooklm_intake_path: resolved.notebooklmIntake
      }
    },
    lanes: {
      level2_graph_candidates: level2Lane.items,
      level3_native_candidates: level3Lane.items,
      royal_arch_future_candidates: royalArchLane.items,
      blocked_higher_degree_candidates: blockedLane.items,
      notebooklm_intake_candidates: notebooklmLane.items
    },
    merged_action_queue: mergedQueue
  };

  const reportArtifact = buildReport({
    inputs: queueArtifact.meta.inputs,
    level2Lane,
    level3Lane,
    royalArchLane,
    blockedLane,
    notebooklmLane,
    mergedQueue
  });
  const notebooklmLedger = buildNotebooklmLedger(notebooklmLane, resolved.reviewPacketOutput);
  const notebooklmReviewPacket = buildNotebooklmReviewPacket(notebooklmLane, resolved.ledgerOutput);

  writeJsonAtomic(resolved.queueOutput, queueArtifact);
  writeJsonAtomic(resolved.reportOutput, reportArtifact);
  writeJsonAtomic(resolved.ledgerOutput, notebooklmLedger);
  writeJsonAtomic(resolved.reviewPacketOutput, notebooklmReviewPacket);

  process.stdout.write(`Phase M.8 queue written: ${resolved.queueOutput}\n`);
  process.stdout.write(`Phase M.8 report written: ${resolved.reportOutput}\n`);
  process.stdout.write(`Phase M.8 ledger written: ${resolved.ledgerOutput}\n`);
  process.stdout.write(`Phase M.8 review packet written: ${resolved.reviewPacketOutput}\n`);
  process.stdout.write(`Level 2 actionable candidates: ${level2Lane.summary.actionable_count}\n`);
  process.stdout.write(`Level 3 native candidates: ${level3Lane.summary.total_candidates}\n`);
  process.stdout.write(`Royal Arch future-lane candidates: ${royalArchLane.summary.queue_count}\n`);
}

main();
