import json
from pprint import pprint

# Load the JSON file (replace with your actual path)
with open('msft_resnet50_profile.json', 'r') as f:
    data = json.load(f)

# Extract the 'files' dictionary
files_data = data.get('files', {})

# Target file key
target_file = "/home/cc/AI-Energy-Optimization/scalene/resnet50_coco_dir.py"

total_elapsed = 0.0
total_gpu_joule = 0.0
total_cpu_joule = 0.0  # NEW

if target_file in files_data:
    file_entry = files_data[target_file]

    # Helper to check if we should include this entry
    def should_include(entry):
        n_gpu = entry.get('n_gpu_percent')
        if n_gpu is not None and n_gpu >= 99.0:
            print(
                f" - Skipping entry (n_gpu_percent={n_gpu}): "
                f"{entry.get('line') or entry.get('name') or 'top-level'} | "
                f"GPU Joule: {entry.get('gpu_joule_usage')} | "
                f"CPU Joule: {entry.get('cpu_joule_usage')}\n"
            )
            return False
        return True

    # Top-level (per-file) totals
    if should_include(file_entry):
        if 'elapsed_time_sec' in file_entry:
            total_elapsed += file_entry['elapsed_time_sec']
        if 'gpu_joule_usage' in file_entry:
            total_gpu_joule += file_entry['gpu_joule_usage']
        if 'cpu_joule_usage' in file_entry:  # NEW
            total_cpu_joule += file_entry['cpu_joule_usage']

    # Per-line details (mirror GPU logic)
    if 'lines' in file_entry:
        lines = file_entry['lines']
        for line_info in lines:
            if should_include(line_info):
                if 'elapsed_time_sec' in line_info:
                    total_elapsed += line_info['elapsed_time_sec']
                if 'gpu_joule_usage' in line_info:
                    total_gpu_joule += line_info['gpu_joule_usage']
                if 'cpu_joule_usage' in line_info:  # NEW
                    total_cpu_joule += line_info['cpu_joule_usage']
        print(f" - Processed {len(lines)} line entries.")

# Final totals
print("\n=== Totals (resnet50_coco_dir.py only) ===")
print(f"Total elapsed time (s): {total_elapsed:.6f}")
print(f"Total GPU joules:       {total_gpu_joule:.6f}")
print(f"Total CPU joules:       {total_cpu_joule:.6f}")  # NEW
