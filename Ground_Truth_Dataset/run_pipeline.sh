#!/bin/bash
#
# Master Pipeline Script - Ground Truth Dataset
# Runs the complete pipeline from mining repos to analyzing test coverage
# Always uses single-file commits only
#
# Pipeline Phases:
#   1. Mine repositories (with pre-clone filters)
#   2. Validate test presence
#   3. Validate repo type (filter C++/CUDA repos) - NEW!
#   4. Extract commits (single-file only)
#   5. Map tests to commits
#   6. Analyze test coverage
#   7. Checkout commits (optional with --full)
#
# Usage:
#   ./run_pipeline.sh                    # Run with defaults
#   ./run_pipeline.sh --max-repos 20     # Custom repo limit
#   ./run_pipeline.sh --skip-mine        # Skip mining phase
#   ./run_pipeline.sh --full             # Include checkout phase
#

set -e  # Exit on error

# Default parameters
MAX_REPOS=10
MAX_COMMITS=1000
SKIP_MINE=false
INCLUDE_CHECKOUT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-repos)
            MAX_REPOS="$2"
            shift 2
            ;;
        --max-commits)
            MAX_COMMITS="$2"
            shift 2
            ;;
        --skip-mine)
            SKIP_MINE=true
            shift
            ;;
        --full)
            INCLUDE_CHECKOUT=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --max-repos N       Maximum repositories to mine (default: 10)"
            echo "  --max-commits N     Maximum commits per repo (default: 500)"
            echo "  --skip-mine         Skip mining phase (use existing repos)"
            echo "  --full              Include checkout phase"
            echo "  --help              Show this help message"
            echo ""
            echo "Note: Always uses single-file commits only"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [ ! -d "scripts" ]; then
    echo "ERROR: scripts/ directory not found"
    echo "Please run from Ground_Truth_Dataset/"
    exit 1
fi

# Start pipeline
echo ""
echo "=== Ground Truth Dataset Pipeline ==="
echo "Max repos: $MAX_REPOS"
echo "Max commits per repo: $MAX_COMMITS"
echo "Single-file commits: always"
echo "Include checkout: $INCLUDE_CHECKOUT"
echo ""

START_TIME=$(date +%s)

# Phase 1: Mine repositories
if [ "$SKIP_MINE" = false ]; then
    echo "[1/6] Mining repositories..."
    python scripts/mine_repos.py --max $MAX_REPOS
    echo "Done"
    echo ""
else
    echo "[1/6] Skipping mining phase"
    echo ""
fi

# Phase 1.5: Validate test presence
echo "[2/6] Validating test presence..."
python scripts/validate_test_presence.py
echo "Done"
echo ""

# Phase 1.6: Validate repository type (NEW - filters C++/CUDA repos)
echo "[3/6] Validating repository type (filter C++/CUDA)..."
python scripts/validate_repo_type.py
echo "Done"
echo ""

# Phase 2: Extract commits (always single-file)
echo "[4/6] Extracting commits (single-file only)..."
python scripts/extract_commits.py --max $MAX_COMMITS --single
echo "Done"
echo ""

# Phase 2.5: Map tests to commits
echo "[5/6] Mapping tests to commits..."
python scripts/map_tests_to_commits.py
echo "Done"
echo ""

# Phase 3: Analyze test coverage
echo "[6/6] Analyzing test coverage..."
python scripts/analyze_test_coverage.py
echo "Done"
echo ""

# Phase 4: Checkout commits (optional)
if [ "$INCLUDE_CHECKOUT" = true ]; then
    echo "[7/7] Checking out commits..."
    python scripts/checkout_commits.py
    echo "Done"
    echo ""
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

# Final summary
echo "=== Pipeline Complete ==="
echo "Time: ${MINUTES}m ${SECONDS}s"
echo ""
echo "Generated files:"
echo "  - results/repo_metadata.json (Phase 1)"
echo "  - results/test_validation.json (Phase 1.5)"
echo "  - results/repo_type_validation.json (Phase 1.6 - NEW)"
echo "  - results/valid_repos_summary.json (Phase 1.6 - NEW)"
echo "  - candidate_commits.csv (Phase 2)"
echo "  - test_mapping.csv (Phase 2.5)"
echo "  - coverage_analysis.csv (Phase 3)"

if [ "$INCLUDE_CHECKOUT" = true ]; then
    echo "  - checkouts/"
fi

echo ""

# Show final count
if [ -f "coverage_analysis.csv" ]; then
    FINAL_COUNT=$(($(wc -l < coverage_analysis.csv) - 1))
    echo "Final dataset: $FINAL_COUNT commits"
fi

echo ""
echo "Done!"
