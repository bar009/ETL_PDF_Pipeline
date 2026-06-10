param(
  [Parameter(Mandatory = $true)][string]$SourcePdfPath,
  [string]$SourceBookName = "",
  [string]$BranchRoot = "",
  [string]$OutputRoot = "",
  [string]$WorkId = "",
  [string]$StagingDir = "",
  [string]$WorkTitle = "",
  [ValidateSet("level1", "level2", "level3", "multi")][string]$PrimaryDegree = "multi",
  [string]$SourceKind = "reference-compendium",
  [ValidateSet("en", "he")][string]$Language = "en",
  [string[]]$AppliesToDegrees = @(),
  [string]$DefaultVisibilityLevel = "internal",
  [string]$DefaultSensitivityLevel = "guarded",
  [string]$DefaultTraditionScope = "interpretive",
  [string]$LibraryCategory = "etl_imports",
  [ValidateSet("gemini", "dry-run")][string]$Provider0104 = "gemini",
  [ValidateSet("gemini", "heuristic")][string]$Provider0507 = "heuristic",
  [switch]$PromoteLive,
  [switch]$PublishWorkSnapshot,
  [switch]$FinalizeLiveRelease,
  [switch]$SkipPhase1,
  [switch]$AllowDryRunPreprocess,
  [switch]$IncludeCompanions,
  [switch]$ReuseExistingState,
  [switch]$ForceFreshRun,
  [switch]$OverwritePdf,
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$PdfHandleRoot = Join-Path $Root "PDF_handle"
$PdfFilesDir = Join-Path $PdfHandleRoot "PDF_files"
$RoutingConfigPath = Join-Path $PdfHandleRoot "work_routing.json"
$RunnerPath = Join-Path $PdfHandleRoot "TOOLS\runners\run_new_material_e2e.py"

function Resolve-RepoPath {
  param([Parameter(Mandatory = $true)][string]$PathValue)

  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }

  return [System.IO.Path]::GetFullPath((Join-Path $Root $PathValue))
}

function Convert-ToSlug {
  param([Parameter(Mandatory = $true)][string]$Value)

  $slug = $Value.ToLowerInvariant()
  $slug = [regex]::Replace($slug, "[^a-z0-9]+", "-")
  $slug = $slug.Trim("-")
  return $slug
}

function New-TimestampSlug {
  return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")
}

function Get-DefaultAppliesToDegrees {
  param([Parameter(Mandatory = $true)][string]$Degree)

  switch ($Degree) {
    "level1" { return @("library", "level1") }
    "level2" { return @("library", "level2") }
    "level3" { return @("library", "level3") }
    default { return @("library", "level1", "level2") }
  }
}

function Read-JsonObject {
  param([Parameter(Mandatory = $true)][string]$PathValue)
  return Get-Content -Path $PathValue -Raw -Encoding utf8 | ConvertFrom-Json
}

function Write-JsonObject {
  param(
    [Parameter(Mandatory = $true)][string]$PathValue,
    [Parameter(Mandatory = $true)]$Payload
  )

  $directory = Split-Path -Parent $PathValue
  if (-not [string]::IsNullOrWhiteSpace($directory)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
  }

  $json = $Payload | ConvertTo-Json -Depth 100
  Set-Content -Path $PathValue -Value ($json + [Environment]::NewLine) -Encoding utf8
}

