#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");

const defaults = {
  queue: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_queue.json",
  report: "PDF_handle/TOOLS/data/phase_m_8_topic_discovery_report.json",
  level3SpecOutput: "PDF_handle/TOOLS/data/level3_boundary_seed_spec.json",
  royalArchSpecOutput: "PDF_handle/TOOLS/data/royal_arch_boundary_seed.json",
  level3GoldsetOutput: "PDF_handle/TOOLS/data/level3_boundary_goldset_seed.json",
  level2TriageOutput: "PDF_handle/TOOLS/data/phase_m_8_level2_top_triage_frames.json",
  seedReportOutput: "PDF_handle/TOOLS/data/phase_m_8_1_seed_report.json"
};

const level2FrameTemplates = {
  "level2-candidate-allegory-hadarim-hamisra-hamoamad-structure": {
    target_slug: "level2-threshold-officers-and-candidate-structure",
    target_title: "הסף, נושאי המשרה והמועמד כמבנה מעבר",
    level2_type: "structure",
    category: "lodge_structure_deep",
    knowledge_type: "lodge_structure",
    knowledge_goal: "לקרוא את הסף, נושאי המשרה והמפגש הראשוני עם המועמד כמבנה מעבר לימודי ולא רק כרצף של תחנות.",
    core_question: "איך הסף, השומר, נושאי המשרה והמועמד יוצרים יחד מבנה מעבר אחד?",
    structure_axes: ["סף", "שומר", "פגישה", "סמכות", "מעבר"],
    triage_reason:
      "This is the cleanest open lodge-structure candidate and it complements the existing chain-of-office entry without duplicating it."
  },
  "level2-candidate-even-gvil-gvila-hamaavar-relationship": {
    target_slug: "level2-rough-ashlar-transition-and-measure-relationship",
    target_title: "אבן הגוויל, המעבר ותיקון המידות כיחס אחד",
    level2_type: "relationship",
    category: "relationships_between_symbols",
    knowledge_type: "symbol",
    knowledge_goal: "להגדיר יחס בין חומר גלם, מעבר ותיקון מידות בלי לחזור למערכת הכלים שכבר נבנתה ב-Level 2.",
    core_question: "איך אבן הגוויל, המעבר ותיקון המידות מגדירים זה את זה כיחס אחד?",
    structure_axes: ["חומר גלם", "מעבר", "תיקון", "מידה", "צורה"],
    triage_reason:
      "This candidate stays distinct from the existing ashlar system by centering the relationship itself rather than the full symbolic system."
  },
  "level2-candidate-bamasa-cable-habakasha-hahovala-process": {
    target_slug: "level2-cable-tow-entry-and-guided-movement-process",
    target_title: "מן הבקשה אל ההובלה: תהליך הכניסה המודרכת",
    level2_type: "process",
    category: "ritual_dynamics",
    knowledge_type: "ritual",
    knowledge_goal: "לסדר את הבקשה, חבל המשיכה וההובלה הראשונה כתהליך חינוכי אחד של כניסה מודרכת.",
    core_question: "איך הבקשה, חבל המשיכה וההובלה הראשונית בונים תהליך כניסה אחד?",
    structure_axes: ["בקשה", "קשירה", "הולכה", "תחנות", "כניסה"],
    triage_reason:
      "This is the strongest open ritual-dynamics candidate and gives Level 2 a missing process lane around guided entry."
  }
};

const level3CategoryDescriptions = {
  symbolic_systems: {
    status: "proposed",
    description: "Native Level 3 symbolic systems centered on Hiram, loss, fidelity, and the third-degree symbolic field."
  },
  ritual_dynamics: {
    status: "proposed",
    description: "Native Level 3 process readings centered on raising, restoration, and degree-specific ritual movement."
  },
  relationships_between_symbols: {
    status: "proposed",
    description: "Native Level 3 symbol relationships such as grave, acacia, mortality, and continuity."
  }
};

