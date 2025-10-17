import json
import os
import subprocess
import shutil
from pathlib import Path
import time
import re
import toml
from collections import defaultdict, Counter

def parse_dependencies(repo_path):
    """
    Parse dependency manifest files from a repository
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        dict: Parsed dependencies with metadata
    """
    repo_path = Path(repo_path)
    dependencies = {
        'requirements_txt': [],
        'pyproject_toml': [],
        'setup_py': [],
        'pipfile': [],
        'conda_yml': [],
        'poetry_lock': [],
        'all_dependencies': set(),
        'manifest_files_found': []
    }
    
    # Define manifest files to look for
    manifest_files = {
        'requirements.txt': 'requirements_txt',
        'requirements-dev.txt': 'requirements_txt',
        'requirements-test.txt': 'requirements_txt',
        'dev-requirements.txt': 'requirements_txt',
        'pyproject.toml': 'pyproject_toml',
        'setup.py': 'setup_py',
        'Pipfile': 'pipfile',
        'environment.yml': 'conda_yml',
        'environment.yaml': 'conda_yml',
        'conda.yml': 'conda_yml',
        'poetry.lock': 'poetry_lock'
    }
    
    # Search for manifest files (including subdirectories)
    for manifest_file, dep_type in manifest_files.items():
        # Check root directory
        file_path = repo_path / manifest_file
        if file_path.exists():
            dependencies['manifest_files_found'].append(str(file_path.relative_to(repo_path)))
            deps = _parse_manifest_file(file_path, dep_type)
            dependencies[dep_type].extend(deps)
            dependencies['all_dependencies'].update(dep.lower() for dep in deps)
        
        # Check common subdirectories
        for subdir in ['src', 'lib', 'app', 'backend', 'frontend', 'api']:
            subdir_path = repo_path / subdir / manifest_file
            if subdir_path.exists():
                dependencies['manifest_files_found'].append(str(subdir_path.relative_to(repo_path)))
                deps = _parse_manifest_file(subdir_path, dep_type)
                dependencies[dep_type].extend(deps)
                dependencies['all_dependencies'].update(dep.lower() for dep in deps)
    
    # Convert set back to list for JSON serialization
    dependencies['all_dependencies'] = list(dependencies['all_dependencies'])
    
    return dependencies

def _parse_manifest_file(file_path, dep_type):
    """Parse individual manifest file based on type"""
    dependencies = []
    
    try:
        if dep_type == 'requirements_txt':
            dependencies = _parse_requirements_txt(file_path)
        elif dep_type == 'pyproject_toml':
            dependencies = _parse_pyproject_toml(file_path)
        elif dep_type == 'setup_py':
            dependencies = _parse_setup_py(file_path)
        elif dep_type == 'pipfile':
            dependencies = _parse_pipfile(file_path)
        elif dep_type == 'conda_yml':
            dependencies = _parse_conda_yml(file_path)
        elif dep_type == 'poetry_lock':
            dependencies = _parse_poetry_lock(file_path)
            
    except Exception as e:
        print(f"    Warning: Could not parse {file_path}: {e}")
    
    return dependencies

def _parse_requirements_txt(file_path):
    """Parse requirements.txt file"""
    dependencies = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-'):
                # Extract package name (before version specifiers)
                match = re.match(r'^([a-zA-Z0-9\-_\.]+)', line)
                if match:
                    dependencies.append(match.group(1))
    return dependencies

def _parse_pyproject_toml(file_path):
    """Parse pyproject.toml file"""
    dependencies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        # Poetry dependencies
        if 'tool' in data and 'poetry' in data['tool']:
            poetry_deps = data['tool']['poetry'].get('dependencies', {})
            for dep in poetry_deps.keys():
                if dep != 'python':  # Skip python version
                    dependencies.append(dep)
        
        # PEP 621 dependencies
        if 'project' in data:
            project_deps = data['project'].get('dependencies', [])
            for dep in project_deps:
                match = re.match(r'^([a-zA-Z0-9\-_\.]+)', dep)
                if match:
                    dependencies.append(match.group(1))
                    
    except Exception as e:
        # Fallback to text parsing if TOML parsing fails
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Simple regex to find dependency-like patterns
            deps = re.findall(r'"([a-zA-Z0-9\-_\.]+)"', content)
            dependencies.extend(deps)
    
    return dependencies

