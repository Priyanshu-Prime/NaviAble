"""Augment a YOLO dataset (images + labels) using Albumentations.

This script reads images and corresponding YOLO .txt labels (class x_center y_center w h normalized),
applies a set of randomized augmentations and writes augmented images and new label files preserving YOLO format.

Usage example:
  python yolo/augment_dataset.py --src images/train --labels labels/train --out augmented --copies 3

It will create `out/images` and `out/labels` with augmented files named <orig>_aug<N>.jpg/.txt
"""
import argparse
import os
import glob
import random
from PIL import Image
import numpy as np

try:
    import albumentations as A
except Exception:
    A = None


def yolo_to_bbox(yolo, img_w, img_h):
    # yolo: x_center y_center w h normalized
    x_c, y_c, w, h = map(float, yolo)
    x_c *= img_w
    y_c *= img_h
    w *= img_w
    h *= img_h
    x_min = x_c - w / 2
    y_min = y_c - h / 2
    x_max = x_c + w / 2
    y_max = y_c + h / 2
    return [x_min, y_min, x_max, y_max]


def bbox_to_yolo(bbox, img_w, img_h):
    x_min, y_min, x_max, y_max = bbox
    w = x_max - x_min
    h = y_max - y_min
    x_c = x_min + w / 2
    y_c = y_min + h / 2
    return [x_c / img_w, y_c / img_h, w / img_w, h / img_h]


def make_transform():
    if A is None:
        raise RuntimeError("Albumentations is required. Install with: pip install albumentations")
    # Compose a set of useful augmentations for object detection
    return A.Compose(
        [
            A.OneOf([
                A.HorizontalFlip(p=0.5),
                A.RandomRotate90(p=0.2),
            ], p=0.6),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15, val_shift_limit=10, p=0.5),
            A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=10, p=0.5, border_mode=0),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.2),
        ],
        bbox_params=A.BboxParams(format='pascal_voc', label_fields=['category_ids'])
    )


def augment_image_label(image_path, label_path, out_image_path, out_label_path, transform, seed=None):
    img = Image.open(image_path).convert('RGB')
    img_w, img_h = img.size
    img_np = np.array(img)

    boxes = []
    class_ids = []
    if os.path.exists(label_path):
        for line in open(label_path):
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            class_id = int(parts[0])
            yolo_box = parts[1:5]
            bbox = yolo_to_bbox(yolo_box, img_w, img_h)
            boxes.append(bbox)
            class_ids.append(class_id)

    # Apply transform
    try:
        augmented = transform(image=img_np, bboxes=boxes, category_ids=class_ids)
    except Exception as e:
        raise RuntimeError(f"Albumentations transform failed: {e}")

    aug_img = Image.fromarray(augmented['image'])
    aug_img.save(out_image_path, quality=95)

    # convert bboxes back to YOLO and save
    with open(out_label_path, 'w') as fh:
        for cid, bbox in zip(augmented.get('category_ids', []), augmented.get('bboxes', [])):
            # bbox is pascal_voc (x_min,y_min,x_max,y_max)
            yolo_box = bbox_to_yolo(bbox, aug_img.width, aug_img.height)
            # clip and skip invalid boxes
            x_c, y_c, w, h = yolo_box
            if w <= 0 or h <= 0:
                continue
            x_c = max(0.0, min(1.0, x_c))
            y_c = max(0.0, min(1.0, y_c))
            w = max(0.0, min(1.0, w))
            h = max(0.0, min(1.0, h))
            fh.write(f"{cid} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True, help='source images folder')
    parser.add_argument('--labels', required=True, help='source labels folder (yolo txt)')
    parser.add_argument('--out', required=True, help='output root for augmented data')
    parser.add_argument('--copies', type=int, default=3, help='number of augmentations per image')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    transform = make_transform()

    out_images = os.path.join(args.out, 'images')
    out_labels = os.path.join(args.out, 'labels')
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    images = sorted(glob.glob(os.path.join(args.src, '*.*')))
    if not images:
        print('No images found in', args.src)
        return

    for img_path in images:
        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(args.labels, f"{base}.txt")
        # copy original as well
        orig_out_img = os.path.join(out_images, base + '.jpg')
        Image.open(img_path).convert('RGB').save(orig_out_img, quality=95)
        if os.path.exists(label_path):
            # copy original label
            dst_label = os.path.join(out_labels, base + '.txt')
            with open(label_path) as fr, open(dst_label, 'w') as fw:
                fw.write(fr.read())

        for i in range(args.copies):
            out_image_path = os.path.join(out_images, f"{base}_aug{i+1}.jpg")
            out_label_path = os.path.join(out_labels, f"{base}_aug{i+1}.txt")
            augment_image_label(img_path, label_path, out_image_path, out_label_path, transform, seed=args.seed + i)

    print('Augmentation complete. Augmented data in:', args.out)


if __name__ == '__main__':
    import argparse
    main()

