#!/usr/bin/env python3
"""
Validate that cloned repositories are application repos (not frameworks).

Post-clone validation to filter out:
- Framework repos with C++/CUDA compilation
- Cython repos with compiled Python extensions
- Repos with heavy system library dependencies
- Complex infrastructure/service repos
- Repos with GUI dependencies
- Repos requiring large data downloads
- Repos with undiscoverable tests


"""

import os
import json
import subprocess
from pathlib import Path


# ============================================================================
# NEGATIVE PATTERNS (indicators of complex builds)
# ============================================================================

BUILD_HELL_PATTERNS = [
    'CUDAExtension', 'CppExtension', 'cpp_extension',
    'torch.utils.cpp_extension', 'Extension(',
    'cmdclass=', 'ext_modules=',
]

COMPILED_FILE_EXTENSIONS = {'.cu', '.cuh', '.cpp', '.cc', '.c', '.h', '.hpp', '.pyx', '.pyd'}

COMPLEX_INFRA_PATTERNS = [
    'docker-compose.yml', 'kubernetes', 'helm',
    'celery', 'ray.serve', 'kubeflow',
]

GUI_PATTERNS = [
    'cv2.imshow', 'plt.show(', 'matplotlib.pyplot.show',
    'tkinter', 'pyglet',
]

DATA_DOWNLOAD_PATTERNS = [
    'download=True', 's3://', 'wget ', 'curl ',
    'gdown', 'kaggle datasets',
]

# Dependencies that require complex system libraries or compilation
# These are "trojan horse" dependencies that look pip-installable but fail
HEAVY_DEPENDENCY_BLACKLIST = [
    'mmcv', 'mmdet', 'mmseg', 'mmengine',  # OpenMMLab (requires C++ compilation)
    'detectron2',                           # Facebook Research (requires C++ compilation)
    'gdal', 'rasterio', 'fiona',           # Geospatial (requires GDAL system libraries)
    'deepspeed',                            # Microsoft (requires C++ compilation)
    'horovod',                              # Distributed training (requires MPI)
    'cython',                               # Compilation dependency
    'cupy',                                 # CUDA bindings (requires CUDA toolkit)
]

# ============================================================================
# POSITIVE PATTERNS (ML framework dependencies)
# ============================================================================

ML_FRAMEWORKS = [
    'torch', 'pytorch', 'pytorch-lightning',
    'tensorflow', 'keras', 'tf-',
    'jax', 'flax',
    'scikit-learn', 'sklearn',
    'xgboost', 'lightgbm', 'catboost',
]



def check_dependency_files(repo_path):
    """
    Check if repo uses ML frameworks as dependencies.

    Returns: (has_ml_deps: bool, frameworks_found: list)
    """
    dep_files = [
        'requirements.txt',
        'requirements-dev.txt',
        'environment.yml',
        'pyproject.toml',
        'setup.cfg',
        'setup.py',
    ]

    frameworks_found = []

    for dep_file in dep_files:
        file_path = repo_path / dep_file
        if file_path.exists():
            try:
                content = file_path.read_text().lower()
                for framework in ML_FRAMEWORKS:
                    if framework in content:
                        frameworks_found.append(framework)
            except Exception:
                continue

    return len(frameworks_found) > 0, list(set(frameworks_found))


