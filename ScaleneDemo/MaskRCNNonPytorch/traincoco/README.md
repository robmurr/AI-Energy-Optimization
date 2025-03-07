
# PyTorch Simple Mask R-CNN Setup and Profiling

## Repository Link

Clone the official repository:

[PyTorch-Simple-MaskRCNN Repository](https://github.com/Okery/PyTorch-Simple-MaskRCNN)

```bash
git clone https://github.com/Okery/PyTorch-Simple-MaskRCNN.git
cd PyTorch-Simple-MaskRCNN
```

---

## Dataset Setup

Download the COCO 2017 dataset:

1. [Train Images (train2017.zip)](http://images.cocodataset.org/zips/train2017.zip)
2. [Validation Images (val2017.zip)](http://images.cocodataset.org/zips/val2017.zip)
3. [Annotations (annotations\_trainval2017.zip)](http://images.cocodataset.org/annotations/annotations_trainval2017.zip)

After downloading, right click on each of the zipped file and click `extract all` then, organize them into a new `coco2017` folder under `PyTorch-Simple-MaskRCNN`:

Note: it do take long time to download and extract all the files.(Tooks about 1.5 hours for me)
Note2: Make sure there's no another folder in the annotations or train2017 or val2017. Which there should be all data in these three folder
```
PyTorch-Simple-MaskRCNN/
├── coco2017/
│   ├── annotations/
│   ├── train2017/
│   ├── val2017/
```

---

## Conda Environment Setup

Create the environment using the provided `environment.yml` file:

### environment.yml

Create and activate the environment:

```bash
conda env create -f environment.yml
conda activate maskrcnn_pytorch
```

---

## Run Training with Scalene Profiling

With the environment active, run the training script with Scalene from the root folder of the repo:

```bash
scalene train.py --use-cuda --iters 20 --dataset coco --data-dir coco2017
```

This will generate a `profile.html` file in the root folder. Depending on your hardware, training may take a significant amount of time.

---

## Notes

- This setup uses PyTorch and Torchvision compatible with CUDA (if available).
- If running on a CPU-only machine, modify the script to use `device='cpu'`.
- Scalene provides **line-by-line CPU, memory, and GPU usage** insights.

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
- If PyTorch complains about missing CUDA, ensure you have the correct drivers installed or switch to CPU mode.

---

## License

This project follows the original license from the [PyTorch-Simple-MaskRCNN](https://github.com/Okery/PyTorch-Simple-MaskRCNN) repository.

