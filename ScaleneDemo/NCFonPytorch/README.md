# PyTorch NCF Setup and Profiling

## Repository Link

Clone the NVIDIA DeepLearningExamples repository:

[NVIDIA DeepLearningExamples Repository](https://github.com/NVIDIA/DeepLearningExamples)

```bash
git clone https://github.com/NVIDIA/DeepLearningExamples.git
cd DeepLearningExamples/PyTorch/Recommendation/NCF
```
## Dataset Setup
Download the MovieLens 20M dataset:
https://files.grouplens.org/datasets/movielens/ml-20m.zip

After downloading, right click on  the zipped file and click `extract all` then, put the files in the data directory of the NCF folder

Run the preprocessing script to prepare the dataset

```bash
./prepare_dataset.sh
```
This will generate preprocessed data in ../../data/cache/ml-20m

Note: Downloading and preprocessing may take 1–2 hours depending on your network and system.
Note 2: If you place ml-20m.zip in a different location, update the paths in prepare_dataset.sh to point to the correct location (e.g., replace /data/ml-20m.zip with your path).

The resulting directory structure should look like:
DeepLearningExamples/
├── PyTorch/
│   ├── Recommendation/
│   │   ├── NCF/
│   ├── data/
│   │   ├── cache/
│   │   │   ├── ml-20m/

## Conda Environment Setup
Create a Conda environment with the require dependencies. Place the provided evironment.yml file in the NCF directory:

environment.yml
```yaml
name: ncf_pytorch
channels:
  - pytorch
  - conda-forge
  - defaults
dependencies:
  - python=3.8
  - pytorch
  - torchvision
  - cudatoolkit=11.3
  - numpy
  - tqdm
  - pip
  - pip:
      - scalene
```

Create and activate the environment:
```bash
conda env create -f environment.yml
conda activate ncf_pytorch
```

## Run Training with Scalene Profiling
With the environment active, run the training script with scalene from the NCF directory:
```bash
scalene -- python -m torch.distributed.launch --nproc_per_node=1 --use_env ncf.py --data ../../data/cache/ml-20m --checkpoint_dir ../../checkpoints --amp --epochs 1
```
This will generate `profile.json` and `profile.html` files in the current directory. Depending on your hardware, training may take a significant amount of time.
Note:

Replace `../../data/cache/ml-20m` with the actual path to your preprocessed dataset if different.
Replace `../../checkpoints` with your preferred directory for model checkpoints.
The `--amp` flag enables Automatic Mixed Precision for GPU training. If no GPU is available, PyTorch will fall back to CPU.
The `--epochs 1` flag limits training to one epoch for testing purposes.


## Notes

- This setup uses PyTorch with CUDA support for GPU acceleration (if available).
- Scalene provides line-by-line CPU, memory, and GPU usage insights.
- If running on a CPU-only machine, the script will automatically use device='cpu', but GPU-related statistics in the profiling output will be null or zero.
- Ensure sufficient disk space for the dataset (~1 GB for preprocessed data) and checkpoints.


## Troubleshooting

- If conda env create fails, verify Conda installation:
```bash
conda --version
```

- If Scalene gives an error, ensure you are inside the environment and try:
```bash
pip install scalene
```

- If PyTorch complains about missing CUDA, verify CUDA toolkit installation or ensure PyTorch CPU version is installed:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```
If it returns False, the script will run on CPU.
- If dataset preprocessing fails, check that ml-20m.zip is in the correct location and that prepare_dataset.sh points to it.


## License
This project follows the original license from the NVIDIA DeepLearningExamples repository.