# Scalene Profiling Tool

A Python profiler that provides detailed performance metrics with enhanced elapsed time tracking.

## Overview

Scalene is a high-performance CPU, GPU, and memory profiler for Python that provides detailed metrics about your code's execution. This modified version includes an additional `elapsed_time_sec` parameter in the profiler output.

## Prerequisites

- Python
- Required dependencies (listed in requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/AI-Energy-Optimization.git
```

2. Navigate to the Scalene directory:
```bash
cd AI-Energy-Optimization/Task20_Scalene
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run Scalene on a Python script using the following command:

```bash
scalene test/testme.py
```

## Expected Output

When you run Scalene on the test script, you should observe:

1. A web interface will open in your browser (you can close this as the results are not relevant for this test).

2. The terminal will display:
   - Numbers 1-9
   - Text output "TESTME"
   - File path ['test/testme.py'] at the top of the output

3. A `profile.json` file will be generated in the Scalene folder, containing profiling data.

## Enhanced Features

This version of Scalene includes an additional parameter in the profiler output:

- `elapsed_time_sec`: This parameter is added to both the "functions" and "lines" sections of the JSON output, providing more detailed timing information compared to the standard Scalene output.

## File Structure

- `scalene/` - Main directory containing the Scalene profiler
- `test/testme.py` - Test script for verifying Scalene functionality
- `requirements.txt` - List of required Python packages
- `profile.json` - Generated profiler output (created after running Scalene)

## Troubleshooting

If you encounter issues:

- Ensure all dependencies are correctly installed
- Verify you're running the command from the correct directory
- Check Python version compatibility
