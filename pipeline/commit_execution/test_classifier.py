#!/usr/bin/env python3
import ast
import os
import re
from pathlib import Path
from typing import Set, List, Tuple

INTEGRATION_IMPORTS = {
    'requests', 'httpx', 'aiohttp', 'urllib.request', 'urllib3',
    'websocket', 'websockets', 'socket', 'socketio',
    'psycopg2', 'pymongo', 'mysql', 'sqlalchemy', 'redis', 'pymysql',
    'celery', 'kombu', 'pika', 'kafka',
    'docker', 'kubernetes', 'boto3', 'azure', 'google.cloud',
    'selenium', 'playwright', 'pyppeteer',
    'flask', 'django', 'fastapi', 'tornado', 'aiohttp.web',
    'grpc', 'zeromq', 'zmq',
}

INTEGRATION_PATTERNS = [
    r'\.get\s*\(\s*["\']https?://',
    r'\.post\s*\(\s*["\']https?://',
    r'\.put\s*\(\s*["\']https?://',
    r'\.delete\s*\(\s*["\']https?://',
    r'urlopen\s*\(',
    r'\.connect\s*\(\s*["\']',
    r'subprocess\.(run|Popen|call)\s*\(',
    r'@pytest\.mark\.(integration|slow|e2e|functional|api)',
    r'@pytest\.mark\.skip',
    r'localhost:\d+',
    r'127\.0\.0\.1:\d+',
    r'0\.0\.0\.0:\d+',
]

INTEGRATION_DIR_PATTERNS = [
    'integration', 'e2e', 'functional', 'api_tests', 'acceptance',
    'end_to_end', 'smoke', 'system',
]

INTEGRATION_FILE_PATTERNS = [
    r'test_integration', r'test_e2e', r'test_api', r'test_functional',
    r'integration_test', r'e2e_test', r'conftest',
]


class TestClassifier:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def get_imports_from_file(self, filepath: Path) -> Set[str]:
        imports = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
                        imports.add(node.module)
        except:
            pass
        return imports
    
    def has_integration_patterns(self, filepath: Path) -> Tuple[bool, List[str]]:
        reasons = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for pattern in INTEGRATION_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    reasons.append(f"pattern:{pattern[:30]}")
        except:
            pass
        return len(reasons) > 0, reasons
    
    def is_integration_path(self, filepath: Path) -> Tuple[bool, List[str]]:
        reasons = []
        path_str = str(filepath).lower()
        for pattern in INTEGRATION_DIR_PATTERNS:
            if f'/{pattern}/' in path_str or f'\\{pattern}\\' in path_str:
                reasons.append(f"dir:{pattern}")
        filename = filepath.stem.lower()
        for pattern in INTEGRATION_FILE_PATTERNS:
            if re.search(pattern, filename):
                reasons.append(f"filename:{pattern}")
        return len(reasons) > 0, reasons
    
    def has_integration_imports(self, filepath: Path) -> Tuple[bool, List[str]]:
        reasons = []
        imports = self.get_imports_from_file(filepath)
        for imp in imports:
            imp_lower = imp.lower()
            for integration_imp in INTEGRATION_IMPORTS:
                if imp_lower == integration_imp.lower() or imp_lower.startswith(integration_imp.lower() + '.'):
                    reasons.append(f"import:{imp}")
                    break
        return len(reasons) > 0, reasons
    
    def has_fixture_dependencies(self, filepath: Path) -> Tuple[bool, List[str]]:
        reasons = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            fixture_patterns = [
                r'@pytest\.fixture.*\n.*def\s+\w+.*:\s*\n.*(?:subprocess|server|client|connection|database|redis|mongo)',
                r'def\s+\w+\(.*(?:live_server|test_server|api_client|db_session)',
                r'usefixtures\(["\'].*(?:server|database|redis|client)',
            ]
            for pattern in fixture_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    reasons.append(f"fixture:{pattern[:30]}")
        except:
            pass
        return len(reasons) > 0, reasons
    
    def classify_test_file(self, filepath: Path) -> dict:
        result = {
            'path': str(filepath),
            'is_unit_test': True,
            'reasons': [],
        }
        
        is_int_path, path_reasons = self.is_integration_path(filepath)
        if is_int_path:
            result['is_unit_test'] = False
            result['reasons'].extend(path_reasons)
        
        has_int_imports, import_reasons = self.has_integration_imports(filepath)
        if has_int_imports:
            result['is_unit_test'] = False
            result['reasons'].extend(import_reasons)
        
        has_int_patterns, pattern_reasons = self.has_integration_patterns(filepath)
        if has_int_patterns:
            result['is_unit_test'] = False
            result['reasons'].extend(pattern_reasons)
        
        has_fixtures, fixture_reasons = self.has_fixture_dependencies(filepath)
        if has_fixtures:
            result['is_unit_test'] = False
            result['reasons'].extend(fixture_reasons)
        
        return result
    
    def find_test_files(self, test_paths: List[str] = None) -> List[Path]:
        test_files = []
        if test_paths:
            for tp in test_paths:
                path = self.repo_path / tp
                if path.is_file() and path.suffix == '.py':
                    test_files.append(path)
                elif path.is_dir():
                    test_files.extend(path.rglob('test_*.py'))
                    test_files.extend(path.rglob('*_test.py'))
        else:
            for test_dir in ['tests', 'test', 'testing']:
                td = self.repo_path / test_dir
                if td.exists():
                    test_files.extend(td.rglob('test_*.py'))
                    test_files.extend(td.rglob('*_test.py'))
        return list(set(test_files))
    
    def classify_tests(self, test_paths: List[str] = None) -> dict:
        test_files = self.find_test_files(test_paths)
        unit_tests = []
        integration_tests = []
        
        for tf in test_files:
            classification = self.classify_test_file(tf)
            if classification['is_unit_test']:
                unit_tests.append(classification)
            else:
                integration_tests.append(classification)
        
        return {
            'unit_tests': unit_tests,
            'integration_tests': integration_tests,
            'total': len(test_files),
            'unit_count': len(unit_tests),
            'integration_count': len(integration_tests),
        }


