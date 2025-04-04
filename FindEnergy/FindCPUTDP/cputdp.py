import cpuinfo
 import requests
 
 def get_cpu_name():
     info = cpuinfo.get_cpu_info()
     return info.get("brand_raw", "Unknown CPU")
 
 def query_tdp_from_backend():
     cpu_name = get_cpu_name()
     response = requests.post("http://fennecs.duckdns.org:5000/get-tdp", json={"cpu_name": cpu_name})
     if response.status_code == 200:
         print(f"TDP: {response.json().get('tdp')}W")
     else:
         print("Error:", response.text)
 
 if __name__ == "__main__":
     query_tdp_from_backend()
