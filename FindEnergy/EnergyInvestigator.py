import wmi
import pynvml



def get_cpu_tdp():
    intel_core_processors = {
    "10th Gen": {
        "Desktop": {
                
                "Core i3-10100":   {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                "Core i3-10100F":  {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                "Core i3-10300":   {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                "Core i3-10320":   {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                
                "Core i5-10400":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-10400F":  {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-10500":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-10600":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-10600K":  {"Cores": 6, "Threads": 12, "TDP (W)": 125},
                "Core i5-10600KF": {"Cores": 6, "Threads": 12, "TDP (W)": 125},
                
                "Core i7-10700":   {"Cores": 8, "Threads": 16, "TDP (W)": 65},
                "Core i7-10700K":  {"Cores": 8, "Threads": 16, "TDP (W)": 125},
                "Core i7-10700KF": {"Cores": 8, "Threads": 16, "TDP (W)": 125},
                
                "Core i9-10900":   {"Cores": 10, "Threads": 20, "TDP (W)": 65},
                "Core i9-10900K":  {"Cores": 10, "Threads": 20, "TDP (W)": 125},
                "Core i9-10900KF": {"Cores": 10, "Threads": 20, "TDP (W)": 125},
            
        },
        "Mobile": {
                "Core i5-10300H":   {"Cores": 4, "Threads": 8,  "TDP (W)": 45},
                "Core i7-10750H":   {"Cores": 6, "Threads": 12, "TDP (W)": 45},
                "Core i7-10875H":   {"Cores": 8, "Threads": 16, "TDP (W)": 45},
                "Core i9-10980HK":  {"Cores": 8, "Threads": 16, "TDP (W)": 45},
            
        }
    },
    "11th Gen": {
        "Desktop": {
                
                "Core i3-11100":   {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                "Core i3-11100B":  {"Cores": 4, "Threads": 8,  "TDP (W)": 65},
                "Core i3-11100T":  {"Cores": 4, "Threads": 8,  "TDP (W)": 35},
                
                "Core i5-11400":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-11400F":  {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-11500":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-11600":   {"Cores": 6, "Threads": 12, "TDP (W)": 65},
                "Core i5-11600K":  {"Cores": 6, "Threads": 12, "TDP (W)": 125},
                "Core i5-11600KF": {"Cores": 6, "Threads": 12, "TDP (W)": 125},
               
                "Core i7-11700":   {"Cores": 8, "Threads": 16, "TDP (W)": 65},
                "Core i7-11700K":  {"Cores": 8, "Threads": 16, "TDP (W)": 125},
                "Core i7-11700KF": {"Cores": 8, "Threads": 16, "TDP (W)": 125},
              
                "Core i9-11900":   {"Cores": 8, "Threads": 16, "TDP (W)": 65},
                "Core i9-11900K":  {"Cores": 8, "Threads": 16, "TDP (W)": 125},
                "Core i9-11900KF": {"Cores": 8, "Threads": 16, "TDP (W)": 125},
            
        },
        "Mobile": {
                "Core i7-11800H":  {"Cores": 8, "Threads": 16, "TDP (W)": 45},
                "Core i5-11400H":  {"Cores": 6, "Threads": 12, "TDP (W)": 45},
                "Core i7-11370H":  {"Cores": 4, "Threads": 8,  "TDP (W)": 35},
            
        }
    },
    "12th Gen": {
        "Desktop": {
               
                "Core i3-12100":   {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 60},
                "Core i3-12100F":  {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 58},
                "Core i3-12100T":  {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 35},
               
                "Core i5-12400":    {"Performance Cores": 6, "Efficiency Cores": 0, "Threads": 12, "TDP (W)": 65},
                "Core i5-12400F":   {"Performance Cores": 6, "Efficiency Cores": 0, "Threads": 12, "TDP (W)": 65},
                "Core i5-12600K":   {"Performance Cores": 6, "Efficiency Cores": 4, "Threads": 16, "TDP (W)": 125},
                "Core i5-12600KF":  {"Performance Cores": 6, "Efficiency Cores": 4, "Threads": 16, "TDP (W)": 125},
                
                "Core i7-12700":    {"Performance Cores": 8, "Efficiency Cores": 4, "Threads": 20, "TDP (W)": 65},
                "Core i7-12700F":   {"Performance Cores": 8, "Efficiency Cores": 4, "Threads": 20, "TDP (W)": 65},
                "Core i7-12700K":   {"Performance Cores": 8, "Efficiency Cores": 4, "Threads": 20, "TDP (W)": 125},
                "Core i7-12700KF":  {"Performance Cores": 8, "Efficiency Cores": 4, "Threads": 20, "TDP (W)": 125},
                
                "Core i9-12900":    {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 65},
                "Core i9-12900F":   {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 65},
                "Core i9-12900K":   {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 125},
                "Core i9-12900KF":  {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 125},
            
        },
        "Mobile": {
                "Core i9-12900HK": {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 45},
                "Core i7-12700H":  {"Performance Cores": 6, "Efficiency Cores": 8, "Threads": 20, "TDP (W)": 45},
                "Core i5-12500H":  {"Performance Cores": 4, "Efficiency Cores": 8, "Threads": 16, "TDP (W)": 45},
            
        }
    },
    "13th Gen": {
        "Desktop": {
            
              
                "Core i3-13100":   {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 60},
                "Core i3-13100F":  {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 58},
                "Core i3-13100T":  {"Performance Cores": 4, "Efficiency Cores": 0, "Threads": 8,  "TDP (W)": 35},
               
                "Core i5-13400":    {"Performance Cores": 6, "Efficiency Cores": 4, "Threads": 16, "TDP (W)": 65},
                "Core i5-13400F":   {"Performance Cores": 6, "Efficiency Cores": 4, "Threads": 16, "TDP (W)": 65},
                "Core i5-13600K":   {"Performance Cores": 6, "Efficiency Cores": 8, "Threads": 20, "TDP (W)": 125},
                "Core i5-13600KF":  {"Performance Cores": 6, "Efficiency Cores": 8, "Threads": 20, "TDP (W)": 125},
                
                "Core i7-13700":    {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 65},
                "Core i7-13700F":   {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 65},
                "Core i7-13700K":   {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 125},
                "Core i7-13700KF":  {"Performance Cores": 8, "Efficiency Cores": 8, "Threads": 24, "TDP (W)": 125},
                
                "Core i9-13900":    {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 65},
                "Core i9-13900F":   {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 65},
                "Core i9-13900K":   {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 125},
                "Core i9-13900KF":  {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 125},
            
        },
        "Mobile": {
            
                "Core i9-13980HX": {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 55},
                "Core i9-13900H":  {"Performance Cores": 8, "Efficiency Cores": 16, "Threads": 32, "TDP (W)": 45},
                "Core i7-13700HX": {"Performance Cores": 8, "Efficiency Cores": 8,  "Threads": 24, "TDP (W)": 45},
                "Core i7-13700H":  {"Performance Cores": 8, "Efficiency Cores": 8,  "Threads": 24, "TDP (W)": 45},
                "Core i5-13500HX": {"Performance Cores": 6, "Efficiency Cores": 8,  "Threads": 20, "TDP (W)": 45},
                "Core i5-13500H":  {"Performance Cores": 6, "Efficiency Cores": 8,  "Threads": 20, "TDP (W)": 45},
            
        }
    }
    }

    c = wmi.WMI()
    for processor in c.Win32_Processor():
        print(f"CPU Name: {processor.Name}")
        splitName = processor.Name.split()
        print(splitName)
        generationNum = splitName[0] + " " + splitName[1]
        cpu = "Core " + splitName[4]
        TDP = 0
        notFound = True
        try:
            TDP = intel_core_processors[generationNum]['Desktop'][cpu]['TDP (W)']
            notFound = False
        except KeyError:
            print(f"CPU isn't a desktop model")
        try:
            if(notFound):
                TDP = intel_core_processors[generationNum]['Mobile'][cpu]['TDP (W)']
                notFound = False
        except KeyError:
            print(f"CPU isn't a mobile/laptop model")
        
        if(notFound):
            print("CPU not found in database. Update this method's database for processing of your CPU model")
        else:
             print(str(TDP) + "W")
             return TDP

get_cpu_tdp()
    
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