def _parse_setup_py(file_path):
    """Parse setup.py file (basic extraction)"""
    dependencies = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    # Look for install_requires or requirements patterns
    patterns = [
        r'install_requires\s*=\s*\[(.*?)\]',
        r'requires\s*=\s*\[(.*?)\]',
        r'"([a-zA-Z0-9\-_\.]+)(?:[><=!].*?)?"'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            # Extract individual package names
            deps = re.findall(r'"([a-zA-Z0-9\-_\.]+)', match)
            dependencies.extend(deps)
    
    return list(set(dependencies))  # Remove duplicates

def _parse_pipfile(file_path):
    """Parse Pipfile"""
    dependencies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        # Get packages from [packages] and [dev-packages]
        for section in ['packages', 'dev-packages']:
            if section in data:
                dependencies.extend(data[section].keys())
                
    except Exception:
        # Fallback to text parsing
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            deps = re.findall(r'^([a-zA-Z0-9\-_\.]+)\s*=', content, re.MULTILINE)
            dependencies.extend(deps)
    
    return dependencies

def _parse_conda_yml(file_path):
    """Parse conda environment.yml file"""
    dependencies = []
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if 'dependencies' in data:
            for dep in data['dependencies']:
                if isinstance(dep, str):
                    # Extract package name
                    match = re.match(r'^([a-zA-Z0-9\-_\.]+)', dep)
                    if match:
                        dependencies.append(match.group(1))
                elif isinstance(dep, dict) and 'pip' in dep:
                    # Handle pip dependencies in conda file
                    for pip_dep in dep['pip']:
                        match = re.match(r'^([a-zA-Z0-9\-_\.]+)', pip_dep)
                        if match:
                            dependencies.append(match.group(1))
                            
    except ImportError:
        # PyYAML not available, do basic text parsing
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            deps = re.findall(r'- ([a-zA-Z0-9\-_\.]+)', content)
            dependencies.extend(deps)
    except Exception:
        pass
    
    return dependencies

def _parse_poetry_lock(file_path):
    """Parse poetry.lock file"""
    dependencies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)
        
        if 'package' in data:
            for package in data['package']:
                if 'name' in package:
                    dependencies.append(package['name'])
                    
    except Exception:
        # Fallback to text parsing
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            deps = re.findall(r'name = "([a-zA-Z0-9\-_\.]+)"', content)
            dependencies.extend(deps)
    
    return dependencies


