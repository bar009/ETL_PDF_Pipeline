param(
  [string]$SandboxSiteRoot = "",
  [string]$PublishedSiteRoot = "",
  [string]$Level1Path = "",
  [string]$Level2Path = "",
  [string]$LibraryPath = "",
  [string]$NotebooklmIntake = "experiments/notebooklm_validation/discovery_mindmap_intake.json",
  [string]$FutureEntryRoot = "PDF_handle/preservation/future_entries",
  [string]$BundleDir = ""
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ToolsDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SiteRootsConfigPath = Join-Path $Root "sites\site_roots.json"
$DefaultSiteRootsConfig = [ordered]@{
  live_site_root = "sites/live/v0.4-current"
  legacy_live_site_root = "0.3"
  work_site_root = "sites/work/v0.4"
  legacy_work_site_root = "0.3-copy"
  sandbox_sites_root = "sandbox_sites"
  published_sites_root = "published_sites"
  legacy_sites_archive_root = "archive/legacy_sites"
}
$DefaultReportRoot = Join-Path $Root "PDF_handle\TOOLS\reports\phase_m_9_post_pdf_full_planning_bundle"
$LatestPointerPath = Join-Path $Root "PDF_handle\TOOLS\data\phase_m_9_post_pdf_full_planning_latest.json"

function Resolve-RepoPath {
  param([Parameter(Mandatory = $true)][string]$PathValue)

  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }

  return [System.IO.Path]::GetFullPath((Join-Path $Root $PathValue))
}

function Get-SiteRootsConfig {
  if ($script:SiteRootsConfig) {
    return $script:SiteRootsConfig
  }

  $merged = [ordered]@{}
  foreach ($entry in $DefaultSiteRootsConfig.GetEnumerator()) {
    $merged[$entry.Key] = $entry.Value
  }

  if (Test-Path $SiteRootsConfigPath) {
    $raw = Get-Content -Path $SiteRootsConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
    foreach ($property in $raw.PSObject.Properties) {
      if ($property.Value -is [string] -and -not [string]::IsNullOrWhiteSpace($property.Value)) {
        $merged[$property.Name] = $property.Value.Trim()
      }
    }
  }

  $script:SiteRootsConfig = $merged
  return $script:SiteRootsConfig
}

function Resolve-ConfiguredRepoPath {
  param([Parameter(Mandatory = $true)][string]$Key)

  $config = Get-SiteRootsConfig
  return Resolve-RepoPath $config[$Key]
}

function Test-SiteRoot {
  param([Parameter(Mandatory = $true)][string]$SiteRoot)

  $dataDir = Join-Path $SiteRoot "data"
  return (Test-Path $dataDir) -and (Test-Path (Join-Path $dataDir "content.schema.json"))
}

