#!/usr/bin/env python3
"""
Generate Modular Docker Setup

This script creates individual Docker containers for each ML repository.
"""

import json
import os
from pathlib import Path
import yaml


def get_repositories(repos_dir="successful_clones"):
    """Get list of available repositories"""
    repos_path = Path(repos_dir)
    repositories = []
    
    if not repos_path.exists():
        print(f"Repository directory {repos_path} does not exist")
        return repositories
    
    for repo_dir in repos_path.iterdir():
        if repo_dir.is_dir():
            # Clean repo name for Docker service names
            repo_name = repo_dir.name.replace('_', '-').replace('.', '-').lower()
            repositories.append({
                'original_name': repo_dir.name,
                'service_name': repo_name,
                'path': repo_dir
            })
    
    return repositories


def generate_dockerfile(repo_info, port, template_path="Dockerfile.template"):
    """Generate Dockerfile for a specific repository"""
    with open(template_path, 'r') as f:
        template = f.read()
    
    dockerfile_content = template.replace('{{REPO_NAME}}', repo_info['original_name'])
    dockerfile_content = dockerfile_content.replace('{{PORT}}', str(port))
    
    # Create repo-specific directory
    repo_docker_dir = Path(f"docker_repos/{repo_info['service_name']}")
    repo_docker_dir.mkdir(parents=True, exist_ok=True)
    
    # Write Dockerfile
    dockerfile_path = repo_docker_dir / "Dockerfile"
    with open(dockerfile_path, 'w', encoding='utf-8') as f:
        f.write(dockerfile_content)
    
    return dockerfile_path


def generate_docker_compose(repositories):
    """Generate docker-compose.yml for all repositories"""
    services = {}
    base_port = 8888
    
    for i, repo_info in enumerate(repositories):
        port = base_port + i
        service_name = repo_info['service_name']
        
        # Generate individual Dockerfile
        dockerfile_path = generate_dockerfile(repo_info, port)
        print(f"Generated Dockerfile for {repo_info['original_name']} -> {dockerfile_path}")
        
        services[service_name] = {
            'build': {
                'context': '.',
                'dockerfile': f'docker_repos/{service_name}/Dockerfile'
            },
            'ports': [f"{port}:{port}"],
            'volumes': [
                f"./analysis/{service_name}:/workspace/analysis"
            ],
            'environment': [
                'JUPYTER_ENABLE_LAB=yes',
                f'REPO_NAME={repo_info["original_name"]}'
            ],
            'container_name': f'ml-analysis-{service_name}'
        }
    
    docker_compose = {
        'services': services
    }
    
    # Write docker-compose.yml
    with open('docker-compose-modular.yml', 'w', encoding='utf-8') as f:
        yaml.dump(docker_compose, f, default_flow_style=False, indent=2)
    
    return docker_compose


def generate_startup_script(repositories):
    """Generate convenience scripts for managing containers"""
    base_port = 8888
    
    # Generate start script
    start_script = "#!/bin/bash\n\n"
    start_script += "echo 'Starting ML Repository Analysis Containers'\n"
    start_script += "echo '================================================'\n\n"
    
    for i, repo_info in enumerate(repositories):
        port = base_port + i
        start_script += f"echo '{repo_info['original_name']} -> http://localhost:{port}'\n"
    
    start_script += "\necho ''\n"
    start_script += "echo 'Building and starting all containers...'\n"
    start_script += "docker-compose -f docker-compose-modular.yml up --build -d\n\n"
    start_script += "echo 'All containers started!'\n"
    start_script += "echo 'Access repositories at the URLs shown above'\n"
    
    with open('start_all_repos.sh', 'w', encoding='utf-8') as f:
        f.write(start_script)
    
    # Generate Windows batch file
    start_bat = "@echo off\n"
    start_bat += "echo Starting ML Repository Analysis Containers\n"
    start_bat += "echo ================================================\n\n"
    
    for i, repo_info in enumerate(repositories):
        port = base_port + i
        start_bat += f"echo {repo_info['original_name']} -^> http://localhost:{port}\n"
    
    start_bat += "\necho.\n"
    start_bat += "echo Building and starting all containers...\n"
    start_bat += "docker-compose -f docker-compose-modular.yml up --build -d\n\n"
    start_bat += "echo All containers started!\n"
    start_bat += "echo Access repositories at the URLs shown above\n"
    start_bat += "pause\n"
    
    with open('start_all_repos.bat', 'w', encoding='utf-8') as f:
        f.write(start_bat)
    
    # Make shell script executable
    os.chmod('start_all_repos.sh', 0o755)
    
    return start_script


def main():
    print("🔧 Generating Modular Docker Setup for ML Repositories")
    print("=" * 60)
    
    # Get available repositories
    repositories = get_repositories()
    
    if not repositories:
        print("No repositories found!")
        return
    
    print(f"Found {len(repositories)} repositories:")
    for repo in repositories:
        print(f"  - {repo['original_name']} -> {repo['service_name']}")
    
    print("\nGenerating Docker configuration...")
    
    # Create analysis directories
    analysis_dir = Path("analysis")
    analysis_dir.mkdir(exist_ok=True)
    
    for repo in repositories:
        repo_analysis_dir = analysis_dir / repo['service_name']
        repo_analysis_dir.mkdir(exist_ok=True)
    
    # Generate docker-compose.yml
    docker_compose = generate_docker_compose(repositories)
    print(f"Generated docker-compose-modular.yml with {len(repositories)} services")
    
    # Generate startup scripts
    generate_startup_script(repositories)
    print("Generated startup scripts (start_all_repos.sh and start_all_repos.bat)")
    
    # Generate README
    readme_content = f"""# Modular ML Repository Analysis

This setup provides individual Docker containers for each ML repository.

## Available Repositories ({len(repositories)} total):

"""
    
    base_port = 8888
    for i, repo in enumerate(repositories):
        port = base_port + i
        readme_content += f"- **{repo['original_name']}**: http://localhost:{port}\n"
    
    readme_content += """
## Usage:

### Start All Containers:
```bash
# Linux/Mac
./start_all_repos.sh

# Windows
start_all_repos.bat

# Or manually
docker-compose -f docker-compose-modular.yml up --build -d
```

### Start Individual Container:
```bash
docker-compose -f docker-compose-modular.yml up --build -d <service-name>
```

### Stop All Containers:
```bash
docker-compose -f docker-compose-modular.yml down
```

### View Logs:
```bash
docker-compose -f docker-compose-modular.yml logs -f <service-name>
```

## Container Structure:
- Each container runs Jupyter on its own port
- Repository code is mounted at `/workspace/repo/`
- Analysis notebooks can be saved to `/workspace/analysis/`
- Dependencies are installed automatically during build
"""
    
    with open('README-modular.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("Generated README-modular.md")
    
    print(f"\nModular Docker setup complete!")
    print(f"Generated files:")
    print(f"  - docker-compose-modular.yml")
    print(f"  - start_all_repos.sh / start_all_repos.bat")
    print(f"  - README-modular.md")
    print(f"  - docker_repos/ directory with individual Dockerfiles")
    print(f"\nTo start all containers: ./start_all_repos.sh")


if __name__ == "__main__":
    main()
