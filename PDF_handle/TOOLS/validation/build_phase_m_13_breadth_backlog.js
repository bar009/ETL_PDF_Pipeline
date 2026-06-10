const fs = require("fs");
const path = require("path");
const { getWorkSiteRoot, resolveWorkspacePath } = require("../lib/site_roots");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const DEFAULT_QUEUE_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_8_topic_discovery_queue.json");
const DEFAULT_LEVEL2_PATH = path.join(getWorkSiteRoot(), "data", "level2.json");
const DEFAULT_LEVEL3_PATH = path.join(getWorkSiteRoot(), "data", "level3.json");
const DEFAULT_GOLDSET_PATH = path.join(ROOT, "PDF_handle", "TOOLS", "data", "level3_boundary_goldset_seed.json");
const DEFAULT_JSON_OUTPUT = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_13_breadth_backlog.json");
const DEFAULT_MD_OUTPUT = path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_13_breadth_backlog.md");

const LEVEL3_DERIVED_CANDIDATES = [
  {
    queue_id: "level3-breadth-01-charge-and-duty-framework",
    title_hint: "מטען ההקמה וחובת רב־בונה כמסגרת",
    slug_hint: "level3-charge-and-duty-framework",
    priority: "high",
    confidence: "medium",
    suggested_type: "structure",
    category_hint: null,
    next_gate: "frame_before_fill",
    why_new:
      "The current Level 3 lane covers raising structurally, but it does not yet isolate the charge-at-raising and duty framework as its own topic.",
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
      "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree"
    ]
  },
  {
    queue_id: "level3-breadth-02-burial-honor-and-memorial-structure",
    title_hint: "כבוד הקבורה והזיכרון כמבנה דרגה שלישית",
    slug_hint: "level3-burial-honor-and-memorial-structure",
    priority: "high",
    confidence: "medium",
    suggested_type: "structure",
    category_hint: null,
    next_gate: "frame_before_fill",
    why_new:
      "The current Level 3 lane uses burial-service anchors, but it does not yet split out a dedicated memorial-honor structure topic.",
    source_anchor: [
      "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service",
      "blue-lodge-ritual-reference-guide-2021-section-0078-ceremonies-at-the-grave"
    ]
  },
  {
    queue_id: "level3-breadth-03-third-degree-tracing-board-map",
    title_hint: "לוח הדרגה השלישית כמפת משמעות",
    slug_hint: "level3-third-degree-tracing-board-map",
    priority: "medium",
    confidence: "medium",
    suggested_type: "system",
    category_hint: "symbolic_systems",
    next_gate: "frame_before_fill",
    why_new:
      "The tracing-board anchor currently supports several Level 3 entries, but it is not yet represented as its own mapping topic.",
    source_anchor: [
      "textbook-freemasonry-tracing-boards-en",
      "textbook-freemasonry-tracing-boards-he"
    ]
  }
];

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const queue = loadJson(config.queuePath);
  const level2 = loadJson(config.level2Path);
  const level3 = loadJson(config.level3Path);
  const goldset = loadJson(config.goldsetPath);

  const level2Entries = level2.entries || [];
  const level2Signals = level2Entries.map((entry) => ({
    slug: entry.slug,
    title: entry.title,
    basis: collectEntryBasis(entry)
  }));

  const level2Candidates = (queue.lanes?.level2_graph_candidates || [])
    .filter((candidate) => candidate.is_actionable === true)
    .map((candidate) => {
      const basis = collectCandidateBasis(candidate);
      const overlap = findTopCoverage(basis, level2Signals);
      return {
        queue_id: candidate.queue_id,
        title_hint: candidate.candidate_title_hint,
        slug_hint: candidate.target_slug_hint,
        priority: candidate.priority,
        confidence: candidate.confidence,
        suggested_type: candidate.suggested_type,
        category_hint: candidate.category_hint,
        score: candidate.score,
        source_anchor: basis,
        likely_covered_by: overlap.slug,
        max_basis_overlap_ratio: overlap.ratio,
        coverage_status: overlap.ratio >= 0.5 ? "likely_already_covered" : "unresolved",
        why_new: candidate.why_new
      };
    });

  const unresolvedLevel2 = level2Candidates
    .filter((candidate) => candidate.coverage_status === "unresolved")
    .sort(compareBacklogPriority);
  const splitLevel2 = level2Candidates
    .filter(
      (candidate) =>
        candidate.coverage_status === "likely_already_covered" &&
        (candidate.slug_hint === null || candidate.max_basis_overlap_ratio < 1)
    )
    .sort(compareBacklogPriority);

  const existingLevel3Slugs = new Set((level3.entries || []).map((entry) => entry.slug));
  const existingLevel3Links = new Set(
    (level3.entries || []).flatMap((entry) => (entry.knowledge_links || []).map((link) => link.slug))
  );

  const derivedLevel3 = LEVEL3_DERIVED_CANDIDATES.map((candidate) => {
    const linkedAnchorCount = candidate.source_anchor.filter((slug) => existingLevel3Links.has(slug)).length;
    return {
      ...candidate,
      source_anchor_count: candidate.source_anchor.length,
      anchor_already_supporting_current_lane: linkedAnchorCount,
      readiness: "candidate_not_framed"
    };
  }).sort(compareBacklogPriority);

  const backlog = {
    phase: "phase_m13_breadth_backlog",
    generated_at: new Date().toISOString(),
    inputs: {
      queue_path: slash(config.queuePath),
      level2_path: slash(config.level2Path),
      level3_path: slash(config.level3Path),
      goldset_path: slash(config.goldsetPath)
    },
    current_state: {
      level2_entry_count: level2Entries.length,
      level3_entry_count: (level3.entries || []).length,
      level3_existing_slugs: Array.from(existingLevel3Slugs).sort(),
      level3_positive_anchor_count: (goldset.positive_examples || []).length
    },
    level2: {
      actionable_candidates_seen: level2Candidates.length,
      unresolved_candidate_count: unresolvedLevel2.length,
      unresolved_candidates: unresolvedLevel2,
      split_candidate_count: splitLevel2.length,
      split_candidates: splitLevel2
    },
    level3: {
      core_entry_count: (level3.entries || []).length,
      breadth_candidate_count: derivedLevel3.length,
      derived_breadth_candidates: derivedLevel3
    },
    recommended_next_wave: {
      level2: (unresolvedLevel2.length ? unresolvedLevel2 : splitLevel2).slice(0, 6).map((candidate) => candidate.queue_id),
      level3: derivedLevel3.slice(0, 3).map((candidate) => candidate.queue_id)
    }
  };

  const md = renderMarkdown(backlog);
  writeFile(config.jsonOutput, `${JSON.stringify(backlog, null, 2)}\n`);
  writeFile(config.mdOutput, md);

  process.stdout.write(
    `${JSON.stringify(
      {
        json_output: slash(config.jsonOutput),
        md_output: slash(config.mdOutput),
        unresolved_level2: backlog.level2.unresolved_candidate_count,
        level3_breadth_candidates: backlog.level3.breadth_candidate_count
      },
      null,
      2
    )}\n`
  );
}

