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
import argparse

# Keywords
# 1. High-Confidence Technical Keywords (Almost always performance/energy related)
ML_PERFORMANCE_KEYWORDS = [
    "fp16", "bf16", "mixed precision", "amp",  # Precision
    "quantization", "quantize", "prune", "pruning",  # Model compression
    "fused", "fuse", "kernel", "cuda", "cudnn",  # Ops
    "vectorize", "broadcast", "jit", "compile",  # Compilation
    "inference time", "throughput", "latency", "flops" # Metrics
]

# 2. Data & Memory Keywords (Crucial for system energy)
DATA_MEMORY_KEYWORDS = [
    "dataloader", "num_workers", "pin_memory", "prefetch",  # Data loading
    "memory leak", "oom", "out of memory", "peak memory",  # Memory constraints
    "gradient accumulation", "checkpointing", "buffer"      # Training tricks
]

# 3. General "Intent" Keywords (Must be paired with code changes)
GENERAL_PERF_KEYWORDS = [
    "speed up", "accelerate", "fast", "slow",
    "optimize", "optimization", "efficiency", "efficient",
    "bottleneck", "overhead", "performance"
]

# COMBINED SEARCH LIST
REFACTORING_KEYWORDS = ML_PERFORMANCE_KEYWORDS + DATA_MEMORY_KEYWORDS + GENERAL_PERF_KEYWORDS

def load_repo_metadata(metadata_file="results/repo_metadata.json"):
    metadata_path = Path(__file__).parent.parent / metadata_file

    with open(metadata_path, 'r') as f:
        return json.load(f)

def load_valid_repos():
    """
    Load valid repository list from Phase 1.6 (repo type validation).

    Tries to load from valid_repos_summary.json (Phase 1.6) first.
    Falls back to test_validation.json (Phase 1.5) if Phase 1.6 not run.

    Returns: set of valid repo names, or None if no validation found
    """
    base_path = Path(__file__).parent.parent / "results"

    # Try Phase 1.6 output first (preferred - only application repos)
    phase_1_6_path = base_path / "valid_repos_summary.json"
    if phase_1_6_path.exists():
        with open(phase_1_6_path, 'r') as f:
            summary = json.load(f)
        valid_repos = set(summary['valid_repo_names'])
        print(f"✅ Loaded Phase 1.6 validation: {len(valid_repos)} valid APPLICATION repos")
        print(f"   (Filtered out C++/CUDA/complex repos)")
        return valid_repos

    # Fallback to Phase 1.5 output (repos with tests, but may include C++/CUDA repos)
    phase_1_5_path = base_path / "test_validation.json"
    if phase_1_5_path.exists():
        with open(phase_1_5_path, 'r') as f:
            validation_data = json.load(f)
        repos_with_tests = {repo["repo"] for repo in validation_data if repo["has_tests"]}
        print(f"⚠️  Using Phase 1.5 validation: {len(repos_with_tests)} repos with tests")
        print(f"   (May include C++/CUDA repos - run validate_repo_type.py for better filtering)")
        return repos_with_tests

    # No validation found
    print(f"⚠️  No validation found. Proceeding with all repos.")
    print(f"   Run validate_test_presence.py (Phase 1.5) or validate_repo_type.py (Phase 1.6)")
    return None

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

def save_results(df, output_file="candidate_commits.csv", single_file_only=False):
    """
    Save results to CSV file, optionally filtering for single file commits.

    Args:
        df: DataFrame with commit data
        output_file: Output filename
        single_file_only: If True, only save commits with exactly 1 modified file
    """
    if single_file_only:
        original_count = len(df)
        df = df[df['files_changed'] == 1].copy()
        filtered_count = len(df)
        print(f"\nFiltered to single-file commits: {filtered_count} of {original_count} ({filtered_count/original_count*100:.2f}%)")

    output_path = Path(__file__).parent.parent / output_file
    df.to_csv(output_path, index=False)
    print(f"Saved results to {output_path}")


def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Extract PyTorch optimization/refactoring commits from repositories'
    )
    parser.add_argument(
        '--single',
        action='store_true',
        help='Only output commits with exactly 1 modified file'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=500,
        help='Maximum commits to extract per repository (default: 500)'
    )

    args = parser.parse_args()

    print("="*60)
    print("COMMIT MINING")
    print("="*60)
    print(f"Max commits per repository: {args.max}")

    if args.single:
        print("Filter: Only commits with exactly 1 modified file will be saved")
    print()

    # Load repository metadata from Phase 1
    repos = load_repo_metadata()

    if not repos:
        return 1

    print(f"Loaded metadata for {len(repos)} repositories")
    print()

    # Load valid repos (Phase 1.6 preferred, Phase 1.5 fallback)
    valid_repos = load_valid_repos()
    print()

    # Mine commits (only from valid repos)
    df = mine_commits(max_commits_per_repo=args.max, repos_with_tests=valid_repos)

    if df.empty:
        print("\nError: No candidate commits found.")
        return 1

    # Save results (with optional filtering)
    save_results(df, single_file_only=args.single)

    print("\nComplete!")
    print("="*60 + "\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
