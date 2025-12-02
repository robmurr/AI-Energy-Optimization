#!/usr/bin/env python3
"""
Checkout Commits - Create isolated checkouts of parent and target commits

By default, uses coverage_analysis.csv (filtered commits with test coverage)
Can also use test_mapping.csv or candidate_commits.csv via command-line args

Usage:
    python checkout_commits.py                           # Use coverage_analysis.csv
    python checkout_commits.py --input test_mapping.csv  # Use test_mapping.csv
    python checkout_commits.py --max 10                  # Limit to first 10 commits
"""

import os
import sys
import csv
import subprocess
import argparse
from pathlib import Path

def checkout_commit(repo_path, commit_hash, target_dir):
    """
    Checkout a specific commit to a target directory.

    """
    try:
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Use git worktree to create an isolated checkout
        result = subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "add", str(target_dir), commit_hash],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        return False, "Timeout during checkout"
    except Exception as e:
        return False, str(e)

""" The main function that processes the commits and creates the checkouts. """
def process_commits(csv_path, repos_dir="repos", checkouts_dir="checkouts", max_commits=None):

    # Load commits
    commits = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            commits.append(row)
            if max_commits and len(commits) >= max_commits:
                break

    if max_commits:
        print(f"Processing first {max_commits} commits only\n")

    print(f"Processing {len(commits)} commits...\n")

    # Prepare paths
    base_path = Path(__file__).parent.parent
    repos_path = base_path / repos_dir
    checkouts_path = base_path / checkouts_dir
    checkouts_path.mkdir(exist_ok=True)

    # Track results
    success_count = 0
    failures = []

    for idx, row in enumerate(commits):
        repo_name = row['repo']
        commit_hash = row['commit_hash']
        parent_hash = row['parent_hash']

        print(f"[{idx+1}/{len(commits)}] Processing {repo_name}/{commit_hash[:8]}...", end=" ")

        # Skip if no parent hash
        if not parent_hash or parent_hash.strip() == '':
            failures.append({
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_error': 'No parent hash',
                'target_error': 'Skipped due to no parent'
            })
            print("SKIPPED (no parent hash)")
            continue

        repo_path = repos_path / repo_name
       # Skip if no repo exist locally
        if not repo_path.exists():
            failures.append({
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_error': 'Repository not found',
                'target_error': 'Repository not found'
            })
            print("FAILED (repository not found)")
            continue

        # Create unique directory names
        checkout_id = f"{repo_name}_{commit_hash[:8]}"
        parent_dir = checkouts_path / f"{checkout_id}_parent"
        target_dir = checkouts_path / f"{checkout_id}_target"

        # Checkout parent
        parent_success, parent_error = checkout_commit(repo_path, parent_hash, parent_dir)

        # Checkout target
        target_success, target_error = checkout_commit(repo_path, commit_hash, target_dir)

        # Log status
        if parent_success and target_success:
            success_count += 1
            print("SUCCESS (both checkouts completed)")
        else:
            failures.append({
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_error': parent_error if not parent_success else None,
                'target_error': target_error if not target_success else None
            })
            print("FAILED")
            if not parent_success:
                print(f"  Parent error: {parent_error}")
            if not target_success:
                print(f"  Target error: {target_error}")

    return success_count, failures, len(commits)

""" Display the results in terminal. """
def display_summary(success_count, failures, total):
    print("\n" + "="*60)
    print("CHECKOUT RESULTS")
    print("="*60)

    print(f"Successful checkouts: {success_count}/{total}")

    # Show failures if any
    if len(failures) > 0:
        print("\nFailures:")
        for failure in failures:
            print(f"\n  {failure['repo']}/{failure['commit_hash'][:8]}:")
            if failure['parent_error']:
                print(f"    Parent: {failure['parent_error']}")
            if failure['target_error']:
                print(f"    Target: {failure['target_error']}")

    print("="*60)

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Checkout commits for before/after comparison'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='coverage_analysis.csv',
        help='Input CSV file (default: coverage_analysis.csv)'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=5,
        help='Maximum number of commits to checkout (default: all)'
    )
    args = parser.parse_args()

    print("="*60)
    print("REPOSITORY CHECKOUT")
    print("="*60)
    print()

    # Check if input CSV exists
    csv_path = Path(__file__).parent.parent / args.input
    if not csv_path.exists():
        print(f"Error: {args.input} not found.")
        print(f"Expected path: {csv_path}")
        print("\nAvailable options:")
        print("  - coverage_analysis.csv (default, filtered commits)")
        print("  - test_mapping.csv (commits with tests)")
        print("  - candidate_commits.csv (all extracted commits)")
        return 1

    print(f"Input file: {args.input}")
    if args.max:
        print(f"Max commits: {args.max}")
    print()

    # Process commits
    success_count, failures, total = process_commits(csv_path, max_commits=args.max)

    display_summary(success_count, failures, total)

    print("\nComplete!")

    return 0

if __name__ == "__main__":
    sys.exit(main())
