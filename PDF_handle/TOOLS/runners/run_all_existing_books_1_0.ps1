[CmdletBinding()]
param(
  [string]$BranchRoot = "",
  [string]$OutputRoot = "",
  [string]$RoutingConfigPath = "",
  [ValidateSet("gemini", "dry-run")][string]$Provider0104 = "gemini",
  [ValidateSet("gemini", "heuristic")][string]$Provider0507 = "heuristic",
  [int]$MaxAttemptsPerBook = 4,
  [int]$InitialRetryDelaySeconds = 90,
  [double]$RetryBackoffMultiplier = 2.0,
  [switch]$PromoteLive,
  [switch]$PublishWorkSnapshot,
  [switch]$FinalizeLiveRelease,
  [switch]$SkipPhase1,
  [switch]$AllowDryRunPreprocess,
  [switch]$IncludeCompanions,
  [switch]$ForceFreshRun,
  [switch]$ContinueOnError,
  [string[]]$SourceBookNames = @(),
  [Alias("h")][switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
  Write-Output "Usage:"
  Write-Output "  powershell -ExecutionPolicy Bypass -File .\\PDF_handle\\TOOLS\\runners\\run_all_existing_books_1_0.ps1 [-PromoteLive] [-SkipPhase1] [-ForceFreshRun] [-ContinueOnError]"
  Write-Output ""
  Write-Output "Common modes:"
  Write-Output "  Resume from an interrupted preprocess run:"
  Write-Output "    ...run_all_existing_books_1_0.ps1 -PromoteLive -ContinueOnError"
  Write-Output ""
  Write-Output "  Reuse existing Step 4 artifacts only:"
  Write-Output "    ...run_all_existing_books_1_0.ps1 -SkipPhase1 -PromoteLive -ContinueOnError"
  Write-Output ""
  Write-Output "  Force a full fresh rerun:"
  Write-Output "    ...run_all_existing_books_1_0.ps1 -ForceFreshRun -PromoteLive -ContinueOnError"
  exit 0
}

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$PdfHandleRoot = Join-Path $Root "PDF_handle"
$PdfFilesDir = Join-Path $PdfHandleRoot "PDF_files"
$WrapperPath = Join-Path $PdfHandleRoot "TOOLS\runners\run_new_material_e2e_full.ps1"
$EffectiveRoutingConfigPath = if ([string]::IsNullOrWhiteSpace($RoutingConfigPath)) {
  Join-Path $PdfHandleRoot "work_routing.json"
} else {
  if ([System.IO.Path]::IsPathRooted($RoutingConfigPath)) {
    [System.IO.Path]::GetFullPath($RoutingConfigPath)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $Root $RoutingConfigPath))
  }
}

function Resolve-OptionalRepoPath {
  param([string]$PathValue, [string]$DefaultPath)

  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return $DefaultPath
  }
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $Root $PathValue))
}

function New-TimestampSlug {
  return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")
}

function Get-RetryDelaySeconds {
  param(
    [int]$AttemptNumber,
    [int]$BaseDelaySeconds,
    [double]$BackoffMultiplier
  )

  if ($AttemptNumber -le 1) {
    return 0
  }

  $delay = [double]$BaseDelaySeconds
  for ($i = 3; $i -le $AttemptNumber; $i++) {
    $delay = $delay * $BackoffMultiplier
  }
  return [Math]::Ceiling($delay)
}

