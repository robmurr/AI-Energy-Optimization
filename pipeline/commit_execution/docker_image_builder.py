#!/usr/bin/env python3
"""
Docker Image Builder Module
Handles Dockerfile creation and Docker image building.
"""

import subprocess
from pathlib import Path
from typing import Optional


class DockerImageBuilder:
    """Handles Docker image building operations."""
    
    def __init__(self, docker_dir: Path, log_func):
        """
        Initialize the Docker image builder.
        
        Args:
            docker_dir: Directory for storing Dockerfiles
            log_func: Logging function to use
        """
        self.docker_dir = Path(docker_dir)
        self.docker_dir.mkdir(exist_ok=True)
        self.log = log_func
    
    def create_dockerfile(self, repo_path: Path, repo_name: str) -> Path:
        """
        Create a Dockerfile for a repository.
        Builds a base container that can be reused for multiple commits.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            
        Returns:
            Path to created Dockerfile
        """
        dockerfile_path = self.docker_dir / f"{repo_name}_Dockerfile"
        
        has_requirements = (repo_path / 'requirements.txt').exists()
        has_setup_py = (repo_path / 'setup.py').exists()
        has_pyproject = (repo_path / 'pyproject.toml').exists()
        has_conda = (repo_path / 'environment.yml').exists() or (repo_path / 'environment.yaml').exists()
        has_requirements_test = (repo_path / 'requirements-test.txt').exists() or (repo_path / 'requirements_test.txt').exists()
        
        dockerfile_content = f"""# Dockerfile for {repo_name}
                                    # Base container - build once, reuse for multiple commits
                                    FROM python:3.9-slim

                                    # Install system dependencies
                                    RUN apt-get update && apt-get install -y \\
                                        git \\
                                        build-essential \\
                                        curl \\
                                        && rm -rf /var/lib/apt/lists/*

                                    # Install common test runners
                                    RUN pip install --no-cache-dir \\
                                        pytest \\
                                        pytest-cov \\
                                        unittest-xml-reporting \\
                                        nose

                                    # Set working directory
                                    WORKDIR /workspace

                                    # Copy repository (will be mounted as volume at runtime, but copy for initial setup)
                                    COPY . /workspace/

                                    # Install dependencies based on what's available
                                    """
        
        if has_conda:
            dockerfile_content += """
                # Install conda dependencies (if available)
                RUN if [ -f environment.yml ]; then \\
                    apt-get update && apt-get install -y wget && \\
                    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \\
                    bash miniconda.sh -b -p /opt/conda && \\
                    /opt/conda/bin/conda env create -f environment.yml || true; \\
                    fi
                """
        
        if has_requirements:
            dockerfile_content += """
                # Install from requirements.txt
                RUN if [ -f requirements.txt ]; then \\
                    pip install --no-cache-dir -r requirements.txt || true; \\
                    fi
                """
        
        if has_requirements_test:
            dockerfile_content += """
                # Install test requirements
                RUN if [ -f requirements-test.txt ]; then \\
                    pip install --no-cache-dir -r requirements-test.txt || true; \\
                    elif [ -f requirements_test.txt ]; then \\
                    pip install --no-cache-dir -r requirements_test.txt || true; \\
                    fi
                """
        
        if has_setup_py:
            dockerfile_content += """
                # Install from setup.py (try to install in editable mode)
                RUN if [ -f setup.py ]; then \\
                    pip install --no-cache-dir -e . || pip install --no-cache-dir . || true; \\
                    fi
                """
        
        if has_pyproject:
            dockerfile_content += """
                # Install from pyproject.toml
                RUN if [ -f pyproject.toml ]; then \\
                    pip install --no-cache-dir -e . || pip install --no-cache-dir . || true; \\
                    fi
                """
        
        dockerfile_content += """
            # Default command
            CMD ["/bin/bash"]
            """
        
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        self.log(f"Created Dockerfile: {dockerfile_path}")
        return dockerfile_path
    
    def build_docker_image(self, repo_path: Path, repo_name: str, dockerfile_path: Path) -> Optional[str]:
        """
        Build a Docker image for a repository.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            dockerfile_path: Path to Dockerfile
            
        Returns:
            Image name/tag or None if build failed
        """
        image_name = f"{repo_name.lower().replace(' ', '_').replace('/', '_')}:latest"
        
        self.log(f"Building Docker image: {image_name}")
        self.log(f"  Dockerfile: {dockerfile_path}")
        self.log(f"  Build context: {repo_path}")
        
        try:
            cmd = [
                'docker', 'build',
                '-f', str(dockerfile_path),
                '-t', image_name,
                str(repo_path)
            ]
            
            self.log(f"  Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=1800  
            )
            
            if result.returncode == 0:
                self.log(f"Successfully built image: {image_name}")
                return image_name
            else:
                self.log(f"Failed to build image {image_name}: {result.stderr}", "ERROR")
                if result.stdout:
                    self.log(f"Build stdout: {result.stdout[:500]}", "ERROR")
                return None
                
        except subprocess.TimeoutExpired:
            self.log(f"Timeout building image: {image_name}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Error building image {image_name}: {e}", "ERROR")
            return None


