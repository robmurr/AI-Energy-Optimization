#!/usr/bin/env python3
"""
Dependency Installation Script for ML Repository Analysis

This script reads repository metadata files and installs all dependencies
found across the cloned ML repositories.
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path


def install_dependencies(repos_dir="ml_repos_isolated/successful_clones", output_file="dependency_install_report.json"):
    """Install dependencies from all repository metadata files"""
    repos_path = Path(repos_dir)
    installed_packages = set()
    failed_installs = []
    
    print("Installing dependencies from all repositories...")
    
    if not repos_path.exists():
        print(f"Error: Repository directory {repos_path} does not exist")
        return False
    
    for repo_dir in repos_path.iterdir():
        if repo_dir.is_dir():
            metadata_file = repo_dir / 'repo_metadata.json'
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    dependencies = metadata.get('dependencies', {}).get('all_dependencies', [])
                    repo_name = metadata.get('name', repo_dir.name)
                    
                    print(f"Processing {repo_name}: {len(dependencies)} dependencies")
                    
                    for dep in dependencies:
                        if dep not in installed_packages:
                            try:
                                print(f"  Installing {dep}...")
                                result = subprocess.run([
                                    sys.executable, '-m', 'pip', 'install', dep, '--quiet'
                                ], capture_output=True, text=True, timeout=120)
                                
                                if result.returncode == 0:
                                    installed_packages.add(dep)
                                    print(f"  SUCCESS: {dep}")
                                else:
                                    print(f"  FAILED: {dep} - {result.stderr.strip()}")
                                    failed_installs.append(f"{dep}: {result.stderr.strip()}")
                                    
                            except subprocess.TimeoutExpired:
                                print(f"  TIMEOUT: {dep}")
                                failed_installs.append(f"{dep}: Timeout")
                            except Exception as e:
                                print(f"  ERROR: {dep} - {e}")
                                failed_installs.append(f"{dep}: {e}")
                        else:
                            print(f"  SKIPPED: {dep} (already installed)")
                            
                except Exception as e:
                    print(f"Error processing {repo_dir.name}: {e}")
    
    print(f"\n=== DEPENDENCY INSTALLATION COMPLETE ===")
    print(f"Successfully installed: {len(installed_packages)} unique packages")
    print(f"Failed installations: {len(failed_installs)}")
    
    if failed_installs:
        print(f"\nFailed packages (first 10):")
        for fail in failed_installs[:10]:
            print(f"  - {fail}")
    
    # Save installation report
    report = {
        'installed_packages': list(installed_packages),
        'failed_installs': failed_installs,
        'total_installed': len(installed_packages),
        'total_failed': len(failed_installs)
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"Installation report saved to: {output_file}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Install dependencies from ML repository metadata')
    parser.add_argument('--repos-dir', default='ml_repos_isolated/successful_clones',
                       help='Directory containing cloned repositories')
    parser.add_argument('--output', default='dependency_install_report.json',
                       help='Output file for installation report')
    
    args = parser.parse_args()
    
    success = install_dependencies(args.repos_dir, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
