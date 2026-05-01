#!/usr/bin/env python3
"""
Dataset Analysis Script - Analyze the Stair & Ramp Detection Dataset
"""

import os
from pathlib import Path
from collections import defaultdict
import cv2

def analyze_dataset():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    dataset_root = project_root / "dataset"

    print("=" * 70)
    print("STAIR & RAMP DETECTION DATASET ANALYSIS")
    print("=" * 70)

    splits = ['train', 'valid', 'test']
    total_images = 0
    total_annotations = 0
    class_counts = defaultdict(lambda: {'ramp': 0, 'stair': 0})

    for split in splits:
        split_path = Path(dataset_root) / split
        images_path = split_path / 'images'
        labels_path = split_path / 'labels'

        if images_path.exists():
            img_count = len(list(images_path.glob('*.jpg'))) + len(list(images_path.glob('*.png')))
            total_images += img_count

            print(f"\n📊 {split.upper()} SET:")
            print(f"   Images: {img_count}")

            # Count annotations
            label_count = 0
            ramp_count = 0
            stair_count = 0

            if labels_path.exists():
                for label_file in labels_path.glob('*.txt'):
                    with open(label_file, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts:
                                class_id = int(parts[0])
                                label_count += 1
                                if class_id == 0:
                                    ramp_count += 1
                                elif class_id == 1:
                                    stair_count += 1

            total_annotations += label_count
            class_counts[split]['ramp'] = ramp_count
            class_counts[split]['stair'] = stair_count

            print(f"   Total Objects: {label_count}")
            print(f"   - Ramps: {ramp_count} ({100*ramp_count/label_count:.1f}%)")
            print(f"   - Stairs: {stair_count} ({100*stair_count/label_count:.1f}%)")

            # Sample image info
            if img_count > 0:
                sample_img = list(images_path.glob('*.jpg'))[0]
                img = cv2.imread(str(sample_img))
                if img is not None:
                    h, w = img.shape[:2]
                    print(f"   Sample Image Size: {w}x{h}px")

    print(f"\n" + "=" * 70)
    print("DATASET SUMMARY:")
    print("=" * 70)
    print(f"Total Images: {total_images}")
    print(f"Total Annotations: {total_annotations}")

    total_ramps = sum(c['ramp'] for c in class_counts.values())
    total_stairs = sum(c['stair'] for c in class_counts.values())

    print(f"\nClass Distribution (All Sets):")
    print(f"  - Ramps:  {total_ramps} ({100*total_ramps/total_annotations:.1f}%)")
    print(f"  - Stairs: {total_stairs} ({100*total_stairs/total_annotations:.1f}%)")

    print(f"\nData Split Ratio:")
    print(f"  - Train: {class_counts['train']['ramp'] + class_counts['train']['stair']} objects")
    print(f"  - Valid: {class_counts['valid']['ramp'] + class_counts['valid']['stair']} objects")
    print(f"  - Test:  {class_counts['test']['ramp'] + class_counts['test']['stair']} objects")

    print("\n" + "=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70)

if __name__ == "__main__":
    analyze_dataset()
