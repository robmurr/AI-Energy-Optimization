import pynvml

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

max_power = get_gpu_max_power_limit()
if max_power is not None:
    print(f"Maximum GPU Power Limit: {max_power} watts")

