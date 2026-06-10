#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  ROOT,
  getLiveSiteRoot,
  getPublishedSitesRoot,
  getWorkSiteRoot,
  resolveWorkspacePath,
} = require("../lib/site_roots");

const TOOLS_DIR = path.resolve(__dirname, "..");

const DEFAULTS = {
  sandboxSiteRoot: getWorkSiteRoot({ requireRuntimeAssets: true }),
  level1Path: path.join(getLiveSiteRoot(), "data", "level1.json"),
  level2Path: path.join(getWorkSiteRoot(), "data", "level2.json"),
  libraryPath: path.join(getWorkSiteRoot(), "data", "library.json"),
  notebooklmIntake: path.join(ROOT, "experiments", "notebooklm_validation", "discovery_mindmap_intake.json"),
  futureEntryRoot: path.join(ROOT, "PDF_handle", "preservation", "future_entries"),
  reportRoot: path.join(ROOT, "PDF_handle", "TOOLS", "reports", "phase_m_9_post_pdf_full_planning_bundle"),
  latestPointer: path.join(ROOT, "PDF_handle", "TOOLS", "data", "phase_m_9_post_pdf_full_planning_latest.json")
};

function main() {
  const options = parseArgs(process.argv.slice(2));
  const config = resolveConfig(options);
  const executedAt = new Date().toISOString();
  const bundleDir = resolveBundleDir(config.bundleDir);

  fs.mkdirSync(bundleDir, { recursive: true });

  const paths = {
    degreeReadinessAudit: path.join(bundleDir, "degree_readiness_audit.json"),
    m5ReportDir: path.join(bundleDir, "phase_m_5_post_fill_audit"),
    m7Smoke: path.join(bundleDir, "phase_m_7_full_system_smoke_report.json"),
    m8Queue: path.join(bundleDir, "phase_m_8_topic_discovery_queue.json"),
    m8Report: path.join(bundleDir, "phase_m_8_topic_discovery_report.json"),
    level3SeedSpec: path.join(bundleDir, "level3_boundary_seed_spec.json"),
    royalArchSeedSpec: path.join(bundleDir, "royal_arch_boundary_seed.json"),
    level3GoldsetSeed: path.join(bundleDir, "level3_boundary_goldset_seed.json"),
    level2TriageFrames: path.join(bundleDir, "phase_m_8_level2_top_triage_frames.json"),
    m8SeedReport: path.join(bundleDir, "phase_m_8_1_seed_report.json"),
    bundleReport: path.join(bundleDir, "phase_m_9_post_pdf_full_planning_bundle_report.json"),
    bundleSummary: path.join(bundleDir, "phase_m_9_post_pdf_full_planning_bundle_summary.md")
  };

  const runLog = [];

  runLog.push(
    runNodeScript("audit_degree_readiness.js", [
      "--site-root",
      config.sandboxSiteRoot,
      "--published-site-root",
      config.publishedSiteRoot,
      "--output",
      paths.degreeReadinessAudit
    ])
  );

  const m5Run = runNodeScript("run_phase_m_5_post_fill_audit.js", [
    "--level2",
    config.level2Path,
    "--level1",
    config.level1Path,
    "--library",
    config.libraryPath,
    "--report-dir",
    paths.m5ReportDir
  ]);
  runLog.push(m5Run);

  runLog.push(
    runNodeScript("run_phase_m_7_full_system_smoke.js", [
      "--sandbox",
      path.join(config.sandboxSiteRoot, "data"),
      "--published",
      path.join(config.publishedSiteRoot, "data"),
      "--output",
      paths.m7Smoke
    ])
  );

  runLog.push(
    runNodeScript("run_phase_m_8_topic_discovery.js", [
      "--level1",
      config.level1Path,
      "--level2",
      config.level2Path,
      "--library",
      config.libraryPath,
      "--futureEntryRoot",
      config.futureEntryRoot,
      "--notebooklmIntake",
      config.notebooklmIntake,
      "--queueOutput",
      paths.m8Queue,
      "--reportOutput",
      paths.m8Report
    ])
  );

  runLog.push(
    runNodeScript("run_phase_m_8_1_seed_specs.js", [
      "--queue",
      paths.m8Queue,
      "--report",
      paths.m8Report,
      "--level3SpecOutput",
      paths.level3SeedSpec,
      "--royalArchSpecOutput",
      paths.royalArchSeedSpec,
      "--level3GoldsetOutput",
      paths.level3GoldsetSeed,
      "--level2TriageOutput",
      paths.level2TriageFrames,
      "--seedReportOutput",
      paths.m8SeedReport
    ])
  );

  const degreeReadiness = readJson(paths.degreeReadinessAudit);
  const m5Audit = readJson(path.join(paths.m5ReportDir, "phase_m_5_post_fill_audit.json"));
  const m7Smoke = readJson(paths.m7Smoke);
  const m8Report = readJson(paths.m8Report);
  const level3SeedSpec = readJson(paths.level3SeedSpec);
  const royalArchSeedSpec = readJson(paths.royalArchSeedSpec);
  const level3GoldsetSeed = readJson(paths.level3GoldsetSeed);
  const level2TriageFrames = readJson(paths.level2TriageFrames);
  const m8SeedReport = readJson(paths.m8SeedReport);
  const m7FailedChecks = Object.entries(m7Smoke.checks || {})
    .filter(([, value]) => value && value.pass === false)
    .map(([check, value]) => ({
      check,
      critical: value.critical === true,
      detail: value.detail || ""
    }));

  const bundleReport = {
    meta: {
      phase: "phase_m9_post_pdf_full_planning_bundle",
      executed_at: executedAt,
      mode: "post_pdf_full_planning_bundle",
      provider_policy: "no_new_provider_calls",
      notebooklm_calls: 0,
      gemini_calls: 0,
      purpose:
        "Rerun the full post-PDF planning stack from existing local data so topic allocation, validation, and Level 3 seeding are ready without repeating the initial token-heavy PDF stage."
    },
    inputs: {
      sandbox_site_root: config.sandboxSiteRoot,
      published_site_root: config.publishedSiteRoot,
      level1_path: config.level1Path,
      level2_path: config.level2Path,
      library_path: config.libraryPath,
      future_entry_root: config.futureEntryRoot,
      notebooklm_intake: config.notebooklmIntake
    },
    outputs: {
      bundle_dir: bundleDir,
      degree_readiness_audit: paths.degreeReadinessAudit,
      m5_report_dir: paths.m5ReportDir,
      m7_smoke_report: paths.m7Smoke,
      m8_queue: paths.m8Queue,
      m8_report: paths.m8Report,
      level3_boundary_seed_spec: paths.level3SeedSpec,
      royal_arch_boundary_seed: paths.royalArchSeedSpec,
      level3_boundary_goldset_seed: paths.level3GoldsetSeed,
      level2_top_triage_frames: paths.level2TriageFrames,
      m8_seed_report: paths.m8SeedReport
    },
    execution_log: runLog,
    summary: {
      degree_readiness_architecture_truth: degreeReadiness.summary?.architecture_truth || "",
      m5_lane_status: m5Audit.overall_status,
      m7_overall_status: m7Smoke.overall_status,
      m7_critical_failures: m7Smoke.critical_failures,
      m7_error_count: m7Smoke.error_count,
      level2_actionable_candidates: m8Report.summary?.level2?.actionable_count || 0,
      level2_top_actionable: m8Report.summary?.level2?.top_actionable || [],
      level3_seed_candidates: level3SeedSpec.native_anchor_candidates?.length || 0,
      level3_seed_topics: (level3SeedSpec.native_anchor_candidates || []).map((item) => item.candidate_topic),
      royal_arch_future_candidates: royalArchSeedSpec.lane_candidates?.length || 0,
      royal_arch_future_topics: (royalArchSeedSpec.lane_candidates || []).map((item) => item.candidate_topic),
      blocked_higher_degree_labels: level3GoldsetSeed.blocked_examples?.map((item) => item.blocked_label) || [],
      level2_triage_frame_count: level2TriageFrames.topic_frames?.length || 0,
      m7_failed_checks: m7FailedChecks.map((item) => item.check)
    },
    residual_warnings: m7FailedChecks,
    next_execution_path: [
      {
        step: "Level 2 framing/fill",
        action:
          "Use the generated triage frames as the next controlled Level 2 framing set instead of opening a broader discovery wave.",
        artifact: paths.level2TriageFrames
      },
      {
        step: "Level 3 boundary approval",
        action:
          "Review and adjudicate the Level 3 seed spec and goldset seed before creating any level3 runtime file.",
        artifacts: [paths.level3SeedSpec, paths.level3GoldsetSeed]
      },
      {
        step: "Royal Arch adjacent-lane approval",
        action:
          "Treat Royal Arch as its own future lane using the dedicated boundary seed, not as blocked Level 3 residue.",
        artifact: paths.royalArchSeedSpec
      },
      {
        step: "Smoke follow-up",
        action:
          m7Smoke.critical_failures > 0
            ? "Resolve critical smoke blockers before treating the full system as stable."
            : "Only non-critical smoke issues remain; topic planning can proceed without reopening the post-PDF stack."
      }
    ],
    overall_status: deriveOverallStatus({ m5Audit, m7Smoke, m8SeedReport })
  };

  writeJson(paths.bundleReport, bundleReport);
  writeFile(paths.bundleSummary, buildMarkdownSummary(bundleReport));
  writeJson(DEFAULTS.latestPointer, {
    phase: "phase_m9_post_pdf_full_planning_bundle",
    updated_at: executedAt,
    bundle_dir: bundleDir,
    bundle_report: paths.bundleReport,
    bundle_summary: paths.bundleSummary,
    overall_status: bundleReport.overall_status
  });

  process.stdout.write(`Planning bundle completed: ${bundleDir}\n`);
  process.stdout.write(`Bundle report: ${paths.bundleReport}\n`);
  process.stdout.write(`Bundle summary: ${paths.bundleSummary}\n`);
}