def clone_ml_repositories(dataset_file="ml_repositories_dataset.json", 
                         base_dir="ml_repos_isolated", 
                         max_repos=None,
                         shallow_clone=True,
                         skip_existing=True):
    """
    Clone ML repositories with intact dependencies only
    
    Args:
        dataset_file: JSON file containing repository data
        base_dir: Base directory for isolated cloning
        max_repos: Maximum number of repositories to clone (None for all)
        shallow_clone: If True, perform shallow clone (faster, less storage)
        skip_existing: If True, skip repositories that are already cloned
    """
    
    # Load the dataset
    try:
        with open(dataset_file, 'r', encoding='utf-8') as f:
            repos = json.load(f)
        print(f"Loaded {len(repos)} repositories from {dataset_file}")
    except FileNotFoundError:
        print(f"Dataset file {dataset_file} not found. Run fetch_repo.py first.")
        return
    except json.JSONDecodeError as e:
        print(f"Error reading JSON file: {e}")
        return
    
    # Create isolated directory structure
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)
    
    # Create subdirectories for organization
    dirs = {
        'successful': base_path / 'successful_clones',
        'failed': base_path / 'failed_clones', 
        'logs': base_path / 'logs'
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(exist_ok=True)
    
    # Limit repositories if specified
    if max_repos:
        repos = repos[:max_repos]
        print(f"Limiting to first {max_repos} repositories")
    
    # Statistics tracking
    stats = {
        'total': len(repos),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'no_dependencies': 0,
        'errors': []
    }
    
    # Log file for detailed tracking
    log_file = dirs['logs'] / f"clone_log_{int(time.time())}.txt"
    
    print(f"\n=== CLONING REPOSITORIES ===")
    print(f"Target directory: {base_path.absolute()}")
    print(f"Shallow clone: {shallow_clone}")
    print(f"Skip existing: {skip_existing}")
    print(f"Log file: {log_file}")
    
    # Configure Git for Windows long paths
    try:
        subprocess.run(['git', 'config', '--global', 'core.longpaths', 'true'], 
                      capture_output=True, check=False)
        print(f"Enabled Git long path support")
    except Exception:
        print(f"Could not enable Git long path support")
    
    print()
    
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"ML Repository Cloning Log\n")
        log.write(f"Started at: {time.ctime()}\n")
        log.write(f"Total repositories: {stats['total']}\n\n")
        
        for i, repo in enumerate(repos, 1):
            repo_name = repo['name']
            repo_url = repo['clone_url']
            owner = repo['owner']['login']
            
            # Create safe directory name with shorter paths for Windows
            safe_name = f"{owner}_{repo_name}".replace('/', '_').replace('\\', '_')
            # Truncate very long names to avoid Windows path limits
            if len(safe_name) > 50:
                safe_name = safe_name[:47] + "..."
            clone_path = dirs['successful'] / safe_name
            
            print(f"[{i}/{stats['total']}] {owner}/{repo_name}")
            log.write(f"[{i}/{stats['total']}] {owner}/{repo_name}\n")
            log.write(f"URL: {repo_url}\n")
            
            # Check if already exists
            if skip_existing and clone_path.exists():
                print(f"  Skipped (already exists)")
                log.write(f"  Status: SKIPPED (already exists)\n\n")
                stats['skipped'] += 1
                continue
            
            try:
                # Prepare git clone command with Windows long path support
                cmd = ['git', 'clone']
                if shallow_clone:
                    cmd.extend(['--depth', '1'])  # Shallow clone
                
                # Enable long path support for Windows
                cmd.extend(['-c', 'core.longpaths=true'])
                cmd.extend([repo_url, str(clone_path)])
                
                # Execute clone with timeout
                print(f"  Cloning...")
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=300,  # 5 minute timeout
                    cwd=str(base_path.parent)  # Use parent directory to avoid double nesting
                )
                
                if result.returncode == 0:
                    print(f"  Cloned successfully")
                    log.write(f"  Status: CLONED\n")
                    log.write(f"  Path: {clone_path}\n")
                    
                    # Parse dependencies - REQUIRED
                    print(f"  Checking dependencies...")
                    # Check if the repository was cloned to a nested path
                    actual_clone_path = clone_path
                    if not actual_clone_path.exists():
                        # Try the nested path structure
                        nested_path = base_path / base_path.name / 'successful_clones' / safe_name
                        if nested_path.exists():
                            actual_clone_path = nested_path
                    
                    dependencies = parse_dependencies(actual_clone_path)
                    
                    # Check if repository has usable dependencies
                    has_dependencies = (
                        len(dependencies['manifest_files_found']) > 0 and 
                        len(dependencies['all_dependencies']) > 0
                    )
                    
                    if has_dependencies:
                        print(f"  Dependencies found - keeping repository")
                        log.write(f"  Status: SUCCESS (has dependencies)\n")
                        log.write(f"  Dependencies: {len(dependencies['all_dependencies'])} total\n")
                        log.write(f"  Manifest files: {', '.join(dependencies['manifest_files_found'])}\n")
                        
                        # Create metadata file with dependencies
                        metadata = {
                            'name': repo_name,
                            'owner': owner,
                            'stars': repo['stargazers_count'],
                            'language': repo['language'],
                            'description': repo['description'],
                            'url': repo['html_url'],
                            'clone_url': repo_url,
                            'cloned_at': time.ctime(),
                            'dependencies': dependencies
                        }
                        
                        with open(actual_clone_path / 'repo_metadata.json', 'w') as meta_file:
                            json.dump(metadata, meta_file, indent=2)
                        
                        stats['successful'] += 1
                    else:
                        print(f"  No dependencies found - removing repository")
                        log.write(f"  Status: REJECTED (no dependencies)\n")
                        log.write(f"  Manifest files found: {len(dependencies['manifest_files_found'])}\n")
                        
                        # Remove the cloned repository
                        shutil.rmtree(actual_clone_path, ignore_errors=True)
                        stats['no_dependencies'] += 1
                        
                else:
                    print(f"  Failed: {result.stderr.strip()}")
                    log.write(f"  Status: FAILED\n")
                    log.write(f"  Error: {result.stderr.strip()}\n")
                    stats['failed'] += 1
                    stats['errors'].append(f"{owner}/{repo_name}: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                print(f"  Timeout - repository not cloned")
                log.write(f"  Status: TIMEOUT\n")
                stats['failed'] += 1
                stats['errors'].append(f"{owner}/{repo_name}: Timeout")
                
                # Clean up partial clone
                if clone_path.exists():
                    shutil.rmtree(clone_path, ignore_errors=True)
                    
            except Exception as e:
                print(f"  Error: {e}")
                log.write(f"  Status: ERROR\n")
                log.write(f"  Exception: {e}\n")
                stats['failed'] += 1
                stats['errors'].append(f"{owner}/{repo_name}: {e}")
            
            log.write(f"\n")
            
            # Small delay to be respectful
            time.sleep(1)
    
    # Final statistics
    print(f"\n=== CLONING COMPLETE ===")
    print(f"Total repositories processed: {stats['total']}")
    print(f"Successfully cloned with dependencies: {stats['successful']}")
    print(f"Rejected (no dependencies): {stats['no_dependencies']}")
    print(f"Failed to clone: {stats['failed']}")
    print(f"Skipped (already exists): {stats['skipped']}")
    print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
    
    print(f"\nRepositories with intact dependencies: {dirs['successful']}")
    print(f"Detailed log: {log_file}")
    
    return stats

def create_docker_environment(base_dir="ml_repos_isolated"):
    """
    Create a Dockerfile for isolated analysis environment with dependency installation
    """
    dockerfile_content = """
# Dockerfile for ML Repository Analysis
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install base tools for dependency management
RUN pip install --no-cache-dir \\
    pip \\
    setuptools \\
    wheel \\
    toml \\
    pyyaml \\
    requests \\
    jupyter \\
    notebook

# Create working directory
WORKDIR /workspace

# Copy repositories
COPY successful_clones/ /workspace/repos/

# Copy dependency installation script
COPY install_dependencies.py /workspace/

# Install all repository dependencies
RUN python /workspace/install_dependencies.py --repos-dir /workspace/repos --output /workspace/dependency_install_report.json

# Set up Jupyter
EXPOSE 8888
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
"""
    
    dockerfile_path = Path(base_dir) / "Dockerfile"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    
    # Copy the dependency installation script
    import shutil
    script_source = Path(__file__).parent / "install_dependencies.py"
    script_dest = Path(base_dir) / "install_dependencies.py"
    
    try:
        shutil.copy2(script_source, script_dest)
        print(f"Copied dependency installation script to {script_dest}")
    except Exception as e:
        print(f"Warning: Could not copy install_dependencies.py: {e}")
        # Create a simple fallback script
        fallback_script = '''#!/usr/bin/env python3
import sys
print("Dependency installation script not available")
print("Run: pip install -r requirements.txt for each repository manually")
sys.exit(0)
'''
        with open(script_dest, 'w', encoding='utf-8') as f:
            f.write(fallback_script)
    
    docker_compose_content = """
version: '3.8'
services:
  ml-analysis:
    build: .
    ports:
      - "8888:8888"
    volumes:
      - ./analysis:/workspace/analysis
    environment:
      - JUPYTER_ENABLE_LAB=yes
"""
    
    compose_path = Path(base_dir) / "docker-compose.yml"
    with open(compose_path, 'w') as f:
        f.write(docker_compose_content)
    
    # Create analysis directory
    analysis_dir = Path(base_dir) / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    
    print(f"Docker environment created in {base_dir}")
    print("Dependencies will be automatically installed during Docker build")
    print("To use:")
    print(f"  cd {base_dir}")
    print("  docker-compose up --build")

if __name__ == "__main__":
    import sys
    
    print("ML Repository Cloning Tool")
    print("This will clone repositories from your dataset in an isolated environment\n")
    
    # Check for --no-docker flag
    auto_build_docker = '--no-docker' not in sys.argv
    if '--no-docker' in sys.argv:
        sys.argv.remove('--no-docker')
        print("Docker auto-build disabled (--no-docker flag detected)")
    else:
        print("Docker environment will be built automatically after cloning")
    
    # Windows long path warning
    import platform
    if platform.system() == "Windows":
        print("🔧 WINDOWS USERS: If you encounter 'Filename too long' errors:")
        print("   1. Run as Administrator: gpedit.msc")
        print("   2. Navigate to: Computer Configuration > Administrative Templates > System > Filesystem")
        print("   3. Enable: 'Enable Win32 long paths'")
        print("   4. Restart your computer")
        print("   OR run this script as Administrator\n")
    
    # Configuration
    config = {
        'dataset_file': 'ml_repositories_dataset.json',
        'base_dir': 'ml_repos_isolated',
        'max_repos': 10,  # Start with 10 for testing, set to None for all
        'shallow_clone': True,  # Faster, less storage
        'skip_existing': True,   # Skip already cloned repos
        'auto_build_docker': auto_build_docker
    }
    
    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    # Clone repositories
    stats = clone_ml_repositories(**config)
    
    # Create Docker environment for repositories with intact dependencies
    if stats and stats['successful'] > 0:
        print("\nCreating Docker environment for isolated analysis...")
        create_docker_environment(config['base_dir'])
        
        # Automatically build Docker environment if enabled
        if config.get('auto_build_docker', True):
            print("\nBuilding Docker environment with dependencies...")
            try:
                import subprocess
                import os
                
                # Change to the Docker build directory
                docker_dir = Path(config['base_dir'])
                
                print(f"Building Docker image in {docker_dir.absolute()}...")
                result = subprocess.run([
                    'docker-compose', 'up', '--build', '-d'
                ], cwd=str(docker_dir), capture_output=True, text=True, timeout=1800)  # 30 min timeout
                
                if result.returncode == 0:
                    print("Docker environment built successfully!")
                    print("Jupyter notebook is now running at: http://localhost:8888")
                    print("All ML repository dependencies are installed and ready to use")
                    print("\nTo stop the environment: docker-compose down")
                else:
                    print("Docker build failed:")
                    print(result.stderr)
                    print("\nTo build manually:")
                    print(f"  cd {config['base_dir']}")
                    print("  docker-compose up --build")
                    
            except subprocess.TimeoutExpired:
                print("Docker build timed out (30 minutes)")
                print("The build is still running in the background")
            except FileNotFoundError:
                print("Docker or docker-compose not found")
                print("Please install Docker Desktop and try again")
                print("\nTo build manually:")
                print(f"  cd {config['base_dir']}")
                print("  docker-compose up --build")
            except Exception as e:
                print(f"Error building Docker environment: {e}")
                print("\nTo build manually:")
                print(f"  cd {config['base_dir']}")
                print("  docker-compose up --build")
        else:
            print("\nDocker auto-build skipped (use --no-docker flag to disable)")
            print("To build manually:")
            print(f"  cd {config['base_dir']}")
            print("  docker-compose up --build")
        
        print("\n" + "="*50)
        print("For manual dependency installation (NOT recommended):")
        print(f"  python install_dependencies.py --repos-dir {config['base_dir']}/successful_clones")
        print("This will install to your HOST system - use Docker instead!")
