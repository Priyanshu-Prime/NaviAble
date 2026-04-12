"""Class-aware augmentation for YOLO dataset.

This script uses `yolo/augment_dataset.py` utilities to create augmentations but
allocates more augmentations to images containing under-represented classes so
that the final class counts approach a common target (default: maximum class count).

Usage:
  python yolo/augment_class_aware.py --src images/train --labels labels/train --out train_aug \
      --copies-default 1 --max-per-image 5 --target-mode max --dry-run

The script first computes class frequencies, then builds a plan assigning
augmentation counts per image to reduce class imbalance. It can run in dry-run
mode to preview the plan without writing files.
"""
import os
import sys
import glob
import random
import collections

# make relative imports work when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from yolo.augment_dataset import augment_image_label, make_transform
from config import YOLO_CLASSES


def load_image_class_map(labels_dir):
    """Return mapping base_name -> list of class_ids, and per-class counts."""
    images = []
    image_classes = {}
    class_counts = collections.Counter()
    for p in glob.glob(os.path.join(labels_dir, "*.txt")):
        base = os.path.splitext(os.path.basename(p))[0]
        classes = []
        for line in open(p):
            parts = line.strip().split()
            if not parts:
                continue
            try:
                cid = int(parts[0])
            except Exception:
                continue
            classes.append(cid)
            class_counts[cid] += 1
        if classes:
            image_classes[base] = classes
            images.append(base)
    return images, image_classes, class_counts


def compute_target(class_counts, mode='max'):
    vals = list(class_counts.values())
    if not vals:
        return 0
    if mode == 'max':
        return max(vals)
    if mode == 'median':
        vals = sorted(vals)
        mid = len(vals) // 2
        return vals[mid]
    if mode == 'mean':
        return int(sum(vals) / len(vals))
    # default fallback
    return max(vals)


def build_augmentation_plan(images, image_classes, class_counts, target, max_per_image=5, copies_default=0, seed=42):
    random.seed(seed)
    # Initialize plan with default copies per image
    plan = collections.Counter({img: copies_default for img in images})

    # Per-image assigned augmentations cannot exceed max_per_image
    per_image_max = {img: max_per_image for img in images}

    # For each class with deficit, sample images containing that class and assign aug copies
    deficits = {c: max(0, target - class_counts.get(c, 0)) for c in range(len(YOLO_CLASSES))}

    # Map class -> list of images containing it
    images_by_class = {c: [img for img,cl in image_classes.items() if c in cl] for c in deficits}

    for c, d in deficits.items():
        if d <= 0:
            continue
        pool = images_by_class.get(c, [])
        if not pool:
            print(f"Warning: no images found for class {c} ('{YOLO_CLASSES[c]}'), cannot augment this class")
            continue
        # Greedy: repeatedly sample images from pool that haven't hit max
        attempts = 0
        while d > 0 and attempts < d * 10:
            img = random.choice(pool)
            if plan[img] < per_image_max[img]:
                plan[img] += 1
                d -= 1
            else:
                # all sampled image hit max; check if any in pool still available
                if all(plan[i] >= per_image_max[i] for i in pool):
                    print(f"Reached per-image max for all images of class {c}. Remaining deficit: {d}")
                    break
            attempts += 1

    return plan


def summarize_plan(plan, image_classes, class_counts, target):
    total_aug = sum(plan.values())
    print(f"Planned augmentations: total images to augment (sum copies) = {total_aug}")
    # estimate new class counts
    est_counts = dict(class_counts)
    for img, copies in plan.items():
        cls = image_classes.get(img, [])
        for c in cls:
            est_counts[c] = est_counts.get(c, 0) + copies
    print("Class summary: (class_id name) before -> estimated after")
    for c in range(len(YOLO_CLASSES)):
        before = class_counts.get(c, 0)
        after = est_counts.get(c, before)
        print(f"{c} {YOLO_CLASSES[c]}: {before} -> {after}")


def run_plan(plan, src_images_dir, src_labels_dir, out_root, transform_seed=42):
    out_images = os.path.join(out_root, 'images')
    out_labels = os.path.join(out_root, 'labels')
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)
    transform = make_transform()

    for img_base, copies in plan.items():
        src_img = None
        for ext in ('.jpg', '.jpeg', '.png'):
            candidate = os.path.join(src_images_dir, img_base + ext)
            if os.path.exists(candidate):
                src_img = candidate
                break
        if src_img is None:
            print(f"Warning: image for base {img_base} not found in {src_images_dir}")
            continue
        src_lbl = os.path.join(src_labels_dir, img_base + '.txt')
        # copy original first if not already copied
        orig_out_img = os.path.join(out_images, img_base + '.jpg')
        if not os.path.exists(orig_out_img):
            Image_open = __import__('PIL').Image.open
            Image_open(src_img).convert('RGB').save(orig_out_img, quality=95)
            if os.path.exists(src_lbl):
                with open(src_lbl) as fr, open(os.path.join(out_labels, img_base + '.txt'), 'w') as fw:
                    fw.write(fr.read())

        # now create augmentations
        for i in range(copies):
            out_image_path = os.path.join(out_images, f"{img_base}_aug{i+1}.jpg")
            out_label_path = os.path.join(out_labels, f"{img_base}_aug{i+1}.txt")
            try:
                augment_image_label(src_img, src_lbl, out_image_path, out_label_path, transform, seed=transform_seed + i)
            except Exception as e:
                # Skip problematic augmentation cases (e.g., tiny numerical bbox errors)
                print(f"Warning: augmentation failed for {img_base} copy {i+1}: {e}")
                continue


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True, help='source images folder')
    parser.add_argument('--labels', required=True, help='source labels folder')
    parser.add_argument('--out', required=True, help='output folder for augmented dataset')
    parser.add_argument('--copies-default', type=int, default=0, help='default augment copies per image')
    parser.add_argument('--max-per-image', type=int, default=5, help='maximum augment copies allowed per image')
    parser.add_argument('--target-mode', choices=['max','median','mean'], default='max')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    images, image_classes, class_counts = load_image_class_map(args.labels)
    if not images:
        print('No labeled images found in', args.labels)
        return

    target = compute_target(class_counts, mode=args.target_mode)
    print('Current class counts:')
    for c in range(len(YOLO_CLASSES)):
        print(c, YOLO_CLASSES[c], class_counts.get(c,0))
    print('Target per-class count:', target)

    plan = build_augmentation_plan(images, image_classes, class_counts, target, max_per_image=args.max_per_image, copies_default=args.copies_default, seed=args.seed)
    summarize_plan(plan, image_classes, class_counts, target)

    if args.dry_run:
        print('Dry run: no files will be written.')
        return

    print('Running augmentation plan...')
    run_plan(plan, args.src, args.labels, args.out, transform_seed=args.seed)
    print('Class-aware augmentation complete. Augmented data in:', args.out)


if __name__ == '__main__':
    main()