function Test-RetryableFailure {
  param([string]$LogPath)

  if (-not (Test-Path $LogPath)) {
    return $false
  }

  $logText = Get-Content -Path $LogPath -Raw -Encoding utf8
  $nonRetryablePatterns = @(
    "exceeded its spending cap",
    "spending cap",
    "billing",
    "insufficient balance",
    "selected-work parity between work and live is not pass",
    "step 6 validation failed",
    "refusing to write live data because step 6 validation failed"
  )
  foreach ($pattern in $nonRetryablePatterns) {
    if ($logText -match [regex]::Escape($pattern)) {
      return $false
    }
  }

  $patterns = @(
    "429",
    "500",
    "502",
    "503",
    "504",
    "rate limit",
    "resource exhausted",
    "quota",
    "deadline exceeded",
    "timed out",
    "timeout",
    "temporarily unavailable",
    "connection reset",
    "connection aborted",
    "network error",
    "ssl",
    "api key",
    "service unavailable",
    "internal server error"
  )

  foreach ($pattern in $patterns) {
    if ($logText -match [regex]::Escape($pattern)) {
      return $true
    }
  }

  return $false
}

function Test-FatalBudgetFailure {
  param([string]$LogPath)

  if (-not (Test-Path $LogPath)) {
    return $false
  }

  $logText = Get-Content -Path $LogPath -Raw -Encoding utf8
  $patterns = @(
    "exceeded its spending cap",
    "spending cap",
    "resource_exhausted",
    "resource exhausted",
    "insufficient balance"
  )

  foreach ($pattern in $patterns) {
    if ($logText -match [regex]::Escape($pattern)) {
      return $true
    }
  }

  return $false
}