function Assert-EnvReady {
  param(
    [Parameter(Mandatory = $true)][string]$Provider,
    [switch]$SkipPreprocess
  )

  if (-not $SkipPreprocess -and $Provider -eq "gemini" -and [string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    throw "GEMINI_API_KEY is not set in the current shell."
  }

  if ($PublishWorkSnapshot -or $FinalizeLiveRelease) {
    if (-not $PromoteLive) {
      throw "Publish and finalize require -PromoteLive."
    }
  }

  if ($ReuseExistingState -and $ForceFreshRun) {
    throw "Use either -ReuseExistingState or -ForceFreshRun, not both."
  }
}

function Ensure-TargetPdf {
  param(
    [Parameter(Mandatory = $true)][string]$InputPdfPath,
    [Parameter(Mandatory = $true)][string]$TargetPdfPath
  )

  if (-not (Test-Path $InputPdfPath)) {
    throw "Source PDF not found: $InputPdfPath"
  }

  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $TargetPdfPath) | Out-Null

  $sameFile = $false
  if (Test-Path $TargetPdfPath) {
    try {
      $sameFile = ((Resolve-Path $InputPdfPath).Path -eq (Resolve-Path $TargetPdfPath).Path)
    } catch {
      $sameFile = $false
    }
  }

  if ($sameFile) {
    return $TargetPdfPath
  }

  if ((Test-Path $TargetPdfPath) -and -not $OverwritePdf) {
    throw "Target PDF already exists: $TargetPdfPath. Re-run with -OverwritePdf to replace it."
  }

  Copy-Item -Path $InputPdfPath -Destination $TargetPdfPath -Force:$OverwritePdf
  return $TargetPdfPath
}

function Ensure-RoutingEntry {
  param(
    [Parameter(Mandatory = $true)][string]$PathValue,
    [Parameter(Mandatory = $true)][hashtable]$Entry
  )

  $payload = Read-JsonObject $PathValue
  if (-not $payload.works) {
    throw "work_routing.json is missing the works array."
  }

  $existing = @($payload.works | Where-Object { $_.source_book_name -eq $Entry.source_book_name })
  if ($existing.Count -gt 1) {
    throw "Routing contains duplicate source_book_name entries for $($Entry.source_book_name)."
  }

  if ($existing.Count -eq 1) {
    $row = $existing[0]
    $mismatches = @()
    foreach ($key in @(
      "work_id",
      "staging_dir",
      "work_title",
      "primary_degree",
      "source_kind",
      "language",
      "default_visibility_level",
      "default_sensitivity_level",
      "default_tradition_scope",
      "library_category"
    )) {
      if ($row.$key -ne $Entry[$key]) {
        $mismatches += $key
      }
    }

    $existingDegrees = @($row.applies_to_degrees | ForEach-Object { [string]$_ }) | Sort-Object
    $targetDegrees = @($Entry.applies_to_degrees | ForEach-Object { [string]$_ }) | Sort-Object
    if ((Compare-Object -ReferenceObject $existingDegrees -DifferenceObject $targetDegrees).Count -gt 0) {
      $mismatches += "applies_to_degrees"
    }

    if ($mismatches.Count -gt 0) {
      throw "Existing routing entry for $($Entry.source_book_name) conflicts on: $($mismatches -join ', ')"
    }

    return @{
      status = "existing"
      work_id = $row.work_id
      staging_dir = $row.staging_dir
    }
  }

  $workIdConflict = @($payload.works | Where-Object { $_.work_id -eq $Entry.work_id })
  if ($workIdConflict.Count -gt 0) {
    throw "work_id already exists in routing: $($Entry.work_id)"
  }

  $stagingConflict = @($payload.works | Where-Object { $_.staging_dir -eq $Entry.staging_dir })
  if ($stagingConflict.Count -gt 0) {
    throw "staging_dir already exists in routing: $($Entry.staging_dir)"
  }

  $newWorks = New-Object System.Collections.ArrayList
  foreach ($row in $payload.works) {
    [void]$newWorks.Add($row)
  }
  [void]$newWorks.Add([pscustomobject]$Entry)
  $payload.works = $newWorks
  Write-JsonObject -PathValue $PathValue -Payload $payload

  return @{
    status = "created"
    work_id = $Entry.work_id
    staging_dir = $Entry.staging_dir
  }
}