function parseArgs(args) {
  const parsed = {};
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = args[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = next;
    index += 1;
  }
  return parsed;
}

function resolveConfig(options) {
  return {
    sandboxSiteRoot: resolvePathOption(options["sandbox-site-root"], DEFAULTS.sandboxSiteRoot),
    publishedSiteRoot: resolvePublishedSiteRoot(options["published-site-root"]),
    level1Path: resolvePathOption(options.level1, DEFAULTS.level1Path),
    level2Path: resolvePathOption(options.level2, DEFAULTS.level2Path),
    libraryPath: resolvePathOption(options.library, DEFAULTS.libraryPath),
    notebooklmIntake: resolvePathOption(options["notebooklm-intake"] || options.notebooklmIntake, DEFAULTS.notebooklmIntake),
    futureEntryRoot: resolvePathOption(options["future-entry-root"] || options.futureEntryRoot, DEFAULTS.futureEntryRoot),
    bundleDir: options["bundle-dir"] || "",
  };
}

function resolvePublishedSiteRoot(explicitPath) {
  if (explicitPath) {
    return resolvePathOption(explicitPath, explicitPath);
  }

  const publishedRoot = getPublishedSitesRoot();
  const candidates = fs.existsSync(publishedRoot)
    ? fs.readdirSync(publishedRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
    : [];

  const semverCandidates = candidates
    .map((name) => ({ name, parsed: parseLiveVersion(name) }))
    .filter((item) => item.parsed);

  if (semverCandidates.length > 0) {
    semverCandidates.sort((left, right) => compareVersionTuples(right.parsed.version, left.parsed.version));
    return path.join(publishedRoot, semverCandidates[0].name);
  }

  return getLiveSiteRoot({ requireRuntimeAssets: true });
}

function parseLiveVersion(name) {
  const match = /^(\d+)\.(\d+)(?:\.(\d+))?-live-/u.exec(name);
  if (!match) return null;
  return {
    version: [Number(match[1]), Number(match[2]), Number(match[3] || 0)]
  };
}

function compareVersionTuples(left, right) {
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const leftPart = left[index] || 0;
    const rightPart = right[index] || 0;
    if (leftPart !== rightPart) {
      return leftPart - rightPart;
    }
  }
  return 0;
}

