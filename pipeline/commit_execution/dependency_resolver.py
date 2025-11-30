#!/usr/bin/env python3
import re
import subprocess
import sys
from typing import Optional, List, Tuple

KNOWN_PACKAGE_MAPPINGS = {
    'cv2': ['opencv-python-headless', 'opencv-python', 'opencv-contrib-python'],
    'PIL': ['pillow', 'Pillow'],
    'sklearn': ['scikit-learn'],
    'skimage': ['scikit-image'],
    'yaml': ['pyyaml', 'PyYAML'],
    'bs4': ['beautifulsoup4'],
    'dotenv': ['python-dotenv'],
    'jwt': ['pyjwt', 'PyJWT'],
    'serial': ['pyserial'],
    'cv': ['opencv-python-headless', 'opencv-python'],
    'magic': ['python-magic'],
    'dateutil': ['python-dateutil'],
    'elasticsearch': ['elasticsearch'],
    'psycopg2': ['psycopg2-binary'],
    'MySQLdb': ['mysqlclient', 'mysql-connector-python'],
    'Image': ['pillow', 'Pillow'],
    'wx': ['wxPython'],
    'Crypto': ['pycryptodome', 'pycrypto'],
    'OpenSSL': ['pyopenssl'],
    'usb': ['pyusb'],
    'git': ['gitpython'],
    'colored': ['colored', 'termcolor'],
    'simplejson': ['simplejson'],
}


def parse_import_error(error_text: str) -> Optional[str]:
    patterns = [
        r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        r"ImportError: No module named ['\"]?([^'\";\s]+)['\"]?",
        r"ImportError: cannot import name ['\"]([^'\"]+)['\"]",
        r"ModuleNotFoundError: No module named '([^']+)'",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_text)
        if match:
            module = match.group(1).split('.')[0]
            return module
    
    return None


def get_package_candidates(module_name: str) -> List[str]:
    candidates = []
    
    if module_name in KNOWN_PACKAGE_MAPPINGS:
        candidates.extend(KNOWN_PACKAGE_MAPPINGS[module_name])
    
    candidates.append(module_name)
    candidates.append(module_name.lower())
    candidates.append(module_name.replace('_', '-'))
    candidates.append(f"py{module_name.lower()}")
    candidates.append(f"python-{module_name.lower()}")
    
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    
    return unique


def try_install_package(package_name: str, timeout: int = 120) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--no-cache-dir', package_name],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return True, f"Successfully installed {package_name}"
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Installation timed out for {package_name}"
    except Exception as e:
        return False, str(e)


def resolve_and_install(module_name: str) -> Tuple[bool, str, str]:
    candidates = get_package_candidates(module_name)
    
    for package in candidates:
        success, message = try_install_package(package)
        if success:
            return True, package, message
    
    return False, "", f"Could not install module '{module_name}' - tried: {candidates}"


def process_test_output(test_output: str) -> Tuple[bool, List[str]]:
    installed = []
    remaining_errors = []
    
    lines = test_output.split('\n')
    
    for i, line in enumerate(lines):
        if 'ModuleNotFoundError' in line or 'ImportError' in line:
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
            module = parse_import_error(context)
            
            if module:
                success, package, message = resolve_and_install(module)
                if success:
                    installed.append(f"{module} -> {package}")
                else:
                    remaining_errors.append(f"{module}: {message}")
    
    return len(installed) > 0, installed


def generate_resolver_script() -> str:
    return '''
        import re
        import subprocess
        import sys

        KNOWN_MAPPINGS = {
            'cv2': ['opencv-python-headless', 'opencv-python'],
            'PIL': ['pillow'],
            'sklearn': ['scikit-learn'],
            'skimage': ['scikit-image'],
            'yaml': ['pyyaml'],
            'bs4': ['beautifulsoup4'],
            'dotenv': ['python-dotenv'],
            'jwt': ['pyjwt'],
            'serial': ['pyserial'],
            'dateutil': ['python-dateutil'],
            'psycopg2': ['psycopg2-binary'],
            'Image': ['pillow'],
            'git': ['gitpython'],
            'Crypto': ['pycryptodome'],
            'OpenSSL': ['pyopenssl'],
        }

        def parse_error(text):
            patterns = [
                r"ModuleNotFoundError: No module named ['\\"']([^'\\"']+)['\\"']",
                r"ImportError: No module named ['\\"']?([^'\\"';\\s]+)",
            ]
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return m.group(1).split('.')[0]
            return None

        def get_candidates(module):
            candidates = KNOWN_MAPPINGS.get(module, [])
            candidates.extend([module, module.lower(), module.replace('_', '-'), f"py{module.lower()}", f"python-{module.lower()}"])
            return list(dict.fromkeys(candidates))

        def try_install(pkg):
            try:
                r = subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '-q', pkg], capture_output=True, timeout=120)
                return r.returncode == 0
            except:
                return False

        def resolve(error_output):
            module = parse_error(error_output)
            if not module:
                return False, None
            
            for pkg in get_candidates(module):
                if try_install(pkg):
                    return True, pkg
            return False, None

        if __name__ == '__main__':
            import json
            error_text = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[1] if len(sys.argv) > 1 else '')
            success, pkg = resolve(error_text)
            print(json.dumps({'success': success, 'package': pkg, 'module': parse_error(error_text)}))
        '''


if __name__ == '__main__':
    test_error = """
==================================== ERRORS ====================================
________________ ERROR collecting tests/compare/test_quality.py ________________
ImportError while importing test module '/workspace/repo/tests/compare/test_quality.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/compare/test_quality.py:9: in <module>
    from cv2 import imread, cvtColor, COLOR_BGR2RGB
E   ModuleNotFoundError: No module named 'cv2'
=========================== short test summary info ============================
ERROR tests/compare/test_quality.py
"""
    
    print("=" * 60)
    print("DEPENDENCY RESOLVER TEST")
    print("=" * 60)
    
    module = parse_import_error(test_error)
    print(f"\nParsed module from error: {module}")
    
    if module:
        candidates = get_package_candidates(module)
        print(f"Package candidates: {candidates}")
        
        print(f"\nAttempting to install '{module}'...")
        success, package, message = resolve_and_install(module)
        
        if success:
            print(f"SUCCESS: Installed {package}")
        else:
            print(f"FAILED: {message}")
    else:
        print("Could not parse module name from error")