function renderMarkdown(backlog) {
  const lines = [];
  lines.push("# Phase M.13 Breadth Backlog");
  lines.push("");
  lines.push(`Generated: ${backlog.generated_at}`);
  lines.push("");
  lines.push("## Current State");
  lines.push("");
  lines.push(`- Level 2 entries: ${backlog.current_state.level2_entry_count}`);
  lines.push(`- Level 3 entries: ${backlog.current_state.level3_entry_count}`);
  lines.push(`- Level 2 unresolved breadth candidates: ${backlog.level2.unresolved_candidate_count}`);
  lines.push(`- Level 2 split candidates: ${backlog.level2.split_candidate_count}`);
  lines.push(`- Level 3 breadth candidates: ${backlog.level3.breadth_candidate_count}`);
  lines.push("");
  lines.push("## Recommended Next Wave");
  lines.push("");
  for (const queueId of backlog.recommended_next_wave.level2) {
    const item = backlog.level2.unresolved_candidates.find((candidate) => candidate.queue_id === queueId);
    if (item) lines.push(`- Level 2: ${item.title_hint}`);
  }
  for (const queueId of backlog.recommended_next_wave.level3) {
    const item = backlog.level3.derived_breadth_candidates.find((candidate) => candidate.queue_id === queueId);
    if (item) lines.push(`- Level 3: ${item.title_hint}`);
  }
  lines.push("");
  lines.push("## Level 2 Unresolved Candidates");
  lines.push("");
  for (const candidate of backlog.level2.unresolved_candidates) {
    lines.push(
      `- ${candidate.queue_id}: ${candidate.title_hint} | priority=${candidate.priority} | overlap=${candidate.max_basis_overlap_ratio.toFixed(
        2
      )}`
    );
  }
  lines.push("");
  lines.push("## Level 2 Split Candidates");
  lines.push("");
  for (const candidate of backlog.level2.split_candidates) {
    lines.push(
      `- ${candidate.queue_id}: ${candidate.title_hint} | priority=${candidate.priority} | overlap=${candidate.max_basis_overlap_ratio.toFixed(
        2
      )}`
    );
  }
  lines.push("");
  lines.push("## Level 3 Derived Breadth Candidates");
  lines.push("");
  for (const candidate of backlog.level3.derived_breadth_candidates) {
    lines.push(`- ${candidate.queue_id}: ${candidate.title_hint} | priority=${candidate.priority}`);
  }
  lines.push("");
  return `${lines.join("\n")}\n`;
}

