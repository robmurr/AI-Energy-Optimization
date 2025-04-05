
# GPU TDP Finder

This project helps you find the maximum power limit (TDP) of your Nvidia GPU using the `pynvml` package. The script connects to your GPU and retrieves the maximum power limit (in watts) for the specified GPU. It supports Nvidia GPUs and requires the `pynvml` package.

## Requirements

- **Python 3.11+**
- **pynvml**: A Python binding for Nvidia's Management Library (NVML), used to interact with Nvidia GPUs.

You can install the required package by running:

```bash
pip install pynvml
```

## How to Execute the Script

1. **Clone or Download the Repository**

   Ensure that you have the `EnergyInvestigator.py` script on your local machine.

2. **Run the Script**

   Execute the script by running the following command in your terminal:

   ```bash
   python3 EnergyInvestigator.py
   ```

   This will:

   - Initialize the Nvidia Management Library (NVML)
   - Retrieve the maximum power limit (TDP) for the GPU at index `0` (or a different index, if specified)
   - Print the TDP in watts


3. **Expected Output**

   The script will output the maximum power limit (TDP) of the GPU in watts. For example:

   ```bash
   Maximum GPU Power Limit: 250.0 watts
   ```

## Notes

- **Nvidia GPU Required**: This script only works with Nvidia GPUs that support NVML. Ensure that your system has the necessary Nvidia drivers installed and an Nvidia GPU available.
  
- **Multiple GPUs**: By default, the script queries the first GPU (index `0`). If you want to query a different GPU, simply change the script to the gpu index you want.