function Test-RuntimeSiteRoot {
  param([Parameter(Mandatory = $true)][string]$SiteRoot)

  return (Test-SiteRoot $SiteRoot) `
    -and (Test-Path (Join-Path $SiteRoot "js")) `
    -and (Test-Path (Join-Path $SiteRoot "css")) `
    -and (Test-Path (Join-Path $SiteRoot "index.html"))
}

function Resolve-CanonicalSiteRoot {
  param(
    [Parameter(Mandatory = $true)][string]$PrimaryKey,
    [Parameter(Mandatory = $true)][string]$LegacyKey,
    [switch]$RequireRuntimeAssets
  )

  $preferred = Resolve-ConfiguredRepoPath $PrimaryKey
  $legacy = Resolve-ConfiguredRepoPath $LegacyKey

  if ($RequireRuntimeAssets) {
    if (Test-RuntimeSiteRoot $preferred) {
      return $preferred
    }

    return $legacy
  }

  if (Test-SiteRoot $preferred) {
    return $preferred
  }

  return $legacy
}

function Get-LiveSiteRoot {
  param([switch]$RequireRuntimeAssets)

  return Resolve-CanonicalSiteRoot -PrimaryKey "live_site_root" -LegacyKey "legacy_live_site_root" -RequireRuntimeAssets:$RequireRuntimeAssets
}

function Get-WorkSiteRoot {
  param([switch]$RequireRuntimeAssets)

  return Resolve-CanonicalSiteRoot -PrimaryKey "work_site_root" -LegacyKey "legacy_work_site_root" -RequireRuntimeAssets:$RequireRuntimeAssets
}

function Get-PublishedSitesRoot {
  return Resolve-ConfiguredRepoPath "published_sites_root"
}

function Resolve-PathOption {
  param(
    [string]$ExplicitPath,
    [Parameter(Mandatory = $true)][string]$DefaultPath
  )

  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
    return Resolve-RepoPath $ExplicitPath
  }

  return Resolve-RepoPath $DefaultPath
}

function Resolve-PublishedSiteRoot {
  param([string]$ExplicitPath)

  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
    return Resolve-RepoPath $ExplicitPath
  }

  $publishedRoot = Get-PublishedSitesRoot
  if (-not (Test-Path $publishedRoot)) {
    return Get-LiveSiteRoot -RequireRuntimeAssets
  }

  $latest = Get-ChildItem -Path $publishedRoot -Directory |
    ForEach-Object {
      if ($_.Name -match '^(\d+)\.(\d+)(?:\.(\d+))?-live-') {
        $patch = 0
        if ($matches[3]) {
          $patch = [int]$matches[3]
        }

        [PSCustomObject]@{
          Path = $_.FullName
          Major = [int]$matches[1]
          Minor = [int]$matches[2]
          Patch = $patch
        }
      }
    } |
    Sort-Object Major, Minor, Patch -Descending |
    Select-Object -First 1

  if ($latest) {
    return $latest.Path
  }

  return Get-LiveSiteRoot -RequireRuntimeAssets
}

function Resolve-BundleDir {
  param([string]$ExplicitPath)

  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
    return Resolve-RepoPath $ExplicitPath
  }

  $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")
  return Join-Path $DefaultReportRoot $timestamp
}

function Write-JsonFile {
  param(
    [Parameter(Mandatory = $true)][string]$PathValue,
    [Parameter(Mandatory = $true)]$Payload
  )

  $directory = Split-Path -Parent $PathValue
  if (-not [string]::IsNullOrWhiteSpace($directory)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
  }

  $Payload | ConvertTo-Json -Depth 100 | Set-Content -Path $PathValue -Encoding utf8
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$PathValue)
  return Get-Content -Path $PathValue -Raw -Encoding utf8 | ConvertFrom-Json
}

function Invoke-NodeStep {
  param(
    [Parameter(Mandatory = $true)][string]$ScriptName,
    [Parameter(Mandatory = $true)][string[]]$Arguments
  )

  $scriptPath = Join-Path $ToolsDir $ScriptName
  $outputLines = & node $scriptPath @Arguments 2>&1
  $exitCode = $LASTEXITCODE

  $stdout = ($outputLines | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine

  $logEntry = [PSCustomObject]@{
    script = $scriptPath
    args = $Arguments
    exit_code = $exitCode
    output = $stdout.Trim()
  }

  if ($exitCode -ne 0) {
    throw "Script failed: $ScriptName`n$($logEntry.output)"
  }

  return $logEntry
}

function Derive-OverallStatus {
  param($M5Audit, $M7Smoke, $M8SeedReport)

  if ($M7Smoke.critical_failures -gt 0) {
    return "fail"
  }

  if ($M5Audit.overall_status -eq "fail") {
    return "fail"
  }

  if ($M7Smoke.error_count -gt 0 -or $M5Audit.overall_status -eq "pass-with-warnings") {
    return "pass-with-warnings"
  }

  if ($M8SeedReport.overall_status -eq "pass") {
    return "pass"
  }

  return "pass-with-warnings"
}