const level3CandidateNotes = {
  "level3-candidate-hiram-loss-and-fidelity-system": {
    boundary_focus: "Native Master Mason identity built around Hiram, loss, fidelity, and the unresolved absence of the genuine word.",
    explicit_exclusions: [
      "Do not drift into Royal Arch recovery-of-the-word material.",
      "Do not treat appendant completion narratives as native Level 3 closure."
    ]
  },
  "level3-candidate-raising-and-restoration-process": {
    boundary_focus: "Native third-degree process centered on raising as restoration, completion, and passage through loss.",
    explicit_exclusions: [
      "Do not expand into later-degree restoration systems.",
      "Do not treat burial service as a standalone degree lane."
    ]
  },
  "level3-candidate-acacia-grave-and-immortality-relationship": {
    boundary_focus: "Native mortality relationship between grave, acacia, continuity, and the symbolic survival of what is not merely physical.",
    explicit_exclusions: [
      "Do not collapse into generic funeral instruction.",
      "Do not import Royal Arch vault or hidden-name symbolism."
    ]
  }
};

const level3GoldsetPreferredSources = {
  "level3-candidate-hiram-loss-and-fidelity-system": [
    "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree",
    "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
    "textbook-freemasonry-tracing-boards-en"
  ],
  "level3-candidate-raising-and-restoration-process": [
    "blue-lodge-ritual-reference-guide-2021-section-0075-charge-at-raising-to-the-sublime-degree-of-master-mason",
    "blue-lodge-ritual-reference-guide-2021-section-0058-master-mason-degree"
  ],
  "level3-candidate-acacia-grave-and-immortality-relationship": [
    "textbook-freemasonry-tracing-boards-en",
    "blue-lodge-ritual-reference-guide-2021-section-0078-ceremonies-at-the-grave",
    "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service"
  ]
};

const royalArchCategoryDescriptions = {
  vault_and_recovery_motifs: {
    status: "proposed",
    description: "Royal Arch motifs centered on hidden vaults, subterranean discovery, and recovered foundations."
  },
  names_words_and_recovery: {
    status: "proposed",
    description: "Royal Arch material centered on names, lost-word recovery, and verbal restoration systems."
  },
  return_and_restoration_histories: {
    status: "proposed",
    description: "Royal Arch historical-restoration frames centered on return from Babylon and restored continuity."
  }
};

const royalArchCandidateNotes = {
  royal_arch_hidden_vault_motifs: {
    category_id: "vault_and_recovery_motifs",
    boundary_focus: "Hidden vault, subterranean recovery, and rediscovered foundation motifs native to Royal Arch/Chapter framing.",
    explicit_exclusions: [
      "Do not collapse this into native Master Mason grave or raising material.",
      "Do not import this lane into Level 3 boundary approval."
    ]
  },
  royal_arch_names_and_word: {
    category_id: "names_words_and_recovery",
    boundary_focus: "Names, word-recovery, and recovered utterance systems that belong to Royal Arch rather than native Level 3.",
    explicit_exclusions: [
      "Do not treat recovery-of-the-word as native Level 3 closure.",
      "Do not flatten this lane into generic biblical naming motifs."
    ]
  },
  royal_arch_return_from_babylon: {
    category_id: "return_and_restoration_histories",
    boundary_focus: "Return-from-Babylon and restoration-history material that belongs to a separate Royal Arch historical-symbolic lane.",
    explicit_exclusions: [
      "Do not merge this historical restoration frame into Level 3 raising.",
      "Do not treat Babylon-return motifs as appendant detail inside Blue Lodge Level 3."
    ]
  }
};

