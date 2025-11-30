#!/usr/bin/env python3
"""
Fetch Commits Pipeline
Orchestrates the complete commit mining pipeline across multiple frameworks.
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json


class PipelineRunner:
    """Manages the execution of the commit mining pipeline."""
    
    def __init__(self, root_dir=None):
        """
        Initialize the pipeline runner.
        
        Args:
            root_dir: Root directory for commit_mining. If None, uses parent of this script.
        """
        if root_dir is None:
            self.root_dir = Path(__file__).parent.parent
        else:
            self.root_dir = Path(root_dir)
        
        self.frameworks = ['matplotlib', 'tensorflow', 'pytorch']
        # Save to commit_storage in the same directory as this script
        self.output_dir = Path(__file__).parent / 'commit_storage'
        self.test_mappings_dir = Path(__file__).parent / 'test_mappings'
        self.test_mappings_dir.mkdir(exist_ok=True)
        
        # Pipeline steps in order
        self.pipeline_steps = [
            'mine_repos.py',
            'validate_test_presence.py',
            'extract_commits.py',
            'map_tests_to_commits.py',
            'checkout_commits.py'
        ]
        
        # Parameters
        self.max_repos = None
        self.max_commits = None
        self.skip_mine = False
        self.include_checkout = False
    
    def log(self, message, level="INFO"):
        """Print message without timestamps or brackets."""
        print(message)
    
    def run_script(self, script_path, working_dir):
        """
        Run a Python script as a subprocess.
        
        Args:
            script_path: Path to the script to run
            working_dir: Directory to run the script from
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        return self.run_script_with_args(script_path, working_dir, [])
    
    def run_script_with_args(self, script_path, working_dir, args):
        """
        Run a Python script as a subprocess with arguments.
        
        Args:
            script_path: Path to the script to run
            working_dir: Directory to run the script from
            args: List of command-line arguments
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        script_path = Path(script_path)
        working_dir = Path(working_dir)
        
        if not script_path.exists():
            return False, "", f"Script not found: {script_path}"
        
        cmd_str = f"{script_path.name} {' '.join(args)}" if args else script_path.name
        self.log(f"Running {cmd_str} in {working_dir.name}/")
        
        try:
            cmd = [sys.executable, str(script_path)] + args
            result = subprocess.run(
                cmd,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout per script
            )
            
            if result.returncode == 0:
                self.log(f"Successfully completed {script_path.name}")
                return True, result.stdout, result.stderr
            else:
                self.log(f"Script failed with return code {result.returncode}: {script_path.name}")
                if result.stderr:
                    self.log(f"Error: {result.stderr}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            error_msg = f"Script timed out after 1 hour: {script_path.name}"
            return False, "", error_msg
            
        except Exception as e:
            error_msg = f"Exception while running {script_path.name}: {type(e).__name__}: {str(e)}"
            return False, "", error_msg
    
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
        framework_dir = self.root_dir / "commit_mining" /framework_name
        
        self.log(f"\nStarting pipeline for {framework_name.upper()}")
        
        # Check if framework directory exists
        if not framework_dir.exists():
            self.log(f"Framework directory not found: {framework_dir}")
            return False, None
        
        # Check if all required scripts are present
        is_ready, missing = self.check_framework_setup(framework_dir)
        if not is_ready:
            self.log(f"Missing required scripts in {framework_name}: {', '.join(missing)}")
            return False, None
        
        # Run each pipeline step in order
        for step_num, script_name in enumerate(self.pipeline_steps, 1):
            # Skip mining if requested
            if script_name == 'mine_repos.py' and self.skip_mine:
                self.log(f"Step {step_num}/{len(self.pipeline_steps)}: {script_name} (SKIPPED)")
                continue
            
            # Skip checkout if not requested
            if script_name == 'checkout_commits.py' and not self.include_checkout:
                self.log(f"Step {step_num}/{len(self.pipeline_steps)}: {script_name} (SKIPPED)")
                continue
            
            self.log(f"Step {step_num}/{len(self.pipeline_steps)}: {script_name}")
            
            script_path = framework_dir / script_name
            
            # Build command arguments
            cmd_args = []
            if script_name == 'mine_repos.py' and self.max_repos:
                cmd_args = ['--max', str(self.max_repos)]
            elif script_name == 'extract_commits.py' and self.max_commits:
                cmd_args = ['--max', str(self.max_commits), '--single']
            
            if cmd_args:
                # Run with arguments
                success, stdout, stderr = self.run_script_with_args(script_path, framework_dir, cmd_args)
            else:
                success, stdout, stderr = self.run_script(script_path, framework_dir)
            
            if not success:
                self.log(f"Pipeline failed at step {step_num} ({script_name}) for {framework_name}")
                return False, None
            
            # After map_tests_to_commits.py, copy the CSV to test_mappings/
            if script_name == 'map_tests_to_commits.py':
                self.collect_test_mapping(framework_name, framework_dir)
        
        # Only return checkouts if checkout_commits.py was actually run in this execution
        # (not from previous runs)
        if self.include_checkout:
            checkouts_dir = framework_dir / 'checkouts'
            if checkouts_dir.exists() and any(checkouts_dir.iterdir()):
                self.log(f"Successfully completed pipeline for {framework_name}")
                return True, checkouts_dir
        
        self.log(f"Successfully completed pipeline for {framework_name}")
        return True, None
    
    def collect_checkouts(self, framework_checkouts):
        """
        Collect all checkouts from different frameworks into a single directory.
        
        Args:
            framework_checkouts: Dict mapping framework names to their checkout directories
        """
        self.log("\nCollecting checkouts from all frameworks")
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        collection_summary = {
            'timestamp': datetime.now().isoformat(),
            'frameworks': {}
        }
        
        total_collected = 0
        
        for framework, checkouts_dir in framework_checkouts.items():
            if checkouts_dir is None:
                self.log(f"No checkouts to collect for {framework}")
                collection_summary['frameworks'][framework] = {
                    'status': 'no_checkouts',
                    'count': 0
                }
                continue
            
            collected_count = 0
            failed_count = 0
            
            # Copy each checkout directory directly to output_dir (no framework subdirectory)
            for checkout_item in checkouts_dir.iterdir():
                if not checkout_item.is_dir():
                    continue
                
                target_path = self.output_dir / checkout_item.name
                
                try:
                    if target_path.exists():
                        self.log(f"Removing existing checkout: {target_path.name}")
                        shutil.rmtree(target_path)
                    
                    shutil.copytree(checkout_item, target_path)
                    collected_count += 1
                    total_collected += 1
                    
                except Exception as e:
                    self.log(f"Failed to copy {checkout_item.name}: {str(e)}")
                    failed_count += 1
            
            self.log(f"Collected {collected_count} checkouts from {framework} (failed: {failed_count})")
            
            collection_summary['frameworks'][framework] = {
                'status': 'success',
                'collected': collected_count,
                'failed': failed_count,
                'source_dir': str(checkouts_dir)
            }
        
        collection_summary['total_collected'] = total_collected
        
        # Save collection summary
        summary_path = self.output_dir / 'collection_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(collection_summary, f, indent=2)
        
        self.log(f"Total checkouts collected: {total_collected}")
        self.log(f"Output directory: {self.output_dir.absolute()}")
        
        return total_collected
    
    def collect_test_mapping(self, framework_name, framework_dir):
        """
        Collect test mapping CSV from a framework and save to test_mappings/.
        
        Args:
            framework_name: Name of the framework
            framework_dir: Path to framework directory
        """
        test_mapping_file = framework_dir / 'test_mapping.csv'
        
        if not test_mapping_file.exists():
            self.log(f"Test mapping file not found for {framework_name}: {test_mapping_file}")
            return
        
        # Copy to test_mappings/ with framework prefix
        target_file = self.test_mappings_dir / f"{framework_name}_test_mapping.csv"
        
        try:
            shutil.copy2(test_mapping_file, target_file)
            self.log(f"Copied test mapping for {framework_name} to {target_file.name}")
        except Exception as e:
            self.log(f"Failed to copy test mapping for {framework_name}: {str(e)}")
    
    def run_full_pipeline(self):
        """
        Run the complete pipeline for all frameworks.
        
        Returns:
            Dict with results for each framework
        """
        self.log("=" * 70)
        self.log("STARTING COMMIT MINING PIPELINE")
        self.log("=" * 70)
        self.log(f"Root directory: {self.root_dir.absolute()}")
        self.log(f"Frameworks: {', '.join(self.frameworks)}")
        self.log("")
        
        results = {}
        framework_checkouts = {}
        
        # Run pipeline for each framework
        for framework in self.frameworks:
            success, checkouts_dir = self.run_framework_pipeline(framework)
            results[framework] = success
            
            if success and checkouts_dir is not None:
                framework_checkouts[framework] = checkouts_dir
            
            self.log("")  # Empty line between frameworks
        
        # Collect all checkouts
        if framework_checkouts:
            total_collected = self.collect_checkouts(framework_checkouts)
        else:
            self.log("No checkouts to collect from any framework")
            total_collected = 0
        
        # Print final summary
        self.log("\n" + "=" * 70)
        self.log("PIPELINE EXECUTION SUMMARY")
        self.log("=" * 70)
        
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        self.log(f"Frameworks processed: {len(results)}")
        self.log(f"Successful: {successful}")
        self.log(f"Failed: {failed}")
        self.log(f"Total checkouts collected: {total_collected}")
        
        for framework, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            self.log(f"  {framework}: {status}")
        
        self.log("=" * 70)
        self.log("Complete!")
        self.log("=" * 70)
        
        return results


def main():
    """Main entry point for the pipeline."""
    
    parser = argparse.ArgumentParser(
        description='Fetch commits and run test mapping pipeline across multiple frameworks'
    )
    parser.add_argument(
        '--max-repos',
        type=int,
        default=None,
        help='Maximum repositories to mine per framework (default: all)'
    )
    parser.add_argument(
        '--max-commits',
        type=int,
        default=None,
        help='Maximum commits per repository (default: all)'
    )
    parser.add_argument(
        '--skip-mine',
        action='store_true',
        help='Skip mining phase (use existing repos)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Include checkout phase'
    )
    parser.add_argument(
        '--root-dir',
        type=str,
        default=None,
        help='Root directory for commit_mining (default: parent of script directory)'
    )
    
    args = parser.parse_args()
    
    # Parse root directory
    if args.root_dir:
        root_dir = Path(args.root_dir)
        if not root_dir.exists():
            print(f"Error: Provided root directory does not exist: {root_dir}")
            return 1
    else:
        root_dir = None
    
    try:
        runner = PipelineRunner(root_dir)
        
        # Set parameters
        runner.max_repos = args.max_repos
        runner.max_commits = args.max_commits
        runner.skip_mine = args.skip_mine
        runner.include_checkout = args.full
        
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
