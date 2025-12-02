#!/usr/bin/env python3
"""
Analyze Test Coverage of Modified Code
"""

import os
import re
import ast
import csv
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class ModifiedElement:
    """Represents a modified code element (function, class, or method)"""
    name: str
    element_type: str  # 'function', 'class', or 'method'
    parent_class: str = None  # For methods, the containing class

    def __str__(self):
        if self.element_type == 'method' and self.parent_class:
            return f"{self.parent_class}.{self.name}"
        return self.name


@dataclass
class CoverageAnalysis:
    """Results of coverage analysis for a commit"""
    repo: str
    commit_hash: str
    parent_hash: str = ""
    modified_files: str = ""
    relevant_tests: str = ""
    test_strategy: str = ""

    # What changed
    modified_elements: List[ModifiedElement] = field(default_factory=list)

    # What tests exercise
    tested_elements: Set[str] = field(default_factory=set)
    imported_elements: Set[str] = field(default_factory=set)
    called_elements: Set[str] = field(default_factory=set)

    # Coverage metrics
    coverage_status: str = "unknown"  # 'full', 'partial', 'none', 'unknown'
    coverage_percentage: float = 0.0
    matched_elements: List[str] = field(default_factory=list)
    unmatched_elements: List[str] = field(default_factory=list)