function parseArgs(argv) {
  const options = { ...defaults };
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

function resolveRepoPath(targetPath) {
  return path.isAbsolute(targetPath) ? targetPath : path.resolve(repoRoot, targetPath);
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

function byCandidateTopic(items) {
  return new Map(items.map((item) => [item.candidate_topic, item]));
}

function uniqueBy(list, pickKey) {
  const seen = new Set();
  const output = [];
  for (const item of list) {
    const key = pickKey(item);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    output.push(item);
  }
  return output;
}

function buildLevel2TriageFrames(queue) {
  const level2Items = byCandidateTopic(queue.lanes.level2_graph_candidates || []);
  const frames = [];

  for (const [candidateTopic, template] of Object.entries(level2FrameTemplates)) {
    const candidate = level2Items.get(candidateTopic);
    if (!candidate) {
      throw new Error(`Missing required Level 2 candidate in M8 queue: ${candidateTopic}`);
    }

    frames.push({
      candidate_topic: candidate.candidate_topic,
      target_slug: template.target_slug,
      target_title: template.target_title,
      level2_type: template.level2_type,
      category: template.category,
      knowledge_type: template.knowledge_type,
      source_entries: candidate.source_anchor?.based_on_entries || [],
      knowledge_goal: template.knowledge_goal,
      core_question: template.core_question,
      structure_axes: template.structure_axes,
      triage_reason: template.triage_reason,
      source_rank: candidate.rank,
      source_confidence: candidate.confidence,
      overlap_with_existing_level2: candidate.overlap_with_existing_level2 || null
    });
  }

  return {
    meta: {
      phase: "phase_m8_1_level2_top_triage_frames",
      degree: "level2",
      generated_at: new Date().toISOString(),
      source_phase: "phase_m8_topic_discovery",
      purpose: "Promote the top open Level 2 candidates into controlled frame-ready artifacts without opening another broad discovery round.",
      build_count: frames.length
    },
    triage_rules: {
      source_selection: "top_actionable_only",
      count: frames.length,
      priority_rule: "top actionable candidates from phase_m_8_topic_discovery_report.json",
      non_goal: "No content fill or site writes."
    },
    topic_frames: frames
  };
}

function buildLevel3BoundarySpec(queue, report) {
  const level3Items = queue.lanes.level3_native_candidates || [];
  const royalArchItems = queue.lanes.royal_arch_future_candidates || [];
  const blockedItems = queue.lanes.blocked_higher_degree_candidates || [];
  const proposedCategories = uniqueBy(
    level3Items
      .map((item) => item.category_hint)
      .filter(Boolean)
      .map((categoryId) => ({
        id: categoryId,
        ...level3CategoryDescriptions[categoryId]
      })),
    (item) => item.id
  );

  return {
    meta: {
      phase: "phase_m8_1_level3_boundary_seed",
      generated_at: new Date().toISOString(),
      source_phase: "phase_m8_topic_discovery",
      status: "seed_ready_not_approved",
      purpose: "Turn the M8 Level 3 native discovery output into a controlled boundary seed spec before any Level 3 runtime build."
    },
    current_truth: {
      level3_runtime_exists: false,
      level3_degree_registry_exists: false,
      build_ready: false,
      discovery_candidate_count: report.summary?.level3?.total_candidates || level3Items.length
    },
    scope_statement: {
      native_center_of_gravity:
        "Level 3 is seeded here as native Master Mason content centered on Hiram, raising, loss, fidelity, grave, acacia, mortality, and continuity.",
      explicit_non_goals: [
        "Royal Arch recovery-of-the-word material routed to its own adjacent lane",
        "appendant or Chapter-only systems",
        "generic funeral administration as a standalone lane",
        "full ritual-detail leakage"
      ]
    },
    provisional_category_set: proposedCategories,
    boundary_rules: {
      keep_native_only_when: [
        "the source is clearly anchored in Master Mason or third-degree material",
        "the meaning is still readable without Royal Arch completion",
        "the candidate remains a native third-degree symbolic/process/relationship reading"
      ],
      reject_or_block_when: [
        "the material depends on Royal Arch names, hidden vault, or return-from-Babylon themes",
        "the material is appendant, Chapter, or later-degree by ownership",
        "the material is only generic funeral procedure without native third-degree symbolic center"
      ],
      non_negotiable_exclusions: blockedItems.map((item) => item.candidate_topic),
      redirected_adjacent_lanes: royalArchItems.map((item) => item.candidate_topic)
    },
    native_anchor_candidates: level3Items.map((item) => ({
      candidate_topic: item.candidate_topic,
      candidate_title_hint: item.candidate_title_hint,
      suggested_type: item.suggested_type,
      category_hint: item.category_hint,
      confidence: item.confidence,
      core_question: item.core_question,
      why_new: item.why_new,
      boundary_focus: level3CandidateNotes[item.candidate_topic]?.boundary_focus || "",
      explicit_exclusions: level3CandidateNotes[item.candidate_topic]?.explicit_exclusions || [],
      source_evidence_slugs: (item.source_anchor?.evidence_entries || []).map((entry) => entry.slug)
    })),
    blockers_before_build: [
      "approve the provisional Level 3 category set",
      "adjudicate a binding Level 3 boundary goldset",
      "decide whether the current candidate overlap is acceptable or needs consolidation",
      "keep Level 3 out of runtime until the boundary is approved"
    ]
  };
}

function buildRoyalArchBoundarySpec(queue, report) {
  const royalArchItems = queue.lanes.royal_arch_future_candidates || [];
  const proposedCategories = uniqueBy(
    royalArchItems
      .map((item) => royalArchCandidateNotes[item.candidate_topic]?.category_id || "unclassified_royal_arch")
      .map((categoryId) => ({
        id: categoryId,
        ...(royalArchCategoryDescriptions[categoryId] || {
          status: "proposed",
          description: "Royal Arch material that still needs narrower category design."
        })
      })),
    (item) => item.id
  );

  return {
    meta: {
      phase: "phase_m8_1_royal_arch_boundary_seed",
      generated_at: new Date().toISOString(),
      source_phase: "phase_m8_topic_discovery",
      status: "seed_ready_not_approved",
      purpose: "Create a separate adjacent-lane boundary seed for Royal Arch so it is not mixed into native Level 3."
    },
    current_truth: {
      runtime_exists: false,
      degree_registry_exists: false,
      build_ready: false,
      discovery_candidate_count: royalArchItems.length
    },
    relationship_to_level3: {
      adjacent_not_native: true,
      rule: "Royal Arch is modeled here as its own future lane and not as a Level 3 extension."
    },
    scope_statement: {
      center_of_gravity:
        "Royal Arch is seeded here around word recovery, hidden vault, restored names, and return/restoration histories that sit outside native Master Mason Level 3 ownership.",
      explicit_non_goals: [
        "Do not merge Royal Arch recovery systems into native Level 3 raising.",
        "Do not flatten Royal Arch into generic biblical research only.",
        "Do not publish a runtime lane before its adjacent-scope rules are approved."
      ]
    },
    provisional_category_set: proposedCategories,
    lane_candidates: royalArchItems.map((item) => ({
      candidate_topic: item.candidate_topic,
      candidate_title_hint: item.candidate_title_hint,
      category_hint: royalArchCandidateNotes[item.candidate_topic]?.category_id || null,
      queue_kind: item.queue_kind,
      source_unit_count: item.source_anchor?.unit_count || 0,
      sample_review_units: item.source_anchor?.sample_review_units || [],
      source_entry_slugs: item.source_anchor?.source_entry_slugs || [],
      boundary_focus: royalArchCandidateNotes[item.candidate_topic]?.boundary_focus || item.why_new,
      explicit_exclusions: royalArchCandidateNotes[item.candidate_topic]?.explicit_exclusions || []
    })),
    blockers_before_build: [
      "approve Royal Arch as a separate adjacent lane",
      "adjudicate a Royal Arch category set and naming convention",
      "decide whether Royal Arch should become a runtime lane or stay as preservation/research first",
      "keep Royal Arch outside Level 3 runtime and Level 3 goldset approval"
    ]
  };
}

function buildLevel3GoldsetSeed(queue) {
  const level3Items = queue.lanes.level3_native_candidates || [];
  const royalArchItems = queue.lanes.royal_arch_future_candidates || [];
  const blockedItems = queue.lanes.blocked_higher_degree_candidates || [];

  const positiveExamples = [];
  for (const item of level3Items) {
    const preferredSlugs = new Set(level3GoldsetPreferredSources[item.candidate_topic] || []);
    const evidenceEntries = item.source_anchor?.evidence_entries || [];
    const selectedEntries = evidenceEntries.filter((entry) => preferredSlugs.has(entry.slug));
    const fallbackEntries = selectedEntries.length > 0 ? selectedEntries : evidenceEntries.slice(0, 2);

    for (const entry of fallbackEntries) {
      positiveExamples.push({
        library_slug: entry.slug,
        title: entry.title,
        target_scope_class: "native_level3_candidate",
        target_candidate_topic: item.candidate_topic,
        rationale: `Positive native Level 3 anchor for ${item.candidate_topic}.`
      });
    }
  }

  return {
    schema_version: "seed-1.0.0",
    phase: "phase_m8_1_level3_boundary_goldset_seed",
    generated_at: new Date().toISOString(),
    status: "seed_not_binding_yet",
    positive_examples: positiveExamples,
    adjacent_lane_examples: royalArchItems.map((item) => ({
      adjacent_label: item.candidate_topic,
      target_outcome: "royal_arch_future_lane",
      rationale: item.why_new
    })),
    blocked_examples: blockedItems.map((item) => ({
      blocked_label: item.candidate_topic,
      target_outcome: "blocked_higher_degree_queue",
      rationale: item.why_new
    })),
    caution_examples: [
      {
        library_slug: "blue-lodge-ritual-reference-guide-2021-section-0077-burial-service",
        caution: "Use as a mortality/masonic-honor support anchor only, not as a standalone Level 3 product lane."
      },
      {
        library_slug: "textbook-freemasonry-tracing-boards-en",
        caution: "Use as a symbolic consolidation source only; do not let the tracing-board overview flatten native Level 3 identity."
      }
    ]
  };
}

function buildSeedReport({ level3Spec, royalArchSpec, level3GoldsetSeed, level2TriageFrames, queue, report }) {
  return {
    meta: {
      phase: "phase_m8_1_seed_outputs",
      generated_at: new Date().toISOString(),
      source_phase: "phase_m8_topic_discovery"
    },
    summary: {
      level3_seed_candidates: level3Spec.native_anchor_candidates.length,
      level3_proposed_categories: level3Spec.provisional_category_set.map((item) => item.id),
      level3_goldset_positive_examples: level3GoldsetSeed.positive_examples.length,
      royal_arch_adjacent_lane_candidates: royalArchSpec.lane_candidates.length,
      royal_arch_proposed_categories: royalArchSpec.provisional_category_set.map((item) => item.id),
      royal_arch_labels: royalArchSpec.lane_candidates.map((item) => item.candidate_topic),
      level3_blocked_labels: level3GoldsetSeed.blocked_examples.map((item) => item.blocked_label),
      level2_top_triage_frames: level2TriageFrames.topic_frames.length,
      level2_discovery_pressure: report.saturation_and_stop_rules?.level2_discovery_pressure || "unknown",
      merged_action_queue_count: queue.merged_action_queue?.length || 0
    },
    next_execution_path: [
      {
        step: "Approve Level 3 boundary direction",
        action:
          "Review level3_boundary_seed_spec.json and decide whether the three native candidates are the correct starting boundary set."
      },
      {
        step: "Adjudicate Level 3 goldset seed",
        action:
          "Turn level3_boundary_goldset_seed.json into a binding goldset before any level3 runtime or fill work."
      },
      {
        step: "Approve Royal Arch adjacent lane",
        action:
          "Use royal_arch_boundary_seed.json as the separate future-lane seed so Royal Arch never gets folded into Level 3."
      },
      {
        step: "Frame the top Level 2 triage set",
        action:
          "Use phase_m_8_level2_top_triage_frames.json as the next controlled framing/fill input instead of reopening broad discovery."
      }
    ],
    overall_status: "pass"
  };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const resolved = {
    queue: resolveRepoPath(options.queue),
    report: resolveRepoPath(options.report),
    level3SpecOutput: resolveRepoPath(options.level3SpecOutput),
    royalArchSpecOutput: resolveRepoPath(options.royalArchSpecOutput),
    level3GoldsetOutput: resolveRepoPath(options.level3GoldsetOutput),
    level2TriageOutput: resolveRepoPath(options.level2TriageOutput),
    seedReportOutput: resolveRepoPath(options.seedReportOutput)
  };

  const queue = readJson(resolved.queue);
  const report = readJson(resolved.report);

  const level2TriageFrames = buildLevel2TriageFrames(queue);
  const level3Spec = buildLevel3BoundarySpec(queue, report);
  const royalArchSpec = buildRoyalArchBoundarySpec(queue, report);
  const level3GoldsetSeed = buildLevel3GoldsetSeed(queue);
  const seedReport = buildSeedReport({
    level3Spec,
    royalArchSpec,
    level3GoldsetSeed,
    level2TriageFrames,
    queue,
    report
  });

  writeJsonAtomic(resolved.level3SpecOutput, level3Spec);
  writeJsonAtomic(resolved.royalArchSpecOutput, royalArchSpec);
  writeJsonAtomic(resolved.level3GoldsetOutput, level3GoldsetSeed);
  writeJsonAtomic(resolved.level2TriageOutput, level2TriageFrames);
  writeJsonAtomic(resolved.seedReportOutput, seedReport);

  process.stdout.write(`Level 3 boundary seed spec written: ${resolved.level3SpecOutput}\n`);
  process.stdout.write(`Royal Arch boundary seed written: ${resolved.royalArchSpecOutput}\n`);
  process.stdout.write(`Level 3 goldset seed written: ${resolved.level3GoldsetOutput}\n`);
  process.stdout.write(`Level 2 top triage frames written: ${resolved.level2TriageOutput}\n`);
  process.stdout.write(`Seed report written: ${resolved.seedReportOutput}\n`);
}

main();