$resolvedSourcePdfPath = Resolve-RepoPath $SourcePdfPath
$effectiveSourceBookName = if ([string]::IsNullOrWhiteSpace($SourceBookName)) {
  [System.IO.Path]::GetFileNameWithoutExtension($resolvedSourcePdfPath)
} else {
  $SourceBookName.Trim()
}

$resolvedBranchRoot = if ([string]::IsNullOrWhiteSpace($BranchRoot)) {
  Join-Path $PdfHandleRoot "runs"
} else {
  Resolve-RepoPath $BranchRoot
}
$timestampSlug = New-TimestampSlug
$resolvedOutputRoot = if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
  Join-Path $resolvedBranchRoot ("new_material_e2e\" + $effectiveSourceBookName + "\" + $timestampSlug)
} else {
  Resolve-RepoPath $OutputRoot
}
New-Item -ItemType Directory -Force -Path $resolvedBranchRoot | Out-Null
New-Item -ItemType Directory -Force -Path $resolvedOutputRoot | Out-Null

$sourceCaptureDir = Join-Path $resolvedOutputRoot "source_pdf"
New-Item -ItemType Directory -Force -Path $sourceCaptureDir | Out-Null

$routingPayload = Read-JsonObject $RoutingConfigPath
$existingRoute = @($routingPayload.works | Where-Object { $_.source_book_name -eq $effectiveSourceBookName })
if ($existingRoute.Count -gt 1) {
  throw "Routing contains duplicate source_book_name entries for $effectiveSourceBookName."
}
$existingRouteRow = if ($existingRoute.Count -eq 1) { $existingRoute[0] } else { $null }

$defaultWorkId = Convert-ToSlug $effectiveSourceBookName
if ([string]::IsNullOrWhiteSpace($defaultWorkId)) {
  throw "Could not derive work_id from SourceBookName. Pass -WorkId explicitly."
}

$effectiveWorkId = if ($existingRouteRow) {
  if (-not [string]::IsNullOrWhiteSpace($WorkId) -and $WorkId.Trim() -ne $existingRouteRow.work_id) {
    throw "Explicit WorkId does not match the existing routing entry for $effectiveSourceBookName."
  }
  [string]$existingRouteRow.work_id
} elseif ([string]::IsNullOrWhiteSpace($WorkId)) {
  $defaultWorkId
} else {
  $WorkId.Trim()
}

$effectiveStagingDir = if ($existingRouteRow) {
  if (-not [string]::IsNullOrWhiteSpace($StagingDir) -and $StagingDir.Trim() -ne $existingRouteRow.staging_dir) {
    throw "Explicit StagingDir does not match the existing routing entry for $effectiveSourceBookName."
  }
  [string]$existingRouteRow.staging_dir
} elseif ([string]::IsNullOrWhiteSpace($StagingDir)) {
  $effectiveWorkId
} else {
  $StagingDir.Trim()
}

$effectiveWorkTitle = if ($existingRouteRow) {
  if (-not [string]::IsNullOrWhiteSpace($WorkTitle) -and $WorkTitle.Trim() -ne $existingRouteRow.work_title) {
    throw "Explicit WorkTitle does not match the existing routing entry for $effectiveSourceBookName."
  }
  [string]$existingRouteRow.work_title
} elseif ([string]::IsNullOrWhiteSpace($WorkTitle)) {
  ($effectiveSourceBookName -replace "_", " ").Trim()
} else {
  $WorkTitle.Trim()
}