function resolveBundleDir(explicitPath) {
  if (explicitPath) {
    return resolvePathOption(explicitPath, explicitPath);
  }
  return path.join(DEFAULTS.reportRoot, buildTimestampDir());
}

function resolvePathOption(value, fallback) {
  return resolveWorkspacePath(value || fallback);
}

function buildTimestampDir() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}-${pad(
    now.getMinutes()
  )}-${pad(now.getSeconds())}Z`;
}

function runNodeScript(scriptName, args) {
  const scriptPath = path.join(TOOLS_DIR, scriptName);
  const result = spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: ROOT,
    encoding: "utf8"
  });

  const logEntry = {
    script: scriptPath,
    args,
    exit_code: result.status ?? 0,
    stdout: (result.stdout || "").trim(),
    stderr: (result.stderr || "").trim()
  };

  if (result.status !== 0) {
    throw new Error(
      `Script failed: ${scriptName}\n${logEntry.stdout}\n${logEntry.stderr}`.trim()
    );
  }

  return logEntry;
}

function deriveOverallStatus({ m5Audit, m7Smoke, m8SeedReport }) {
  if (m7Smoke.critical_failures > 0) {
    return "fail";
  }
  if (m5Audit.overall_status === "fail") {
    return "fail";
  }
  if (m7Smoke.error_count > 0 || m5Audit.overall_status === "pass-with-warnings") {
    return "pass-with-warnings";
  }
  return m8SeedReport.overall_status === "pass" ? "pass" : "pass-with-warnings";
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function writeFile(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, payload, "utf8");
}

function buildMarkdownSummary(bundleReport) {
  const lines = [
    "# Post-PDF Full Planning Bundle",
    "",
    `- Executed at: ${bundleReport.meta.executed_at}`,
    `- Overall status: ${bundleReport.overall_status}`,
    `- Provider policy: ${bundleReport.meta.provider_policy}`,
    `- Published site root used: ${bundleReport.inputs.published_site_root}`,
    "",
    "## Key Results",
    "",
    `- M5 lane status: ${bundleReport.summary.m5_lane_status}`,
    `- M7 smoke: ${bundleReport.summary.m7_overall_status} (${bundleReport.summary.m7_error_count} errors, ${bundleReport.summary.m7_critical_failures} critical)`,
    `- Level 2 actionable candidates: ${bundleReport.summary.level2_actionable_candidates}`,
    `- Level 3 seed candidates: ${bundleReport.summary.level3_seed_candidates}`,
    `- Royal Arch future-lane candidates: ${bundleReport.summary.royal_arch_future_candidates}`,
    `- Level 2 top frames ready: ${bundleReport.summary.level2_triage_frame_count}`,
    "",
    "## Residual Warnings",
    ""
  ];

  for (const warning of bundleReport.residual_warnings || []) {
    lines.push(`- ${warning.check}: ${warning.detail}`);
  }

  lines.push(
    "",
    "## Level 2 Top Actionable",
    ""
  );

  for (const slug of bundleReport.summary.level2_top_actionable) {
    lines.push(`- ${slug}`);
  }

  lines.push("", "## Level 3 Seed Topics", "");
  for (const slug of bundleReport.summary.level3_seed_topics) {
    lines.push(`- ${slug}`);
  }

  lines.push("", "## Royal Arch Future Lane", "");
  for (const slug of bundleReport.summary.royal_arch_future_topics) {
    lines.push(`- ${slug}`);
  }

  lines.push("", "## Blocked Higher-Degree Labels", "");
  for (const label of bundleReport.summary.blocked_higher_degree_labels) {
    lines.push(`- ${label}`);
  }

  lines.push("", "## Next Path", "");
  for (const step of bundleReport.next_execution_path) {
    lines.push(`- ${step.step}: ${step.action}`);
  }

  return `${lines.join("\n")}\n`;
}

main();
