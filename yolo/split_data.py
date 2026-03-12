import os
import sys
import shutil
import random
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATASET_DIR, LABELS_OUT_DIR, NAVIABLE_DATASET_DIR


def split_dataset(image_dir, label_dir, output_root, split_ratio=0.8):
    output_path = Path(output_root)
    for subset in ["train", "val"]:
        (output_path / "images" / subset).mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / subset).mkdir(parents=True, exist_ok=True)

    img_path = Path(image_dir)
    lbl_path = Path(label_dir)

    all_images = [
        f
        for f in os.listdir(image_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    valid_pairs = []
    for img_name in all_images:
        stem = Path(img_name).stem
        expected_label = lbl_path / f"{stem}.txt"
        if expected_label.exists():
            valid_pairs.append((img_name, f"{stem}.txt"))

    if not valid_pairs:
        print("ERROR: No matching image-label pairs found.")
        return

    print(f"Found {len(valid_pairs)} matching pairs. Splitting now...")

    random.seed(42)
    random.shuffle(valid_pairs)

    split_idx = int(len(valid_pairs) * split_ratio)
    if split_idx == len(valid_pairs) and len(valid_pairs) > 0:
        split_idx -= 1

    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]

    def move_data(pairs, subset):
        for img_file, lbl_file in pairs:
            shutil.copy2(img_path / img_file, output_path / "images" / subset / img_file)
            shutil.copy2(lbl_path / lbl_file, output_path / "labels" / subset / lbl_file)
        return len(pairs)

    t_count = move_data(train_pairs, "train")
    v_count = move_data(val_pairs, "val")

    print("--- SPLIT SUMMARY ---")
    print(f"Total pairs processed: {len(valid_pairs)}")
    print(f"Moved to TRAIN: {t_count}")
    print(f"Moved to VAL:   {v_count}")
    print(f"Location: {output_path.absolute()}")


if __name__ == "__main__":
    split_dataset(
        str(DATASET_DIR / "images"),
        str(LABELS_OUT_DIR),
        str(NAVIABLE_DATASET_DIR),
    )
