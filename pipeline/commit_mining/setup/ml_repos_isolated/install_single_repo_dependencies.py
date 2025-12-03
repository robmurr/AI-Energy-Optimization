#!/usr/bin/env python3
"""
Single Repository Dependency Installation Script

This script installs dependencies for a single ML repository.
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path


def install_single_repo_dependencies(repo_dir="/workspace/repo", output_file="dependency_install_report.json"):
    """Install dependencies from a single repository metadata file"""
    repo_path = Path(repo_dir)
    installed_packages = set()
    failed_installs = []
    
    print(f"Starting dependency installation for repository in: {repo_path}")
    
    if not repo_path.exists():
        print(f"Error: Repository directory {repo_path} does not exist")
        return False
    
    metadata_file = repo_path / 'repo_metadata.json'
    if not metadata_file.exists():
        print(f"Warning: No repo_metadata.json found in {repo_path}")
        print("No dependencies to install - container ready!")
        return True
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        dependencies = metadata.get('dependencies', {}).get('all_dependencies', [])
        repo_name = metadata.get('name', repo_path.name)
        
        print(f"\n{'='*60}")
        print(f"PROCESSING REPOSITORY: {repo_name}")
        print(f"Total dependencies to install: {len(dependencies)}")
        print(f"{'='*60}")
        
        if not dependencies:
            print("No dependencies found for this repository")
            print("Container ready!")
            return True
        
        print(f"Dependencies to install: {', '.join(dependencies[:10])}{'...' if len(dependencies) > 10 else ''}")
        print()
        
        for i, dep in enumerate(dependencies, 1):
            try:
                print(f"📥 [{i}/{len(dependencies)}] Installing {dep}...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', dep, '--quiet'
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    installed_packages.add(dep)
                    print(f"SUCCESS: {dep}")
                else:
                    print(f"FAILED: {dep} - {result.stderr.strip()}")
                    failed_installs.append(f"{dep}: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                print(f"TIMEOUT: {dep}")
                failed_installs.append(f"{dep}: Timeout")
            except Exception as e:
                print(f"ERROR: {dep} - {e}")
                failed_installs.append(f"{dep}: {e}")
                
    except Exception as e:
        print(f"Error processing repository metadata: {e}")
        return False
    
    print(f"\n{'='*60}")
    print(f"DEPENDENCY INSTALLATION COMPLETE FOR {repo_name}")
    print(f"Successfully installed: {len(installed_packages)} packages")
    print(f"Failed installations: {len(failed_installs)}")
    print(f"{'='*60}")
    
    if failed_installs:
        print(f"\nFailed packages:")
        for fail in failed_installs:
            print(f"  - {fail}")
    
    # Save installation report
    report = {
        'repository': repo_name,
        'installed_packages': list(installed_packages),
        'failed_installs': failed_installs,
        'total_installed': len(installed_packages),
        'total_failed': len(failed_installs)
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"Installation report saved to: {output_file}")
    print("Container is ready for analysis!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Install dependencies for a single ML repository')
    parser.add_argument('--repo-dir', default='/workspace/repo',
                       help='Directory containing the repository')
    parser.add_argument('--output', default='dependency_install_report.json',
                       help='Output file for installation report')
    
    args = parser.parse_args()
    
    success = install_single_repo_dependencies(args.repo_dir, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