class DiffParser:
    """Parse git diffs to extract modified code elements"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def get_diff(self, parent_hash: str, commit_hash: str, file_path: str) -> str:
        """Get the git diff for a specific file between two commits"""
        try:
            cmd = [
                'git', 'diff',
                f'{parent_hash}..{commit_hash}',
                '--', file_path
            ]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            print(f"Error getting diff: {e}")
            return ""

    def get_file_content(self, commit_hash: str, file_path: str) -> str:
        """Get file content at a specific commit"""
        try:
            cmd = ['git', 'show', f'{commit_hash}:{file_path}']
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            print(f"Error getting file content: {e}")
        return ""

    def build_line_to_element_map(self, file_content: str) -> Dict[int, ModifiedElement]:
        """Build a map from line numbers to code elements (functions, classes, methods)"""
        line_map = {}

        try:
            tree = ast.parse(file_content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Map all lines in the class to the class
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        for line in range(node.lineno, node.end_lineno + 1):
                            line_map[line] = ModifiedElement(
                                name=node.name,
                                element_type='class'
                            )

                    # Map methods within the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if hasattr(item, 'lineno') and hasattr(item, 'end_lineno'):
                                for line in range(item.lineno, item.end_lineno + 1):
                                    line_map[line] = ModifiedElement(
                                        name=item.name,
                                        element_type='method',
                                        parent_class=node.name
                                    )

                elif isinstance(node, ast.FunctionDef):
                    # Only map top-level functions (not methods, which are handled above)
                    # Check if this function is not inside a class
                    is_method = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef) and node in parent.body:
                            is_method = True
                            break

                    if not is_method and hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        for line in range(node.lineno, node.end_lineno + 1):
                            line_map[line] = ModifiedElement(
                                name=node.name,
                                element_type='function'
                            )

        except SyntaxError:
            pass  # If we can't parse, return empty map

        return line_map

    def get_changed_line_numbers(self, diff: str) -> Set[int]:
        """Extract the line numbers that were modified in the diff"""
        changed_lines = set()

        # Parse diff hunks to find changed lines
        # Format: @@ -old_start,old_count +new_start,new_count @@
        hunk_header_pattern = r'@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s*@@'

        current_line = None
        for line in diff.split('\n'):
            # Check for hunk header
            match = re.match(hunk_header_pattern, line)
            if match:
                current_line = int(match.group(1))
                continue

            if current_line is None:
                continue

            # Track line numbers for added/modified lines
            if line.startswith('+') and not line.startswith('+++'):
                changed_lines.add(current_line)
                current_line += 1
            elif line.startswith('-') and not line.startswith('---'):
                # Deleted lines don't increment the new line number
                pass
            elif not line.startswith('\\'):  # Ignore "\ No newline at end of file"
                # Context line
                current_line += 1

        return changed_lines

    def extract_modified_elements(self, diff: str) -> List[ModifiedElement]:
        """Extract functions, classes, and methods from a diff"""
        elements = []
        seen_elements = set()  # Track unique elements

        # Split diff into hunks with their headers
        hunk_pattern = r'@@[^@]*@@([^\n]*)\n(.*?)(?=@@|$)'
        hunks = re.finditer(hunk_pattern, diff, flags=re.MULTILINE | re.DOTALL)

        for hunk_match in hunks:
            hunk_header = hunk_match.group(1).strip()
            hunk_content = hunk_match.group(2)

            # Extract context from hunk header (e.g., "def function_name:" or "class ClassName:")
            context_elements = self._extract_context_from_header(hunk_header)
            for elem in context_elements:
                elem_key = (elem.name, elem.element_type, elem.parent_class)
                if elem_key not in seen_elements:
                    elements.append(elem)
                    seen_elements.add(elem_key)

            # Also look for new function/class definitions in added lines
            added_lines = []
            for line in hunk_content.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    added_lines.append(line[1:])  # Remove the '+' prefix

            if added_lines:
                # Try to parse as Python code
                code = '\n'.join(added_lines)
                for elem in self._parse_code_elements(code):
                    elem_key = (elem.name, elem.element_type, elem.parent_class)
                    if elem_key not in seen_elements:
                        elements.append(elem)
                        seen_elements.add(elem_key)

        return elements

    def _extract_context_from_header(self, header: str) -> List[ModifiedElement]:
        """Extract function/class/method context from diff hunk header"""
        elements = []

        # Pattern: class ClassName:
        class_match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', header)
        if class_match:
            elements.append(ModifiedElement(
                name=class_match.group(1),
                element_type='class'
            ))

        # Pattern: def method_name( inside a class
        func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', header)
        if func_match:
            func_name = func_match.group(1)
            # If we found a class earlier, this is a method
            if class_match:
                elements.append(ModifiedElement(
                    name=func_name,
                    element_type='method',
                    parent_class=class_match.group(1)
                ))
            else:
                elements.append(ModifiedElement(
                    name=func_name,
                    element_type='function'
                ))

        return elements

    def _parse_code_elements(self, code: str) -> List[ModifiedElement]:
        """Parse Python code to extract functions, classes, and methods"""
        elements = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this is a method (inside a class) or a function
                    parent_class = self._find_parent_class(tree, node)
                    if parent_class:
                        elements.append(ModifiedElement(
                            name=node.name,
                            element_type='method',
                            parent_class=parent_class
                        ))
                    else:
                        elements.append(ModifiedElement(
                            name=node.name,
                            element_type='function'
                        ))

                elif isinstance(node, ast.ClassDef):
                    elements.append(ModifiedElement(
                        name=node.name,
                        element_type='class'
                    ))

        except SyntaxError:
            # If we can't parse as complete Python, try regex patterns
            elements.extend(self._regex_extract_elements(code))

        return elements

    def _find_parent_class(self, tree: ast.AST, func_node: ast.FunctionDef) -> str:
        """Find the parent class of a function node"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if func_node in node.body:
                    return node.name
        return None

    def _regex_extract_elements(self, code: str) -> List[ModifiedElement]:
        """Fallback: Use regex to extract function/class definitions"""
        elements = []

        # Match function definitions
        func_pattern = r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(func_pattern, code, re.MULTILINE):
            elements.append(ModifiedElement(
                name=match.group(1),
                element_type='function'
            ))

        # Match class definitions
        class_pattern = r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(class_pattern, code, re.MULTILINE):
            elements.append(ModifiedElement(
                name=match.group(1),
                element_type='class'
            ))

        return elements


