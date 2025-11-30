#!/usr/bin/env python3
"""
Map Modified Files to Relevant Tests

"""

import os
import sys
import csv
import subprocess
from pathlib import Path


def find_test_by_convention(repo_path, modified_file):
    """
    strategy1: file name conventions.
    ex: comfy/models/foo.py → tests/models/test_foo.py
    """
    basename = Path(modified_file).stem
    parent_dir = Path(modified_file).parent

    test_patterns = [
        f"test_{basename}.py",
        f"{basename}_test.py",
    ]

    test_dirs = ["tests", "test", "testing"]

    candidates = []

    for test_dir in test_dirs:
        test_dir_path = repo_path / test_dir
        if test_dir_path.exists():
            for pattern in test_patterns:
                candidate = test_dir_path / pattern
                if candidate.exists():
                    candidates.append(str(candidate.relative_to(repo_path)))
                
                if parent_dir != Path('.'):
                    parts = parent_dir.parts
                    if len(parts) > 1:
                        subdir = Path(*parts[1:]) 
                    else:
                        subdir = parts[0]

                    candidate = test_dir_path / subdir / pattern
                    if candidate.exists():
                        candidates.append(str(candidate.relative_to(repo_path)))

    return candidates


def find_test_by_directory(repo_path, modified_file):
    """
    Strategy2: Find test directory that matches the modified file's directory.

    ex: torch/nn/functional.py → test/nn/
    """
    parent_dir = Path(modified_file).parent
    test_dirs = ["tests", "test", "testing"]

    candidates = []

    for test_dir in test_dirs:
        test_dir_path = repo_path / test_dir
        if not test_dir_path.exists():
            continue

        parts = parent_dir.parts
        if len(parts) > 1:
            subdir = Path(*parts[1:]) 
            matching_test_dir = test_dir_path / subdir
            if matching_test_dir.exists():
                candidates.append(str(matching_test_dir.relative_to(repo_path)))
        elif len(parts) == 1:
            matching_test_dir = test_dir_path / parts[0]
            if matching_test_dir.exists():
                candidates.append(str(matching_test_dir.relative_to(repo_path)))

    return candidates


def find_test_by_imports(repo_path, modified_file):
    """
    strategy3: Find test files that import the modified file.

    """
    # Convert file path to module path
    #  comfy/model_base.py -> comfy.model_base
    module_path = Path(modified_file).with_suffix('')
    module_name = str(module_path).replace(os.sep, '.')

    # Extract the last component for partial matching
    # comfy.model_base -> model_base
    module_basename = module_path.stem

    test_dirs = ["tests", "test", "testing"]
    candidates = []

    for test_dir in test_dirs:
        test_dir_path = repo_path / test_dir
        if not test_dir_path.exists():
            continue

        # Search for import
        patterns = [
            f"from {module_name} import",  # from comfy.model_base import
            f"from {module_name.rsplit('.', 1)[0]} import {module_basename}",  # from comfy import model_base
            f"import {module_name}",  # import comfy.model_base
        ]

        # handle if file is in a package (e.g., src/transformers/...)
        parts = module_name.split('.')
        if len(parts) > 1 and parts[0] in ['src', 'lib']:
            alt_module = '.'.join(parts[1:])
            patterns.extend([
                f"from {alt_module} import",
                f"import {alt_module}",
            ])

        for pattern in patterns:
            # OPTION 1: Use grep (fast, but only works on Mac/Linux with grep installed)
            grep_success = False
            try:
                result = subprocess.run(
                    ['grep', '-r', '-l', '--include=*.py', pattern, str(test_dir_path)],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=5
                )

                if result.returncode == 0:
                    # add test files
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            test_file = Path(line).relative_to(repo_path)
                            candidates.append(str(test_file))
                    grep_success = True

            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, OSError):
                # Skip if grep fails, times out, or is not available (Windows)
                pass

            # OPTION 2: Pure Python search (cross-platform, works on Windows)
            # Use this if grep failed or is not available
            if not grep_success:
                try:
                    # Search for pattern in Python files recursively
                    for py_file in test_dir_path.rglob('*.py'):
                        try:
                            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern in content:
                                    test_file = py_file.relative_to(repo_path)
                                    candidates.append(str(test_file))
                        except (IOError, OSError):
                            # Skip files we can't read
                            continue
                except Exception:
                    # Skip if search fails
                    pass

    # Remove duplicates while preserving order
    return list(dict.fromkeys(candidates))


