const fs = require("fs");
const path = require("path");

const FORBIDDEN_PATTERNS = {
  "Royal Arch": /Royal Arch/gi,
  "Lost Word": /Lost Word/gi,
  hiram: /\u05d7\u05d9\u05e8\u05dd/g,
  third_degree: /\u05d3\u05e8\u05d2\u05d4 \u05e9\u05dc\u05d9\u05e9\u05d9\u05ea/g,
  completion: /completion/gi,
  secret: /secret/gi,
  standalone_sod: /(?<!\p{L})\u05e1\u05d5\u05d3(?!\p{L})/gu,
  standalone_mila: /(?<!\p{L})\u05de\u05d9\u05dc\u05d4(?!\p{L})/gu,
};

const ENTRY_TYPE_BLOCKLIST = new Set(["category", "hub"]);
const PROCESS_CATEGORIES = new Set(["preparation", "ritual_flow", "inner_work"]);
const CATEGORY_SIGNAL_WEIGHTS = {
  preparation: 1.1,
  ritual_flow: 1.15,
  lodge_structure: 1.0,
  degree_board: 1.1,
  tools_and_signs: 1.0,
  obligation_and_law: 0.95,
  inner_work: 1.0,
  gate: 0.75,
  glossary_and_review: 0.55,
};
const DISCOVERY_SOURCE_BASE = {
  repeated_reference: 66,
  co_occurrence: 62,
  sequential_flow: 60,
  shared_category: 56,
};
const CATEGORY_TYPE_HINT = {
  preparation: "process",
  ritual_flow: "process",
  inner_work: "process",
  lodge_structure: "structure",
  degree_board: "system",
  tools_and_signs: "relationship",
  obligation_and_law: "relationship",
  gate: "structure",
  glossary_and_review: "relationship",
};
const GENERIC_SLUG_TOKENS = new Set([
  "l1",
  "level",
  "degree",
  "harishona",
  "badraga",
  "category",
  "landing",
  "what",
  "is",
  "mahi",
  "mahu",
  "and",
  "bein",
  "shel",
  "bemerkhav",
  "halishka",
  "ritual",
  "tools",
  "tool",
  "inner",
  "work",
  "gate",
  "glossary",
  "review",
  "board",
  "lodge",
  "flow",
  "obligation",
  "preparation",
]);

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function entryText(entry) {
  const keywords = (entry.keywords || []).join(" ");
  const aliases = (entry.aliases || []).join(" ");
  const related = ["prior", "companion", "deeper"]
    .flatMap((bucket) => ((entry.related_topics || {})[bucket] || []))
    .join(" ");
  return [
    entry.title || "",
    entry.short_summary || "",
    entry.full_summary || "",
    entry.symbolic_meaning || "",
    entry.candidate_lesson || "",
    keywords,
    aliases,
    related,
  ]
    .filter(Boolean)
    .join("\n");
}

function hasBoundaryRisk(entry) {
  const text = entryText(entry);
  return Object.values(FORBIDDEN_PATTERNS).some((pattern) => pattern.test(text));
}

function isDiscoveryEligible(entry) {
  return (
    entry.degree === "level1" &&
    !ENTRY_TYPE_BLOCKLIST.has(entry.type) &&
    entry.category !== "gate" &&
    entry.category !== "glossary_and_review" &&
    !hasBoundaryRisk(entry)
  );
}

function slugTokens(slug) {
  return slug
    .split("-")
    .filter((token) => token && !GENERIC_SLUG_TOKENS.has(token) && token.length > 2);
}

