#!/usr/bin/env python3
"""
Mine PyTorch repositories from GitHub.

UPDATED: Now filters for APPLICATION repos 
         instead of FRAMEWORK repos
"""

import os
import sys
import requests
from git import Repo
from pathlib import Path
import json
import argparse
import datetime

try:
    from dotenv import load_dotenv
    # Load from Ground_Truth_Dataset/.env
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass



# PRE-CLONE FILTERS: Exclude framework repos, keep application repos


# Organizations that build frameworks (not application repos)
EXCLUDED_ORGS = {
    'pytorch', 'tensorflow', 'google', 'google-research',
    'facebookresearch', 'keras-team', 'numpy', 'pandas-dev',
    'scikit-learn', 'matplotlib', 'apache', 'openai',
    'huggingface',  # transformers is a framework-like library
    'deepmind', 'microsoft',  # Too broad, includes DeepSpeed, etc.
}

# Exact repo names to exclude (core frameworks only)
# Note: Only exact matches excluded, not substrings
# "pytorch" excluded, "pytorch-tutorial" kept
CORE_FRAMEWORK_REPOS = {
    'pytorch', 'torch', 'tensorflow', 'jax', 'scikit-learn',
    'keras', 'mxnet', 'paddlepaddle', 'chainer', 'caffe',
    'theano', 'onnx', 'onnxruntime', 'transformers',
    'numpy', 'pandas', 'scipy', 'matplotlib',
}


def should_exclude_repo_preclone(repo_data):
    """
    Pre-clone filtering based on GitHub metadata.

    Excludes framework repos and repos likely to have complex builds.
    Keeps application repos that use frameworks as dependencies.

    Returns: (should_exclude: bool, reason: str)
    """
    full_name = repo_data.get('full_name', '')
    owner = full_name.split('/')[0] if '/' in full_name else ''
    repo_name = repo_data.get('name', '').lower()

    # 1. Exclude framework organizations
    if owner.lower() in EXCLUDED_ORGS:
        return True, f"Framework org: {owner}"

    # 2. Exclude core framework repos (exact name match only, not substring)
    if repo_name in CORE_FRAMEWORK_REPOS:
        return True, f"Core framework: {repo_name}"

    # 3. Exclude if too large (likely complex framework)
    size_kb = repo_data.get('size', 0)
    if size_kb > 300_000:  # 300 MB
        return True, f"Too large: {size_kb/1024:.0f}MB (>300MB)"

    # 4. Exclude if too popular (likely a framework, not an application)
    stars = repo_data.get('stargazers_count', 0)
    if stars > 10_000:
        return True, f"Too popular: {stars} stars (likely framework)"

    # 5. Exclude forks (duplicates of other repos)
    if repo_data.get('fork', False):
        return True, "Is a fork"

    # 6. Exclude if not recently maintained
    updated_str = repo_data.get('updated_at', '')
    if updated_str:
        try:
            updated = datetime.datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            days_since = (datetime.datetime.now(datetime.timezone.utc) - updated).days
            if days_since > 730:  # 2 years
                return True, f"Inactive: not updated in {days_since} days"
        except Exception:
            pass

    # 7. Require Python as primary language
    language = repo_data.get('language')
    if language != 'Python':
        return True, f"Not Python: {language}"

    # Passed all filters - this is likely an application repo!
    return False, None


