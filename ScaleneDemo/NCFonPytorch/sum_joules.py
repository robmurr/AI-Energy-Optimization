import json
from pprint import pprint

# Load the JSON file (replace 'your_file.json' with the actual path)
with open('NCF_profile.json', 'r') as f:
    data = json.load(f)

# Extract the 'files' dictionary
files_data = data.get('files', {})

# Target file key
target_file = "/home/cc/GreenAI/AI-Energy-Optimization/ScaleneDemo/NCFonPytorch/NCF/ncf.py"

total_elapsed = 0.0
total_gpu_joule = 0.0

if target_file in files_data:
    file_entry = files_data[target_file]
    # print(f"Found data for {target_file}")

    # Helper to check if we should include this entry
    def should_include(entry):
        n_gpu = entry.get('n_gpu_percent')
        if n_gpu is not None and n_gpu >= 99.0:
            #print(f" - Skipping entry (n_gpu_percent= {n_gpu}): {entry.get('line') or entry.get('name') or 'top-level'}GPU Joule Consumption: {entry.get('gpu_joule_usage')}\n\n")
            return False
        return True

    # Top-level (per-file) totals
    if should_include(file_entry):
        if 'elapsed_time_sec' in file_entry:
            added = file_entry['elapsed_time_sec']
            total_elapsed += added
            #print(f" - Added top-level elapsed_time_sec: {added}")
        if 'gpu_joule_usage' in file_entry:
            added = file_entry['gpu_joule_usage']
            total_gpu_joule += added
            #print(f" - Added top-level gpu_joule_usage: {added}")

    # Per-line or per-function details
    if 'lines' in file_entry:
        lines = file_entry['lines']
        for line_info in lines:
            if should_include(line_info):
                if 'elapsed_time_sec' in line_info:
                    added = line_info['elapsed_time_sec']
                    total_elapsed += added
                if 'gpu_joule_usage' in line_info:
                    added = line_info['gpu_joule_usage']
                    total_gpu_joule += added
                    if added > 1.0:
                        print(f"{line_info['line']} contributed to: {added}")
        print(f" - Processed {len(lines)} line entries (skipped where n_gpu_percent=100.0)")
    else:
        print(" - No 'lines' or 'functions' section found; only top-level totals processed.")

else:
    print(f"File {target_file} not found in the JSON 'files' section.")

# Final summed results
print("\n=== SUMMED RESULTS FOR ncf.py (excluding n_gpu_percent>99.0) ===")
print(f"Total elapsed_time_sec: {total_elapsed:.6f}")
print(f"Total gpu_joule_usage: {total_gpu_joule:.6f}")