$resolvedSandboxSiteRoot = Resolve-PathOption -ExplicitPath $SandboxSiteRoot -DefaultPath (Get-WorkSiteRoot -RequireRuntimeAssets)
$resolvedLevel1Path = Resolve-PathOption -ExplicitPath $Level1Path -DefaultPath (Join-Path (Get-LiveSiteRoot) "data\level1.json")
$resolvedLevel2Path = Resolve-PathOption -ExplicitPath $Level2Path -DefaultPath (Join-Path (Get-WorkSiteRoot) "data\level2.json")
$resolvedLibraryPath = Resolve-PathOption -ExplicitPath $LibraryPath -DefaultPath (Join-Path (Get-WorkSiteRoot) "data\library.json")
$resolvedNotebooklmIntake = Resolve-RepoPath $NotebooklmIntake
$resolvedFutureEntryRoot = Resolve-RepoPath $FutureEntryRoot
$resolvedPublishedSiteRoot = Resolve-PublishedSiteRoot $PublishedSiteRoot
$resolvedBundleDir = Resolve-BundleDir $BundleDir

New-Item -ItemType Directory -Force -Path $resolvedBundleDir | Out-Null

$paths = [ordered]@{
  degreeReadinessAudit = Join-Path $resolvedBundleDir "degree_readiness_audit.json"
  m5ReportDir = Join-Path $resolvedBundleDir "phase_m_5_post_fill_audit"
  m7Smoke = Join-Path $resolvedBundleDir "phase_m_7_full_system_smoke_report.json"
  m8Queue = Join-Path $resolvedBundleDir "phase_m_8_topic_discovery_queue.json"
  m8Report = Join-Path $resolvedBundleDir "phase_m_8_topic_discovery_report.json"
  level3SeedSpec = Join-Path $resolvedBundleDir "level3_boundary_seed_spec.json"
  royalArchSeedSpec = Join-Path $resolvedBundleDir "royal_arch_boundary_seed.json"
  level3GoldsetSeed = Join-Path $resolvedBundleDir "level3_boundary_goldset_seed.json"
  level2TriageFrames = Join-Path $resolvedBundleDir "phase_m_8_level2_top_triage_frames.json"
  m8SeedReport = Join-Path $resolvedBundleDir "phase_m_8_1_seed_report.json"
  bundleReport = Join-Path $resolvedBundleDir "phase_m_9_post_pdf_full_planning_bundle_report.json"
  bundleSummary = Join-Path $resolvedBundleDir "phase_m_9_post_pdf_full_planning_bundle_summary.md"
}

$executionLog = @()
$executionLog += Invoke-NodeStep -ScriptName "audit_degree_readiness.js" -Arguments @(
  "--site-root", $resolvedSandboxSiteRoot,
  "--published-site-root", $resolvedPublishedSiteRoot,
  "--output", $paths.degreeReadinessAudit
)
$executionLog += Invoke-NodeStep -ScriptName "run_phase_m_5_post_fill_audit.js" -Arguments @(
  "--level2", $resolvedLevel2Path,
  "--level1", $resolvedLevel1Path,
  "--library", $resolvedLibraryPath,
  "--report-dir", $paths.m5ReportDir
)
$executionLog += Invoke-NodeStep -ScriptName "run_phase_m_7_full_system_smoke.js" -Arguments @(
  "--sandbox", (Join-Path $resolvedSandboxSiteRoot "data"),
  "--published", (Join-Path $resolvedPublishedSiteRoot "data"),
  "--output", $paths.m7Smoke
)
$executionLog += Invoke-NodeStep -ScriptName "run_phase_m_8_topic_discovery.js" -Arguments @(
  "--level1", $resolvedLevel1Path,
  "--level2", $resolvedLevel2Path,
  "--library", $resolvedLibraryPath,
  "--futureEntryRoot", $resolvedFutureEntryRoot,
  "--notebooklmIntake", $resolvedNotebooklmIntake,
  "--queueOutput", $paths.m8Queue,
  "--reportOutput", $paths.m8Report
)
$executionLog += Invoke-NodeStep -ScriptName "run_phase_m_8_1_seed_specs.js" -Arguments @(
  "--queue", $paths.m8Queue,
  "--report", $paths.m8Report,
  "--level3SpecOutput", $paths.level3SeedSpec,
  "--royalArchSpecOutput", $paths.royalArchSeedSpec,
  "--level3GoldsetOutput", $paths.level3GoldsetSeed,
  "--level2TriageOutput", $paths.level2TriageFrames,
  "--seedReportOutput", $paths.m8SeedReport
)

