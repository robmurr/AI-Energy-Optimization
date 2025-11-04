#!/usr/bin/env python3
"""
----- Checkout Commits -----
"""

import os
import sys
import csv
import subprocess
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
    with open(csv_path, 'r') as f:
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
    print("="*60)
    print("REPOSITORY CHECKOUT")
    print("="*60)
    print()

    # Check if candidate_commits.csv exists
    csv_path = Path(__file__).parent.parent / "candidate_commits.csv"
    if not csv_path.exists():
        print("Error: candidate_commits.csv not found.")
        return 1

    # Process commits (start with first 5 for testing)
    success_count, failures, total = process_commits(csv_path, max_commits=5)

    display_summary(success_count, failures, total)

    print("\nComplete!")

    return 0

if __name__ == "__main__":
    sys.exit(main())