def fetch_pytorch_repos(token=None, max_repos=10, min_stars=50):
    """
    Fetch PyTorch APPLICATION repositories (not framework repos).

    NEW: Uses pre-clone filtering to exclude framework repos.
    """
    headers = {"Authorization": f"token {token}"} if token else {}

    # NEW: Fetch 3x more repos since we'll filter many out
    fetch_count = min(max_repos * 3, 100)  # GitHub API max is 100 per page

    # NEW: Search for pytorch-related repos, but with upper limit to exclude frameworks
    # Pre-clone filtering will exclude framework repos
    query = f'pytorch OR torch language:Python stars:{min_stars}..5000'

    url = f"https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": fetch_count
    }

    print(f"Searching GitHub for PyTorch-related repos...")
    print(f"  Query: pytorch OR torch (Python, {min_stars}-5000 stars)")
    print(f"  Pre-clone filters will exclude framework repos")
    print(f"  Fetching up to {fetch_count} repos (will filter to ~{max_repos})")
    print()

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if "items" not in data:
            print("Error: No 'items' in API response")
            return []

        # NEW: Apply pre-clone filtering
        repos = []
        excluded_count = 0
        excluded_reasons = {}

        for item in data["items"]:
            # NEW: Capture additional metadata for filtering
            repo_data = {
                "name": item["name"],
                "full_name": item["full_name"],
                "clone_url": item["clone_url"],
                "stars": item["stargazers_count"],
                "size": item.get("size", 0),  # NEW: Size in KB
                "fork": item.get("fork", False),  # NEW: Is fork?
                "description": item["description"] or "No description",
                "language": item["language"],
                "updated_at": item["updated_at"]
            }

            # NEW: Apply pre-clone filter
            should_exclude, reason = should_exclude_repo_preclone(repo_data)

            if should_exclude:
                excluded_count += 1
                excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
                print(f"❌ SKIP: {repo_data['full_name']:40} - {reason}")
                continue

            # Passed filters - keep this repo
            repos.append(repo_data)
            size_mb = repo_data['size'] / 1024
            print(f"✅ KEEP: {repo_data['full_name']:40} ({repo_data['stars']:5} ⭐, {size_mb:5.1f}MB)")

            # Stop once we have enough repos
            if len(repos) >= max_repos:
                break

        # Print filtering summary
        print()
        print("="*60)
        print("PRE-CLONE FILTERING SUMMARY")
        print("="*60)
        print(f"Fetched from GitHub: {len(data['items'])} repos")
        print(f"Excluded: {excluded_count} repos")
        print(f"Kept: {len(repos)} repos")
        print()

        if excluded_reasons:
            print("Exclusion reasons:")
            for reason, count in sorted(excluded_reasons.items(), key=lambda x: -x[1]):
                print(f"  - {reason}: {count}")
            print()

        return repos

    except requests.exceptions.RequestException as e:
        print(f"Error fetching repositories: {e}")
        return []

def clone_repositories(repos, target_dir="repos"):
    """
    Clone repositories to local directory.

    """
    target_path = Path(__file__).parent.parent / target_dir
    target_path.mkdir(exist_ok=True)

    print(f"\nCloning {len(repos)} repositories to {target_path}...")
    print()

    cloned = []
    skipped = []

    for idx, repo_data in enumerate(repos, 1):
        repo_name = repo_data["name"]
        repo_path = target_path / repo_name

        print(f"[{idx}/{len(repos)}] {repo_name}...", end=" ")

        # Skip if exists
        if repo_path.exists():
            print(f"already exists, skipping")
            skipped.append(repo_data)
            continue

        try:
            Repo.clone_from(repo_data["clone_url"], str(repo_path))
            print(f"cloned successfully ({repo_data['stars']} stars)")
            cloned.append(repo_data)
        except Exception as e:
            print(f"FAILED: {e}")

    return cloned, skipped

def save_repo_metadata(repos, filename="repo_metadata.json"):
    metadata_path = Path(__file__).parent.parent / "results" / filename
    metadata_path.parent.mkdir(exist_ok=True)

    with open(metadata_path, 'w') as f:
        json.dump(repos, f, indent=2)

    print(f"\nSaved metadata to {metadata_path}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Mine PyTorch APPLICATION repositories (not framework repos)'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=10,
        help='Maximum number of repositories to clone (default: 10)'
    )
    parser.add_argument(
        '--min-stars',
        type=int,
        default=50,
        help='Minimum star count for repositories (default: 50)'
    )

    args = parser.parse_args()

    print("="*60)
    print("REPOSITORY MINING - APPLICATION REPOS ONLY")
    print("="*60)
    print(" Target: Application repos that USE frameworks")
    print(" Exclude: Framework repos that BUILD frameworks")
    print()
    print(f"Max repositories: {args.max}")
    print(f"Min stars: {args.min_stars}")
    print("="*60)
    print()

    # Load GitHub token from environment variable
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print(" Error: GITHUB_TOKEN environment variable not set")
        print("Please set it using: export GITHUB_TOKEN='your_token_here'")
        print("Or create a .env file in Ground_Truth_Dataset/ directory")
        return 1

    # Fetch repositories (with pre-clone filtering)
    repos = fetch_pytorch_repos(token=token, max_repos=args.max, min_stars=args.min_stars)

    if not repos:
        print(" No repositories found after filtering. Exiting.")
        print("   Try lowering --min-stars or increasing --max")
        return 1

    print(f"Found {len(repos)} application repositories to clone:")
    for i, repo in enumerate(repos, 1):
        size_mb = repo['size'] / 1024
        print(f"  {i}. {repo['full_name']:40} ({repo['stars']:5} ⭐, {size_mb:5.1f}MB)")
    print()

    # Clone repos
    cloned, skipped = clone_repositories(repos)

    # Save metadata
    all_repos = cloned + skipped
    save_repo_metadata(all_repos)

    print()
    print("="*60)
    print("CLONING SUMMARY")
    print("="*60)
    print(f"  • Cloned: {len(cloned)} repos")
    print(f"  • Skipped (already exist): {len(skipped)} repos")
    print(f"  • Total: {len(all_repos)} repos")
    print("="*60)
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