class TestAnalyzer:
    """Analyze test files to determine what they actually test"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def analyze_test_file(self, test_file_path: str, modified_file_path: str, commit_hash: str) -> Tuple[Set[str], Set[str]]:
        """
        Analyze a test file to see what elements it exercises from the modified file.
        Reads test file from specific commit, not current filesystem.
        Returns (imported_elements, called_elements)
        """
        imported = set()
        called = set()

        try:
            # Read test file from specific commit
            cmd = ['git', 'show', f'{commit_hash}:{test_file_path}']
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Test file doesn't exist at this commit
                return imported, called

            content = result.stdout

            # Extract imported elements
            imported = self._extract_imports(content, modified_file_path)

            # Extract called elements
            called = self._extract_calls(content)

        except Exception as e:
            print(f"Error analyzing test file {test_file_path}: {e}")

        return imported, called

    def _extract_imports(self, content: str, modified_file_path: str) -> Set[str]:
        """Extract what is imported from the modified file"""
        imported = set()

        # Convert file path to module path (e.g., comfy/samplers.py -> comfy.samplers)
        module_path = modified_file_path.replace('/', '.').replace('\\', '.').replace('.py', '')

        # Pattern 1: from module import X, Y, Z
        pattern1 = rf'from\s+{re.escape(module_path)}\s+import\s+([^\n]+)'
        for match in re.finditer(pattern1, content):
            imports = match.group(1)
            # Split by comma and clean up
            for item in imports.split(','):
                item = item.strip()
                # Handle "as" aliases
                if ' as ' in item:
                    item = item.split(' as ')[0].strip()
                imported.add(item)

        # Pattern 2: from module.submodule import X
        if '/' in module_path or '\\' in module_path:
            parts = re.split(r'[/\\]', module_path)
            for i in range(len(parts)):
                partial_module = '.'.join(parts[:i+1])
                pattern = rf'from\s+{re.escape(partial_module)}\s+import\s+([^\n]+)'
                for match in re.finditer(pattern, content):
                    imports = match.group(1)
                    for item in imports.split(','):
                        item = item.strip()
                        if ' as ' in item:
                            item = item.split(' as ')[0].strip()
                        imported.add(item)

        # Pattern 3: import module (then look for module.X usage)
        pattern3 = rf'import\s+{re.escape(module_path)}(?:\s+as\s+(\w+))?'
        for match in re.finditer(pattern3, content):
            alias = match.group(1) or module_path.split('.')[-1]
            # Find usages like alias.function_name
            usage_pattern = rf'{re.escape(alias)}\.([a-zA-Z_][a-zA-Z0-9_]*)'
            for usage_match in re.finditer(usage_pattern, content):
                imported.add(usage_match.group(1))

        return imported

    def _extract_calls(self, content: str) -> Set[str]:
        """Extract function/class/method calls from test code"""
        called = set()

        # Pattern: function_name( or ClassName( or obj.method_name(
        call_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(call_pattern, content):
            called.add(match.group(1))

        # Pattern: Class.method or module.function
        dotted_pattern = r'\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(dotted_pattern, content):
            called.add(match.group(1))

        # Pattern: mock/patch targets
        mock_pattern = r'[@(](mock|patch)\s*\(["\']([^"\']+)["\']'
        for match in re.finditer(mock_pattern, content):
            target = match.group(2)
            # Extract the last component (function/class/method name)
            if '.' in target:
                called.add(target.split('.')[-1])

        return called


class CoverageAnalyzer:
    """Main analyzer that coordinates diff parsing and test analysis"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.repos_dir = base_dir / 'repos'

    def analyze_commit(self, row: dict) -> CoverageAnalysis:
        """Analyze coverage for a single commit"""
        repo = row['repo']
        commit_hash = row['commit_hash']
        modified_files = row['modified_files']
        relevant_tests = row['relevant_tests']
        test_strategy = row['test_strategy']

        repo_path = self.repos_dir / repo

        # Initialize analysis result
        analysis = CoverageAnalysis(
            repo=repo,
            commit_hash=commit_hash,
            modified_files=modified_files,
            relevant_tests=relevant_tests,
            test_strategy=test_strategy
        )

        if not repo_path.exists():
            print(f"Repository not found: {repo_path}")
            return analysis

        # Get parent commit hash
        parent_hash = self._get_parent_hash(repo_path, commit_hash)
        if not parent_hash:
            print(f"Could not find parent hash for {commit_hash}")
            return analysis

        # Store parent hash in analysis
        analysis.parent_hash = parent_hash

        # Parse diff to find modified elements
        diff_parser = DiffParser(repo_path)
        for file_path in modified_files.split(';'):
            file_path = file_path.strip()
            if not file_path.endswith('.py'):
                continue  # Only analyze Python files

            # Get the diff
            diff = diff_parser.get_diff(parent_hash, commit_hash, file_path)
            if not diff:
                continue

            # Get the file content at the commit to build line map
            file_content = diff_parser.get_file_content(commit_hash, file_path)
            if not file_content:
                # Fallback to old method
                elements = diff_parser.extract_modified_elements(diff)
                analysis.modified_elements.extend(elements)
                continue

            # Build line-to-element map
            line_map = diff_parser.build_line_to_element_map(file_content)

            # Get changed line numbers
            changed_lines = diff_parser.get_changed_line_numbers(diff)

            # Find which elements were modified
            seen_elements = set()
            for line_num in changed_lines:
                if line_num in line_map:
                    elem = line_map[line_num]
                    elem_key = (elem.name, elem.element_type, elem.parent_class)
                    if elem_key not in seen_elements:
                        analysis.modified_elements.append(elem)
                        seen_elements.add(elem_key)

            # Also check for new function/class definitions using old method
            elements = diff_parser.extract_modified_elements(diff)
            for elem in elements:
                elem_key = (elem.name, elem.element_type, elem.parent_class)
                if elem_key not in seen_elements:
                    analysis.modified_elements.append(elem)
                    seen_elements.add(elem_key)

        # Analyze test files (read from commit, not filesystem)
        test_analyzer = TestAnalyzer(repo_path)
        for test_file in relevant_tests.split(';'):
            test_file = test_file.strip()
            if not test_file:
                continue

            for modified_file in modified_files.split(';'):
                modified_file = modified_file.strip()
                if not modified_file.endswith('.py'):
                    continue

                imported, called = test_analyzer.analyze_test_file(test_file, modified_file, commit_hash)
                analysis.imported_elements.update(imported)
                analysis.called_elements.update(called)

        # Combine imported and called elements
        analysis.tested_elements = analysis.imported_elements | analysis.called_elements

        # Calculate coverage
        self._calculate_coverage(analysis)

        return analysis

    def _get_parent_hash(self, repo_path: Path, commit_hash: str) -> str:
        """Get the parent commit hash"""
        try:
            cmd = ['git', 'rev-parse', f'{commit_hash}^']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            print(f"Error getting parent hash: {e}")
        return None

    def _calculate_coverage(self, analysis: CoverageAnalysis):
        """Calculate coverage metrics"""
        if not analysis.modified_elements:
            analysis.coverage_status = "no_changes_detected"
            return

        if not analysis.tested_elements:
            analysis.coverage_status = "no_tests_detected"
            return

        # Check which modified elements are tested
        for element in analysis.modified_elements:
            element_str = str(element)

            # Check if the element name appears in tested elements
            # For methods, check both "ClassName.method_name" and "method_name"
            if element.element_type == 'method':
                if (element_str in analysis.tested_elements or
                    element.name in analysis.tested_elements or
                    element.parent_class in analysis.tested_elements):
                    analysis.matched_elements.append(element_str)
                else:
                    analysis.unmatched_elements.append(element_str)
            else:
                if element.name in analysis.tested_elements:
                    analysis.matched_elements.append(element_str)
                else:
                    analysis.unmatched_elements.append(element_str)

        # Calculate coverage percentage
        total_elements = len(analysis.modified_elements)
        matched_elements = len(analysis.matched_elements)

        if total_elements > 0:
            analysis.coverage_percentage = (matched_elements / total_elements) * 100

        # Determine coverage status
        if matched_elements == 0:
            analysis.coverage_status = "none"
        elif matched_elements == total_elements:
            analysis.coverage_status = "full"
        else:
            analysis.coverage_status = "partial"


