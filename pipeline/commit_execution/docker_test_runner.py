#!/usr/bin/env python3
"""
Docker Test Runner for Commit Pairs
Parses repositories from CSV and sets up Docker containers to run tests
on commit pairs (current commit and its parent commit).
"""

import csv
import json
import os
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import tempfile

# Import Docker-related modules
from docker_image_builder import DockerImageBuilder
from docker_container_runner import DockerContainerRunner


class DockerTestRunner:
    """Manages Docker container setup and test execution for commit pairs."""
    
    def __init__(self, csv_path: Path, output_dir: Path, repos_base_dir: Optional[Path] = None):
        """
        Initialize the Docker test runner.
        
        Args:
            csv_path: Path to aggregated_test_mapping.csv
            output_dir: Directory for storing results
            repos_base_dir: Base directory containing cloned repositories
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        script_dir = Path(__file__).parent
        self.framework_repos_dirs = {
            'pytorch': script_dir.parent / 'commit_mining' / 'pytorch' / 'repos',
            'tensorflow': script_dir.parent / 'commit_mining' / 'tensorflow' / 'repos',
            'matplotlib': script_dir.parent / 'commit_mining' / 'matplotlib' / 'repos',
        }
        
        if repos_base_dir:
            self.repos_base_dir = Path(repos_base_dir)
        else:
            self.repos_base_dir = None
        
        self.results_dir = self.output_dir / 'test_results'
        self.results_dir.mkdir(exist_ok=True)
        
        self.docker_dir = self.output_dir / 'docker_containers'
        self.docker_dir.mkdir(exist_ok=True)
        
        self.local_repos_dir = self.output_dir / 'local_repos'
        self.local_repos_dir.mkdir(exist_ok=True)
        
        self.docker_image_builder = DockerImageBuilder(self.docker_dir, self.log)
        self.docker_container_runner = DockerContainerRunner(self.log)
        
        self.stats = {
            'total_commits': 0,
            'processed_commits': 0,
            'failed_commits': 0,
            'skipped_commits': 0,
            'repos_processed': set(),
            'errors': [],
            'total_commits_processed': 0  
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Print a message to terminal (no file logging)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
    
    def parse_csv(self) -> Dict[str, List[Dict]]:
        """
        Parse the aggregated_test_mapping.csv file.
        
        Returns:
            Dictionary mapping repo names to lists of commit records
        """
        commits_by_repo = defaultdict(list)
        
        if not self.csv_path.exists():
            self.log(f"CSV file not found: {self.csv_path}", "ERROR")
            return commits_by_repo
        
        self.log(f"Parsing CSV: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                repo = row['repo']
                commits_by_repo[repo].append(row)
                self.stats['total_commits'] += 1
        
        self.log(f"Found {len(commits_by_repo)} repositories with {self.stats['total_commits']} total commits")
        return commits_by_repo
    
    def get_repo_remote_url(self, repo_path: Path) -> Optional[str]:
        """
        Get the remote URL for a repository.
        
        Args:
            repo_path: Path to the git repository
            
        Returns:
            Remote URL or None if not found
        """
        try:
            cmd = ['git', 'remote', 'get-url', 'origin']
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            if result.returncode == 0:
                url = result.stdout.strip()
                if url:
                    return url
        except Exception as e:
            self.log(f"Error getting remote URL for {repo_path}: {e}", "WARNING")
        
        return None
    
    def get_parent_commit(self, repo_path: Path, commit_hash: str) -> Optional[str]:
        """
        Get the parent commit hash for a given commit.
        
        Args:
            repo_path: Path to the git repository
            commit_hash: Commit hash to get parent for
            
        Returns:
            Parent commit hash or None if not found
        """
        try:
            cmd = ['git', 'rev-parse', f'{commit_hash}~1']
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace', 
                timeout=30
            )
            
            if result.returncode == 0:
                parent_hash = result.stdout.strip()
                if parent_hash:
                    return parent_hash
        except subprocess.TimeoutExpired:
            self.log(f"Timeout getting parent commit for {commit_hash[:8]}", "WARNING")
        except Exception as e:
            self.log(f"Error getting parent commit for {commit_hash[:8]}: {e}", "WARNING")
        
        return None
    
    def clone_and_checkout_local(
        self,
        repo_remote_url: str,
        commit_hash: str,
        repo_name: str
    ) -> Optional[Path]:
        """
        Clone repository locally and checkout specific commit.
        Creates a local copy of the repo checked out at the specified commit.
        
        Args:
            repo_remote_url: Remote URL of the repository
            commit_hash: Commit hash to checkout
            repo_name: Repository name (for directory naming)
            
        Returns:
            Path to checked-out repository or None if failed
        """
        repo_dir_name = f"{repo_name}_{commit_hash[:8]}"
        repo_checkout_path = self.local_repos_dir / repo_dir_name
        
        if repo_checkout_path.exists() and (repo_checkout_path / '.git').exists():
            try:
                cmd = ['git', 'rev-parse', 'HEAD']
                result = subprocess.run(
                    cmd,
                    cwd=str(repo_checkout_path),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip() == commit_hash:
                    self.log(f"Reusing existing checkout: {repo_dir_name}")
                    return repo_checkout_path
            except Exception:
                pass
        
        if repo_checkout_path.exists():
            try:
                shutil.rmtree(repo_checkout_path)
            except Exception as e:
                self.log(f"Warning: Could not remove existing directory {repo_dir_name}: {e}", "WARNING")
        
        self.log(f"Cloning {repo_name} locally for commit {commit_hash[:8]}...")
        try:
            cmd = ['git', 'clone', '--no-checkout', repo_remote_url, str(repo_checkout_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  
            )
            
            if result.returncode != 0:
                self.log(f"Failed to clone {repo_name}: {result.stderr}", "ERROR")
                if repo_checkout_path.exists():
                    try:
                        shutil.rmtree(repo_checkout_path)
                    except Exception:
                        pass
                return None
            
            self.log(f"Checking out commit {commit_hash[:8]}...")
            cmd = ['git', 'checkout', commit_hash]
            result = subprocess.run(
                cmd,
                cwd=str(repo_checkout_path),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log(f"Failed to checkout commit {commit_hash[:8]}: {result.stderr}", "ERROR")
                if repo_checkout_path.exists():
                    try:
                        shutil.rmtree(repo_checkout_path)
                    except Exception:
                        pass
                return None
            
            cmd = ['git', 'rev-parse', 'HEAD']
            result = subprocess.run(
                cmd,
                cwd=str(repo_checkout_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                current_commit = result.stdout.strip()
                if current_commit == commit_hash:
                    self.log(f"Successfully cloned and checked out {repo_name} at {commit_hash[:8]}")
                    return repo_checkout_path
                else:
                    self.log(f"Warning: Checkout verification failed. Expected {commit_hash[:8]}, got {current_commit[:8]}", "WARNING")
            
            return repo_checkout_path
            
        except subprocess.TimeoutExpired:
            self.log(f"Timeout cloning/checking out {repo_name} at {commit_hash[:8]}", "ERROR")
            if repo_checkout_path.exists():
                try:
                    shutil.rmtree(repo_checkout_path)
                except Exception:
                    pass
            return None
        except Exception as e:
            self.log(f"Error cloning/checking out {repo_name} at {commit_hash[:8]}: {e}", "ERROR")
            if repo_checkout_path.exists():
                try:
                    shutil.rmtree(repo_checkout_path)
                except Exception:
                    pass
            return None
    
    def cleanup_local_repo(self, repo_path: Path):
        if repo_path and repo_path.exists():
            try:
                shutil.rmtree(repo_path)
            except Exception:
                pass
    
    def verify_test_files_exist(self, local_repo_path: Path, test_files: str) -> bool:
        """
        Verify that test files exist in the cloned repository.
        
        Args:
            local_repo_path: Path to locally cloned repository
            test_files: Semicolon-separated test file paths
            
        Returns:
            True if at least one test file exists, False otherwise
        """
        if not local_repo_path.exists():
            self.log(f"  Verification failed: Local repo path does not exist: {local_repo_path}", "DEBUG")
            return False
        
        if not test_files or test_files == 'None' or test_files.strip() == '':
            test_dir = local_repo_path / 'test'
            tests_dir = local_repo_path / 'tests'
            test_exists = test_dir.exists() or tests_dir.exists()
            self.log(f"  No test files specified, checking test directories: test={test_dir.exists()}, tests={tests_dir.exists()}", "DEBUG")
            return test_exists
        
        normalized_test_files = test_files.replace('\\', '/')
        self.log(f"  Verifying test files in: {local_repo_path.name}", "DEBUG")
        self.log(f"  Normalized test files: {normalized_test_files}", "DEBUG")
        
        test_file_list = [f.strip() for f in normalized_test_files.split(';') if f.strip()]
        
        for test_file in test_file_list:
            self.log(f"  Checking test file: {test_file}", "DEBUG")
            
            test_path = local_repo_path / test_file
            self.log(f"    Exact path: {test_path}", "DEBUG")
            self.log(f"    Exists: {test_path.exists()}", "DEBUG")
            if test_path.exists():
                self.log(f"    ✓ Found exact path: {test_path}", "DEBUG")
                return True
            
            filename = test_path.name
            self.log(f"    Searching for filename: {filename}", "DEBUG")
            try:
                found_files = list(local_repo_path.rglob(filename))
                self.log(f"    Found {len(found_files)} files with name '{filename}'", "DEBUG")
                if found_files:
                    for found in found_files[:3]:  
                        self.log(f"      - {found.relative_to(local_repo_path)}", "DEBUG")
                    self.log(f"    ✓ Found by filename search: {found_files[0]}", "DEBUG")
                    return True
            except Exception as e:
                self.log(f"    Error searching for filename: {e}", "DEBUG")
            
            if test_path.suffix == '' or '/' in test_file:
                dir_path = local_repo_path / test_file
                self.log(f"    Checking as directory: {dir_path}", "DEBUG")
                self.log(f"    Directory exists: {dir_path.exists()}", "DEBUG")
                if dir_path.exists():
                    self.log(f"    Is directory: {dir_path.is_dir()}", "DEBUG")
                if dir_path.exists() and dir_path.is_dir():
                    self.log(f"    ✓ Found directory: {dir_path}", "DEBUG")
                    return True
        
        test_dir = local_repo_path / 'test'
        tests_dir = local_repo_path / 'tests'
        test_dir_exists = test_dir.exists()
        tests_dir_exists = tests_dir.exists()
        self.log(f"  Fallback: checking test directories - test={test_dir_exists}, tests={tests_dir_exists}", "DEBUG")
        
        if tests_dir.exists():
            try:
                test_contents = list(tests_dir.iterdir())[:10]  
                self.log(f"  Contents of tests/ directory:", "DEBUG")
                for item in test_contents:
                    self.log(f"    - {item.name} ({'dir' if item.is_dir() else 'file'})", "DEBUG")
            except Exception:
                pass
        
        return test_dir_exists or tests_dir_exists
    
    def filter_test_output(self, stdout: str) -> str:
        """
        Filter stdout to only include test output, removing git checkout messages.
        
        Args:
            stdout: Raw stdout from test execution
            
        Returns:
            Filtered stdout with only test output
        """
        lines = stdout.split('\n')
        filtered_lines = []
        skip_until_test = True
        
        git_patterns = [
            'Cleaning repository state',
            'HEAD is now at',
            'Updated',
            'Fetching latest commits',
            'Checking out commit',
            'Successfully checked out',
            'Previous HEAD position',
            'You are in',
            'detached HEAD',
            'Turn off this advice',
            'git switch',
            'Updating files:',
            'Note: switching to',
        ]
        
        test_patterns = [
            'Running tests',
            'test_',
            'PASSED',
            'FAILED',
            'ERROR',
            'collected',
            'pytest',
            'unittest',
            'nosetests',
            'Ran',
            'tests',
        ]
        
        for line in lines:
            is_git_message = any(pattern.lower() in line.lower() for pattern in git_patterns)
            is_test_output = any(pattern.lower() in line.lower() for pattern in test_patterns)
            
            if is_test_output:
                skip_until_test = False
            
            if not skip_until_test and not is_git_message:
                filtered_lines.append(line)
            elif not skip_until_test and is_git_message:
                continue
        
        return '\n'.join(filtered_lines).strip()
    
    def find_repo_path(self, repo_name: str) -> Optional[Path]:
        """
        Find the path to a cloned repository in commit_mining/{framework}/repos/ directories.
        
        Args:
            repo_name: Name of the repository from CSV
            
        Returns:
            Path to repository or None if not found
        """
        if self.repos_base_dir and self.repos_base_dir.exists():
            possible_names = [
                repo_name,
                repo_name.lower(),
                repo_name.replace('-', '_'),
                repo_name.replace('_', '-'),
            ]
            for name in possible_names:
                repo_path = self.repos_base_dir / name
                if repo_path.exists() and (repo_path / '.git').exists():
                    return repo_path
        
        possible_names = [
            repo_name,
            repo_name.lower(),
            repo_name.replace('-', '_'),
            repo_name.replace('_', '-'),
        ]
        
        for framework, repos_dir in self.framework_repos_dirs.items():
            if not repos_dir.exists():
                continue
            
            for name in possible_names:
                repo_path = repos_dir / name
                if repo_path.exists() and (repo_path / '.git').exists():
                    self.log(f"Found {repo_name} in {framework}/repos/{name}")
                    return repo_path
            
            for item in repos_dir.iterdir():
                if not item.is_dir() or item.name.startswith('.'):
                    continue
                
                item_lower = item.name.lower()
                for name in possible_names:
                    name_lower = name.lower()
                    if name_lower == item_lower or name_lower in item_lower or item_lower in name_lower:
                        git_dir = item / '.git'
                        if git_dir.exists():
                            self.log(f"Found {repo_name} in {framework}/repos/{item.name} (matched)")
                            return item
        
        return None
    
    def create_dockerfile(self, repo_path: Path, repo_name: str) -> Path:
        """
        Create a Dockerfile for a repository.
        Delegates to DockerImageBuilder.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            
        Returns:
            Path to created Dockerfile
        """
        return self.docker_image_builder.create_dockerfile(repo_path, repo_name)
    
    def build_docker_image(self, repo_path: Path, repo_name: str, dockerfile_path: Path) -> Optional[str]:
        """
        Build a Docker image for a repository.
        Delegates to DockerImageBuilder.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            dockerfile_path: Path to Dockerfile
            
        Returns:
            Image name/tag or None if build failed
        """
        return self.docker_image_builder.build_docker_image(repo_path, repo_name, dockerfile_path)
    
    def run_tests_in_container(
        self,
        image_name: str,
        local_repo_path: Path,
        commit_hash: str,
        test_files: str,
        repo_name: str
    ) -> Tuple[bool, str, str]:
        """
        Run tests in a Docker container for a specific commit.
        Delegates to DockerContainerRunner.
        
        Args:
            image_name: Docker image name
            local_repo_path: Path to locally cloned repository (already checked out at commit)
            commit_hash: Commit hash (for verification/logging)
            test_files: Semicolon-separated test file paths
            repo_name: Repository name
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        success, stdout, stderr = self.docker_container_runner.run_tests_in_container(
            image_name, local_repo_path, commit_hash, test_files, repo_name
        )
        
        filtered_stdout = self.filter_test_output(stdout)
        
        return success, filtered_stdout, stderr
    
    def process_commit_pair(
        self,
        repo_name: str,
        commit_record: Dict,
        image_name: Optional[str]
    ) -> Dict:
        """
        Process a commit pair (current commit and its parent using ~1 notation).
        Follows the pattern: build base container once, then checkout commits and run tests.
        
        Args:
            repo_name: Name of the repository
            commit_record: CSV row with commit information
            image_name: Docker image name (if available)
            
        Returns:
            Dictionary with test results
        """
        commit_hash = commit_record['commit_hash']
        test_files = commit_record.get('relevant_tests', '')
        
        self.log(f"Processing commit pair for {repo_name}: {commit_hash[:8]}")
        
        repo_path = self.find_repo_path(repo_name)
        if not repo_path:
            self.log(f"Repository not found: {repo_name}", "ERROR")
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'status': 'skipped',
                'reason': 'repository_not_found'
            }
        
        repo_remote_url = self.get_repo_remote_url(repo_path)
        if not repo_remote_url:
            self.log(f"Could not get remote URL for {repo_name}", "ERROR")
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'status': 'skipped',
                'reason': 'no_remote_url'
            }
        
        parent_hash = self.get_parent_commit(repo_path, commit_hash)
        if not parent_hash:
            self.log(f"Could not find parent commit for {commit_hash[:8]}", "WARNING")
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': None,
                'status': 'skipped',
                'reason': 'no_parent_commit'
            }
        
        if not image_name:
            dockerfile_path = self.create_dockerfile(repo_path, repo_name)
            image_name = self.build_docker_image(repo_path, repo_name, dockerfile_path)
            if not image_name:
                self.stats['failed_commits'] += 1
                return {
                    'repo': repo_name,
                    'commit_hash': commit_hash,
                    'parent_hash': parent_hash,
                    'status': 'failed',
                    'reason': 'docker_build_failed'
                }
        
        self.log(f"Cloning parent commit locally: {parent_hash[:8]}")
        parent_local_path = self.clone_and_checkout_local(repo_remote_url, parent_hash, repo_name)
        if not parent_local_path:
            self.stats['failed_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'status': 'failed',
                'reason': 'local_clone_failed_parent'
            }
        
        self.log(f"Cloning current commit locally: {commit_hash[:8]}")
        current_local_path = self.clone_and_checkout_local(repo_remote_url, commit_hash, repo_name)
        if not current_local_path:
            self.stats['failed_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'status': 'failed',
                'reason': 'local_clone_failed_current'
            }
        
        self.log(f"Verifying test files exist in cloned repositories...")
        test_files_exist_current = self.verify_test_files_exist(current_local_path, test_files)
        test_files_exist_parent = self.verify_test_files_exist(parent_local_path, test_files)
        
        if test_files_exist_current:
            self.log(f"Test files found in current commit: {commit_hash[:8]}")
        if test_files_exist_parent:
            self.log(f"Test files found in parent commit: {parent_hash[:8]}")
        
        if not test_files_exist_current and not test_files_exist_parent:
            self.log(f"Test files not found in either commit, skipping commit pair: {commit_hash[:8]}", "WARNING")
            self.log(f"  Test files searched: {test_files}", "WARNING")
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'test_files': test_files,
                'status': 'skipped',
                'reason': 'test_files_not_found',
                'note': 'Test files do not exist in either parent or current commit'
            }
        
        self.log(f"Running tests on parent commit (before): {parent_hash[:8]}")
        parent_success, parent_stdout, parent_stderr = self.run_tests_in_container(
            image_name, parent_local_path, parent_hash, test_files, repo_name
        )
        
        if "FRAMEWORK_REPO_SKIP:" in parent_stdout:
            framework = parent_stdout.split("FRAMEWORK_REPO_SKIP:")[1].split()[0] if "FRAMEWORK_REPO_SKIP:" in parent_stdout else "unknown"
            self.log(f"Framework repository detected ({framework}), skipping: {commit_hash[:8]}", "WARNING")
            self.cleanup_local_repo(parent_local_path)
            self.cleanup_local_repo(current_local_path)
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'test_files': test_files,
                'status': 'skipped',
                'reason': 'framework_repo_requires_compilation',
                'framework': framework,
                'note': 'Framework repositories require full source compilation to test commit-specific code'
            }
        
        if "NO_UNIT_TESTS_FOUND" in parent_stdout:
            self.log(f"No unit tests found in parent commit, skipping: {commit_hash[:8]}", "WARNING")
            self.cleanup_local_repo(parent_local_path)
            self.cleanup_local_repo(current_local_path)
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'test_files': test_files,
                'status': 'skipped',
                'reason': 'no_unit_tests_found',
                'note': 'Only integration tests present, no unit tests to run'
            }
        
        self.log(f"Running tests on current commit (after): {commit_hash[:8]}")
        current_success, current_stdout, current_stderr = self.run_tests_in_container(
            image_name, current_local_path, commit_hash, test_files, repo_name
        )
        
        if "NO_UNIT_TESTS_FOUND" in current_stdout:
            self.log(f"No unit tests found in current commit, skipping: {commit_hash[:8]}", "WARNING")
            self.cleanup_local_repo(parent_local_path)
            self.cleanup_local_repo(current_local_path)
            self.stats['skipped_commits'] += 1
            return {
                'repo': repo_name,
                'commit_hash': commit_hash,
                'parent_hash': parent_hash,
                'test_files': test_files,
                'status': 'skipped',
                'reason': 'no_unit_tests_found',
                'note': 'Only integration tests present, no unit tests to run'
            }
        
        results_differ = parent_stdout != current_stdout or parent_success != current_success
        
        result = {
            'repo': repo_name,
            'commit_hash': commit_hash,
            'parent_hash': parent_hash,
            'test_files': test_files,
            'modified_files': commit_record.get('modified_files', ''),
            'test_strategy': commit_record.get('test_strategy', ''),
            'parent_test_results': {
                'success': parent_success,
                'stdout': parent_stdout[:50000],
                'stderr': parent_stderr[:50000],
                'output_length': len(parent_stdout)
            },
            'current_test_results': {
                'success': current_success,
                'stdout': current_stdout[:50000],
                'stderr': current_stderr[:50000],
                'output_length': len(current_stdout)
            },
            'comparison': {
                'results_differ': results_differ,
                'success_changed': parent_success != current_success,
                'output_changed': parent_stdout != current_stdout
            },
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
        
        result_file = self.results_dir / f"{repo_name}_{commit_hash[:8]}_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        self.cleanup_local_repo(parent_local_path)
        self.cleanup_local_repo(current_local_path)
        
        self.stats['processed_commits'] += 1
        return result
    
    def run(self, max_commits: Optional[int] = None, max_repos: Optional[int] = None, total_commits: Optional[int] = None):
        """
        Run the complete test execution pipeline.
        
        Args:
            max_commits: Maximum commits to process per repository
            max_repos: Maximum repositories to process
            total_commits: Maximum total commits to process across all repositories
        """
        self.log("=" * 70)
        self.log("STARTING DOCKER TEST RUNNER")
        self.log("=" * 70)
        
        if total_commits:
            self.log(f"Total commits limit: {total_commits}")
        
        commits_by_repo = self.parse_csv()
        
        if not commits_by_repo:
            self.log("No commits found in CSV", "ERROR")
            return
        
        repos_processed = 0
        total_commits_processed = 0
        
        for repo_name, commits in commits_by_repo.items():
            if max_repos and repos_processed >= max_repos:
                self.log(f"Reached max repositories limit ({max_repos})")
                break
            
            if total_commits and total_commits_processed >= total_commits:
                self.log(f"Reached total commits limit ({total_commits})")
                break
            
            self.log(f"\nProcessing repository: {repo_name}")
            self.log(f"  Commits to process: {len(commits)}")
            
            repo_path = self.find_repo_path(repo_name)
            if not repo_path:
                self.log(f"  Skipping {repo_name}: repository not found", "WARNING")
                continue
            
            dockerfile_path = self.create_dockerfile(repo_path, repo_name)
            image_name = self.build_docker_image(repo_path, repo_name, dockerfile_path)
            
            if not image_name:
                self.log(f"  Skipping {repo_name}: failed to build Docker image", "WARNING")
                continue
            
            commits_to_process = commits[:max_commits] if max_commits else commits
            
            for commit_record in commits_to_process:
                if total_commits and total_commits_processed >= total_commits:
                    self.log(f"Reached total commits limit ({total_commits}), stopping")
                    break
                
                result = self.process_commit_pair(repo_name, commit_record, image_name)
                
                if result['status'] == 'completed':
                    total_commits_processed += 1
                    self.stats['total_commits_processed'] = total_commits_processed
                    progress_str = f"({total_commits_processed}/{total_commits})" if total_commits else ""
                    self.log(f"  ✓ Completed: {commit_record['commit_hash'][:8]} {progress_str}")
                else:
                    self.log(f"  ✗ Skipped/Failed: {commit_record['commit_hash'][:8]} - {result.get('reason', 'unknown')}")
            
            self.stats['repos_processed'].add(repo_name)
            repos_processed += 1
            
            if total_commits and total_commits_processed >= total_commits:
                break
        
        self.save_summary()
        
        self.log("\n" + "=" * 70)
        self.log("DOCKER TEST RUNNER COMPLETE")
        self.log("=" * 70)
        self.log(f"Repositories processed: {len(self.stats['repos_processed'])}")
        self.log(f"Total commits in CSV: {self.stats['total_commits']}")
        self.log(f"Total commits processed: {self.stats['total_commits_processed']}")
        self.log(f"Processed commits: {self.stats['processed_commits']}")
        self.log(f"Failed commits: {self.stats['failed_commits']}")
        self.log(f"Skipped commits: {self.stats['skipped_commits']}")
        self.log(f"Results directory: {self.results_dir}")
    
    def save_summary(self):
        """Save execution summary to JSON."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'total_commits': self.stats['total_commits'],
                'total_commits_processed': self.stats['total_commits_processed'],
                'processed_commits': self.stats['processed_commits'],
                'failed_commits': self.stats['failed_commits'],
                'skipped_commits': self.stats['skipped_commits'],
                'repos_processed': list(self.stats['repos_processed']),
                'repos_count': len(self.stats['repos_processed'])
            },
            'errors': self.stats['errors'][:100]  
        }
        
        summary_file = self.output_dir / 'execution_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.log(f"Summary saved to: {summary_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run tests in Docker containers for commit pairs'
    )
    parser.add_argument(
        '--csv',
        type=str,
        default='test_mappings/aggregated_test_mapping.csv',
        help='Path to aggregated_test_mapping.csv'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='docker_test_results',
        help='Output directory for results'
    )
    parser.add_argument(
        '--repos-dir',
        type=str,
        default=None,
        help='Base directory containing cloned repositories'
    )
    parser.add_argument(
        '--max-commits',
        type=int,
        default=None,
        help='Maximum commits to process per repository'
    )
    parser.add_argument(
        '--max-repos',
        type=int,
        default=None,
        help='Maximum repositories to process'
    )
    parser.add_argument(
        '--total-commits',
        type=int,
        default=None,
        help='Maximum total commits to process across all repositories'
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    csv_path = Path(args.csv) if Path(args.csv).is_absolute() else script_dir / args.csv
    output_dir = Path(args.output_dir) if Path(args.output_dir).is_absolute() else script_dir / args.output_dir
    repos_dir = Path(args.repos_dir) if args.repos_dir and Path(args.repos_dir).is_absolute() else (script_dir / args.repos_dir if args.repos_dir else None)
    
    try:
        runner = DockerTestRunner(csv_path, output_dir, repos_dir)
        runner.run(
            max_commits=args.max_commits,
            max_repos=args.max_repos,
            total_commits=args.total_commits
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nFatal error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