$effectivePrimaryDegree = if ($existingRouteRow) { [string]$existingRouteRow.primary_degree } else { $PrimaryDegree }
$effectiveSourceKind = if ($existingRouteRow) { [string]$existingRouteRow.source_kind } else { $SourceKind }
$effectiveLanguage = if ($existingRouteRow) { [string]$existingRouteRow.language } else { $Language }
$effectiveDefaultVisibilityLevel = if ($existingRouteRow) { [string]$existingRouteRow.default_visibility_level } else { $DefaultVisibilityLevel }
$effectiveDefaultSensitivityLevel = if ($existingRouteRow) { [string]$existingRouteRow.default_sensitivity_level } else { $DefaultSensitivityLevel }
$effectiveDefaultTraditionScope = if ($existingRouteRow) { [string]$existingRouteRow.default_tradition_scope } else { $DefaultTraditionScope }
$effectiveLibraryCategory = if ($existingRouteRow) { [string]$existingRouteRow.library_category } else { $LibraryCategory }
$effectiveAppliesToDegrees = if ($existingRouteRow) {
  @($existingRouteRow.applies_to_degrees)
} elseif ($AppliesToDegrees.Count -gt 0) {
  $AppliesToDegrees
} else {
  Get-DefaultAppliesToDegrees $effectivePrimaryDegree
}
$targetPdfPath = Join-Path $PdfFilesDir ($effectiveSourceBookName + ".pdf")

Assert-EnvReady -Provider $Provider0104 -SkipPreprocess:$SkipPhase1
$placedPdfPath = Ensure-TargetPdf -InputPdfPath $resolvedSourcePdfPath -TargetPdfPath $targetPdfPath
$captureExtension = [System.IO.Path]::GetExtension($placedPdfPath)
$captureFileName = if ([string]::IsNullOrWhiteSpace($captureExtension)) { "source_pdf" } else { "source$captureExtension" }
Copy-Item -Path $placedPdfPath -Destination (Join-Path $sourceCaptureDir $captureFileName) -Force

$entry = @{
  source_book_name = $effectiveSourceBookName
  work_id = $effectiveWorkId
  staging_dir = $effectiveStagingDir
  work_title = $effectiveWorkTitle
  primary_degree = $effectivePrimaryDegree
  source_kind = $effectiveSourceKind
  language = $effectiveLanguage
  applies_to_degrees = @($effectiveAppliesToDegrees)
  default_visibility_level = $effectiveDefaultVisibilityLevel
  default_sensitivity_level = $effectiveDefaultSensitivityLevel
  default_tradition_scope = $effectiveDefaultTraditionScope
  library_category = $effectiveLibraryCategory
}

$routingResult = Ensure-RoutingEntry -PathValue $RoutingConfigPath -Entry $entry

$command = @(
  "python",
  $RunnerPath,
  "--source-book-name", $effectiveSourceBookName,
  "--report-dir", $resolvedOutputRoot,
  "--provider-01-04", $Provider0104,
  "--provider-05-07", $Provider0507
)

if ($SkipPhase1) {
  $command += "--skip-phase1"
}
if ($AllowDryRunPreprocess) {
  $command += "--allow-dry-run-preprocess"
}
if ($PromoteLive) {
  $command += "--promote-live"
}
if ($PublishWorkSnapshot) {
  $command += "--publish-work-snapshot"
}
if ($FinalizeLiveRelease) {
  $command += "--finalize-live-release"
}
if ($IncludeCompanions) {
  $command += "--include-companions"
}
if ($ForceFreshRun) {
  $command += @(
    "--force-step1",
    "--force-step2",
    "--force-step3",
    "--force-step4",
    "--force-step5",
    "--force-step6",
    "--force-step7"
  )
}

if (-not $Quiet) {
  Write-Output "PDF placed at: $placedPdfPath"
  Write-Output "Runs root: $resolvedBranchRoot"
  Write-Output "Output root: $resolvedOutputRoot"
  Write-Output "Routing status: $($routingResult.status)"
  Write-Output "Resolved work_id: $effectiveWorkId"
  Write-Output "Resolved staging_dir: $effectiveStagingDir"
  Write-Output ("Execution mode: " + $(if ($ForceFreshRun) { "force-fresh-run" } else { "reuse-existing-state" }))
  Write-Output "Running full E2E command:"
  Write-Output ($command -join " ")
}

if ($Quiet) {
  $command += "--quiet"
}

& $command[0] $command[1..($command.Count - 1)]
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
  exit $exitCode
}