function Invoke-NativeProcessToLog {
  param(
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$StdoutPath,
    [string]$StderrPath
  )

  $escapedArgumentList = @(
    foreach ($argument in $ArgumentList) {
      if ($null -eq $argument) {
        '""'
        continue
      }
      $text = [string]$argument
      if ($text -match '[\s"]') {
        '"' + ($text -replace '"', '\"') + '"'
      } else {
        $text
      }
    }
  )

  if (Test-Path $StdoutPath) {
    Remove-Item -Force $StdoutPath
  }
  if (Test-Path $StderrPath) {
    Remove-Item -Force $StderrPath
  }

  $process = Start-Process `
    -FilePath $FilePath `
    -ArgumentList $escapedArgumentList `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -NoNewWindow `
    -PassThru `
    -Wait

  $stdoutLines = if (Test-Path $StdoutPath) { @(Get-Content -Path $StdoutPath -Encoding utf8) } else { @() }
  $stderrLines = if (Test-Path $StderrPath) { @(Get-Content -Path $StderrPath -Encoding utf8) } else { @() }

  return @{
    ExitCode = $process.ExitCode
    StdoutLines = $stdoutLines
    StderrLines = $stderrLines
  }
}

if (-not (Test-Path $EffectiveRoutingConfigPath)) {
  throw "Routing config not found: $EffectiveRoutingConfigPath"
}
if (-not (Test-Path $WrapperPath)) {
  throw "Wrapper script not found: $WrapperPath"
}

$ResolvedBranchRoot = Resolve-OptionalRepoPath -PathValue $BranchRoot -DefaultPath (Join-Path $PdfHandleRoot "runs")
$RunTimestamp = New-TimestampSlug
$ResolvedOutputRoot = Resolve-OptionalRepoPath -PathValue $OutputRoot -DefaultPath (Join-Path $ResolvedBranchRoot ("all_existing_books_1_0\" + $RunTimestamp))
New-Item -ItemType Directory -Force -Path $ResolvedBranchRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ResolvedOutputRoot | Out-Null

$routingPayload = Get-Content -Path $EffectiveRoutingConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
$works = @($routingPayload.works)
if ($SourceBookNames.Count -gt 0) {
  $selectedLookup = @{}
  foreach ($name in $SourceBookNames) {
    if (-not [string]::IsNullOrWhiteSpace($name)) {
      $selectedLookup[$name.Trim()] = $true
    }
  }
  $works = @($works | Where-Object { $selectedLookup.ContainsKey([string]$_.source_book_name) })
}

if ($works.Count -eq 0) {
  throw "No works matched the requested selection."
}

$summary = [System.Collections.ArrayList]::new()

Write-Output "Batch run root: $ResolvedOutputRoot"
Write-Output "Matched books: $($works.Count)"

foreach ($work in $works) {
  $sourceBookName = [string]$work.source_book_name
  $bookFolderName = if (-not [string]::IsNullOrWhiteSpace([string]$work.work_id)) {
    [string]$work.work_id
  } else {
    $sourceBookName
  }
  $pdfPath = Join-Path $PdfFilesDir ($sourceBookName + ".pdf")
  $bookOutputRoot = Join-Path $ResolvedOutputRoot $bookFolderName
  New-Item -ItemType Directory -Force -Path $bookOutputRoot | Out-Null

  Write-Output ""
  Write-Output ("=== Running " + $sourceBookName + " ===")

  if (-not (Test-Path $pdfPath)) {
    $record = [pscustomobject]@{
      source_book_name = $sourceBookName
      status = "failed"
      reason = "pdf_missing"
      pdf_path = $pdfPath
      output_root = $bookOutputRoot
    }
    [void]$summary.Add($record)
    Write-Output ("[skip] missing PDF: " + $pdfPath)
    if (-not $ContinueOnError) {
      $summaryPath = Join-Path $ResolvedOutputRoot "batch_summary.json"
      $summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding utf8
      throw "Missing PDF for $sourceBookName"
    }
    continue
  }

  $attemptRecords = [System.Collections.ArrayList]::new()
  $completed = $false
  $lastExitCode = 0
  $lastFailureReason = $null
  $fatalBatchStop = $false

  for ($attempt = 1; $attempt -le $MaxAttemptsPerBook; $attempt++) {
    $attemptOutputRoot = Join-Path $bookOutputRoot ("attempt-" + $attempt.ToString("00"))
    New-Item -ItemType Directory -Force -Path $attemptOutputRoot | Out-Null
    $logPath = Join-Path $attemptOutputRoot "console.log"
    $stdoutPath = Join-Path $attemptOutputRoot "stdout.log"
    $stderrPath = Join-Path $attemptOutputRoot "stderr.log"

    if ($attempt -gt 1) {
      $delaySeconds = Get-RetryDelaySeconds -AttemptNumber $attempt -BaseDelaySeconds $InitialRetryDelaySeconds -BackoffMultiplier $RetryBackoffMultiplier
      Write-Output ("[retry] waiting $delaySeconds second(s) before retry $attempt/$MaxAttemptsPerBook for " + $sourceBookName)
      Start-Sleep -Seconds $delaySeconds
    }

    Write-Output ("[attempt] " + $attempt + "/" + $MaxAttemptsPerBook + " -> " + $sourceBookName)

    $invokeArgs = @(
      "-ExecutionPolicy", "Bypass",
      "-File", $WrapperPath,
      "-SourcePdfPath", $pdfPath,
      "-SourceBookName", $sourceBookName,
      "-BranchRoot", $ResolvedBranchRoot,
      "-OutputRoot", $attemptOutputRoot,
      "-Provider0104", $Provider0104,
      "-Provider0507", $Provider0507,
      "-Quiet"
    )

    if ($PromoteLive) { $invokeArgs += "-PromoteLive" }
    if ($PublishWorkSnapshot) { $invokeArgs += "-PublishWorkSnapshot" }
    if ($FinalizeLiveRelease) { $invokeArgs += "-FinalizeLiveRelease" }
    if ($SkipPhase1) { $invokeArgs += "-SkipPhase1" }
    if ($AllowDryRunPreprocess) { $invokeArgs += "-AllowDryRunPreprocess" }
    if ($IncludeCompanions) { $invokeArgs += "-IncludeCompanions" }
    if ($ForceFreshRun) { $invokeArgs += "-ForceFreshRun" }

    $processResult = Invoke-NativeProcessToLog `
      -FilePath "powershell" `
      -ArgumentList $invokeArgs `
      -StdoutPath $stdoutPath `
      -StderrPath $stderrPath
    $exitCode = [int]$processResult.ExitCode
    $outputLines = @($processResult.StdoutLines + $processResult.StderrLines)
    if ($null -eq $outputLines -or $outputLines.Count -eq 0) {
      Set-Content -Path $logPath -Value "" -Encoding utf8
    } else {
      $outputLines | Set-Content -Path $logPath -Encoding utf8
    }

    if ($exitCode -eq 0) {
      Write-Output ("[completed] " + $sourceBookName + " -> " + $attemptOutputRoot)
      [void]$attemptRecords.Add([pscustomobject]@{
        attempt = $attempt
        status = "completed"
        exit_code = 0
        retryable = $false
        output_root = $attemptOutputRoot
        log_path = $logPath
      })
      $completed = $true
      break
    }

    $fatalBudgetFailure = Test-FatalBudgetFailure -LogPath $logPath
    $retryable = if ($fatalBudgetFailure) { $false } else { Test-RetryableFailure -LogPath $logPath }
    $lastExitCode = $exitCode
    $lastFailureReason = if ($fatalBudgetFailure) {
      "fatal_gemini_budget_exhausted"
    } elseif ($retryable) {
      "retryable_api_or_network_failure"
    } else {
      "wrapper_exit_$exitCode"
    }
    $stderrTail = if (Test-Path $stderrPath) {
      ((Get-Content -Path $stderrPath -Tail 1 -Encoding utf8) -join "").Trim()
    } else {
      ""
    }
    if ($fatalBudgetFailure) {
      Write-Output ("[fatal-budget] " + $sourceBookName + " exit=" + $exitCode + " log=" + $logPath)
    } elseif ($retryable) {
      Write-Output ("[failed-retryable] " + $sourceBookName + " exit=" + $exitCode + " log=" + $logPath)
    } else {
      Write-Output ("[failed] " + $sourceBookName + " exit=" + $exitCode + " log=" + $logPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($stderrTail)) {
      Write-Output ("[reason] " + $stderrTail)
    }

    [void]$attemptRecords.Add([pscustomobject]@{
      attempt = $attempt
      status = "failed"
      exit_code = $exitCode
      retryable = $retryable
      output_root = $attemptOutputRoot
      log_path = $logPath
    })

    if ($fatalBudgetFailure) {
      $fatalBatchStop = $true
      break
    }

    if (-not $retryable) {
      break
    }
  }

  if ($completed) {
    [void]$summary.Add([pscustomobject]@{
      source_book_name = $sourceBookName
      status = "completed"
      reason = $null
      pdf_path = $pdfPath
      output_root = $bookOutputRoot
      attempts = @($attemptRecords)
    })
    continue
  }

  [void]$summary.Add([pscustomobject]@{
    source_book_name = $sourceBookName
    status = "failed"
    reason = $lastFailureReason
    pdf_path = $pdfPath
    output_root = $bookOutputRoot
    attempts = @($attemptRecords)
  })

  if ($fatalBatchStop) {
    $summaryPath = Join-Path $ResolvedOutputRoot "batch_summary.json"
    $summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding utf8
    Write-Output ""
    Write-Output "Batch stopped intentionally: Gemini budget/spending cap is exhausted."
    Write-Output ("See log: " + $logPath)
    Write-Output "Recommended next action: restore budget or rerun later with -SkipPhase1."
    exit $lastExitCode
  }

  if (-not $ContinueOnError) {
    $summaryPath = Join-Path $ResolvedOutputRoot "batch_summary.json"
    $summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding utf8
    exit $lastExitCode
  }
}

$summaryPath = Join-Path $ResolvedOutputRoot "batch_summary.json"
$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding utf8

$completedCount = @($summary | Where-Object { $_.status -eq "completed" }).Count
$failedCount = @($summary | Where-Object { $_.status -eq "failed" }).Count

Write-Output ""
Write-Output "Batch summary written: $summaryPath"
Write-Output "Completed: $completedCount"
Write-Output "Failed: $failedCount"

if ($failedCount -gt 0 -and -not $ContinueOnError) {
  exit 1
}
