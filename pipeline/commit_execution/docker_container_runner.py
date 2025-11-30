#!/usr/bin/env python3
"""
Docker Container Runner Module
Handles running tests in Docker containers with proper path handling.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from docker_test_script import generate_test_script


class DockerContainerRunner:
    """Handles running tests in Docker containers."""
    
    def __init__(self, log_func):
        """
        Initialize the Docker container runner.
        
        Args:
            log_func: Logging function to use
        """
        self.log = log_func
    
    def convert_windows_path_for_docker(self, local_path: Path) -> str:
        """
        Convert Windows path to Docker-compatible path with extensive debugging.
        
        Args:
            local_path: Local path to convert
            
        Returns:
            Docker-compatible path string
        """
        local_path_resolved = local_path.resolve()
        local_path_str = str(local_path_resolved)
        
        self.log(f"=== PATH CONVERSION DEBUG ===")
        self.log(f"Original path: {local_path}")
        self.log(f"Resolved path: {local_path_resolved}")
        self.log(f"Path string: {local_path_str}")
        self.log(f"Path exists: {local_path_resolved.exists()}")
        self.log(f"OS name: {os.name}")
        
        if os.name == 'nt':  
            volume_path = local_path_str.replace('\\', '/')
            
            if volume_path[1] == ':':
                self.log(f"Windows drive letter path detected: {volume_path}")
                
                if not os.path.isabs(local_path_str):
                    self.log(f"WARNING: Path is not absolute: {local_path_str}", "WARNING")
                
                self.log(f"Converted path for Docker: {volume_path}")
            else:
                self.log(f"Non-drive-letter path: {volume_path}")
            
            try:
                path_parts = local_path_resolved.parts
                self.log(f"Path parts: {path_parts}")
                self.log(f"Path parts count: {len(path_parts)}")
            except Exception as e:
                self.log(f"Error analyzing path parts: {e}", "WARNING")
            
            return volume_path
        else:
            volume_path = local_path_str
            self.log(f"Unix path (no conversion needed): {volume_path}")
            return volume_path
    
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
        Uses a locally cloned and checked-out repository mounted as a volume.
        
        Args:
            image_name: Docker image name
            local_repo_path: Path to locally cloned repository (already checked out at commit)
            commit_hash: Commit hash (for verification/logging)
            test_files: Semicolon-separated test file paths
            repo_name: Repository name
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if not local_repo_path.exists():
            error_msg = f"Local repository path does not exist: {local_repo_path}"
            self.log(error_msg, "ERROR")
            return False, "", error_msg
        
        normalized_test_files = test_files.replace('\\', '/') if test_files else ''
        
        try:
            cmd = ['git', 'rev-parse', 'HEAD']
            result = subprocess.run(
                cmd,
                cwd=str(local_repo_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                current_commit = result.stdout.strip()
                if current_commit != commit_hash:
                    self.log(f"Warning: Local repo at {commit_hash[:8]} but HEAD is {current_commit[:8]}", "WARNING")
        except Exception:
            pass  
        
        test_script_content = generate_test_script(commit_hash, normalized_test_files)
        
        try:
            volume_path = self.convert_windows_path_for_docker(local_repo_path)
            
            self.log(f"Mounting local repo: {volume_path} -> /workspace/repo")
            
            # Run the container with the local repo mounted as a volume
            # Include --gpus all to enable GPU access for CUDA-dependent tests
            cmd_with_gpu = [
                'docker', 'run', '--rm',
                '--gpus', 'all',
                '-v', f'{volume_path}:/workspace/repo',
                image_name,
                'bash', '-c', test_script_content
            ]
            
            cmd_without_gpu = [
                'docker', 'run', '--rm',
                '-v', f'{volume_path}:/workspace/repo',
                image_name,
                'bash', '-c', test_script_content
            ]
            
            self.log(f"Docker run command: docker run --rm --gpus all -v {volume_path}:/workspace/repo {image_name} ... [script]")
            self.log(f"Volume mount: {volume_path}:/workspace/repo")
            
            result = subprocess.run(
                cmd_with_gpu,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=600
            )
            
            gpu_error_indicators = [
                "could not select device driver",
                "nvidia-container-cli",
                "unknown flag: --gpus",
                "Error response from daemon: could not select device driver"
            ]
            
            if result.returncode != 0 and any(indicator in result.stderr.lower() for indicator in gpu_error_indicators):
                self.log("GPU access not available (NVIDIA Container Toolkit may not be installed), retrying without GPU...", "WARNING")
                result = subprocess.run(
                    cmd_without_gpu,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=600
                )
            
            self.log(f"Docker container exit code: {result.returncode}")
            if result.stderr:
                stderr_preview = result.stderr[:500] if len(result.stderr) > 500 else result.stderr
                self.log(f"Docker stderr preview: {stderr_preview}")
            
            if "cannot find the file specified" in result.stderr.lower() or \
               "no such file or directory" in result.stderr.lower() or \
               "mount point does not exist" in result.stderr.lower():
                self.log(f"ERROR: Possible volume mount failure!", "ERROR")
                self.log(f"  Volume path: {volume_path}", "ERROR")
                self.log(f"  Local path exists: {local_repo_path.exists()}", "ERROR")
                self.log(f"  Local path: {local_repo_path}", "ERROR")
            
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr
            )
            
        except subprocess.TimeoutExpired:
            self.log("Test execution timed out after 10 minutes", "ERROR")
            return False, "", "Test execution timed out"
        except Exception as e:
            error_msg = f"Error running tests: {e}"
            self.log(error_msg, "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False, "", error_msg

