import pynvml
import cpuinfo
import requests
import torch


def get_cpu_name():
    info = cpuinfo.get_cpu_info()
    if torch.cuda.is_available():
        print("CUDA is available!")
        print(f"Number of GPUs: {torch.cuda.device_count()}")
        print(f"Current GPU: {torch.cuda.current_device()}")
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA is not available.")
    return info.get("brand_raw", "Unknown CPU")

get_cpu_name()
def query_tdp_from_backend():
    cpu_name = get_cpu_name()
    response = requests.post("http://fennecs.duckdns.org:5000/get-tdp", json={"cpu_name": cpu_name})
    if response.status_code == 200:
        return response.json().get('tdp')
    else:
        print("Error:", response.text)

    
def get_gpu_max_power_limit(gpu_index=0):
    """
    Retrieve the maximum power limit for a specified GPU device.
    
    Args:
        gpu_index (int, optional): Index of the GPU device. Defaults to 0.
    
    Returns:
        float: Maximum power limit in watts
    """
    try:
        pynvml.nvmlInit()
        
        # Get handle for the specified GPU
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        
        # Retrieve the maximum power limit
        max_power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000
        
        return max_power_limit
    
    except pynvml.NVMLError as error:
        print(f"Error retrieving GPU power limit: {error}")
        return None
    finally:
        # frees some resources
        pynvml.nvmlShutdown()