def find_relevant_tests(repo_path, modified_files):
    """
    main mapping function
    """
    repo_path = Path(repo_path)
    relevant_tests = []
    strategies_used = []

    for modified_file in modified_files:
        # Skip non-Python files
        if not modified_file.endswith('.py'):
            continue

        # Strategy 1: file convention-based matching
        tests = find_test_by_convention(repo_path, modified_file)
        if tests:
            relevant_tests.extend(tests)
            strategies_used.append('convention')
            continue

        # Strategy 2: Import-based matching
        tests = find_test_by_imports(repo_path, modified_file)
        if tests:
            relevant_tests.extend(tests)
            strategies_used.append('imports')
            continue

        # Strategy 3: Directory-level matching
        test_dirs = find_test_by_directory(repo_path, modified_file)
        if test_dirs:
            relevant_tests.extend(test_dirs)
            strategies_used.append('directory')
            continue

    # Remove duplicates]
    relevant_tests = list(dict.fromkeys(relevant_tests))

    if not relevant_tests:
        return None

    # Determine overall strategy
    if 'convention' in strategies_used:
        strategy = 'convention'
    elif 'imports' in strategies_used:
        strategy = 'imports'
    elif 'directory' in strategies_used:
        strategy = 'directory'
    else:
        strategy = 'mixed'

    return {
        'tests': relevant_tests,
        'strategy': strategy
    }


def process_commits(csv_path, repos_dir="repos", max_commits=None):
    """
    Process commits and map modified files to relevant tests.
    """
    csv_path = Path(csv_path)
    repos_path = Path(__file__).parent / repos_dir

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return []

    # Read commits
    commits = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            commits.append(row)
            if max_commits and len(commits) >= max_commits:
                break

    print(f"Processing {len(commits)} commits...\n")

    results = []

    for idx, commit in enumerate(commits, 1):
        repo_name = commit['repo']
        commit_hash = commit['commit_hash']
        modified_files_str = commit.get('modified_files', '')

        print(f"[{idx}/{len(commits)}] {repo_name}/{commit_hash[:8]}...", end=" ")
        modified_files = [f.strip() for f in modified_files_str.split(';') if f.strip()]

        if not modified_files:
            print("SKIP (no modified files)")
            continue

        # Find relevant tests
        repo_path = repos_path / repo_name
        if not repo_path.exists():
            print("SKIP (repo not found)")
            continue

        test_info = find_relevant_tests(repo_path, modified_files)

        if test_info is None:
            print("SKIP (no tests found in first 3 strategies)")
            continue

        results.append({
            'repo': repo_name,
            'commit_hash': commit_hash,
            'modified_files': modified_files_str,
            'modified_file_count': len(modified_files),
            'relevant_tests': '; '.join(test_info['tests']),
            'test_count': len(test_info['tests']),
            'test_strategy': test_info['strategy']
        })

        print(f"OK ({test_info['strategy']}, {len(test_info['tests'])} test(s))")

    return results


def save_results(results, output_file="test_mapping.csv"):
    output_path = Path(__file__).parent / output_file

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'repo', 'commit_hash', 'modified_files', 'modified_file_count',
            'relevant_tests', 'test_count', 'test_strategy'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {output_path}")


def print_summary(results):
    total = len(results)

    # Count by strategy
    strategies = {}
    for result in results:
        strategy = result['test_strategy']
        strategies[strategy] = strategies.get(strategy, 0) + 1

    # Count by test discovery success
    targeted = sum(1 for r in results if r['test_strategy'] != 'full_suite')

    print("\n" + "="*60)
    print("TEST MAPPING SUMMARY")
    print("="*60)
    print(f"Total commits processed: {total}")
    print(f"\nTest Discovery Strategies:")
    for strategy, count in sorted(strategies.items()):
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {strategy:15s}: {count:3d} ({percentage:5.1f}%)")

    print(f"\nTargeted tests found: {targeted}/{total} ({targeted/total*100:.1f}%)")
    print("="*60)


def main():
    """Main execution function."""
    print("="*60)
    print("MAP TESTS TO COMMITS")
    print("="*60)
    print()

    # Look for candidate_commits.csv in the same directory as this script
    csv_path = Path(__file__).parent / "candidate_commits.csv"
    
    if not csv_path.exists():
        print(f"Error: candidate_commits.csv not found in {Path(__file__).parent}")
        return 1

    # Process commits
    results = process_commits(str(csv_path))

    if not results:
        print("\nNo results to save (no tests found for any commits).")
        return 0  # Not an error, just no tests found

    # Save results
    save_results(results)

    # Print summary
    print_summary(results)

    print("\nComplete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
