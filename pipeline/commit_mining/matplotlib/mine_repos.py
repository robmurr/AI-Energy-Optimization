#!/usr/bin/env python3
"""
Mine Matplotlib repositories from GitHub.
"""

import os
import sys
import requests
from git import Repo
from pathlib import Path
import json

try:
    from dotenv import load_dotenv
    # Load from Ground_Truth_Dataset/.env
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


def fetch_pytorch_repos(token=None, max_repos=10, min_stars=50):

    headers = {"Authorization": f"token {token}"} if token else {}

    # Search for Python repos with matplotlib in name or description
    query = f"matplotlib language:Python stars:>={min_stars}"
    url = f"https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": max_repos
    }

    print(f"Searching GitHub for Matplotlib repos (>={min_stars} stars)...")

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if "items" not in data:
            print("Error: No 'items' in API response")
            return []


        repos = []
        for item in data["items"]:
            repos.append({
                "name": item["name"],
                "full_name": item["full_name"],
                "clone_url": item["clone_url"],
                "stars": item["stargazers_count"],
                "description": item["description"] or "No description",
                "language": item["language"],
                "updated_at": item["updated_at"]
            })

        return repos

    except requests.exceptions.RequestException as e:
        print(f"Error fetching repositories: {e}")
        return []

def clone_repositories(repos, target_dir="repos"):
    """
    Clone repositories to local directory.

    """
    target_path = Path(__file__).parent / target_dir
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
    metadata_path = Path(__file__).parent / "results" / filename
    metadata_path.parent.mkdir(exist_ok=True)

    with open(metadata_path, 'w') as f:
        json.dump(repos, f, indent=2)

    print(f"\nSaved metadata to {metadata_path}")

def main():
    print("="*60)
    print("REPOSITORY MINING")
    print("="*60)
    print()

    # Load GitHub token from environment variable
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set it using: export GITHUB_TOKEN='your_token_here'")
        print("Or create a .env file in Ground_Truth_Dataset/ directory")
        return 1
    print()

    # Fetch repositories (testing with 5 repos)
    repos = fetch_pytorch_repos(token=token, max_repos=5, min_stars=50)

    if not repos:
        print("No repositories found. Exiting.")
        return 1

    print(f"\nFound {len(repos)} Matplotlib repositories:")
    for i, repo in enumerate(repos, 1):
        print(f"  {i}. {repo['full_name']} ({repo['stars']} stars)")

    # Clone repos
    cloned, skipped = clone_repositories(repos)

    # Save metadata
    all_repos = cloned + skipped
    save_repo_metadata(all_repos)

    print(f"\n  • Cloned: {len(cloned)} repos")
    print(f"  • Skipped (existing): {len(skipped)} repos")
    print(f"  • Total: {len(all_repos)} repos")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