function chooseLabelTokens(slugs) {
  const counts = new Map();
  for (const slug of slugs) {
    for (const token of slugTokens(slug)) {
      counts.set(token, (counts.get(token) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([token]) => token)
    .slice(0, 5);
}

function buildCandidateTopic(slugs, suggestedType, family) {
  const tokens = chooseLabelTokens(slugs);
  const joined = (tokens.length ? tokens : [family, suggestedType]).slice(0, 4).join("-");
  return `level2-candidate-${joined}-${suggestedType}`;
}

function buildTitleHint(entryMap, slugs, suggestedType) {
  const titles = slugs.slice(0, 3).map((slug) => entryMap.get(slug).title);
  const prefix =
    suggestedType === "process"
      ? "Process cluster"
      : suggestedType === "structure"
      ? "Structure cluster"
      : suggestedType === "system"
      ? "System cluster"
      : "Relationship cluster";
  return `${prefix}: ${titles.join(" / ")}`;
}

function inferType(categories, discoverySources) {
  if (categories.has("degree_board") && categories.has("lodge_structure")) {
    return "system";
  }
  if (categories.has("degree_board") && categories.has("tools_and_signs")) {
    return "system";
  }
  if (categories.has("degree_board") && categories.has("inner_work")) {
    return "relationship";
  }
  if (categories.has("lodge_structure")) {
    return "structure";
  }
  if (categories.has("degree_board")) {
    return "system";
  }
  if (categories.has("tools_and_signs") && categories.has("obligation_and_law")) {
    return "relationship";
  }
  if (discoverySources.has("repeated_reference") && categories.size >= 2) {
    return "system";
  }
  if (categories.size === 1) {
    return CATEGORY_TYPE_HINT[[...categories][0]] || "structure";
  }
  if ([...categories].some((category) => PROCESS_CATEGORIES.has(category))) {
    return "process";
  }
  if (discoverySources.has("co_occurrence") && categories.size >= 2) {
    return "relationship";
  }
  return "structure";
}

function computeOverlap(candidateSlugs, existingLevel2Links) {
  let closestLevel2Slug = null;
  let maxJaccard = 0;
  let coverageRatio = 0;
  for (const [level2Slug, links] of existingLevel2Links) {
    if (!links.size) continue;
    const intersectionCount = [...candidateSlugs].filter((slug) => links.has(slug)).length;
    const unionCount = new Set([...candidateSlugs, ...links]).size;
    const jaccard = unionCount ? intersectionCount / unionCount : 0;
    const coverage = candidateSlugs.size ? intersectionCount / candidateSlugs.size : 0;
    if (jaccard > maxJaccard || (jaccard === maxJaccard && coverage > coverageRatio)) {
      closestLevel2Slug = level2Slug;
      maxJaccard = jaccard;
      coverageRatio = coverage;
    }
  }
  return {
    closest_level2_slug: closestLevel2Slug,
    max_jaccard: Number(maxJaccard.toFixed(3)),
    coverage_ratio: Number(coverageRatio.toFixed(3)),
  };
}

function candidateQualityScore(family, slugs, categories, centrality, overlap) {
  let score = DISCOVERY_SOURCE_BASE[family];
  score += slugs.length * 5;
  score += Math.min(
    12,
    Math.floor(slugs.reduce((sum, slug) => sum + (centrality.get(slug) || 0), 0) / slugs.length),
  );
  score += categories.size * 4;
  score += Math.floor(
    [...categories].reduce((sum, category) => sum + (CATEGORY_SIGNAL_WEIGHTS[category] || 0.8) * 3, 0),
  );
  if (overlap.coverage_ratio >= 0.8) score -= 35;
  else if (overlap.coverage_ratio >= 0.6) score -= 24;
  else if (overlap.coverage_ratio >= 0.4) score -= 12;
  if (categories.size === 1 && categories.has("glossary_and_review")) score -= 18;
  if (categories.size === 1 && categories.has("gate")) score -= 12;
  return score;
}

function confidenceFromScore(score) {
  return score >= 82 ? "high" : "medium";
}

function buildReason(family, entryMap, slugs, categories, suggestedType) {
  const titles = slugs.slice(0, 3).map((slug) => entryMap.get(slug).title);
  const opener =
    family === "co_occurrence"
      ? "Strong co-occurrence and mutual graph references"
      : family === "shared_category"
      ? "A dense shared-category cluster"
      : family === "sequential_flow"
      ? "A repeatable sequential flow across connected entries"
      : "A repeated reference center that organizes several entries";
  return `${opener} point to a Level 2 ${suggestedType} topic built from ${titles.join(
    " + ",
  )}. The cluster stays grounded in Level 1 while adding structure rather than recap. Primary categories: ${[
    ...categories,
  ]
    .sort()
    .join(", ")}.`;
}

function dedupeKey(slugs) {
  return [...new Set(slugs)].sort().join("|");
}

function buildGraph(level1Entries) {
  const adjacency = new Map();
  const inbound = new Map();
  const references = new Map();
  for (const [slug, entry] of level1Entries) {
    adjacency.set(slug, new Map());
    for (const [bucket, weight] of [
      ["prior", 2],
      ["companion", 3],
      ["deeper", 2],
    ]) {
      for (const relatedSlug of ((entry.related_topics || {})[bucket] || [])) {
        if (!level1Entries.has(relatedSlug)) continue;
        adjacency.get(slug).set(relatedSlug, (adjacency.get(slug).get(relatedSlug) || 0) + weight);
        inbound.set(relatedSlug, (inbound.get(relatedSlug) || 0) + 1);
        if (!references.has(relatedSlug)) references.set(relatedSlug, []);
        references.get(relatedSlug).push([slug, bucket]);
      }
    }
  }
  return { adjacency, inbound, references };
}

function centralityScores(adjacency, inbound) {
  const scores = new Map();
  for (const [slug, neighbors] of adjacency) {
    scores.set(
      slug,
      [...neighbors.values()].reduce((sum, value) => sum + value, 0),
    );
  }
  for (const [slug, count] of inbound) {
    scores.set(slug, (scores.get(slug) || 0) + count * 3);
  }
  return scores;
}

function sharedCategoryCandidates(level1Entries, centrality) {
  const byCategory = new Map();
  for (const [slug, entry] of level1Entries) {
    if (!byCategory.has(entry.category)) byCategory.set(entry.category, []);
    byCategory.get(entry.category).push(slug);
  }
  const raw = [];
  for (const [category, slugs] of byCategory) {
    if (slugs.length < 3) continue;
    const ranked = [...slugs].sort((left, right) => {
      const leftEntry = level1Entries.get(left);
      const rightEntry = level1Entries.get(right);
      const leftScore =
        (centrality.get(left) || 0) +
        (((leftEntry.related_topics || {}).companion || []).length * 2) +
        (leftEntry.keywords || []).length;
      const rightScore =
        (centrality.get(right) || 0) +
        (((rightEntry.related_topics || {}).companion || []).length * 2) +
        (rightEntry.keywords || []).length;
      return rightScore - leftScore;
    });
    raw.push(["shared_category", ranked.slice(0, Math.min(4, ranked.length))]);
    if (ranked.length >= 6) {
      const second = ranked.slice(2, 2 + Math.min(4, ranked.length - 2));
      if (second.length >= 3) raw.push(["shared_category", second]);
    }
  }
  return raw;
}

function repeatedReferenceCandidates(references, centrality) {
  const raw = [];
  const ranked = [...references.entries()].sort((left, right) => {
    const leftScore = left[1].length * 10 + (centrality.get(left[0]) || 0);
    const rightScore = right[1].length * 10 + (centrality.get(right[0]) || 0);
    return rightScore - leftScore;
  });
  for (const [centralSlug, inboundRecords] of ranked) {
    const uniqueReferencers = [];
    for (const [sourceSlug] of inboundRecords) {
      if (!uniqueReferencers.includes(sourceSlug)) uniqueReferencers.push(sourceSlug);
    }
    if (uniqueReferencers.length < 2) continue;
    raw.push(["repeated_reference", [centralSlug, ...uniqueReferencers.slice(0, 3)]]);
  }
  return raw;
}

function coOccurrenceCandidates(adjacency, centrality) {
  const slugs = [...adjacency.keys()].sort();
  const pairScores = [];
  for (let i = 0; i < slugs.length; i += 1) {
    for (let j = i + 1; j < slugs.length; j += 1) {
      const left = slugs[i];
      const right = slugs[j];
      const direct = (adjacency.get(left).get(right) || 0) + (adjacency.get(right).get(left) || 0);
      if (!direct) continue;
      const leftNeighbors = new Set(adjacency.get(left).keys());
      const rightNeighbors = new Set(adjacency.get(right).keys());
      const sharedNeighbors = [...leftNeighbors].filter((slug) => rightNeighbors.has(slug));
      const score =
        direct * 3 +
        sharedNeighbors.length * 2 +
        Math.min(centrality.get(left) || 0, 8) +
        Math.min(centrality.get(right) || 0, 8);
      pairScores.push([score, left, right, sharedNeighbors]);
    }
  }
  return pairScores
    .sort((left, right) => right[0] - left[0])
    .slice(0, 20)
    .map(([_score, left, right, sharedNeighbors]) => {
      const sortedShared = [...sharedNeighbors].sort(
        (a, b) => (centrality.get(b) || 0) - (centrality.get(a) || 0),
      );
      return ["co_occurrence", [...new Set([left, right, ...sortedShared.slice(0, 2)])].slice(0, 4)];
    });
}

function sequentialFlowCandidates(level1Entries) {
  const flowEdges = new Map();
  for (const [slug, entry] of level1Entries) {
    if (!PROCESS_CATEGORIES.has(entry.category)) continue;
    for (const deeperSlug of ((entry.related_topics || {}).deeper || [])) {
      if (!level1Entries.has(deeperSlug)) continue;
      if (!PROCESS_CATEGORIES.has(level1Entries.get(deeperSlug).category)) continue;
      if (!flowEdges.has(slug)) flowEdges.set(slug, []);
      flowEdges.get(slug).push(deeperSlug);
    }
  }
  const raw = [];
  for (const start of [...flowEdges.keys()].sort()) {
    const path = [start];
    const seen = new Set([start]);
    let current = start;
    while (flowEdges.has(current) && flowEdges.get(current).length) {
      const next = flowEdges.get(current)[0];
      if (seen.has(next)) break;
      path.push(next);
      seen.add(next);
      current = next;
      if (path.length >= 4) break;
    }
    if (path.length >= 3) raw.push(["sequential_flow", path]);
  }
  return raw;
}

function buildCandidates(level1Entries, existingLevel2Links) {
  const { adjacency, inbound, references } = buildGraph(level1Entries);
  const centrality = centralityScores(adjacency, inbound);
  const raw = [
    ...sharedCategoryCandidates(level1Entries, centrality),
    ...repeatedReferenceCandidates(references, centrality),
    ...coOccurrenceCandidates(adjacency, centrality),
    ...sequentialFlowCandidates(level1Entries),
  ];

  const accepted = new Map();
  const rejected = [];

  for (const [family, rawSlugs] of raw) {
    const uniqueSlugs = [...new Set(rawSlugs)].filter((slug) => level1Entries.has(slug));
    if (uniqueSlugs.length < 3) {
      rejected.push({
        family,
        based_on_entries: uniqueSlugs,
        reason: "Rejected because the cluster is too small; strong candidates need at least 3 linked entries.",
      });
      continue;
    }
    const categories = new Set(uniqueSlugs.map((slug) => level1Entries.get(slug).category));
    const overlap = computeOverlap(new Set(uniqueSlugs), existingLevel2Links);
    if (overlap.coverage_ratio >= 0.8) {
      rejected.push({
        family,
        based_on_entries: uniqueSlugs,
        reason: `Rejected as near-duplicate of existing ${overlap.closest_level2_slug}.`,
      });
      continue;
    }
    if (categories.size === 1 && categories.has("gate")) {
      rejected.push({
        family,
        based_on_entries: uniqueSlugs,
        reason: "Rejected because gate-only clusters read as Level 1 orientation recap rather than Level 2 structure.",
      });
      continue;
    }
    if (categories.has("gate") || categories.has("glossary_and_review")) {
      rejected.push({
        family,
        based_on_entries: uniqueSlugs,
        reason: "Rejected because gate/glossary material weakens Level 2 topic identity and tends to produce recap rather than structure.",
      });
      continue;
    }
    const suggestedType = inferType(categories, new Set([family]));
    const score = candidateQualityScore(family, uniqueSlugs, categories, centrality, overlap);
    if (score < 60) {
      rejected.push({
        family,
        based_on_entries: uniqueSlugs,
        reason: "Rejected because the cluster was too weak or too abstract after scoring.",
      });
      continue;
    }
    const candidate = {
      candidate_topic: buildCandidateTopic(uniqueSlugs, suggestedType, family),
      candidate_title_hint: buildTitleHint(level1Entries, uniqueSlugs, suggestedType),
      based_on_entries: uniqueSlugs,
      suggested_type: suggestedType,
      confidence: confidenceFromScore(score),
      reason: buildReason(family, level1Entries, uniqueSlugs, categories, suggestedType),
      discovery_sources: [family],
      score,
      basis_categories: [...categories].sort(),
      overlap_with_existing_level2: overlap,
    };
    const key = dedupeKey(uniqueSlugs);
    if (!accepted.has(key) || candidate.score > accepted.get(key).score) {
      accepted.set(key, candidate);
    }
  }

  const ranked = [...accepted.values()].sort((left, right) => {
    if (right.score !== left.score) return right.score - left.score;
    if (left.confidence !== right.confidence) return left.confidence === "high" ? -1 : 1;
    return left.overlap_with_existing_level2.coverage_ratio - right.overlap_with_existing_level2.coverage_ratio;
  });

  const selected = [];
  const selectedSets = [];
  const familyCounts = new Map();
  const typeCounts = new Map();
  const seenTopics = new Set();
  for (const candidate of ranked) {
    const candidateSet = new Set(candidate.based_on_entries);
    const overlapsTooMuch = selectedSets.some((selectedSet) => {
      const union = new Set([...selectedSet, ...candidateSet]);
      const intersectionCount = [...candidateSet].filter((slug) => selectedSet.has(slug)).length;
      return union.size && intersectionCount / union.size > 0.65;
    });
    if (overlapsTooMuch) continue;
    if (seenTopics.has(candidate.candidate_topic)) continue;
    const primaryFamily = candidate.discovery_sources[0];
    const familyCount = familyCounts.get(primaryFamily) || 0;
    if (familyCount >= 5) continue;
    const typeCount = typeCounts.get(candidate.suggested_type) || 0;
    if (typeCount >= 5) continue;
    selected.push(candidate);
    selectedSets.push(candidateSet);
    seenTopics.add(candidate.candidate_topic);
    familyCounts.set(primaryFamily, familyCount + 1);
    typeCounts.set(candidate.suggested_type, typeCount + 1);
    if (selected.length >= 15) break;
  }

  return { candidates: selected, rejected };
}

function main() {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    options[args[i]] = args[i + 1];
  }
  if (!options["--level1"] || !options["--level2"] || !options["--output"]) {
    throw new Error("Usage: node discover_level2_topic_candidates.js --level1 <path> --level2 <path> --output <path> [--max-candidates <n>]");
  }
  const maxCandidates = Number(options["--max-candidates"] || "15");
  const level1Payload = loadJson(options["--level1"]);
  const level2Payload = loadJson(options["--level2"]);

  const level1Entries = new Map(
    level1Payload.entries.filter(isDiscoveryEligible).map((entry) => [entry.slug, entry]),
  );
  const existingLevel2Links = level2Payload.entries.map((entry) => [
    entry.slug,
    new Set((entry.knowledge_links || []).filter((link) => link.degree === "level1").map((link) => link.slug)),
  ]);

  const { candidates, rejected } = buildCandidates(level1Entries, existingLevel2Links);
  const finalCandidates = candidates.slice(0, maxCandidates);

  const typeCounts = {};
  const confidenceCounts = {};
  const discoverySourceCounts = {};
  for (const candidate of finalCandidates) {
    typeCounts[candidate.suggested_type] = (typeCounts[candidate.suggested_type] || 0) + 1;
    confidenceCounts[candidate.confidence] = (confidenceCounts[candidate.confidence] || 0) + 1;
    discoverySourceCounts[candidate.discovery_sources[0]] =
      (discoverySourceCounts[candidate.discovery_sources[0]] || 0) + 1;
  }

  writeJson(options["--output"], {
    generated_at: new Date().toISOString().slice(0, 10),
    phase: "Phase M.3",
    goal: "Discover Level 2 topic candidates from the existing Level 1 graph without inventing unsupported coverage.",
    inputs: {
      level1_path: path.resolve(options["--level1"]).replace(/\\/g, "/"),
      level2_path: path.resolve(options["--level2"]).replace(/\\/g, "/"),
    },
    summary: {
      eligible_level1_entries: level1Entries.size,
      existing_level2_entries: level2Payload.entries.length,
      candidate_count: finalCandidates.length,
      type_counts: Object.fromEntries(Object.entries(typeCounts).sort()),
      confidence_counts: Object.fromEntries(Object.entries(confidenceCounts).sort()),
      discovery_source_counts: Object.fromEntries(Object.entries(discoverySourceCounts).sort()),
      recommended_selection: finalCandidates.slice(0, 8).map((candidate) => candidate.candidate_topic),
      overall_status: finalCandidates.length >= 10 ? "pass" : "pass-with-warnings",
    },
    candidates: finalCandidates.map((candidate, index) => ({
      rank: index + 1,
      ...candidate,
      target_partition_role: "core_degree_content",
      target_degree: "level2",
    })),
    rejected_candidates: rejected.slice(0, 20),
  });
}

main();
