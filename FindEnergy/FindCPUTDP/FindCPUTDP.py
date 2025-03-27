import os, cpuinfo
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()



def get_cpu_name():
    """
    Returns a user-friendly CPU name string if possible,
    e.g. "Apple M1" or "Intel(R) Core(TM) i7-9750H".
    """
    info = cpuinfo.get_cpu_info()
    # Some keys to look for (depending on OS & CPU):
    #   'brand_raw', 'brand', 'arch', etc.
    brand = info.get("brand_raw") or info.get("brand", "Unknown CPU")
    return brand

def get_tdp_from_samaltman():
    """Returns the CPU's TDP in INT form, by doing an OpenAI api call. 
    If the CPU is not easily found through get_cpu_name(), it returns -1.
    """
    cpu_name = get_cpu_name()
    if cpu_name == "Unknown CPU":
        return -1

    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    response = client.responses.create(
        model="gpt-4o",
        instructions="I will give you CPU information and I need you to do research and find the CPU's Thermal Design Power. ONLY return the number of the TDP and NOTHING else.",
        input=cpu_name
    )

    cpu_tdp = int(response.output_text)

    return cpu_tdp

print(get_tdp_from_samaltman())