def main():
    parser = argparse.ArgumentParser(
        description='Analyze test coverage of modified code in commits'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help='Maximum number of commits to analyze (default: all)'
    )
    args = parser.parse_args()

    # Paths
    base_dir = Path(__file__).parent.parent
    test_mapping_file = base_dir / 'test_mapping.csv'
    output_file = base_dir / 'coverage_analysis.csv'

    if not test_mapping_file.exists():
        print(f"Error: {test_mapping_file} not found")
        print("Please run map_tests_to_commits.py first")
        return

    # Read test mapping CSV
    print(f"Reading test mappings from {test_mapping_file}...")
    with open(test_mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total_commits = len(rows)
    if args.max:
        rows = rows[:args.max]
        print(f"Analyzing {len(rows)} of {total_commits} commits (--max {args.max})")
    else:
        print(f"Analyzing all {total_commits} commits")

    # Analyze each commit
    analyzer = CoverageAnalyzer(base_dir)
    results = []

    for i, row in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] Analyzing {row['repo']} - {row['commit_hash'][:8]}...")
        analysis = analyzer.analyze_commit(row)
        results.append(analysis)

        # Print summary
        print(f"  Modified elements: {len(analysis.modified_elements)}")
        print(f"  Tested elements: {len(analysis.tested_elements)}")
        print(f"  Coverage: {analysis.coverage_status} ({analysis.coverage_percentage:.1f}%)")
        if analysis.matched_elements:
            print(f"  Matched: {', '.join(analysis.matched_elements[:3])}" +
                  (f" (+{len(analysis.matched_elements)-3} more)" if len(analysis.matched_elements) > 3 else ""))
        if analysis.unmatched_elements:
            print(f"  Unmatched: {', '.join(analysis.unmatched_elements[:3])}" +
                  (f" (+{len(analysis.unmatched_elements)-3} more)" if len(analysis.unmatched_elements) > 3 else ""))

    # Filter out commits with 0% coverage
    filtered_results = [
        r for r in results
        if r.coverage_status not in ['none', 'no_changes_detected', 'no_tests_detected']
    ]
    excluded_count = len(results) - len(filtered_results)
    print(f"\nFiltering: Excluding {excluded_count} commits with 0% coverage")
    print(f"Keeping {len(filtered_results)} commits with coverage > 0%")

    # Write results to CSV
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'repo', 'commit_hash', 'parent_hash', 'modified_files', 'relevant_tests', 'test_strategy',
            'modified_elements', 'modified_element_count',
            'tested_elements', 'tested_element_count',
            'coverage_status', 'coverage_percentage',
            'matched_elements', 'unmatched_elements'
        ])

        for analysis in filtered_results:
            modified_elements_str = '; '.join(str(e) for e in analysis.modified_elements)
            tested_elements_str = '; '.join(sorted(analysis.tested_elements))
            matched_str = '; '.join(analysis.matched_elements)
            unmatched_str = '; '.join(analysis.unmatched_elements)

            writer.writerow([
                analysis.repo,
                analysis.commit_hash,
                analysis.parent_hash,
                analysis.modified_files,
                analysis.relevant_tests,
                analysis.test_strategy,
                modified_elements_str,
                len(analysis.modified_elements),
                tested_elements_str,
                len(analysis.tested_elements),
                analysis.coverage_status,
                f"{analysis.coverage_percentage:.2f}",
                matched_str,
                unmatched_str
            ])

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    total = len(results)
    total_in_output = len(filtered_results)
    full_coverage = sum(1 for r in results if r.coverage_status == 'full')
    partial_coverage = sum(1 for r in results if r.coverage_status == 'partial')
    no_coverage = sum(1 for r in results if r.coverage_status == 'none')
    no_changes = sum(1 for r in results if r.coverage_status == 'no_changes_detected')
    no_tests = sum(1 for r in results if r.coverage_status == 'no_tests_detected')

    print(f"Total commits analyzed: {total}")
    print(f"Commits in output CSV: {total_in_output} (excluded {total - total_in_output} with 0% coverage)")

    print(f"\nCoverage breakdown (of {total} analyzed):")
    print(f"  Full coverage:       {full_coverage:4d} ({full_coverage/total*100:5.1f}%)")
    print(f"  Partial coverage:    {partial_coverage:4d} ({partial_coverage/total*100:5.1f}%)")
    print(f"  No coverage:         {no_coverage:4d} ({no_coverage/total*100:5.1f}%) [FILTERED OUT]")
    print(f"  No changes detected: {no_changes:4d} ({no_changes/total*100:5.1f}%) [FILTERED OUT]")
    print(f"  No tests detected:   {no_tests:4d} ({no_tests/total*100:5.1f}%) [FILTERED OUT]")

    avg_coverage_all = sum(r.coverage_percentage for r in results) / total if total > 0 else 0
    avg_coverage_kept = sum(r.coverage_percentage for r in filtered_results) / total_in_output if total_in_output > 0 else 0

    print(f"\nAverage coverage (all analyzed): {avg_coverage_all:.2f}%")
    print(f"Average coverage (kept in CSV):  {avg_coverage_kept:.2f}%")

    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
