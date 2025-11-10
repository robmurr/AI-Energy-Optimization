#!/usr/bin/env python3
"""
Fetch Commits Pipeline
Orchestrates the complete commit mining pipeline across multiple frameworks.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import json


class PipelineRunner:
    """Manages the execution of the commit mining pipeline."""
    
    def __init__(self):
        """Initialize the pipeline runner."""
        # Script is in commit_execution/, commit_mining/ is sibling directory
        self.script_dir = Path(__file__).parent
        self.commit_mining_dir = self.script_dir.parent / 'commit_mining'
        self.commit_storage_dir = self.script_dir / 'commit_storage'
        
        self.frameworks = ['matplotlib', 'tensorflow', 'pytorch']
        
        # Pipeline steps in order
        self.pipeline_steps = [
            'mine_repos.py',
            'validate_test_presence.py',
            'extract_commits.py',
            'map_tests_to_commits.py',
            'checkout_commits.py'
        ]
    
    def run_script(self, script_path, working_dir):
        """
        Run a Python script as a subprocess.
        
        Args:
            script_path: Path to the script to run
            working_dir: Directory to run the script from
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        script_path = Path(script_path)
        working_dir = Path(working_dir)
        
        if not script_path.exists():
            return False, "", f"Script not found: {script_path}"
        
        print(f"  Running {script_path.name}...", end=" ", flush=True)
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout per script
            )
            
            if result.returncode == 0:
                print("OK")
                return True, result.stdout, result.stderr
            else:
                print(f"FAILED (code {result.returncode})")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            print("TIMEOUT (1 hour)")
            return False, "", "Timeout after 1 hour"
            
        except Exception as e:
            print(f"ERROR ({type(e).__name__})")
            return False, "", str(e)
    
    def check_framework_setup(self, framework_dir):
        """
        Check if a framework directory has all required scripts.
        
        Args:
            framework_dir: Path to framework directory
            
        Returns:
            Tuple of (is_ready: bool, missing_scripts: list)
        """
        framework_dir = Path(framework_dir)
        missing = []
        
        for script in self.pipeline_steps:
            script_path = framework_dir / script
            if not script_path.exists():
                missing.append(script)
        
        return len(missing) == 0, missing
    
    def run_framework_pipeline(self, framework_name):
        """
        Run the complete pipeline for a single framework.
        
        Args:
            framework_name: Name of the framework (e.g., 'matplotlib')
            
        Returns:
            Tuple of (success: bool, checkouts_dir: Path or None)
        """
        print(f"\n[{framework_name.upper()}]")
        
        framework_dir = self.commit_mining_dir / framework_name
        
        # Check if framework directory exists
        if not framework_dir.exists():
            print(f"  ERROR: Directory not found")
            return False, None
        
        # Check if all required scripts are present
        is_ready, missing = self.check_framework_setup(framework_dir)
        if not is_ready:
            print(f"  SKIP: Missing scripts - {', '.join(missing)}")
            return False, None
        
        # Run each pipeline step in order
        for script_name in self.pipeline_steps:
            script_path = framework_dir / script_name
            success, stdout, stderr = self.run_script(script_path, framework_dir)
            
            if not success:
                return False, None
        
        # Check if checkouts were created
        checkouts_dir = framework_dir / 'checkouts'
        if not checkouts_dir.exists() or not any(checkouts_dir.iterdir()):
            print(f"  No checkouts created")
            return True, None  # Not an error, just no commits to checkout
        
        print(f"  Pipeline completed successfully")
        return True, checkouts_dir
    
    def collect_checkouts(self, framework_checkouts):
        """
        Collect all checkouts from different frameworks into commit_storage directory.
        
        Args:
            framework_checkouts: Dict mapping framework names to their checkout directories
        """
        print("\nCollecting checkouts...")
        
        # Create commit_storage directory
        self.commit_storage_dir.mkdir(exist_ok=True)
        
        collection_summary = {
            'timestamp': datetime.now().isoformat(),
            'storage_location': str(self.commit_storage_dir.absolute()),
            'frameworks': {}
        }
        
        total_collected = 0
        
        for framework, checkouts_dir in framework_checkouts.items():
            if checkouts_dir is None:
                continue
            
            framework_output = self.commit_storage_dir / framework
            framework_output.mkdir(exist_ok=True)
            
            collected_count = 0
            failed_count = 0
            
            # Copy each checkout directory
            for checkout_item in checkouts_dir.iterdir():
                if not checkout_item.is_dir():
                    continue
                
                target_path = framework_output / checkout_item.name
                
                try:
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    
                    shutil.copytree(checkout_item, target_path)
                    collected_count += 1
                    total_collected += 1
                    
                except Exception as e:
                    failed_count += 1
            
            print(f"  {framework}: {collected_count} checkouts collected")
            
            collection_summary['frameworks'][framework] = {
                'status': 'success',
                'collected': collected_count,
                'failed': failed_count,
                'source_dir': str(checkouts_dir),
                'target_dir': str(framework_output)
            }
        
        collection_summary['total_collected'] = total_collected
        
        # Save collection summary
        summary_path = self.commit_storage_dir / 'collection_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(collection_summary, f, indent=2)
        
        print(f"\nTotal collected: {total_collected} checkouts")
        print(f"Storage: {self.commit_storage_dir}")
        
        return total_collected
    
    def run_full_pipeline(self):
        """
        Run the complete pipeline for all frameworks.
        
        Returns:
            Dict with results for each framework
        """
        print("="*60)
        print("COMMIT MINING PIPELINE")
        print("="*60)
        
        # Verify commit_mining directory exists
        if not self.commit_mining_dir.exists():
            print(f"ERROR: commit_mining directory not found")
            return {}
        
        results = {}
        framework_checkouts = {}
        
        # Run pipeline for each framework
        for framework in self.frameworks:
            success, checkouts_dir = self.run_framework_pipeline(framework)
            results[framework] = success
            
            if success and checkouts_dir is not None:
                framework_checkouts[framework] = checkouts_dir
        
        # Collect all checkouts
        if framework_checkouts:
            total_collected = self.collect_checkouts(framework_checkouts)
        else:
            print("\nNo checkouts to collect")
            total_collected = 0
        
        # Print final summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        for framework, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  {framework}: {status}")
        
        print(f"\nTotal: {successful}/{len(results)} successful, {total_collected} checkouts")
        print("="*60)
        
        return results


def main():
    """Main entry point for the pipeline."""
    
    try:
        runner = PipelineRunner()
        results = runner.run_full_pipeline()
        
        # Exit with error code if any framework failed
        if not all(results.values()):
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n\nFatal error in pipeline: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
