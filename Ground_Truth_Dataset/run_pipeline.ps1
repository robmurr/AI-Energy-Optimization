# Master Pipeline Script - Ground Truth Dataset (Windows PowerShell)
# Runs the complete pipeline from mining repos to analyzing test coverage
# Always uses single-file commits only
#
# Usage:
#   .\run_pipeline.ps1                    # Run with defaults
#   .\run_pipeline.ps1 -MaxRepos 20       # Custom repo limit
#   .\run_pipeline.ps1 -SkipMine          # Skip mining phase
#   .\run_pipeline.ps1 -Full              # Include checkout phase
#

param(
    [int]$MaxRepos = 10,
    [int]$MaxCommits = 1000,
    [switch]$SkipMine,
    [switch]$Full,
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host ""
    Write-Host "Usage: .\run_pipeline.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -MaxRepos N       Maximum repositories to mine (default: 10)"
    Write-Host "  -MaxCommits N     Maximum commits per repo (default: 1000)"
    Write-Host "  -SkipMine         Skip mining phase (use existing repos)"
    Write-Host "  -Full             Include checkout phase"
    Write-Host "  -Help             Show this help message"
    Write-Host ""
    Write-Host "Note: Always uses single-file commits only"
    Write-Host ""
    exit 0
}

# Error handling - stop on error
$ErrorActionPreference = "Stop"

# Check if we're in the right directory
if (-not (Test-Path "scripts")) {
    Write-Host "ERROR: scripts/ directory not found"
    Write-Host "Please run from Ground_Truth_Dataset/"
    exit 1
}

# Start pipeline
Write-Host ""
Write-Host "=== Ground Truth Dataset Pipeline ==="
Write-Host "Max repos: $MaxRepos"
Write-Host "Max commits per repo: $MaxCommits"
Write-Host "Single-file commits: always"
Write-Host "Include checkout: $Full"
Write-Host ""

$StartTime = Get-Date

# Phase 1: Mine repositories
if (-not $SkipMine) {
    Write-Host "[1/5] Mining repositories..."
    python scripts/mine_repos.py --max $MaxRepos
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done"
    Write-Host ""
} else {
    Write-Host "[1/5] Skipping mining phase"
    Write-Host ""
}

# Phase 2: Validate test presence
Write-Host "[2/5] Validating test presence..."
python scripts/validate_test_presence.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done"
Write-Host ""

# Phase 3: Extract commits (always single-file)
Write-Host "[3/5] Extracting commits (single-file only)..."
python scripts/extract_commits.py --max $MaxCommits --single
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done"
Write-Host ""

# Phase 4: Map tests to commits
Write-Host "[4/5] Mapping tests to commits..."
python scripts/map_tests_to_commits.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done"
Write-Host ""

# Phase 5: Analyze test coverage
Write-Host "[5/5] Analyzing test coverage..."
python scripts/analyze_test_coverage.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done"
Write-Host ""

# Phase 6: Checkout commits (optional)
if ($Full) {
    Write-Host "[6/6] Checking out commits..."
    python scripts/checkout_commits.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done"
    Write-Host ""
}

# Calculate elapsed time
$EndTime = Get-Date
$Elapsed = $EndTime - $StartTime
$Minutes = [math]::Floor($Elapsed.TotalMinutes)
$Seconds = $Elapsed.Seconds

# Final summary
Write-Host "=== Pipeline Complete ==="
Write-Host "Time: ${Minutes}m ${Seconds}s"
Write-Host ""
Write-Host "Generated files:"
Write-Host "  - results/repo_metadata.json"
Write-Host "  - results/test_validation.json"
Write-Host "  - candidate_commits.csv"
Write-Host "  - test_mapping.csv"
Write-Host "  - coverage_analysis.csv"

if ($Full) {
    Write-Host "  - checkouts/"
}

Write-Host ""

# Show final count
if (Test-Path "coverage_analysis.csv") {
    $LineCount = (Get-Content "coverage_analysis.csv" | Measure-Object -Line).Lines - 1
    Write-Host "Final dataset: $LineCount commits"
}

Write-Host ""
Write-Host "Done!"
