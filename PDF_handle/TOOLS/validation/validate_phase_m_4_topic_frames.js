const fs = require("fs");
const path = require("path");

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function main() {
  const args = process.argv.slice(2);
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    options[args[i]] = args[i + 1];
  }

  if (!options["--frames"] || !options["--level1"] || !options["--level2"] || !options["--candidates"] || !options["--output"]) {
    throw new Error(
      "Usage: node validate_phase_m_4_topic_frames.js --frames <path> --level1 <path> --level2 <path> --candidates <path> --output <path>",
    );
  }

  const framesPayload = loadJson(options["--frames"]);
  const level1Payload = loadJson(options["--level1"]);
  const level2Payload = loadJson(options["--level2"]);
  const candidatesPayload = loadJson(options["--candidates"]);

  const level1Slugs = new Set(level1Payload.entries.map((entry) => entry.slug));
  const level2Slugs = new Set(level2Payload.entries.map((entry) => entry.slug));
  const level2Categories = new Set(Object.keys(level2Payload.categories || {}));
  const candidateMap = new Map((candidatesPayload.candidates || []).map((candidate) => [candidate.candidate_topic, candidate]));

  const findings = [];
  const seenTargetSlugs = new Set();

  if ((framesPayload.meta || {}).degree !== "level2") {
    findings.push({
      severity: "error",
      scope: "meta.degree",
      message: "Frames artifact must declare degree=level2.",
    });
  }

  if ((framesPayload.meta || {}).build_count !== (framesPayload.topic_frames || []).length) {
    findings.push({
      severity: "error",
      scope: "meta.build_count",
      message: "meta.build_count does not match the number of topic frames.",
    });
  }

  for (const frame of framesPayload.topic_frames || []) {
    const frameScope = frame.target_slug || frame.candidate_topic || "unknown-frame";

    if (!candidateMap.has(frame.candidate_topic)) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `candidate_topic ${frame.candidate_topic} does not exist in level2_topic_candidates.json.`,
      });
    } else {
      const candidate = candidateMap.get(frame.candidate_topic);
      const missingFromCandidate = (frame.source_entries || []).filter(
        (slug) => !(candidate.based_on_entries || []).includes(slug),
      );
      if (missingFromCandidate.length) {
        findings.push({
          severity: "warning",
          scope: frameScope,
          message: `source_entries diverge from candidate basis: ${missingFromCandidate.join(", ")}.`,
        });
      }
    }

    if (!["system", "structure", "process", "relationship"].includes(frame.level2_type)) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `Invalid level2_type: ${frame.level2_type}.`,
      });
    }

    if (!level2Categories.has(frame.category)) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `Category ${frame.category} does not exist in level2.json.`,
      });
    }

    if (level2Slugs.has(frame.target_slug)) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `target_slug ${frame.target_slug} already exists in level2.json.`,
      });
    }

    if (seenTargetSlugs.has(frame.target_slug)) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `Duplicate target_slug ${frame.target_slug} inside frames artifact.`,
      });
    }
    seenTargetSlugs.add(frame.target_slug);

    const missingLevel1Sources = (frame.source_entries || []).filter((slug) => !level1Slugs.has(slug));
    if (missingLevel1Sources.length) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: `Missing source_entries in level1.json: ${missingLevel1Sources.join(", ")}.`,
      });
    }

    if (!frame.knowledge_goal || !frame.core_question) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: "Each frame must define both knowledge_goal and core_question.",
      });
    }

    if (!Array.isArray(frame.structure_axes) || frame.structure_axes.length < 3) {
      findings.push({
        severity: "error",
        scope: frameScope,
        message: "Each frame must contain at least 3 structure_axes.",
      });
    }
  }

  const errorCount = findings.filter((finding) => finding.severity === "error").length;
  const warningCount = findings.filter((finding) => finding.severity === "warning").length;

  writeJson(options["--output"], {
    generated_at: new Date().toISOString(),
    phase: "phase_m4a",
    inputs: {
      frames_path: path.resolve(options["--frames"]).replace(/\\/g, "/"),
      level1_path: path.resolve(options["--level1"]).replace(/\\/g, "/"),
      level2_path: path.resolve(options["--level2"]).replace(/\\/g, "/"),
      candidates_path: path.resolve(options["--candidates"]).replace(/\\/g, "/"),
    },
    summary: {
      topic_frame_count: (framesPayload.topic_frames || []).length,
      error_count: errorCount,
      warning_count: warningCount,
      overall_status: errorCount === 0 ? "pass" : "fail",
    },
    findings,
  });
}

main();
