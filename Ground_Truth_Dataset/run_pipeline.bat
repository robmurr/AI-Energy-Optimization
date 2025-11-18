@echo off
REM Master Pipeline Script - Ground Truth Dataset (Windows CMD)
REM Runs the complete pipeline from mining repos to analyzing test coverage
REM Always uses single-file commits only
REM
REM Usage:
REM   run_pipeline.bat                    - Run with defaults
REM   run_pipeline.bat --max-repos 20     - Custom repo limit
REM   run_pipeline.bat --skip-mine        - Skip mining phase
REM   run_pipeline.bat --full             - Include checkout phase
REM

setlocal enabledelayedexpansion

REM Default parameters
set MAX_REPOS=10
set MAX_COMMITS=1000
set SKIP_MINE=0
set INCLUDE_CHECKOUT=0

REM Parse arguments
:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="--max-repos" (
    set MAX_REPOS=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--max-commits" (
    set MAX_COMMITS=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--skip-mine" (
    set SKIP_MINE=1
    shift
    goto parse_args
)
if /i "%~1"=="--full" (
    set INCLUDE_CHECKOUT=1
    shift
    goto parse_args
)
if /i "%~1"=="--help" (
    echo.
    echo Usage: run_pipeline.bat [OPTIONS]
    echo.
    echo Options:
    echo   --max-repos N       Maximum repositories to mine (default: 10^)
    echo   --max-commits N     Maximum commits per repo (default: 1000^)
    echo   --skip-mine         Skip mining phase (use existing repos^)
    echo   --full              Include checkout phase
    echo   --help              Show this help message
    echo.
    echo Note: Always uses single-file commits only
    echo.
    exit /b 0
)
echo Unknown option: %~1
echo Use --help for usage information
exit /b 1

:end_parse

REM Check if we're in the right directory
if not exist "scripts" (
    echo ERROR: scripts/ directory not found
    echo Please run from Ground_Truth_Dataset/
    exit /b 1
)

REM Start pipeline
echo.
echo === Ground Truth Dataset Pipeline ===
echo Max repos: %MAX_REPOS%
echo Max commits per repo: %MAX_COMMITS%
echo Single-file commits: always
echo Include checkout: %INCLUDE_CHECKOUT%
echo.

REM Track start time
set START_TIME=%time%

REM Phase 1: Mine repositories
if %SKIP_MINE%==0 (
    echo [1/5] Mining repositories...
    python scripts\mine_repos.py --max %MAX_REPOS%
    if errorlevel 1 exit /b 1
    echo Done
    echo.
) else (
    echo [1/5] Skipping mining phase
    echo.
)

REM Phase 2: Validate test presence
echo [2/5] Validating test presence...
python scripts\validate_test_presence.py
if errorlevel 1 exit /b 1
echo Done
echo.

REM Phase 3: Extract commits (always single-file)
echo [3/5] Extracting commits (single-file only^)...
python scripts\extract_commits.py --max %MAX_COMMITS% --single
if errorlevel 1 exit /b 1
echo Done
echo.

REM Phase 4: Map tests to commits
echo [4/5] Mapping tests to commits...
python scripts\map_tests_to_commits.py
if errorlevel 1 exit /b 1
echo Done
echo.

REM Phase 5: Analyze test coverage
echo [5/5] Analyzing test coverage...
python scripts\analyze_test_coverage.py
if errorlevel 1 exit /b 1
echo Done
echo.

REM Phase 6: Checkout commits (optional)
if %INCLUDE_CHECKOUT%==1 (
    echo [6/6] Checking out commits...
    python scripts\checkout_commits.py
    if errorlevel 1 exit /b 1
    echo Done
    echo.
)

REM Calculate elapsed time
set END_TIME=%time%

REM Final summary
echo === Pipeline Complete ===
echo Start time: %START_TIME%
echo End time: %END_TIME%
echo.
echo Generated files:
echo   - results\repo_metadata.json
echo   - results\test_validation.json
echo   - candidate_commits.csv
echo   - test_mapping.csv
echo   - coverage_analysis.csv

if %INCLUDE_CHECKOUT%==1 (
    echo   - checkouts\
)

echo.

REM Show final count
if exist "coverage_analysis.csv" (
    for /f %%a in ('find /c /v "" ^< coverage_analysis.csv') do set LINE_COUNT=%%a
    set /a FINAL_COUNT=!LINE_COUNT!-1
    echo Final dataset: !FINAL_COUNT! commits
)

echo.
echo Done!

endlocal