def check_heavy_dependencies(repo_path):
    """
    Check for "trojan horse" dependencies that require system libraries or compilation.

    These dependencies appear pip-installable but require:
    - System libraries (GDAL, MPI, etc.)
    - C++ compilation
    - CUDA toolkit

    Returns: (has_heavy_deps: bool, reason: str)
    """
    # Check all dependency files including nested requirements
    dep_patterns = [
        'requirements*.txt',
        'pyproject.toml',
        'setup.py',
        'setup.cfg',
        'environment.yml',
    ]

    # Also check requirements/ subdirectories (like mmaction2)
    dep_files = []
    for pattern in dep_patterns:
        if '*' in pattern:
            # Handle glob patterns
            base_name = pattern.replace('*', '')
            for file in repo_path.rglob(pattern):
                # Skip deep nesting and hidden directories
                if '.git' in str(file) or file.parts.count('..') > 2:
                    continue
                dep_files.append(file)
        else:
            # Handle exact filenames
            file_path = repo_path / pattern
            if file_path.exists():
                dep_files.append(file_path)

    # Check requirements/ subdirectory
    req_dir = repo_path / 'requirements'
    if req_dir.exists() and req_dir.is_dir():
        for req_file in req_dir.glob('*.txt'):
            dep_files.append(req_file)

    # Scan all dependency files
    for dep_file in dep_files:
        try:
            content = dep_file.read_text().lower()
            for heavy_dep in HEAVY_DEPENDENCY_BLACKLIST:
                # Match exact package name or with version specifiers
                # e.g., "mmcv", "mmcv>=2.0.0", "mmcv==2.1.0"
                if heavy_dep in content:
                    # Verify it's actually a package reference, not just substring
                    # Check for common patterns: "package", "package>=", "package==", etc.
                    import re
                    pattern = rf'\b{re.escape(heavy_dep)}\b'
                    if re.search(pattern, content):
                        return True, f"Requires heavy dependency: {heavy_dep} (in {dep_file.name})"
        except Exception:
            continue

    return False, None


def check_build_complexity(repo_path):
    """
    Check if repo requires complex C++/CUDA compilation.

    Returns: (is_complex: bool, reason: str)
    """
    # Check for build system files
    build_files = [
        'CMakeLists.txt', 'Makefile', 'configure',
        'BUILD', 'WORKSPACE',  # Bazel
    ]

    for build_file in build_files:
        if (repo_path / build_file).exists():
            return True, f"Has {build_file}"

    # Check setup.py for compilation indicators
    setup_py = repo_path / 'setup.py'
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            for pattern in BUILD_HELL_PATTERNS:
                if pattern in content:
                    return True, f"setup.py contains {pattern}"
        except Exception:
            pass

    # Check for compiled source files
    compiled_count = 0
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden dirs and venv
        dirs[:] = [d for d in dirs if not d.startswith('.')
                   and d not in ['venv', 'env', 'node_modules']]

        for file in files:
            if Path(file).suffix in COMPILED_FILE_EXTENSIONS:
                compiled_count += 1
                if compiled_count > 5:  # More than 5 compiled files = likely framework
                    suffix_list = ', '.join(sorted(set(Path(f).suffix for f in files if Path(f).suffix in COMPILED_FILE_EXTENSIONS))[:3])
                    return True, f"Has {compiled_count}+ compiled files ({suffix_list})"

    return False, None


def check_complex_infra(repo_path):
    """
    Check if repo is a complex service/infrastructure project.

    Returns: (is_complex: bool, reason: str)
    """
    # Check for infrastructure files
    for pattern in COMPLEX_INFRA_PATTERNS:
        # Check as filename
        if (repo_path / pattern).exists():
            return True, f"Has {pattern}"

        # Check in subdirectories (limit depth to 2)
        try:
            for root, dirs, files in os.walk(repo_path):
                # Limit search depth
                current_depth = str(root).count(os.sep) - str(repo_path).count(os.sep)
                if current_depth > 2:
                    dirs.clear()  # Don't recurse further
                    continue

                if pattern in root or pattern in ' '.join(files):
                    return True, f"Contains {pattern}"
        except Exception:
            pass

    return False, None


