# CPU TDP Finder

This repository includes a script named `FindCPUTDP.py` which:
1. Determines your CPU name via **py-cpuinfo**.
2. Uses OpenAI’s API (via the **openai** library) to retrieve the CPU’s TDP.
3. Prints the TDP value (or `-1` if unknown) to the terminal.

---

## 1. Set Up a Conda Environment

We provide an `environment.yml` file to automate your environment creation:

1. **Ensure** you have [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) installed.
2. **Clone** or download this repository, then **cd** into its root directory (where `environment.yml` resides).
3. Run:
   ```bash
   conda env create -f environment.yml
   ```
   This will create a new conda environment named `cputdp_env`.
4. **Activate** that environment:
   ```bash
   conda activate cputdp_env
   ```

### `environment.yml` contents

```yaml
name: cputdp_env
channels:
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
    - py-cpuinfo
    - python-dotenv
    - openai
```

This file instructs conda to create a Python 3.11 environment and then installs **py-cpuinfo**, **python-dotenv**, and **openai** via pip.

---

## 2. Configure Your OpenAI API Key

Your script relies on `python-dotenv` to read an `.env` file containing your OpenAI API key.

1. **Create** a file named `.env` in the same directory as `FindCPUTDP.py` (or elsewhere if you intend to specify a custom path in `load_dotenv()`).
2. **Inside** that `.env` file, add:
   ```bash
   OPENAI_API_KEY="YOUR_OPENAI_KEY_HERE"
   ```
3. **Make sure** this file is not tracked in version control (add `.env` to your `.gitignore`).

---

## 3. Run `FindCPUTDP.py`

After activating your `cputdp_env` environment:

```bash
conda activate cputdp_env
python FindCPUTDP.py
```

What happens:
1. The script detects your CPU name using **py-cpuinfo**.
2. It calls the OpenAI API to retrieve the CPU’s Thermal Design Power (TDP).
3. It prints the TDP to your terminal. If your CPU name is unknown, it prints `-1`.

---

## 4. Troubleshooting

- **Missing Packages?** Ensure you ran `conda env create -f environment.yml` inside this folder and then activated the `cputdp_env` environment.
- **Invalid Key or Network Errors?** Check your `.env` file for a valid `OPENAI_API_KEY`, or verify you have an internet connection.
- **Unknown CPU?** If `py-cpuinfo` can’t detect your CPU brand/model, the script returns `-1`.

---

### That’s It!

Your system should now be correctly configured to run `FindCPUTDP.py`. 
Happy coding!
