

import os
import json


def detect_test_framework(repo_path):
    """Detect if a repository has a test suite."""
    indicators_found = []
    test_framework = "unknown"

    config_files = {
        "pytest.ini": "pytest",
        "pytest.cfg": "pytest",
        ".pytest.ini": "pytest",
        "setup.cfg": "pytest/unittest",
        "pyproject.toml": "pytest/unittest",
        "tox.ini": "pytest/unittest",
        "unittest.cfg": "unittest"
    }

    for config_file, framework in config_files.items():
        config_path = os.path.join(repo_path, config_file)
        if os.path.exists(config_path):
            indicators_found.append(config_file)
            if test_framework == "unknown" and "pytest" in framework:
                test_framework = "pytest"

    test_dirs = ["tests", "test", "testing", "unit_tests", "integration_tests"]
    for test_dir in test_dirs:
        test_path = os.path.join(repo_path, test_dir)
        if os.path.exists(test_path) and os.path.isdir(test_path):
            indicators_found.append(f"{test_dir}/")
            if test_framework == "unknown":
                test_framework = "pytest"

    ci_paths = [
        ".github/workflows",
        ".gitlab-ci.yml",
        ".travis.yml",
        "circle.yml",
        ".circleci/config.yml"
    ]

    for ci_path in ci_paths:
        full_path = os.path.join(repo_path, ci_path)
        if os.path.exists(full_path):
            indicators_found.append(ci_path)

    test_files_found = 0
    max_files_to_check = 50

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and
                   d not in ['venv', 'env', 'node_modules', '__pycache__']]

        for file in files:
            if test_files_found >= max_files_to_check:
                break

            if file.startswith("test_") and file.endswith(".py"):
                test_files_found += 1
                if test_framework == "unknown":
                    test_framework = "pytest"
            elif file.endswith("_test.py"):
                test_files_found += 1
                if test_framework == "unknown":
                    test_framework = "unittest"

        if test_files_found >= max_files_to_check:
            break

    if test_files_found > 0:
        indicators_found.append(f"{test_files_found} test file(s)")

    has_tests = len(indicators_found) > 0

    return {
        "has_tests": has_tests,
        "test_indicators": indicators_found,
        "test_framework": test_framework if has_tests else None,
        "test_file_count": test_files_found
    }


def validate_repos():
    repos_dir = "repos"
    results_dir = "results"
    metadata_path = os.path.join(results_dir, "repo_metadata.json")

    if not os.path.exists(repos_dir):
        print(f"Error: {repos_dir}/ directory not found!")
        return

    print(" Validating Test Presence\n")

    metadata = []
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

    repos = [d for d in os.listdir(repos_dir)
             if os.path.isdir(os.path.join(repos_dir, d)) and not d.startswith('.')]

    print(f"Found {len(repos)} repositories\n")

    results = []
    repos_with_tests = 0

    for repo_name in repos:
        repo_path = os.path.join(repos_dir, repo_name)
        test_info = detect_test_framework(repo_path)
        results.append({
            "repo": repo_name,
            **test_info
        })

        if test_info["has_tests"]:
            repos_with_tests += 1
            print(f"{repo_name}: has tests ({test_info['test_framework']})")
        else:
            print(f"{repo_name}: no tests")

    repo_to_test_info = {r["repo"]: r for r in results}

    for repo_meta in metadata:
        repo_name = repo_meta.get("name")
        if repo_name in repo_to_test_info:
            test_info = repo_to_test_info[repo_name]
            repo_meta["has_tests"] = test_info["has_tests"]
            repo_meta["test_framework"] = test_info["test_framework"]
            repo_meta["test_indicators"] = test_info["test_indicators"]
            repo_meta["test_file_count"] = test_info["test_file_count"]

    os.makedirs(results_dir, exist_ok=True)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    test_results_path = os.path.join(results_dir, "test_validation.json")
    with open(test_results_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nRepositories with tests: {repos_with_tests}/{len(repos)}")
    print(f"Results saved to {test_results_path}")


if __name__ == "__main__":
    validate_repos()
