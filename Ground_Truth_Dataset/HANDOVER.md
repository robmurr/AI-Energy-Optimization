# Commit Mining Pipeline - Handover Documentation

## Executive Summary

This document describes the **Commit Mining Pipeline** - the first phase of a larger ground truth dataset creation project. This pipeline mines, validates, and analyzes PyTorch optimization commits from GitHub repositories, producing a validated CSV file of commits ready for Docker containerization and energy profiling.

**Pipeline Scope:** This is ONE component of the overall project. The output CSV serves as input to the next phase (Docker container project for energy profiling).

**Key Achievement:** Multi-stage filtering approach that ensures only Docker-buildable application repositories with comprehensive test coverage are included in the output.

**Quality Metrics:**
- 40% retention rate after repository filtering (application repos only)
- 100% test coverage validation (tests existed and unchanged)
- ~60-70% of commits have verified test coverage of modified code elements

**Pipeline Output:** `coverage_analysis.csv` - Validated commits ready for Docker containerization

---

## Project Overview

### Objective
Mine and validate PyTorch optimization commits from GitHub repositories where:
1. Code changes are from real-world applications (not frameworks)
2. Each commit has associated tests that cover modified code
3. Tests are unchanged between parent and target commits (valid energy comparison)
4. Repositories are Docker-buildable (no C++/CUDA compilation required)
5. Modified code elements are actually exercised by mapped tests

**This pipeline handles:** Repository mining → Validation → Commit extraction → Test mapping → Coverage analysis

**Next phase (separate project):** Docker containerization → Energy profiling → Dataset assembly

### Use Cases for Pipeline Output
- Input for Docker-based energy profiling pipeline
- Ground truth data for machine learning models
- Research on code optimization patterns
- Performance engineering studies

---

## System Architecture

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GROUND TRUTH DATASET PIPELINE                 │
└─────────────────────────────────────────────────────────────────┘

Phase 1: Repository Mining
├── mine_repos.py
│   ├── Search GitHub for PyTorch repos (50-5000 stars)
│   ├── PRE-CLONE FILTER: Exclude framework orgs & core frameworks
│   ├── Clone repositories (full history)
│   └── Output: repos/, repo_metadata.json
│
Phase 1.5: Test Suite Validation
├── validate_test_presence.py
│   ├── Detect test frameworks (pytest, unittest)
│   ├── Check test directories, config files, CI workflows
│   ├── Count test files
│   └── Output: test_validation.json (repos WITH tests only)
│
Phase 1.6: Repository Type Validation
├── validate_repo_type.py
│   ├── POST-CLONE FILTER: Exclude C++/CUDA compilation
│   ├── Check for complex infrastructure (docker-compose, k8s)
│   ├── Verify ML framework dependencies (torch/tensorflow/sklearn)
│   ├── Detect heavy dependencies (mmcv, detectron2, deepspeed)
│   └── Output: valid_repos_summary.json (Docker-buildable repos only)
│
Phase 2: Commit Extraction
├── extract_commits.py
│   ├── Process VALID repos only (from Phase 1.6)
│   ├── Search for refactoring/optimization keywords
│   ├── Verify PyTorch usage in modified files
│   └── Output: candidate_commits.csv
│
Phase 3: Test Mapping
├── map_tests_to_commits.py
│   ├── Map modified files to relevant tests
│   ├── Strategy: convention → imports → directory → full_suite
│   ├── VALIDATE: Tests existed and unchanged in parent & target
│   └── Output: test_mapping.csv (commits with valid tests only)
│
Phase 4: Test Coverage Analysis [FINAL OUTPUT]
├── analyze_test_coverage.py
│   ├── Parse git diff → identify modified functions/classes/methods
│   ├── Analyze test files → extract imports and calls
│   ├── Match modified elements vs tested elements
│   ├── Calculate coverage percentage
│   └── Output: coverage_analysis.csv (>0% coverage only)
│
Phase 5: Commit Checkout [OPTIONAL - for local testing]
└── checkout_commits.py
    ├── Read coverage_analysis.csv or test_mapping.csv
    ├── Use git worktree for isolated checkouts
    ├── Create parent (before) and target (after) directories
    └── Output: checkouts/ directory with paired commits

═══════════════════════════════════════════════════════════
PIPELINE DELIVERABLE: coverage_analysis.csv
→ Input for Docker container project (next phase)
═══════════════════════════════════════════════════════════
```

### Data Flow

```
GitHub API
    ↓
[mine_repos.py] → repo_metadata.json
    ↓                     ↓
repos/ directory  [validate_test_presence.py] → test_validation.json
    ↓                     ↓
