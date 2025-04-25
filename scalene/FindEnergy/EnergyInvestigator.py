import pynvml
import cpuinfo
import requests
import torch


def get_cpu_name():
    info = cpuinfo.get_cpu_info()
    return info.get("brand_raw", "Unknown CPU")


get_cpu_name()
def query_tdp_from_backend():
    cpu_name = get_cpu_name()
    response = requests.post("http://fennecs.duckdns.org:5000/get-tdp", json={"cpu_name": cpu_name})
    if response.status_code == 200:
        return response.json().get('tdp')
    else:
        print("Error:", response.text)

def get_gpu_max_power_limit():
    """
    Retrieve the power limits for all available GPU devices.
    
    Returns:
        list: List of dictionaries containing GPU index and power limit in watts
    """
    gpu_power_limits = []
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for gpu_index in range(device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)                
                power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000
                device_name = pynvml.nvmlDeviceGetName(handle)
                gpu_power_limits.append({
                    "index": gpu_index,
                    "name": device_name,
                    "power_limit": power_limit
                })
            except pynvml.NVMLError as error:
                print(f"Error retrieving info for GPU {gpu_index}: {error}")
        return gpu_power_limits
    except pynvml.NVMLError as error:
        print(f"Error initializing NVML: {error}")
        return []
    finally:
        pynvml.nvmlShutdown()