def generate_classifier_script() -> str:
    return '''
import ast
import os
import re
import sys
import json
from pathlib import Path

INTEGRATION_IMPORTS = {
    'requests', 'httpx', 'aiohttp', 'urllib.request', 'urllib3',
    'websocket', 'websockets', 'socket', 'socketio',
    'psycopg2', 'pymongo', 'mysql', 'sqlalchemy', 'redis', 'pymysql',
    'celery', 'kombu', 'pika', 'kafka',
    'docker', 'kubernetes', 'boto3', 'azure', 'google.cloud',
    'selenium', 'playwright', 'pyppeteer',
    'flask', 'django', 'fastapi', 'tornado', 'aiohttp.web',
    'grpc', 'zeromq', 'zmq',
}

INTEGRATION_PATTERNS = [
    r'\\.get\\s*\\(\\s*["\\'"]https?://',
    r'\\.post\\s*\\(\\s*["\\'"]https?://',
    r'\\.put\\s*\\(\\s*["\\'"]https?://',
    r'\\.delete\\s*\\(\\s*["\\'"]https?://',
    r'urlopen\\s*\\(',
    r'\\.connect\\s*\\(\\s*["\\'"]',
    r'subprocess\\.(run|Popen|call)\\s*\\(',
    r'@pytest\\.mark\\.(integration|slow|e2e|functional|api)',
    r'@pytest\\.mark\\.skip',
    r'localhost:\\d+',
    r'127\\.0\\.0\\.1:\\d+',
    r'0\\.0\\.0\\.0:\\d+',
]

INTEGRATION_DIR_PATTERNS = ['integration', 'e2e', 'functional', 'api_tests', 'acceptance', 'end_to_end', 'smoke', 'system', 'inference']

def get_imports(filepath):
    imports = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
                    imports.add(node.module)
    except:
        pass
    return imports

def is_unit_test(filepath):
    path_str = str(filepath).lower()
    for pattern in INTEGRATION_DIR_PATTERNS:
        if f'/{pattern}/' in path_str or path_str.endswith(f'/{pattern}'):
            return False, f"integration_dir:{pattern}"
    
    imports = get_imports(filepath)
    for imp in imports:
        for int_imp in INTEGRATION_IMPORTS:
            if imp.lower() == int_imp.lower() or imp.lower().startswith(int_imp.lower() + '.'):
                return False, f"import:{imp}"
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for pattern in INTEGRATION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"pattern_match"
    except:
        pass
    
    return True, None

def find_unit_tests(test_paths):
    unit_tests = []
    skipped = []
    
    for tp in test_paths:
        path = Path(tp)
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = list(path.rglob('test_*.py')) + list(path.rglob('*_test.py'))
        else:
            continue
        
        for f in files:
            if 'conftest' in f.name:
                continue
            is_unit, reason = is_unit_test(f)
            if is_unit:
                unit_tests.append(str(f))
            else:
                skipped.append({'path': str(f), 'reason': reason})
    
    return unit_tests, skipped

if __name__ == '__main__':
    test_paths = sys.argv[1:] if len(sys.argv) > 1 else ['tests', 'test']
    existing_paths = [p for p in test_paths if Path(p).exists()]
    
    if not existing_paths:
        print(json.dumps({'unit_tests': [], 'skipped': [], 'error': 'no_test_paths'}))
        sys.exit(0)
    
    unit_tests, skipped = find_unit_tests(existing_paths)
    print(json.dumps({'unit_tests': unit_tests, 'skipped': skipped}))
'''

