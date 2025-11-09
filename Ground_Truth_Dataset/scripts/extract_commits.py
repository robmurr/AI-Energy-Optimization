#!/usr/bin/env python3
"""
------Extract commits-----
"""

import os
import sys
import pandas as pd
from pathlib import Path
from pydriller import Repository
import json

# Keywords
REFACTORING_KEYWORDS = [
    "refactor", "optimize", "performance", "speed", "efficiency",
    "accelerate", "bottleneck", "speed up", "improve performance",
    "faster", "slow", "memory", "cpu", "gpu", "batch",
    "parallel", "vectorize", "cache", "optimize memory",
    "reduce memory", "memory leak", "memory usage"
]

def load_repo_metadata(metadata_file="results/repo_metadata.json"):
    metadata_path = Path(__file__).parent.parent / metadata_file

    with open(metadata_path, 'r') as f:
        return json.load(f)

def load_test_validation(validation_file="results/test_validation.json"):
    """Load test validation results and return repos with tests."""
    validation_path = Path(__file__).parent.parent / validation_file

    if not validation_path.exists():
        print(f"Warning: {validation_file} not found. Proceeding with all repos.")
        return None

    with open(validation_path, 'r') as f:
        validation_data = json.load(f)

    # Return set of repo names that have tests
    repos_with_tests = {repo["repo"] for repo in validation_data if repo["has_tests"]}
    return repos_with_tests

def has_torch_usage(source_code):
    if not source_code:
        return False

    torch_indicators = [
        "import torch",
        "from torch",
        "torch.",
        "nn.Module",
        "torch.tensor",
        "torch.nn",
        "cuda"
    ]

    return any(indicator in source_code for indicator in torch_indicators)

def extract_commits_from_repo(repo_path, repo_name, max_commits=200):
    """
    Extract refactoring/optimization commits from a single repository.
    """
    records = []
    commit_count = 0

    try:
        for commit in Repository(repo_path, only_no_merge=True).traverse_commits():
            # Stop if we've collected enough commits
            if commit_count >= max_commits:
                break

            # Check if commit message contains refactoring keywords
            commit_msg_lower = commit.msg.lower()
            if not any(keyword in commit_msg_lower for keyword in REFACTORING_KEYWORDS):
                continue

            # Check modified Python files
            has_relevant_change = False
            modified_files = []

            for mod in commit.modified_files:
                if mod.filename and mod.filename.endswith(".py"):
                    # Check if the file uses PyTorch
                    source_before = mod.source_code_before or ""
                    source_after = mod.source_code or ""

                    if has_torch_usage(source_before) or has_torch_usage(source_after):
                        has_relevant_change = True
                        modified_files.append(mod.new_path or mod.old_path)

            if has_relevant_change:
                # Replace newlines in commit message with spaces to avoid multi-line CSV fields
                clean_message = " ".join(commit.msg.strip().split())

                records.append({
                    "repo": repo_name,
                    "commit_hash": commit.hash,
                    "parent_hash": commit.parents[0] if commit.parents else None,
                    "author": commit.author.name,
                    "date": commit.author_date.isoformat(),
                    "message": clean_message,
                    "files_changed": len(modified_files),
                    "modified_files": "; ".join(modified_files[:5])  # Limit to first 5 files
                })
                commit_count += 1

    except Exception as e:
        print(f"Warning: Error processing {repo_name}: {e}")

    return records

def mine_commits(repos_dir="repos", max_commits_per_repo=500, repos_with_tests=None):
    """
    only processes repos with test suites if repos_with_tests is provided.
    """
    repos_path = Path(__file__).parent.parent / repos_dir

    if not repos_path.exists():
        print(f"Error: {repos_dir} directory not found.")
        return pd.DataFrame()

    # Get list of repositories
    repo_dirs = [d for d in repos_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

    if not repo_dirs:
        print(f"Error: No repositories found in {repos_dir}")
        return pd.DataFrame()

    # Filter repos based on test validation
    if repos_with_tests is not None:
        original_count = len(repo_dirs)
        repo_dirs = [d for d in repo_dirs if d.name in repos_with_tests]
        skipped = original_count - len(repo_dirs)
        if skipped > 0:
            print(f"\nSkipped {skipped} repository(ies) without test suites")

    print(f"\nMining commits from {len(repo_dirs)} repositories...")
    print()

    all_records = []

    for idx, repo_dir in enumerate(repo_dirs, 1):
        repo_name = repo_dir.name
        print(f"[{idx}/{len(repo_dirs)}] Processing {repo_name}...")

        records = extract_commits_from_repo(str(repo_dir), repo_name, max_commits_per_repo)
        all_records.extend(records)

        print(f"  -> Found {len(records)} candidate commits")

    return pd.DataFrame(all_records)

def save_results(df, output_file="candidate_commits.csv"):
    output_path = Path(__file__).parent.parent / output_file
    df.to_csv(output_path, index=False)
    print(f"\nSaved results to {output_path}")


def main():
    """Main execution function."""
    print("="*60)
    print("COMMIT MINING")
    print("="*60)

    # Load repository metadata from Phase 1
    repos = load_repo_metadata()

    if not repos:
        return 1

    print(f"Loaded metadata for {len(repos)} repositories")

    # Load test validation
    repos_with_tests = load_test_validation()

    if repos_with_tests:
        print(f"Loaded test validation: {len(repos_with_tests)} repositories have tests")
    else:
        print("No test validation found - processing all repositories")

    # Mine commits (only from repos with tests)
    df = mine_commits(max_commits_per_repo=500, repos_with_tests=repos_with_tests)

    if df.empty:
        print("\nError: No candidate commits found.")
        return 1

    # Save results
    save_results(df)

    print("\nComplete!")
    print("="*60 + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