$degreeReadiness = Read-JsonFile $paths.degreeReadinessAudit
$m5Audit = Read-JsonFile (Join-Path $paths.m5ReportDir "phase_m_5_post_fill_audit.json")
$m7Smoke = Read-JsonFile $paths.m7Smoke
$m8Report = Read-JsonFile $paths.m8Report
$level3SeedSpec = Read-JsonFile $paths.level3SeedSpec
$royalArchSeedSpec = Read-JsonFile $paths.royalArchSeedSpec
$level3GoldsetSeed = Read-JsonFile $paths.level3GoldsetSeed
$level2TriageFrames = Read-JsonFile $paths.level2TriageFrames
$m8SeedReport = Read-JsonFile $paths.m8SeedReport
$executedAt = (Get-Date).ToUniversalTime().ToString("o")
$m7FailedChecks = @()
foreach ($property in $m7Smoke.checks.PSObject.Properties) {
  if (-not $property.Value.pass) {
    $m7FailedChecks += [ordered]@{
      check = $property.Name
      critical = $property.Value.critical
      detail = $property.Value.detail
    }
  }
}

$bundleReport = [ordered]@{
  meta = [ordered]@{
    phase = "phase_m9_post_pdf_full_planning_bundle"
    executed_at = $executedAt
    mode = "post_pdf_full_planning_bundle"
    provider_policy = "no_new_provider_calls"
    notebooklm_calls = 0
    gemini_calls = 0
    purpose = "Rerun the full post-PDF planning stack from existing local data so topic allocation, validation, and Level 3 seeding are ready without repeating the initial token-heavy PDF stage."
  }
  inputs = [ordered]@{
    sandbox_site_root = $resolvedSandboxSiteRoot
    published_site_root = $resolvedPublishedSiteRoot
    level1_path = $resolvedLevel1Path
    level2_path = $resolvedLevel2Path
    library_path = $resolvedLibraryPath
    future_entry_root = $resolvedFutureEntryRoot
    notebooklm_intake = $resolvedNotebooklmIntake
  }
  outputs = [ordered]@{
    bundle_dir = $resolvedBundleDir
    degree_readiness_audit = $paths.degreeReadinessAudit
    m5_report_dir = $paths.m5ReportDir
    m7_smoke_report = $paths.m7Smoke
    m8_queue = $paths.m8Queue
    m8_report = $paths.m8Report
    level3_boundary_seed_spec = $paths.level3SeedSpec
    royal_arch_boundary_seed = $paths.royalArchSeedSpec
    level3_boundary_goldset_seed = $paths.level3GoldsetSeed
    level2_top_triage_frames = $paths.level2TriageFrames
    m8_seed_report = $paths.m8SeedReport
  }
  execution_log = $executionLog
  summary = [ordered]@{
    degree_readiness_architecture_truth = $degreeReadiness.summary.architecture_truth
    m5_lane_status = $m5Audit.overall_status
    m7_overall_status = $m7Smoke.overall_status
    m7_critical_failures = $m7Smoke.critical_failures
    m7_error_count = $m7Smoke.error_count
    level2_actionable_candidates = $m8Report.summary.level2.actionable_count
    level2_top_actionable = @($m8Report.summary.level2.top_actionable)
    level3_seed_candidates = @($level3SeedSpec.native_anchor_candidates).Count
    level3_seed_topics = @($level3SeedSpec.native_anchor_candidates | ForEach-Object { $_.candidate_topic })
    royal_arch_future_candidates = @($royalArchSeedSpec.lane_candidates).Count
    royal_arch_future_topics = @($royalArchSeedSpec.lane_candidates | ForEach-Object { $_.candidate_topic })
    blocked_higher_degree_labels = @($level3GoldsetSeed.blocked_examples | ForEach-Object { $_.blocked_label })
    level2_triage_frame_count = @($level2TriageFrames.topic_frames).Count
    m7_failed_checks = @($m7FailedChecks | ForEach-Object { $_.check })
  }
  residual_warnings = $m7FailedChecks
  next_execution_path = @(
    [ordered]@{
      step = "Level 2 framing/fill"
      action = "Use the generated triage frames as the next controlled Level 2 framing set instead of opening a broader discovery wave."
      artifact = $paths.level2TriageFrames
    },
    [ordered]@{
      step = "Level 3 boundary approval"
      action = "Review and adjudicate the Level 3 seed spec and goldset seed before creating any level3 runtime file."
      artifacts = @($paths.level3SeedSpec, $paths.level3GoldsetSeed)
    },
    [ordered]@{
      step = "Royal Arch adjacent-lane approval"
      action = "Treat Royal Arch as its own future lane using the dedicated boundary seed, not as blocked Level 3 residue."
      artifact = $paths.royalArchSeedSpec
    },
    [ordered]@{
      step = "Smoke follow-up"
      action = $(if ($m7Smoke.critical_failures -gt 0) {
          "Resolve critical smoke blockers before treating the full system as stable."
        } else {
          "Only non-critical smoke issues remain; topic planning can proceed without reopening the post-PDF stack."
        })
    }
  )
  overall_status = Derive-OverallStatus -M5Audit $m5Audit -M7Smoke $m7Smoke -M8SeedReport $m8SeedReport
}

