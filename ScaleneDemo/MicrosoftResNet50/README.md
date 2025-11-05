# ResNet-50 Inference on COCO 2017 (Hugging Face, Conda-Only) + Scalene JSON Post-Processing

Model: https://huggingface.co/microsoft/resnet-50

This guide runs **image classification inference** with Hugging Face `microsoft/resnet-50` on **COCO 2017 `val2017`**, profiles with **Scalene**, and then processes the generated **JSON** with `sum_joules_with_cpu.py` to aggregate energy metrics.

---

## 1) Conda Environment (GPU)
Create `environment.yml` in this folder with the contents below, then create/activate it.

### environment.yml
```yaml
name: resnet50_infer
channels:
  - pytorch
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - pytorch
  - torchvision
  - pytorch-cuda=12.1
  - numpy
  - pillow
  - tqdm
  - pip
  - pip:
      - transformers
      - scalene
```

### Create & Activate
```bash
conda env create -f environment.yml
conda activate resnet50_infer
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```
> Requires a compatible NVIDIA driver on the host. If `CUDA available: False`, verify your driver, then recreate the env if needed.

---

## 2) Data (COCO 2017)
Place **COCO val2017** JPEGs in a directory, for example:
```
/home/cc/data/coco/val2017/
```

---

## 3) Run Profiling with Scalene
This runs the ResNet-50 runner under Scalene and writes a **JSON** reports.

```bash
# From the directory containing resnet50_coco_dir.py
scalene ./resnet50_coco_dir.py   --dir /home/cc/data/coco/val2017   --batch 32 --limit 200   --json --outfile msft_resnet50_profile
```
**Output** in the current folder:
- `msft_resnet50_profile.json`

> Tip: if you also want HTML, add the `--html` flag.

---

## 4) Post-Process JSON (sum CPU+GPU joules)
Use your helper script `sum_joules_with_cpu.py` to read Scalene’s JSON and print/aggregate energy totals (including CPU).

```bash
# Example usage
python sum_joules_with_cpu.py
```

**Expected behavior (example):**
- Prints overall totals: `CPU Joules`, `GPU Joules`, `Elapsed Time`

---

## 5) Troubleshooting
- **CUDA not detected**: Update/install the NVIDIA driver (matching CUDA 12.x runtime), then recreate the env.
- **Model download**: First run downloads weights to `~/.cache/huggingface/` (use `HF_HOME` to change).
- **Scalene GPU modes** (Linux): enable per-process accounting for better accuracy  
  ```bash
  python3 -m scalene.set_nvidia_gpu_modes  # may prompt for sudo
  ```

---
