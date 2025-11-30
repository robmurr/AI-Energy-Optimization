#!/usr/bin/env python3
"""
Aggregate Test Mappings from Multiple Frameworks

Combines test mapping CSV files from different frameworks into a single CSV file.
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict, Set


def read_csv_file(csv_path: Path) -> List[Dict]:
    """Read a CSV file and return list of rows as dictionaries."""
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    return rows


def aggregate_test_mappings(test_mappings_dir: Path, output_file: Path) -> int:
    """
    Aggregate all test mapping CSV files from test_mappings directory.
    
    Args:
        test_mappings_dir: Directory containing framework-specific test mapping CSVs
        output_file: Path to output aggregated CSV file
        
    Returns:
        Number of commits aggregated
    """
    test_mappings_dir = Path(test_mappings_dir)
    output_file = Path(output_file)
    
    if not test_mappings_dir.exists():
        print(f"Error: Test mappings directory not found: {test_mappings_dir}")
        return 0
    
    csv_files = list(test_mappings_dir.glob("*_test_mapping.csv"))
    
    if not csv_files:
        print(f"Warning: No test mapping CSV files found in {test_mappings_dir}")
        return 0
    
    print(f"Found {len(csv_files)} test mapping file(s):")
    for csv_file in csv_files:
        print(f"  - {csv_file.name}")
    
    expected_columns = [
        'repo', 'commit_hash', 'modified_files', 'modified_file_count',
        'relevant_tests', 'test_count', 'test_strategy'
    ]
    
    all_rows = []
    seen_commits: Set[tuple] = set()  
    duplicates = 0
    
    for csv_file in csv_files:
        framework_name = csv_file.stem.replace('_test_mapping', '')
        print(f"\nProcessing {framework_name}...")
        
        rows = read_csv_file(csv_file)
        
        if not rows:
            print(f"  No rows found in {csv_file.name}")
            continue
        
        if not all(col in rows[0].keys() for col in expected_columns):
            print(f"  Warning: {csv_file.name} has unexpected columns, skipping")
            continue
        
        added_count = 0
        for row in rows:
            commit_key = (row['repo'], row['commit_hash'])
            
            if commit_key in seen_commits:
                duplicates += 1
                continue
            
            seen_commits.add(commit_key)
            all_rows.append(row)
            added_count += 1
        
        print(f"  Added {added_count} commits (skipped {len(rows) - added_count} duplicates)")
    
    if not all_rows:
        print("\nNo rows to aggregate")
        return 0
    
    print(f"\nWriting aggregated CSV to {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=expected_columns)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"\nAggregation complete!")
    print(f"  Total commits: {len(all_rows)}")
    print(f"  Duplicates skipped: {duplicates}")
    print(f"  Output file: {output_file}")
    
    return len(all_rows)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Aggregate test mapping CSV files from multiple frameworks'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default=None,
        help='Directory containing test mapping CSV files (default: test_mappings/ in script directory)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output aggregated CSV file (default: test_mappings/aggregated_test_mapping.csv)'
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    
    if args.input_dir:
        test_mappings_dir = Path(args.input_dir)
    else:
        test_mappings_dir = script_dir / 'test_mappings'
    
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = test_mappings_dir / 'aggregated_test_mapping.csv'
    
    print("=" * 60)
    print("AGGREGATE TEST MAPPINGS")
    print("=" * 60)
    print()
    
    count = aggregate_test_mappings(test_mappings_dir, output_file)
    
    if count == 0:
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())


