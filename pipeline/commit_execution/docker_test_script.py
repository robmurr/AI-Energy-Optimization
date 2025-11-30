#!/usr/bin/env python3

from test_classifier import generate_classifier_script
from dependency_resolver import generate_resolver_script


def generate_test_script(commit_hash: str, normalized_test_files: str) -> str:
    classifier_script = generate_classifier_script()
    resolver_script = generate_resolver_script()
    
    test_script_content = f"""#!/bin/bash
                                set +e

                                cd /workspace/repo

                                echo "=== DEBUG: Container Environment ===" >&2
                                echo "Current directory: $(pwd)" >&2
                                if [ -d "/workspace/repo" ]; then
                                    echo "✓ /workspace/repo exists" >&2
                                    ls -la /workspace/repo | head -20 >&2
                                    echo "" >&2
                                    echo "Looking for test directories:" >&2
                                    find /workspace/repo -maxdepth 2 -type d -name "*test*" 2>/dev/null | head -10 >&2
                                else
                                    echo "✗ ERROR: /workspace/repo does not exist!" >&2
                                    exit 1
                                fi
                                echo "" >&2

                                CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
                                if [ "$CURRENT_COMMIT" != "{commit_hash}" ]; then
                                    echo "Warning: Expected commit {commit_hash[:8]}, but HEAD is ${{CURRENT_COMMIT:0:8}}" >&2
                                fi

                                echo "Running tests on commit {commit_hash[:8]}..." >&2

                                is_framework_repo() {{
                                    if [ -d "torch/csrc" ] || [ -d "caffe2" ]; then
                                        echo "pytorch" && return 0
                                    fi
                                    if [ -d "tensorflow/core" ] || [ -d "tensorflow/python" ]; then
                                        echo "tensorflow" && return 0
                                    fi
                                    if [ -d "jax/_src" ] && [ -f "jax/__init__.py" ]; then
                                        echo "jax" && return 0
                                    fi
                                    if [ -f "setup.py" ]; then
                                        if grep -q "name.*=.*['\"]torch['\"]" setup.py 2>/dev/null; then
                                            echo "pytorch" && return 0
                                        fi
                                        if grep -q "name.*=.*['\"]tensorflow['\"]" setup.py 2>/dev/null; then
                                            echo "tensorflow" && return 0
                                        fi
                                    fi
                                    return 1
                                }}

                                install_dependencies() {{
                                    cd /workspace/repo
                                    
                                    FRAMEWORK=$(is_framework_repo)
                                    if [ -n "$FRAMEWORK" ]; then
                                        echo "=== DETECTED FRAMEWORK REPOSITORY: $FRAMEWORK ===" >&2
                                        echo "Framework repositories require full source compilation (hours of build time)" >&2
                                        echo "Cannot test commit-specific code without compilation" >&2
                                        echo "RESULT: FRAMEWORK_REPO_SKIP:$FRAMEWORK"
                                        return 1
                                    fi
                                    
                                    if [ -f "requirements.txt" ]; then
                                        echo "Installing from requirements.txt..." >&2
                                        pip install --no-cache-dir -r requirements.txt 2>&1 || echo "Warning: Some requirements failed to install" >&2
                                    fi
                                    
                                    for req_file in "requirements-test.txt" "requirements_test.txt" "test-requirements.txt" "test_requirements.txt" \
                                                    "requirements-dev.txt" "requirements_dev.txt" "dev-requirements.txt" "dev_requirements.txt" \
                                                    "tests/requirements.txt" "test/requirements.txt" "requirements/test.txt" "requirements/dev.txt"; do
                                        if [ -f "$req_file" ]; then
                                            echo "Installing from $req_file..." >&2
                                            pip install --no-cache-dir -r "$req_file" 2>&1 || echo "Warning: Some requirements from $req_file failed to install" >&2
                                        fi
                                    done
                                    
                                    if [ -f "setup.py" ]; then
                                        echo "Installing from setup.py..." >&2
                                        timeout 120 pip install --no-cache-dir -e ".[test,tests,dev,testing]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e ".[test]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e ".[dev]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e . 2>&1 || \
                                        timeout 120 pip install --no-cache-dir . 2>&1 || \
                                        echo "Warning: setup.py installation failed or timed out" >&2
                                    fi
                                    
                                    if [ -f "pyproject.toml" ]; then
                                        echo "Installing from pyproject.toml..." >&2
                                        timeout 120 pip install --no-cache-dir -e ".[test,tests,dev,testing]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e ".[test]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e ".[dev]" 2>&1 || \
                                        timeout 120 pip install --no-cache-dir -e . 2>&1 || \
                                        timeout 120 pip install --no-cache-dir . 2>&1 || \
                                        echo "Warning: pyproject.toml installation failed or timed out" >&2
                                    fi
                                    
                                    echo "Installing common test dependencies..." >&2
                                    pip install --no-cache-dir pytest pytest-cov opencv-python-headless numpy scipy pillow 2>&1 || echo "Warning: Some common test dependencies failed to install" >&2
                                    
                                    echo "Dependency installation complete" >&2
                                }}

                                install_dependencies

                                cat > /tmp/classify_tests.py << 'CLASSIFIER_EOF'
                                {classifier_script}
                                CLASSIFIER_EOF

                                cat > /tmp/resolve_deps.py << 'RESOLVER_EOF'
                                {resolver_script}
                                RESOLVER_EOF

                                TEST_FILES="{normalized_test_files}"
                                MAX_DEPENDENCY_RETRIES=3

                                try_resolve_import_error() {{
                                    local test_output="$1"
                                    
                                    if echo "$test_output" | grep -q "ModuleNotFoundError\\|ImportError"; then
                                        echo "=== DETECTED IMPORT ERROR, ATTEMPTING AUTO-RESOLVE ===" >&2
                                        
                                        RESOLVE_RESULT=$(echo "$test_output" | python /tmp/resolve_deps.py 2>/dev/null)
                                        
                                        if [ -n "$RESOLVE_RESULT" ]; then
                                            SUCCESS=$(echo "$RESOLVE_RESULT" | python -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
                                            PACKAGE=$(echo "$RESOLVE_RESULT" | python -c "import sys,json; print(json.load(sys.stdin).get('package', ''))" 2>/dev/null)
                                            MODULE=$(echo "$RESOLVE_RESULT" | python -c "import sys,json; print(json.load(sys.stdin).get('module', ''))" 2>/dev/null)
                                            
                                            if [ "$SUCCESS" == "True" ]; then
                                                echo "✓ Auto-installed missing dependency: $MODULE -> $PACKAGE" >&2
                                                return 0
                                            else
                                                echo "✗ Could not auto-resolve: $MODULE" >&2
                                                return 1
                                            fi
                                        fi
                                    fi
                                    
                                    return 1
                                }}

                                run_unit_tests() {{
                                    local test_paths="$1"
                                    
                                    echo "=== CLASSIFYING TESTS ===" >&2
                                    
                                    if [ -z "$test_paths" ] || [ "$test_paths" == "None" ]; then
                                        test_paths="tests test"
                                    fi
                                    
                                    IFS=';' read -ra PATHS <<< "$test_paths"
                                    EXISTING_PATHS=""
                                    for p in "${{PATHS[@]}}"; do
                                        p=$(echo "$p" | xargs | tr '\\\\' '/')
                                        if [ -e "$p" ]; then
                                            EXISTING_PATHS="$EXISTING_PATHS $p"
                                        fi
                                    done
                                    
                                    if [ -z "$EXISTING_PATHS" ]; then
                                        for fallback in "tests" "test"; do
                                            if [ -d "$fallback" ]; then
                                                EXISTING_PATHS="$fallback"
                                                break
                                            fi
                                        done
                                    fi
                                    
                                    if [ -z "$EXISTING_PATHS" ]; then
                                        echo "No test directories found" >&2
                                        return 1
                                    fi
                                    
                                    echo "Analyzing test paths: $EXISTING_PATHS" >&2
                                    
                                    CLASSIFICATION=$(python /tmp/classify_tests.py $EXISTING_PATHS 2>/dev/null)
                                    
                                    if [ -z "$CLASSIFICATION" ]; then
                                        echo "Classification failed, running all tests" >&2
                                        python -m pytest $EXISTING_PATHS -v --tb=short 2>&1 || true
                                        return
                                    fi
                                    
                                    UNIT_TESTS=$(echo "$CLASSIFICATION" | python -c "import sys,json; d=json.load(sys.stdin); print(' '.join(d.get('unit_tests',[])))" 2>/dev/null)
                                    SKIPPED=$(echo "$CLASSIFICATION" | python -c "import sys,json; d=json.load(sys.stdin); s=d.get('skipped',[]); print(len(s))" 2>/dev/null)
                                    
                                    echo "=== TEST CLASSIFICATION RESULTS ===" >&2
                                    echo "Unit tests found: $(echo $UNIT_TESTS | wc -w)" >&2
                                    echo "Integration tests skipped: $SKIPPED" >&2
                                    
                                    if [ -n "$SKIPPED" ] && [ "$SKIPPED" != "0" ]; then
                                        echo "Skipped integration tests:" >&2
                                        echo "$CLASSIFICATION" | python -c "import sys,json; d=json.load(sys.stdin); [print(f'  - {{x[\"path\"]}}: {{x[\"reason\"]}}') for x in d.get('skipped',[])]" 2>/dev/null >&2
                                    fi
                                    
                                    if [ -z "$UNIT_TESTS" ]; then
                                        echo "No unit tests found after classification" >&2
                                        echo "RESULT: NO_UNIT_TESTS_FOUND"
                                        return 1
                                    fi
                                    
                                    echo "=== RUNNING UNIT TESTS ===" >&2
                                    echo "Running: $UNIT_TESTS" >&2
                                    
                                    RETRY_COUNT=0
                                    while [ $RETRY_COUNT -lt $MAX_DEPENDENCY_RETRIES ]; do
                                        TEST_OUTPUT=$(python -m pytest $UNIT_TESTS -v --tb=short 2>&1)
                                        TEST_EXIT_CODE=$?
                                        
                                        if echo "$TEST_OUTPUT" | grep -q "ModuleNotFoundError\\|ImportError.*No module"; then
                                            echo "=== IMPORT ERROR DETECTED (Attempt $((RETRY_COUNT + 1))/$MAX_DEPENDENCY_RETRIES) ===" >&2
                                            
                                            if try_resolve_import_error "$TEST_OUTPUT"; then
                                                RETRY_COUNT=$((RETRY_COUNT + 1))
                                                echo "Retrying tests after dependency installation..." >&2
                                                continue
                                            else
                                                echo "Could not resolve import error, proceeding with output" >&2
                                                break
                                            fi
                                        else
                                            break
                                        fi
                                    done
                                    
                                    echo "$TEST_OUTPUT"
                                    
                                    echo "=== TEST EXECUTION COMPLETE ===" >&2
                                    echo "Exit code: $TEST_EXIT_CODE" >&2
                                    echo "Dependency resolution attempts: $RETRY_COUNT" >&2
                                    
                                    return $TEST_EXIT_CODE
                                }}

                                run_unit_tests "$TEST_FILES"
                                """
    
    return test_script_content