def check_gui_dependencies(repo_path):
    """
    Check if tests/code rely on GUI rendering.

    Returns: (has_gui: bool, patterns_found: list)
    """
    patterns_found = []

    # Check test files and main code
    for root, dirs, files in os.walk(repo_path):
        # Focus on test directories and main code
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if not file.endswith('.py'):
                continue

            file_path = Path(root) / file
            try:
                content = file_path.read_text()
                for pattern in GUI_PATTERNS:
                    if pattern in content:
                        patterns_found.append(pattern)
                        if len(patterns_found) >= 3:
                            return True, patterns_found
            except Exception:
                continue

        # Only check top 3 levels
        current_depth = str(root).count(os.sep) - str(repo_path).count(os.sep)
        if current_depth > 3:
            break

    return len(patterns_found) > 0, patterns_found


def check_data_downloads(repo_path):
    """
    Check if tests download large datasets.

    Returns: (downloads_data: bool, patterns_found: list)
    """
    patterns_found = []

    # Check test files specifically
    test_dirs = ['tests', 'test', 'testing']

    for test_dir in test_dirs:
        test_path = repo_path / test_dir
        if not test_path.exists():
            continue

        for root, dirs, files in os.walk(test_path):
            for file in files:
                if not file.endswith('.py'):
                    continue

                file_path = Path(root) / file
                try:
                    content = file_path.read_text()
                    for pattern in DATA_DOWNLOAD_PATTERNS:
                        if pattern in content:
                            patterns_found.append(pattern)
                            if len(patterns_found) >= 2:
                                return True, patterns_found
                except Exception:
                    continue

    return len(patterns_found) > 0, patterns_found


def test_pytest_collection(repo_path):
    """
    Run pytest --collect-only to verify tests are discoverable.

    Returns: (tests_discoverable: bool, error: str)
    """
    try:
        result = subprocess.run(
            ['pytest', '--collect-only'],
            cwd=repo_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
            text=True
        )

        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr[:200]  # First 200 chars of error

    except subprocess.TimeoutExpired:
        return False, "pytest collection timeout"
    except FileNotFoundError:
        # pytest not installed - skip this check
        return True, "pytest not available (skipped)"
    except Exception as e:
        return False, str(e)


# ============================================================================
# MAIN VALIDATION LOGIC
# ============================================================================

def validate_single_repo(repo_name, repo_path):
    """
    Validate a single repository.

    Returns: dict with validation results
    """
    repo_path = Path(repo_path)

    result = {
        'repo': repo_name,
        'is_valid': False,
        'validation_status': 'UNKNOWN',
        'exclusion_reason': None,
        'ml_frameworks_found': [],
        'warnings': [],
    }

    # 1. Must have ML framework dependencies (POSITIVE CHECK)
    has_ml_deps, frameworks = check_dependency_files(repo_path)
    result['ml_frameworks_found'] = frameworks

    if not has_ml_deps:
        result['validation_status'] = 'EXCLUDED'
        result['exclusion_reason'] = 'Not an ML repo (no framework dependencies)'
        return result

    # 2. Check for build complexity (NEGATIVE CHECK)
    is_complex, reason = check_build_complexity(repo_path)
    if is_complex:
        result['validation_status'] = 'EXCLUDED'
        result['exclusion_reason'] = f'Build complexity: {reason}'
        return result

    # 3. Check for heavy dependencies (NEGATIVE CHECK - NEW)
    has_heavy, reason = check_heavy_dependencies(repo_path)
    if has_heavy:
        result['validation_status'] = 'EXCLUDED'
        result['exclusion_reason'] = reason
        return result

    # 4. Check for complex infrastructure (NEGATIVE CHECK)
    is_complex, reason = check_complex_infra(repo_path)
    if is_complex:
        result['validation_status'] = 'EXCLUDED'
        result['exclusion_reason'] = f'Complex infrastructure: {reason}'
        return result

    # 5. Check for GUI dependencies (WARNING, not exclusion)
    has_gui, patterns = check_gui_dependencies(repo_path)
    if has_gui:
        result['warnings'].append(f'GUI patterns found: {patterns[:2]}')
        # Don't exclude, but warn

    # 6. Check for data downloads (WARNING, not exclusion)
    downloads_data, patterns = check_data_downloads(repo_path)
    if downloads_data:
        result['warnings'].append(f'Data download patterns: {patterns[:2]}')
        # Don't exclude, but warn

    # 7. Test pytest discovery (WARNING ONLY - requires package installation)
    # NOTE: Changed from EXCLUSION to WARNING because pytest collection
    #       requires the package to be installed (import errors otherwise)
    tests_ok, error = test_pytest_collection(repo_path)
    if not tests_ok and error != "pytest not available (skipped)":
        result['warnings'].append(f'Pytest collection failed (package not installed)')
        # Don't exclude - this is expected for uninstalled packages

    # If we got here, repo is valid!
    result['is_valid'] = True
    result['validation_status'] = 'VALID'

    return result


