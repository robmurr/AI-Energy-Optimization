# Docker Test Runner for Commit Pairs

This script parses repositories from `aggregated_test_mapping.csv` and sets up Docker containers to run tests on commit pairs (current commit and its parent commit).

## Overview

The script follows this workflow:
1. **Parse CSV**: Reads `aggregated_test_mapping.csv` to get commits and their associated tests
2. **Build Base Container**: Creates a Docker image once per repository with all dependencies
3. **Process Commit Pairs**: For each commit:
   - Gets the parent commit using `~1` notation (`git rev-parse <commit>~1`)
   - Runs tests on the parent commit (before state)
   - Runs tests on the current commit (after state)
   - Compares results and saves them

## Key Features

- **Commit Pair Processing**: Automatically gets parent commits using `~1` notation
- **Efficient Docker Usage**: Builds base container once per repository, then reuses it for multiple commits
- **Multiple Test Runners**: Supports pytest, unittest, and nose
- **Result Comparison**: Compares test outputs between before/after commits
- **Comprehensive Logging**: Logs all operations and saves results to JSON

## Usage

### Basic Usage

```bash
python docker_test_runner.py
```

This will:
- Look for `test_mappings/aggregated_test_mapping.csv` in the script directory
- Auto-detect repository locations
- Process all commits in the CSV

### Advanced Usage

```bash
# Specify custom CSV path
python docker_test_runner.py --csv path/to/aggregated_test_mapping.csv

# Specify output directory
python docker_test_runner.py --output-dir my_results

# Specify repositories directory
python docker_test_runner.py --repos-dir /path/to/cloned/repos

# Limit processing (useful for testing)
python docker_test_runner.py --max-repos 2 --max-commits 5
```

### Command Line Arguments

- `--csv`: Path to aggregated_test_mapping.csv (default: `test_mappings/aggregated_test_mapping.csv`)
- `--output-dir`: Output directory for results (default: `docker_test_results`)
- `--repos-dir`: Base directory containing cloned repositories (auto-detected if not specified)
- `--max-commits`: Maximum commits to process per repository (default: all)
- `--max-repos`: Maximum repositories to process (default: all)

## Repository Detection

The script automatically searches for repositories in common locations:
1. `commit_mining/setup/ml_repos_isolated/successful_clones/`
2. `commit_mining/pytorch/repos/`
3. `commit_mining/tensorflow/repos/`

You can override this with `--repos-dir`.

## Output Structure

```
docker_test_results/
├── test_results/              # Individual test result JSON files
│   ├── repo1_abc1234_results.json
│   ├── repo1_def5678_results.json
│   └── ...
├── docker_containers/         # Generated Dockerfiles
│   ├── repo1_Dockerfile
│   └── ...
├── logs/                      # Execution logs
│   └── docker_test_runner_YYYYMMDD.log
└── execution_summary.json     # Overall execution summary
```

## Result Format

Each result JSON file contains:

```json
{
  "repo": "pytorch",
  "commit_hash": "abc123...",
  "parent_hash": "def456...",
  "test_files": "test/test_file.py",
  "modified_files": "torch/nn/module.py",
  "test_strategy": "imports",
  "parent_test_results": {
    "success": true,
    "stdout": "...",
    "stderr": "...",
    "output_length": 1234
  },
  "current_test_results": {
    "success": true,
    "stdout": "...",
    "stderr": "...",
    "output_length": 1234
  },
  "comparison": {
    "results_differ": false,
    "success_changed": false,
    "output_changed": false
  },
  "status": "completed",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Docker Strategy

The script follows the pattern described in the setup folder:

1. **Build base container once**:
   ```bash
   docker build -t my-project:base .
   ```

2. **Run analysis for commit pairs**:
   ```bash
   docker run my-project:base bash -c "
     git checkout <parent-commit>
     ./run-tests.sh > before.log
     
     git checkout <current-commit>
     ./run-tests.sh > after.log
     
     diff before.log after.log
   "
   ```

## Commit Parent Resolution

The script uses Git's `~1` notation to get the parent commit:
- `~1` means "first parent" (one commit back)
- For merge commits, `~1` follows the first parent
- Uses `git rev-parse <commit-hash>~1` to get parent hash

## Requirements

- Docker installed and running
- Python 3.7+
- Git installed
- Cloned repositories available

## Troubleshooting

### Repository Not Found
If you see "repository not found" errors:
- Check that repositories are cloned in the expected location
- Use `--repos-dir` to specify the correct path
- Ensure repository names match between CSV and directory names

### Docker Build Failures
- Check Docker is running: `docker ps`
- Review Dockerfile in `docker_containers/` directory
- Some repositories may have complex dependencies that need manual adjustment

### Test Execution Failures
- Check logs in `logs/` directory
- Some test files may not exist at older commits
- Test runners may need to be installed in Dockerfile

### Parent Commit Not Found
- Some commits may be the first commit (no parent)
- Merge commits may have multiple parents (script uses first parent)
- Check git log: `git log --oneline <commit-hash>~1`

## Example Workflow

```bash
# 1. Ensure CSV exists
ls test_mappings/aggregated_test_mapping.csv

# 2. Ensure repositories are cloned
ls commit_mining/setup/ml_repos_isolated/successful_clones/

# 3. Run with limits for testing
python docker_test_runner.py --max-repos 1 --max-commits 3

# 4. Check results
cat docker_test_results/execution_summary.json
ls docker_test_results/test_results/

# 5. Run full pipeline
python docker_test_runner.py
```

## Notes

- The script builds Docker images which can take time (especially for large repos)
- Test execution can be slow; consider using `--max-commits` for initial testing
- Results are saved incrementally, so you can stop and resume
- Docker containers are cleaned up after each test run (`--rm` flag)


