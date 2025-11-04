import requests
import time
import json

def fetch_ml_repos(min_stars=50, per_page=100, max_pages=5, single_per_topic=False):
    """
    Fetch Python repositories related to machine learning and various algorithms
    
    Args:
        min_stars: Minimum star count for repositories
        per_page: Number of repositories per API request (max 100)
        max_pages: Maximum pages to fetch per topic
        single_per_topic: If True, fetch only the top repository for each topic
    """
    base_url = "https://api.github.com/search/repositories"
    
    # Comprehensive ML topics and keywords
    ml_topics = [
        # Core ML/AI
        "machine-learning", "artificial-intelligence", "deep-learning", "neural-networks",
        "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
        
        # ML Algorithms
        "supervised-learning", "unsupervised-learning", "reinforcement-learning",
        "classification", "regression", "clustering", "dimensionality-reduction",
        "decision-trees", "random-forest", "svm", "naive-bayes", "knn", "linear-regression",
        "logistic-regression", "gradient-boosting", "xgboost", "lightgbm",
        
        # Deep Learning Specific
        "convolutional-neural-networks", "recurrent-neural-networks", "lstm", "gru",
        "transformer", "attention-mechanism", "generative-adversarial-networks", "gan",
        "autoencoder", "variational-autoencoder", "computer-vision", "natural-language-processing",
        
        # Specialized Areas
        "time-series", "anomaly-detection", "recommendation-systems", "collaborative-filtering",
        "feature-engineering", "model-selection", "hyperparameter-tuning", "cross-validation",
        "ensemble-methods", "boosting", "bagging", "stacking",
        
        # Advanced Topics
        "federated-learning", "transfer-learning", "few-shot-learning", "meta-learning",
        "continual-learning", "multi-task-learning", "self-supervised-learning",
        "graph-neural-networks", "knowledge-distillation", "neural-architecture-search"
    ]
    
    all_repos = []
    
    for topic in ml_topics:
        print(f"Searching for repositories with topic: {topic}")
        
        # If single_per_topic is True, only fetch 1 page with 1 result
        pages_to_fetch = 1 if single_per_topic else max_pages
        results_per_page = 1 if single_per_topic else per_page
        
        for page in range(1, pages_to_fetch + 1):
            query_parts = [
                f"stars:>={min_stars}",
                "language:Python",
                f"topic:{topic}"
            ]
            
            params = {
                "q": " ".join(query_parts),
                "sort": "stars",
                "order": "desc",
                "per_page": results_per_page,
                "page": page
            }
            
            try:
                response = requests.get(base_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    repos = data.get('items', [])
                    
                    if not repos:  # No more results
                        break
                        
                    all_repos.extend(repos)
                    if single_per_topic:
                        print(f"  Found: {repos[0]['name']} ({repos[0]['stargazers_count']:,} stars)")
                    else:
                        print(f"  Page {page}: Found {len(repos)} repositories")
                    
                    # Rate limiting - GitHub allows 10 requests per minute for unauthenticated
                    time.sleep(6)  # Wait 6 seconds between requests
                    
                    # If single_per_topic, we only want one repo, so break after first successful request
                    if single_per_topic:
                        break
                    
                elif response.status_code == 403:
                    print(f"  Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                else:
                    print(f"  Error {response.status_code}: {response.text}")
                    break
                    
            except Exception as e:
                print(f"  Error fetching {topic}: {e}")
                break
    
    # Remove duplicates based on repository ID
    unique_repos = {}
    for repo in all_repos:
        unique_repos[repo['id']] = repo
    
    return list(unique_repos.values())

def save_repos_to_file(repos, filename="ml_repositories_dataset.json"):
    """Save the repository data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(repos)} repositories to {filename}")

def analyze_repos(repos):
    """Analyze the collected repositories"""
    if not repos:
        return
        
    print(f"\n=== DATASET ANALYSIS ===")
    print(f"Total unique repositories: {len(repos)}")
    
    # Language distribution
    languages = {}
    for repo in repos:
        lang = repo.get('language', 'Unknown')
        languages[lang] = languages.get(lang, 0) + 1
    
    print(f"\nTop languages:")
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {lang}: {count}")
    
    # Star distribution
    stars = [repo['stargazers_count'] for repo in repos]
    print(f"\nStar statistics:")
    print(f"  Min stars: {min(stars)}")
    print(f"  Max stars: {max(stars)}")
    print(f"  Average stars: {sum(stars) / len(stars):.1f}")
    
    # Top repositories
    print(f"\nTop 10 repositories by stars:")
    sorted_repos = sorted(repos, key=lambda x: x['stargazers_count'], reverse=True)
    for i, repo in enumerate(sorted_repos[:10]):
        print(f"  {i+1}. {repo['name']} - {repo['stargazers_count']:,} stars")
        print(f"     {repo['html_url']}")
        if repo.get('description'):
            print(f"     {repo['description'][:100]}...")
        print()

# Build ML dataset
if __name__ == "__main__":
    print("Building comprehensive Machine Learning repository dataset...")
    print("This process will take several minutes due to rate limiting\n")
    
    try:
        # Fetch repositories (adjust parameters as needed)
        # Set single_per_topic=True for shallow fetch (37 repos total, 1 repo per topic)
        repos = fetch_ml_repos(
            min_stars=50,           # Lower threshold to get more variety
            per_page=100,           # Max per request
            max_pages=3,            # Pages per topic (adjust based on time constraints)
            single_per_topic=True   # Change to False for full dataset
        )
        
        if repos:
            print(f"Successfully collected {len(repos)} unique repositories!")
            
            # Save to file
            save_repos_to_file(repos, "ml_repositories_dataset.json")
            
            # Analyze the dataset
            analyze_repos(repos)
            print(f"ML repository dataset has been saved to 'ml_repositories_dataset.json'")
            
        else:
            print("No repositories found")
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        if 'repos' in locals() and repos:
            print(f"Partial dataset collected: {len(repos)} repositories")
            save_repos_to_file(repos, "partial_ml_dataset.json")
    except Exception as e:
        print(f"Error during dataset collection: {e}")
        if 'repos' in locals() and repos:
            print(f"Saving partial results: {len(repos)} repositories")
            save_repos_to_file(repos, "partial_ml_dataset.json")