function collectCandidateBasis(candidate) {
  return unique(candidate.source_anchor?.based_on_entries || []);
}

function collectEntryBasis(entry) {
  const relies = Array.isArray(entry.relies_on_level1_topics) ? entry.relies_on_level1_topics : [];
  const links = (entry.knowledge_links || [])
    .filter((link) => link.degree === "level1")
    .map((link) => link.slug);
  return unique([...relies, ...links]);
}

function findTopCoverage(candidateBasis, entrySignals) {
  if (candidateBasis.length === 0) {
    return { slug: null, ratio: 0 };
  }
  let best = { slug: null, ratio: 0 };
  for (const entry of entrySignals) {
    const shared = candidateBasis.filter((item) => entry.basis.includes(item));
    const ratio = shared.length / candidateBasis.length;
    if (ratio > best.ratio) {
      best = { slug: entry.slug, ratio };
    }
  }
  return best;
}

function compareBacklogPriority(a, b) {
  const priorityScore = { high: 3, medium: 2, low: 1, info: 0 };
  const pa = priorityScore[a.priority] ?? 0;
  const pb = priorityScore[b.priority] ?? 0;
  if (pb !== pa) return pb - pa;
  return (b.score || 0) - (a.score || 0) || a.queue_id.localeCompare(b.queue_id);
}

function unique(items) {
  return [...new Set(items)];
}

function resolveConfig(options) {
  return {
    queuePath: resolvePath(options.queue, DEFAULT_QUEUE_PATH),
    level2Path: resolvePath(options.level2, DEFAULT_LEVEL2_PATH),
    level3Path: resolvePath(options.level3, DEFAULT_LEVEL3_PATH),
    goldsetPath: resolvePath(options.goldset, DEFAULT_GOLDSET_PATH),
    jsonOutput: resolvePath(options.json, DEFAULT_JSON_OUTPUT),
    mdOutput: resolvePath(options.md, DEFAULT_MD_OUTPUT)
  };
}

function resolvePath(value, fallback) {
  if (typeof value === "string" && value.trim()) {
    return resolveWorkspacePath(value.trim());
  }
  return fallback;
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
      continue;
    }
    options[key] = next;
    index += 1;
  }
  return options;
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeFile(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function slash(filePath) {
  return path.resolve(filePath).replace(/\\/g, "/");
}

main();
