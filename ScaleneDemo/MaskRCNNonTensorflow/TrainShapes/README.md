
# Mask-RCNN TF2.14.0 Profiling with Scalene

## Repository Link

Clone the official repository:

[Mask-RCNN_TF2.14.0 Repository](https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0)

```bash
git clone https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0.git
cd Mask-RCNN_TF2.14.0
```

---

## Add the Shapes Training Script

Move your `train_shapes.py` file into `/mrcnn`, so your folder looks like this:

```
Mask-RCNN_TF2.14.0/
├── mrcnn/
│   ├── train_shapes.py/
```


## Conda Environment Setup

Create the environment using the provided `environment.yml` file (already modified to include Scalene):

### environment.yml

```yaml
name: maskrcnn-tf2
channels:
  - defaults
dependencies:
  - python=3.10.12
  - pip=23.3
  - pip:
      - cython==3.0.5
      - h5py==3.9.0
      - imgaug==0.4.0
      - ipython==7.34.0
      - ipython-genutils==0.2.0
      - ipython-sql==0.5.0
      - keras==2.14.0
      - matplotlib==3.7.1
      - numpy==1.23.5
      - opencv-contrib-python==4.8.0.76
      - opencv-python==4.8.0.76
      - pillow==9.4.0
      - scikit-image==0.19.3
      - scipy==1.11.3
      - tensorboard==2.14.1
      - tensorflow-macos==2.14.0  # For Apple Silicon
      #- tensorflow-metal  # Uncomment if you want Metal GPU acceleration
      - typing_extensions>=4.9
      - scalene  # Added for profiling
```

Create and activate the environment:

```bash
conda env create -f environment.yml
conda activate maskrcnn-tf2
```

---

## Run the Shapes Training Script with Scalene

With the environment active, run the shapes script from the root folder of the repo using Scalene:

```bash
scalene -m mrcnn.train_shapes
```

This will generate a `profile.html` file in the root folder. It also took like 30 minutes to run on my M1 MacbookAir so plan accordingly. 

---

## Notes

- This setup uses `tensorflow-macos` for Apple Silicon (M1/M2/M3).  
- If you're using a regular x86 system, replace `tensorflow-macos` with:
    ```yaml
    - tensorflow==2.14.0
    ```
- If you want GPU acceleration on Apple Silicon, uncomment(This lead to problems for me):
    ```yaml
    - tensorflow-metal
    ```
- Scalene will give you **line-by-line CPU, memory, and GPU usage**.

---

## Troubleshooting

- If `conda env create` fails, check if Conda is correctly installed:
    ```bash
    conda --version
    ```
- If Scalene gives an error, ensure you are inside the environment and try:
    ```bash
    pip install scalene
    ```
- If TensorFlow complains, make sure you're on the correct machine (Apple Silicon vs. regular x86), or remove the Apple Silicon Metal GPU acceleration.

---

## License

This project follows the original license from the [Mask-RCNN_TF2.14.0](https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0) repository.