$summaryLines = @(
  "# Post-PDF Full Planning Bundle",
  "",
  "- Executed at: $executedAt",
  "- Overall status: $($bundleReport.overall_status)",
  "- Provider policy: $($bundleReport.meta.provider_policy)",
  "- Published site root used: $resolvedPublishedSiteRoot",
  "",
  "## Key Results",
  "",
  "- M5 lane status: $($bundleReport.summary.m5_lane_status)",
  "- M7 smoke: $($bundleReport.summary.m7_overall_status) ($($bundleReport.summary.m7_error_count) errors, $($bundleReport.summary.m7_critical_failures) critical)",
  "- Level 2 actionable candidates: $($bundleReport.summary.level2_actionable_candidates)",
  "- Level 3 seed candidates: $($bundleReport.summary.level3_seed_candidates)",
  "- Royal Arch future-lane candidates: $($bundleReport.summary.royal_arch_future_candidates)",
  "- Level 2 top frames ready: $($bundleReport.summary.level2_triage_frame_count)",
  "",
  "## Residual Warnings",
  ""
)

foreach ($warning in $bundleReport.residual_warnings) {
  $summaryLines += "- $($warning.check): $($warning.detail)"
}

$summaryLines += @(
  "",
  "## Level 2 Top Actionable",
  ""
)

foreach ($item in $bundleReport.summary.level2_top_actionable) {
  $summaryLines += "- $item"
}

$summaryLines += "", "## Level 3 Seed Topics", ""
foreach ($item in $bundleReport.summary.level3_seed_topics) {
  $summaryLines += "- $item"
}

$summaryLines += "", "## Royal Arch Future Lane", ""
foreach ($item in $bundleReport.summary.royal_arch_future_topics) {
  $summaryLines += "- $item"
}

$summaryLines += "", "## Blocked Higher-Degree Labels", ""
foreach ($item in $bundleReport.summary.blocked_higher_degree_labels) {
  $summaryLines += "- $item"
}

$summaryLines += "", "## Next Path", ""
foreach ($step in $bundleReport.next_execution_path) {
  $summaryLines += "- $($step.step): $($step.action)"
}

Write-JsonFile -PathValue $paths.bundleReport -Payload $bundleReport
Set-Content -Path $paths.bundleSummary -Value (($summaryLines -join [Environment]::NewLine) + [Environment]::NewLine) -Encoding utf8
Write-JsonFile -PathValue $LatestPointerPath -Payload ([ordered]@{
  phase = "phase_m9_post_pdf_full_planning_bundle"
  updated_at = $executedAt
  bundle_dir = $resolvedBundleDir
  bundle_report = $paths.bundleReport
  bundle_summary = $paths.bundleSummary
  overall_status = $bundleReport.overall_status
})

Write-Output "Planning bundle completed: $resolvedBundleDir"
Write-Output "Bundle report: $($paths.bundleReport)"
Write-Output "Bundle summary: $($paths.bundleSummary)"
