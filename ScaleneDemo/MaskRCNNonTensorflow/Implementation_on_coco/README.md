
# Mask-RCNN TF2.14.0 demo Profiling with Scalene

## Repository Link

Clone the official repository:

[Mask-RCNN_TF2.14.0 Repository](https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0)

```bash
git clone https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0.git
cd Mask-RCNN_TF2.14.0
```

---
## Add mask_rcnn_coco.h5

Click and download the given file mask_rcnn_coco.h5: https://github.com/matterport/Mask_RCNN/releases/download/v2.0/mask_rcnn_coco.h5

Add `mask_rcnn_coco.h5` to Mask_RCNN_TF2.14.0, so your folder looks like this:
```
Mask-RCNN_TF2.14.0/
├── mask_rcnn_coco.h5/
```

## Replace environment.yml

Replace `environment.yml` under Mask_RCNN_TF2.14.0 to `new_enviroment.yml`,so your folder looks like this:

```
Mask-RCNN_TF2.14.0/
├── new_environment.yml_/
```


## Conda Environment Setup

Create the environment using the `new__environment.yml` file (already modified to include Scalene):

### new__environment.yml

```yaml
name: maskrcnn-tf2
channels:
  - defaults
dependencies:
  - pip=23.3
  - python=3.10.12
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
      - tensorflow==2.14.0 #commet if use mac
      #uncomment if using mac- tensorflow-macos==2.14.1
      - scalene
```

Create and activate the environment:

```bash
conda env create -f new__environment.yml
conda activate maskrcnn-tf2
```

---

## Run the mrcnn-prediction.py Script with Scalene

With the environment active, run the mask-rcnn-prediction script from the root folder of the repo using Scalene:

```bash
scalene mrcnn-prediction.py
```

This will generate a `profile.html` file in the root folder.  

---

## Notes

- This setup uses `tensorflow` for x86 system.  
- If you're using a mac system with M1,M2,M3,M4, replace `tensorflow` with:
    ```yaml
    - tensorflow-macos==2.14.1
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
- If `scalene mrcnn-prediction.py` gives an error, ensure you have the right numpy version by:
    ```bash
    pip install numpy=1.23.5
    ```
    Answering `y` if it asked `y/n`

- If TensorFlow complains, make sure you're on the correct machine (Apple Silicon vs. regular x86), or remove the Apple Silicon Metal GPU acceleration.

---

## License

This project follows the original license from the [Mask-RCNN_TF2.14.0](https://github.com/z-mahmud22/Mask-RCNN_TF2.14.0) repository.