def validate_all_repos():
    """
    Main function: validate all cloned repositories.
    """
    repos_dir = Path('repos')
    results_dir = Path('results')

    # Read test validation results
    test_validation_path = results_dir / 'test_validation.json'
    if not test_validation_path.exists():
        print(" Error: test_validation.json not found!")
        print("   Run validate_test_presence.py first (Phase 1.5)")
        return

    with open(test_validation_path) as f:
        test_results = json.load(f)

    # Only validate repos that have tests
    repos_with_tests = [r['repo'] for r in test_results if r['has_tests']]

    print("="*60)
    print("REPOSITORY TYPE VALIDATION (Phase 1.6)")
    print("="*60)
    print("Exclusion criteria:")
    print("   C++/CUDA/Cython compilation requirements")
    print("   Heavy dependencies (mmcv, rasterio, deepspeed, etc.)")
    print("   Complex infrastructure (docker-compose, k8s, etc.)")
    print("   No ML framework dependencies")
    print()
    print("Warning criteria (not excluded):")
    print("    GUI dependencies")
    print("    Data downloads")
    print("    Pytest collection failures")
    print("="*60)
    print(f"Repositories to validate: {len(repos_with_tests)}")
    print()

    all_results = []
    valid_count = 0

    for idx, repo_name in enumerate(repos_with_tests, 1):
        repo_path = repos_dir / repo_name

        print(f"[{idx}/{len(repos_with_tests)}] {repo_name}...", end=" ")

        result = validate_single_repo(repo_name, repo_path)
        all_results.append(result)

        if result['is_valid']:
            valid_count += 1
            frameworks = ', '.join(result['ml_frameworks_found'][:3])
            print(f" VALID ({frameworks})")
            if result['warnings']:
                for warning in result['warnings']:
                    print(f"      {warning}")
        else:
            print(f" {result['exclusion_reason']}")

    # Save results
    output_path = results_dir / 'repo_type_validation.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print()
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Valid application repos: {valid_count}/{len(repos_with_tests)}")
    print(f"Excluded: {len(repos_with_tests) - valid_count}")
    print(f"Results saved to: {output_path}")
    print("="*60)
    print()

    # Create summary for next phase
    valid_repos = [r['repo'] for r in all_results if r['is_valid']]

    if valid_count > 0:
        print("✅Valid application repos:")
        for repo in valid_repos:
            print(f"  - {repo}")
        print()

    # Show exclusion breakdown
    exclusions = {}
    for r in all_results:
        if not r['is_valid']:
            reason = r['exclusion_reason']
            exclusions[reason] = exclusions.get(reason, 0) + 1

    if exclusions:
        print(" Exclusion reasons:")
        for reason, count in sorted(exclusions.items(), key=lambda x: -x[1]):
            print(f"  - {reason}: {count}")
        print()

    # Save summary
    summary = {
        'total_repos_checked': len(repos_with_tests),
        'valid_application_repos': valid_count,
        'excluded_repos': len(repos_with_tests) - valid_count,
        'valid_repo_names': valid_repos
    }

    summary_path = results_dir / 'valid_repos_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {summary_path}")
    print()

    return all_results


if __name__ == '__main__':
    validate_all_repos()
