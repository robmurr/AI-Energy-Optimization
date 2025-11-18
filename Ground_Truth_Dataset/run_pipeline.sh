#!/bin/bash
#
# Master Pipeline Script - Ground Truth Dataset
# Runs the complete pipeline from mining repos to analyzing test coverage
# Always uses single-file commits only
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
    echo "[1/5] Mining repositories..."
    python scripts/mine_repos.py --max $MAX_REPOS
    echo "Done"
    echo ""
else
    echo "[1/5] Skipping mining phase"
    echo ""
fi

# Phase 2: Validate test presence
echo "[2/5] Validating test presence..."
python scripts/validate_test_presence.py
echo "Done"
echo ""

# Phase 3: Extract commits (always single-file)
echo "[3/5] Extracting commits (single-file only)..."
python scripts/extract_commits.py --max $MAX_COMMITS --single
echo "Done"
echo ""

# Phase 4: Map tests to commits
echo "[4/5] Mapping tests to commits..."
python scripts/map_tests_to_commits.py
echo "Done"
echo ""

# Phase 5: Analyze test coverage
echo "[5/5] Analyzing test coverage..."
python scripts/analyze_test_coverage.py
echo "Done"
echo ""

# Phase 6: Checkout commits (optional)
if [ "$INCLUDE_CHECKOUT" = true ]; then
    echo "[6/6] Checking out commits..."
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
echo "  - results/repo_metadata.json"
echo "  - results/test_validation.json"
echo "  - candidate_commits.csv"
echo "  - test_mapping.csv"
echo "  - coverage_analysis.csv"

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