[validate_repo_type.py] → valid_repos_summary.json
    ↓
[extract_commits.py] → candidate_commits.csv
    ↓
[map_tests_to_commits.py] → test_mapping.csv
    ↓
[analyze_test_coverage.py] → coverage_analysis.csv ★ PIPELINE OUTPUT ★
    ↓                              ↓
    ↓                     [Handoff to Docker Project]
    ↓
[checkout_commits.py] → checkouts/ directory (optional, for local testing)
```

---

## Detailed Script Documentation

### 1. mine_repos.py (Phase 1)

**Purpose:** Search GitHub for PyTorch application repositories and clone them locally.

**Methodology:**
1. **GitHub Search Query:** `pytorch OR torch language:Python stars:50..5000`
   - Lower bound (50): Ensures some popularity/quality
   - Upper bound (5000): Excludes mega-frameworks like pytorch/pytorch

2. **Pre-Clone Filtering:**
   - Exclude framework organizations (pytorch, tensorflow, google, etc.)
   - Exclude core framework repos (exact name match: pytorch, torch, transformers)
   - Exclude repos >300MB (likely complex frameworks)
   - Exclude repos >10k stars (likely frameworks, not applications)

3. **Cloning Strategy:**
   - Full clone (not shallow) to access complete commit history
   - Skip if repository already exists locally

**Inputs:**
- GitHub Personal Access Token (from `.env` file or environment variable)
- Command-line arguments: `--max` (max repos to clone)

**Outputs:**
- `repos/` - Directory containing cloned repositories
- `results/repo_metadata.json` - Repository metadata (name, stars, description, URL, clone date)

**Key Design Decisions:**
- **Why full clone?** Need complete history for commit mining (500+ commits per repo)
- **Why star range 50-5000?** Balances quality (>50) vs complexity (<5000)
- **Why exclude framework orgs?** Framework repos require C++/CUDA compilation

**Command:**
```bash
python mine_repos.py --max 20
```

---

### 2. validate_test_presence.py (Phase 1.5)

**Purpose:** Identify repositories with test suites to enable functional validation.

**Methodology:**
1. **Test Framework Detection:**
   - Check config files: pytest.ini, pyproject.toml, setup.cfg, tox.ini
   - Check test directories: tests/, test/, testing/, unit_tests/
   - Check CI/CD workflows: .github/workflows, .gitlab-ci.yml, .travis.yml

2. **Test File Counting:**
   - Search for test_*.py and *_test.py files
   - Limit scan to 50 files (performance optimization)
   - Skip hidden dirs, venv, node_modules

3. **Framework Classification:**
   - pytest: If pytest config or test_*.py files found
   - unittest: If unittest config or *_test.py files found

**Inputs:**
- `results/repo_metadata.json`
- `repos/` directory (cloned repositories)

**Outputs:**
- `results/test_validation.json` - Detailed test validation results
- Updated `results/repo_metadata.json` with `has_tests` field

**Key Design Decisions:**
- **Why validate tests?** No tests = no functional validation of refactorings
- **Why 50 file limit?** Performance optimization for large repos

**Command:**
```bash
python validate_test_presence.py
```

---

### 3. validate_repo_type.py (Phase 1.6)

**Purpose:** Post-clone validation to filter out repositories with complex build requirements.

**Methodology:**
1. **Exclusion Criteria (Build Complexity):**
   - **C++/CUDA Compilation:**
     - CUDAExtension, CppExtension in setup.py
     - .cu, .cuh, .cpp, .c, .h files (compiled extensions)
     - CMakeLists.txt, Makefile
   - **Complex Infrastructure:**
     - docker-compose.yml, kubernetes configs, helm charts
     - celery, ray.serve, kubeflow
   - **Heavy Dependencies (Trojan Horse):**
     - mmcv, mmdet, detectron2 (require C++ compilation)
     - horovod (requires MPI), deepspeed (C++ compilation)
     - cupy (requires CUDA toolkit)

2. **Inclusion Criteria (ML Framework Usage):**
   - Must have torch, tensorflow, or sklearn in dependency files
   - Checks requirements.txt, environment.yml, setup.py, pyproject.toml

3. **Warning Criteria (Not Excluded):**
   - GUI dependencies (cv2.imshow, plt.show) - may fail in Docker
   - Data downloads (s3://, wget, download=True) - tests may timeout
   - Pytest collection failures - tests exist but not discoverable

**Inputs:**
- `results/test_validation.json` (only processes repos WITH tests)
- `repos/` directory

**Outputs:**
- `results/repo_type_validation.json` - Detailed validation results
- `results/valid_repos_summary.json` - List of valid repo names (for Phase 2)

**Key Design Decisions:**
- **Why exclude C++/CUDA?** Docker builds fail without complex toolchains (CUDA, nvcc, g++)
- **Why check dependencies?** Some pip packages require system libraries (GDAL, MPI)
- **Why warning vs exclusion?** GUI/data issues are non-fatal, build issues are fatal

**Expected Results:**
- 40-50% retention rate (valid application repos)
- 50-60% exclusion rate (framework repos, complex builds)

**Command:**
```bash
python validate_repo_type.py
```

---

### 4. extract_commits.py (Phase 2)

**Purpose:** Extract refactoring and optimization commits from valid repositories.

**Methodology:**
1. **Repository Selection:**
   - Reads `valid_repos_summary.json` (Phase 1.6 output)
   - Only processes Docker-buildable application repos with tests

2. **Commit Filtering Criteria:**
   - **Keyword Matching (commit message):**
     - Performance: optimize, performance, speed, efficiency, faster, accelerate
     - Memory: memory, memory leak, reduce memory, optimize memory
     - Parallelization: batch, parallel, vectorize, cache
     - Hardware: cpu, gpu, cuda
   - **PyTorch Usage:** Modified files must import torch/pytorch
   - **Commit Limit:** Configurable max per repo (default: 500)

3. **PyTorch Detection in Files:**
   - Checks for `import torch`, `from torch`, `import pytorch`
   - Uses git show to read file content at specific commit

**Inputs:**
- `results/valid_repos_summary.json` (valid repo names)
- `repos/` directory
- Command-line arguments: `--max` (commits per repo), `--single` (single-file commits only)

**Outputs:**
- `candidate_commits.csv` - Commits with refactoring/optimization keywords

**CSV Columns:**
- repo, commit_hash, parent_hash, author, date, message
- files_changed (count), modified_files (list, truncated to first 5)

**Key Design Decisions:**
- **Why keyword filtering?** Focus on performance-related commits
- **Why verify PyTorch usage?** Ensure commits are relevant to PyTorch optimization
- **Why 500 commit limit?** Balance dataset size vs processing time

**Command:**
```bash
python extract_commits.py --max 50
python extract_commits.py --max 100 --single  # Single-file commits only
```

---

### 5. map_tests_to_commits.py (Phase 3)

**Purpose:** Map modified files to relevant test files and validate tests are unchanged.

**Methodology:**

**Multi-Strategy Test Discovery:**

1. **Convention-based (7.5% success rate):**
   - Direct file name matching
   - `comfy/models/foo.py` → `tests/models/test_foo.py`
   - `src/transformers/trainer.py` → `tests/test_trainer.py`

2. **Import-based (43% success rate):**
   - Search for test files that import the modified file
   - Uses grep: `grep -r "from comfy.models import" tests/`
   - Handles variations: `import module`, `from module import`, `from src.module`
   - Timeout: 5 seconds per grep

3. **Directory-based (11% success rate):**
   - Match directory structure
   - `comfy/utils.py` → `tests/inference/` (if tests/inference/ exists)

4. **Full Suite Fallback (39%):**
   - If no specific tests found, use entire test suite
   - `tests/` or `test/` directory

**Test Validation (Critical):**

For each test file found, validates:
1. Test exists in parent commit (`git ls-tree parent_hash -- test_file`)
2. Test exists in target commit (`git ls-tree commit_hash -- test_file`)
3. Test content is identical (`git show parent:test == git show commit:test`)

If ANY test is modified or missing, commit is EXCLUDED from output.

**Rationale:** Energy comparison requires identical test workload in before/after versions.

**Inputs:**
- `candidate_commits.csv`
- `repos/` directory

**Outputs:**
- `test_mapping.csv` - Commits with validated tests

**CSV Columns:**
- repo, commit_hash, parent_hash, modified_files, modified_file_count
- relevant_tests, test_count, test_strategy
- tests_validated (always "all_unchanged")

**Key Design Decisions:**
- **Why multi-strategy?** No single approach works for all repo structures
- **Why validate unchanged tests?** Ensures fair energy comparison (same workload)
- **Why timeout grep?** Prevents hanging on large repos

**Performance Benefit:**
- Targeted testing: 10-100x faster than full test suite
- 62% of commits have targeted tests (vs 38% full suite)

**Command:**
```bash
python map_tests_to_commits.py
```

---

### 6. analyze_test_coverage.py (Phase 4)

**Purpose:** Verify that mapped tests actually cover the specific code elements modified in each commit.

**Methodology:**

**Step 1: Extract Modified Elements**
1. Get git diff between parent and target commit
2. Parse diff to find changed line numbers
3. Get file content at target commit
4. Parse file with AST (Abstract Syntax Tree) to build line→element map
5. Map changed lines to functions, classes, and methods

**Step 2: Extract Tested Elements**
1. Read test files from specific commit (git show commit:test_file)
2. Extract imports using regex:
   - `from module.path import function, Class`
   - `import module.path`
3. Extract function/method calls using regex:
   - `function_name(`, `Class(`, `obj.method(`
   - Mock/patch targets: `@patch('module.function')`

**Step 3: Calculate Coverage**
1. Match modified elements against tested elements
2. For methods: Match `ClassName.method_name` OR `method_name` OR `ClassName`
3. For functions/classes: Match exact name
4. Calculate coverage percentage: matched / total_modified * 100

**Step 4: Filter Output**
- Exclude commits with 0% coverage (no matching elements)
- Exclude commits with no changes detected (AST parsing failed)
- Exclude commits with no tests detected (empty test analysis)

**Inputs:**
- `test_mapping.csv`
- `repos/` directory
- Command-line arguments: `--max` (limit commits analyzed)

**Outputs:**
- `coverage_analysis.csv` - Only commits with >0% coverage

**CSV Columns:**
- repo, commit_hash, parent_hash, modified_files, relevant_tests, test_strategy
- modified_elements (list), modified_element_count
- tested_elements (set), tested_element_count
- coverage_status (full/partial), coverage_percentage
- matched_elements (what IS tested), unmatched_elements (what is NOT tested)

**Coverage Status:**
- **full (100%):** All modified elements are tested
- **partial (1-99%):** Some modified elements are tested
- **none (0%):** No modified elements are tested [FILTERED OUT]

**Key Design Decisions:**
- **Why AST parsing?** Accurately maps line numbers to code elements
- **Why regex for tests?** AST parsing tests is complex; imports/calls are simple patterns
- **Why filter 0% coverage?** No confidence in energy measurement validity
- **Why read from commits?** Ensures test analysis matches code at commit time

**Expected Results:**
- 35-40% full coverage
- 45-50% partial coverage
- 15-20% no coverage (filtered out)
- Average coverage: 60-70% (after filtering)

**Command:**
```bash
python analyze_test_coverage.py
python analyze_test_coverage.py --max 100  # Analyze first 100 commits
```

---

### 7. checkout_commits.py (Phase 5 - Optional)

**Purpose:** Checkout parent (before) and target (after) versions of commits for local testing and validation.

**Note:** This script is optional. The Docker container project will handle checkouts internally. This script is useful for local development, debugging, and manual verification of commits.

**Methodology:**

**Git Worktree Strategy:**
1. Uses `git worktree add` for isolated checkouts (not copying)
2. Each commit gets TWO directories:
   - `{repo}_{commit_hash[:8]}_parent` - Code BEFORE refactoring
   - `{repo}_{commit_hash[:8]}_target` - Code AFTER refactoring
3. Full repository context preserved (all files, dependencies)

**Checkout Process:**
1. Read input CSV (coverage_analysis.csv or test_mapping.csv)
2. For each commit:
   - Create worktree for parent commit
   - Create worktree for target commit
   - Track success/failure for each
3. Timeout protection: 60s per checkout

**Inputs:**
- `coverage_analysis.csv` (default) or `test_mapping.csv`
- `repos/` directory
- Command-line arguments: `--input`, `--max` (limit commits)

**Outputs:**
- `checkouts/` directory with paired commit directories
- `checkout_results.csv` - Success/failure tracking

**CSV Columns:**
- index, repo, commit_hash, parent_hash
- parent_checkout_success, parent_checkout_error, parent_checkout_path
- target_checkout_success, target_checkout_error, target_checkout_path

**Key Design Decisions:**
- **Why worktree?** Safe, efficient, supports multiple concurrent checkouts
- **Why both parent and target?** Energy profiling compares before/after
- **Why timeout?** Prevent hanging on large checkouts

**Disk Space Estimate:**
- 5 commits: ~500MB
- 186 commits: ~20-40GB
- Depends on repository size

**Command:**
```bash
python checkout_commits.py
python checkout_commits.py --input coverage_analysis.csv --max 50
python checkout_commits.py --input test_mapping.csv  # Use test_mapping instead
```

---

## Pipeline Execution Guide

### Full Pipeline Run (Core Phases)

```bash
# 1. Setup
conda activate energy-pytorch
cd Ground_Truth_Dataset/scripts

# 2. Create .env file with GitHub token
echo "GITHUB_TOKEN=your_token_here" > ../.env

# 3. Run Pipeline (in order) - Core Phases
python mine_repos.py --max 20                    # Phase 1: Clone repos
python validate_test_presence.py                 # Phase 1.5: Validate tests
python validate_repo_type.py                     # Phase 1.6: Validate build type
python extract_commits.py --max 50               # Phase 2: Extract commits
python map_tests_to_commits.py                   # Phase 3: Map tests
python analyze_test_coverage.py                  # Phase 4: Analyze coverage [FINAL OUTPUT]

# 4. Verify Pipeline Output
cat ../coverage_analysis.csv                     # ★ MAIN DELIVERABLE ★

# 5. Optional: Local Checkout (for testing/debugging)
python checkout_commits.py --max 10              # Phase 5 (optional): Checkout commits

# 6. Verify Additional Outputs
ls -lh ../repos/                                 # Cloned repositories
cat ../results/valid_repos_summary.json          # Valid repos
wc -l ../candidate_commits.csv                   # Extracted commits
wc -l ../test_mapping.csv                        # Mapped commits
wc -l ../coverage_analysis.csv                   # Coverage analysis (main output)
ls -lh ../checkouts/                             # Checked out commits (if Phase 5 run)
```

### Quick Start (Small Test)

```bash
# Process just 5 repos, 10 commits each - Core pipeline only
python mine_repos.py --max 5
python validate_test_presence.py
python validate_repo_type.py
python extract_commits.py --max 10
python map_tests_to_commits.py
python analyze_test_coverage.py.                # Produces coverage_analysis.csv

# Optional: Checkout 5 commits for local testing
python checkout_commits.py --max 5
```

**Pipeline Complete:** The `coverage_analysis.csv` file is ready for handoff to the Docker container project.

---



## Pipeline Handoff & Next Steps

### Pipeline Output
This pipeline produces `coverage_analysis.csv` containing validated commits with:
- Repository information
- Commit hashes (parent and target)
- Modified files
- Relevant test files
- Test coverage metrics
- Validation status (tests unchanged, coverage >0%)

### Handoff to Docker Container Project
The `coverage_analysis.csv` file serves as input for the next phase (separate project):

**Next Phase Components (Outside This Pipeline):**
1. **Docker Containerization:**
   - Build Docker images for each repository
   - Install dependencies from requirements.txt
   - Set up test environment

2. **Energy Profiling:**
   - Run Scalene on parent and target commits
   - Measure energy consumption of test suites
   - Collect CPU, GPU, memory metrics

3. **Functional Validation:**
   - Run test suites on parent and target versions
   - Verify tests pass on both versions
   - Filter out commits where tests fail

4. **Dataset Assembly:**
   - Combine commit metadata, test mappings, coverage, energy measurements
   - Export to final dataset format (JSON/parquet)
   - Calculate energy delta statistics


## Contact & Support


**Key Files:**
- Pipeline scripts: `scripts/`
- Results: `results/`
- Cloned repos: `repos/`
- Checkouts: `checkouts/`

**Environment:**
- Conda env: `energy-pytorch`
- Python version: 3.10.18
- Platform: macOS (tested), Linux (should work), Windows (requires WSL)

---

## Appendix: File Structure

### Git-Tracked Files (Committed to Repository)

```
Ground_Truth_Dataset/
├── scripts/                             # Pipeline scripts (all tracked)
│   ├── mine_repos.py                    # Phase 1: Mine repositories
│   ├── validate_test_presence.py        # Phase 1.5: Validate test presence
│   ├── validate_repo_type.py            # Phase 1.6: Validate repo type
│   ├── extract_commits.py               # Phase 2: Extract commits
│   ├── map_tests_to_commits.py          # Phase 3: Map tests to commits
│   ├── analyze_test_coverage.py         # Phase 4: Analyze coverage
│   └── checkout_commits.py              # Phase 5: Checkout commits
│
├── repos/                               # Cloned repositories (empty dir tracked)
│   └── .gitkeep                         # Keeps directory in git
│
├── checkouts/                           # Checked out commits (empty dir tracked)
│   └── .gitkeep                         # Keeps directory in git
│
├── results/                             # Pipeline results (empty dir tracked)
│   └── .gitkeep                         # Keeps directory in git
│
├── dataset/                             # Final dataset (empty dir tracked)
│   └── .gitkeep                         # Keeps directory in git
│
├── run_pipeline.sh                      # Master pipeline (Mac/Linux)
├── HANDOVER.md                          #handover documentation
├── .env.example                         # GitHub token template
└── environment.yml                      # Conda environment specification
```



**Document Version:** 1.0
**Last Updated:** 2025-12-02
**Pipeline Status:** Phases 1-5 implemented and tested
