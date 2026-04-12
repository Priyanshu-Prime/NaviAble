"""Merge multiple YOLO-format dataset folders into a single train folder.

For each source dataset folder this script expects a structure like:
  <src>/images/*.jpg
  <src>/labels/*.txt

It copies images and labels into an output folder, avoiding filename collisions by
prefixing files with the source folder name when needed.

Usage:
 python yolo/merge_datasets.py --src_dirs "dir1:dir2:dir3" --out /abs/path/to/train_combined
"""
import os
import glob
import argparse
import shutil
from pathlib import Path


def safe_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def merge(src_dirs, out_root):
    out_images = os.path.join(out_root, 'images')
    out_labels = os.path.join(out_root, 'labels')
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    seen = set()
    counter = 0
    for src in src_dirs:
        src = src.rstrip('/')
        name = os.path.basename(src) or Path(src).stem
        img_dir = os.path.join(src, 'images')
        lbl_dir = os.path.join(src, 'labels')
        imgs = []
        if os.path.isdir(img_dir):
            imgs = glob.glob(os.path.join(img_dir, '*'))
        else:
            # try src directly if images are at top-level
            imgs = glob.glob(os.path.join(src, 'images', '*'))

        for img_path in imgs:
            if not os.path.isfile(img_path):
                continue
            base = os.path.splitext(os.path.basename(img_path))[0]
            ext = os.path.splitext(img_path)[1]
            new_base = base
            if new_base in seen:
                # create unique name using source name and counter
                counter += 1
                new_base = f"{name}_{base}_{counter}"
            seen.add(new_base)
            dst_img = os.path.join(out_images, new_base + ext)
            safe_copy(img_path, dst_img)

            # copy corresponding label if exists
            src_lbl = os.path.join(lbl_dir, base + '.txt')
            dst_lbl = os.path.join(out_labels, new_base + '.txt')
            if os.path.exists(src_lbl):
                safe_copy(src_lbl, dst_lbl)
            else:
                # create empty label file to indicate no objects
                open(dst_lbl, 'w').close()

    print('Merge complete. Images in:', out_images)
    return out_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src_dirs', required=True, help='colon-separated list of dataset root folders')
    parser.add_argument('--out', required=True, help='output dataset root')
    args = parser.parse_args()
    src_dirs = [p for p in args.src_dirs.split(':') if p]
    merge(src_dirs, args.out)


if __name__ == '__main__':
    main()

