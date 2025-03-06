#!/usr/bin/env python3

"""
train_shapes.py
---------------
A standalone script that trains Mask R-CNN on the toy Shapes dataset,
assuming it is located INSIDE the mrcnn/ folder. We'll use relative
imports like 'from . import model' so that we can run this via:
    python -m mrcnn.train_shapes
from the PARENT folder of 'mrcnn'.
"""

import os
import sys
import random
import math
import numpy as np
import cv2
import tensorflow as tf
os.environ["TF_MPS_DEVICE_DISABLED"] = "1"

# -------------------------------------------------------------------------
# If you run into “Could not find variable” or session-based errors,
# uncomment this line to disable TF2 eager execution (classic TF1 graph mode).
# tf.compat.v1.disable_eager_execution()
# -------------------------------------------------------------------------

# Root directory is one level up from this file's directory
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))

# So that we can save logs in ../logs
MODEL_DIR = os.path.join(ROOT_DIR, "logs")

# We assume mask_rcnn_coco.h5 is in the PARENT folder too.
COCO_MODEL_PATH = os.path.join(ROOT_DIR, "mask_rcnn_coco.h5")


# ---------------- IMPORTS FROM MRCNN (RELATIVE) ----------------
# Because train_shapes.py is in the same folder as config.py, model.py, etc.

from .config import Config
from . import utils
from . import model as modellib
from . import visualize


# If not found, attempt to download COCO weights
if not os.path.exists(COCO_MODEL_PATH):
    utils.download_trained_weights(COCO_MODEL_PATH)


############################################################
#  Config
############################################################

class ShapesConfig(Config):
    """Configuration for training on the toy shapes dataset."""
    NAME = "shapes"
    GPU_COUNT = 1
    IMAGES_PER_GPU = 8  # If you have memory issues, lower this number

    NUM_CLASSES = 1 + 3  # background + 3 shapes (square, circle, triangle)

    # Smaller images for faster training
    IMAGE_MIN_DIM = 128
    IMAGE_MAX_DIM = 128

    # Anchor scales
    RPN_ANCHOR_SCALES = (8, 16, 32, 64, 128)

    TRAIN_ROIS_PER_IMAGE = 32
    STEPS_PER_EPOCH = 100
    VALIDATION_STEPS = 5

############################################################
#  Dataset
############################################################

class ShapesDataset(utils.Dataset):
    """Generates the shapes synthetic dataset: squares, circles, and triangles."""
    def load_shapes(self, count, height, width):
        """Generate the requested number of synthetic images."""
        self.add_class("shapes", 1, "square")
        self.add_class("shapes", 2, "circle")
        self.add_class("shapes", 3, "triangle")

        for i in range(count):
            bg_color, shapes = self.random_image(height, width)
            self.add_image(
                "shapes",
                image_id=i,
                path=None,
                width=width, height=height,
                bg_color=bg_color,
                shapes=shapes
            )

    def load_image(self, image_id):
        """Generate an image from the specs of the given image ID."""
        info = self.image_info[image_id]
        bg_color = np.array(info['bg_color']).reshape([1, 1, 3])
        image = np.ones([info['height'], info['width'], 3], dtype=np.uint8)
        image = image * bg_color.astype(np.uint8)
        for shape, color, dims in info['shapes']:
            image = self.draw_shape(image, shape, dims, color)
        return image

    def image_reference(self, image_id):
        info = self.image_info[image_id]
        if info["source"] == "shapes":
            return info["shapes"]
        else:
            return super(self.__class__, self).image_reference(image_id)

    def load_mask(self, image_id):
        info = self.image_info[image_id]
        shapes = info['shapes']
        count = len(shapes)
        mask = np.zeros([info['height'], info['width'], count], dtype=np.uint8)
        for i, (shape, _, dims) in enumerate(shapes):
            mask[:, :, i:i+1] = self.draw_shape(
                mask[:, :, i:i+1].copy(),
                shape, dims, 1
            )
        # Handle occlusions
        occlusion = np.logical_not(mask[:, :, -1]).astype(np.uint8)
        for i in range(count-2, -1, -1):
            mask[:, :, i] = mask[:, :, i] * occlusion
            occlusion = np.logical_and(
                occlusion, np.logical_not(mask[:, :, i])
            )
        # Map class names (square, circle, triangle) to class IDs
        class_ids = np.array([self.class_names.index(s[0]) for s in shapes])
        return mask.astype(bool), class_ids.astype(np.int32)

    def draw_shape(self, image, shape, dims, color):
        x, y, s = dims
        if shape == 'square':
            cv2.rectangle(image, (x-s, y-s), (x+s, y+s), color, -1)
        elif shape == "circle":
            cv2.circle(image, (x, y), s, color, -1)
        elif shape == "triangle":
            import math
            points = np.array([[
                (x, y - s),
                (x - s / math.sin(math.radians(60)), y + s),
                (x + s / math.sin(math.radians(60)), y + s),
            ]], dtype=np.int32)
            cv2.fillPoly(image, points, color)
        return image

    def random_shape(self, height, width):
        import math
        shape = random.choice(["square", "circle", "triangle"])
        color = tuple([random.randint(0, 255) for _ in range(3)])
        buffer = 20
        y = random.randint(buffer, height - buffer - 1)
        x = random.randint(buffer, width - buffer - 1)
        s = random.randint(buffer, height // 4)
        return shape, color, (x, y, s)

    def random_image(self, height, width):
        bg_color = np.array([random.randint(0, 255) for _ in range(3)])
        shapes = []
        boxes = []
        N = random.randint(1, 4)
        for _ in range(N):
            shape, color, dims = self.random_shape(height, width)
            shapes.append((shape, color, dims))
            x, y, s = dims
            boxes.append([y - s, x - s, y + s, x + s])
        # Non-max suppression to avoid overlapping shapes
        keep_ixs = utils.non_max_suppression(
            np.array(boxes), np.arange(N), 0.3
        )
        shapes = [s for i, s in enumerate(shapes) if i in keep_ixs]
        return bg_color, shapes

############################################################
#  Main
############################################################

def main():
    # Create config
    config = ShapesConfig()
    config.display()

    # Create training and validation sets
    dataset_train = ShapesDataset()
    dataset_train.load_shapes(500, config.IMAGE_SHAPE[0], config.IMAGE_SHAPE[1])
    dataset_train.prepare()

    dataset_val = ShapesDataset()
    dataset_val.load_shapes(50, config.IMAGE_SHAPE[0], config.IMAGE_SHAPE[1])
    dataset_val.prepare()

    # Create model in training mode
    model = modellib.MaskRCNN(mode="training", config=config,
                              model_dir=MODEL_DIR)

    # Load the COCO weights, but exclude the final layers that differ for Shapes
    model.load_weights(
        COCO_MODEL_PATH,
        by_name=True,
        exclude=["mrcnn_class_logits", "mrcnn_bbox_fc",
                 "mrcnn_bbox", "mrcnn_mask"]
    )

    # 1) Train heads
    print("\nStarting Training (Heads Only)...")
    model.train(
        dataset_train,
        dataset_val,
        learning_rate=config.LEARNING_RATE,
        epochs=1,
        layers='heads'
    )

    # 2) Fine-tune all layers
    print("\nStarting Training (All Layers)...")
    model.train(
        dataset_train,
        dataset_val,
        learning_rate=config.LEARNING_RATE / 10,
        epochs=2,
        layers='all'
    )

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
