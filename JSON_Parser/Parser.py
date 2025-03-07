import json

def parse_json(file_path):  
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        files_dict = data["files"]
        first_file_key = next(iter(files_dict))
        file_data = files_dict[first_file_key]
        
        # Get import statements
        imports = file_data.get("imports", [])
        imported_modules = []
        imported_titles = []  

        # Parse import statements
        for import_line in imports:
            if "import" in import_line:
                # Skip duplicate simple imports like 'import warning from layne file'
                if import_line in [imp.get("raw_import") for imp in imported_modules]:
                    continue
                    
                if "from" in import_line:
                    # Handle 'from module import item1, item2' format
                    module_path = import_line.split("from")[1].strip().split()[0]
                    base_module = module_path.split(".")[0] if "." in module_path else module_path
                    
                    # Get everything after 'import'
                    imports_part = import_line.split("import")[1].strip()
                    # Handle multiple imports with aliases like 'from module import item1, item2 as something'
                    for item in imports_part.split(","):
                        item = item.strip()
                        if " as " in item:
                            original, alias = item.split(" as ")
                            imported_modules.append({
                                "module": alias.strip(),
                                "title": base_module,
                                "raw_import": import_line
                            })
                        else:
                            imported_modules.append({
                                "module": item,
                                "title": base_module,
                                "raw_import": import_line
                            })
                    
                    if not base_module in imported_titles:
                        imported_titles.append(base_module)
                else:
                    # Handle 'import module as something' format
                    parts = import_line.split()
                    import_index = parts.index("import")
                    
                    # Handle multiple imports in one line
                    imports_part = " ".join(parts[import_index + 1:])
                    for item in imports_part.split(","):
                        item = item.strip()
                        if " as " in item:
                            original, alias = item.split(" as ")
                            base_module = original.split(".")[0]
                            imported_modules.append({
                                "module": alias,
                                "title": base_module,
                                "raw_import": import_line
                            })
                        else:
                            base_module = item.split(".")[0]
                            imported_modules.append({
                                "module": item,
                                "title": base_module,
                                "raw_import": import_line
                            })
                        
                        if not base_module in imported_titles:
                            imported_titles.append(base_module)

        # Remove duplicate entries while preserving order
        seen = set()
        imported_modules = [
            x for x in imported_modules 
            if not (x["module"] in seen or seen.add(x["module"]))
        ]
        
        #Get the lines from the json file
        lines = file_data.get("lines", [])
        inline_module_usage = {module["module"]: [] for module in imported_modules}
        local_function_usage = []
        
        # Parse lines for imported module keywords (inline functions like Layers and Optimizers that were constructed from a library)
        for line in lines:
            for module_info in imported_modules:
                line_text = line.get("line")
                module_name = module_info["module"].rstrip(".")
                
                starts_with_other_module = any(
                    other_module["module"].rstrip(".") == line_text.lstrip().split('.')[0]
                    for other_module in imported_modules
                    if other_module != module_info
                )
                
                is_valid_usage = (
                    module_name in line_text and
                    not starts_with_other_module
                )

                existing_functions = [
                    usage["function"] 
                    for usage_list in inline_module_usage.values() 
                    for usage in usage_list
                ]
                
                if is_valid_usage and line.get("line") not in existing_functions:
                        inline_module_usage[module_info["module"]].append({
                            "function": line.get("line"),
                            "line_number": line.get("lineno"),
                            "CPU %": round(line.get("n_core_utilization", 0), 2),
                            "GPU %": round(line.get("n_gpu_percent", 0), 2),
                            "SYS %": round(line.get("n_sys_percent", 0), 2),
                            #"Time (sec)": round(line.get("elapsed_time_sec", 0), 6),
                            "module_title": module_info["title"]
                        })

        # Parse functions section for local functions that were defined inside the .py file and called in it
        # First get functions from the json file
        functions = file_data.get("functions", {})  
        for func in functions:
            local_function_usage.append({
                "function": func.get("line"),
                "line_number": func.get("lineno"),
                "CPU %": round(func.get("n_core_utilization"), 2),
                "GPU %": round(func.get("n_gpu_percent"), 2),
                "SYS %": round(func.get("n_sys_percent"), 2),
                #"Time (sec)": round(func.get("elapsed_time_sec"), 6), 
                "module_title": func.get("line")
            })

        # Calculate maximum lengths for formatting CPU, GPU, and SYS percentages inside the text file
        max_line_length = max(
            len(usage["function"].lstrip())
            for module_name, usages in inline_module_usage.items()
            for usage in usages
        ) if any(inline_module_usage.values()) else 0

        max_local_line_length = max(
            len(func["function"].lstrip())
            for func in local_function_usage
        ) if local_function_usage else 0

        max_length = max(max_line_length, max_local_line_length)

        # Here we write results to a text file
        output_file_path = "module_usage_report.txt"
        with open(output_file_path, 'w') as f:
            f.write("Module Usage Report\n")
            f.write("==================\n")
            
            f.write("\nLocal Functions\n")
            f.write("===============\n")
            header = f"Line Numbers | {'Functions':<{max_length}} | CPU % | GPU % | SYS %\n"  #add newline back
            f.write(header)
            f.write("-" * (len(header)) + "\n")

            sorted_local_functions = sorted(local_function_usage, key=lambda x: x['line_number']) #Sort all the data based on the line number
            for func in sorted_local_functions:
                f.write(f"Line {func['line_number']:7} | {func['function'].lstrip():<{max_length}} | "
                       f"{func['CPU %']:5.2f} | {func['GPU %']:5.2f} | {func['SYS %']:5.2f}\n") #add newline back

            f.write("\nInline Function Calls\n")
            f.write("=====================\n")
            title_usage = {}
            for module_name, usages in inline_module_usage.items():
                if usages:
                    module_title = usages[0]['module_title']
                    if module_title not in title_usage:
                        title_usage[module_title] = []
                    title_usage[module_title].extend(usages)
            
            # Write grouped inline results
            for title, usages in title_usage.items():
                f.write(f"\nModule: {title}\n")
                f.write("-" * (len(title) + 8) + "\n")
                header = f"Line Numbers | {'Functions':<{max_length}} | CPU % | GPU % | SYS%\n" #add newline back
                f.write(header)
                f.write("-" * len(header) + "\n")
                sorted_usages = sorted(usages, key=lambda x: x['line_number']) 
                for usage in sorted_usages:
                    function_text = usage['function'].lstrip().rstrip()
                    line = (f"Line {usage['line_number']:7} | "
                           f"{function_text:<{max_length}} | "
                           f"{usage.get('CPU %', 0.0):5.2f} | "
                           f"{usage.get('GPU %', 0.0):5.2f} | "
                           f"{usage.get('SYS %', 0.0):5.2f} | " )
                           #f"{usage.get('Time (sec)', 0.0):5.6f}")
                    f.write(f"{line}\n")
                    result = 10 / 0
        print(f"\nReport written to {output_file_path}")


    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

file_path = "C:/Users/nyros/AI-Energy-Optimization/JSON_Parser/profile.json"
parse_json(file_path)
    