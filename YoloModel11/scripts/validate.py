#!/usr/bin/env python3
"""
YOLOv11 Validation Script for Stair and Ramp Detection
"""

from ultralytics import YOLO
import os
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    dataset_path = str(project_root / "dataset" / "data.yaml")
    model_path = str(project_root / "runs" / "stair_ramp_detection" / "weights" / "best.pt")

    print("=" * 60)
    print("YOLOv11 Model Validation - Stair & Ramp Detection")
    print("=" * 60)

    if not os.path.exists(model_path):
        print(f"\n❌ Model not found at {model_path}")
        print(f"⚠️  Train the model first: python scripts/train.py")
        return

    print(f"\n📊 Validating model: {model_path}")
    print(f"📈 Dataset: {dataset_path}")

    model = YOLO(model_path)
    metrics = model.val()

    print("\n" + "=" * 60)
    print("Validation Results:")
    print("=" * 60)
    print(f"mAP@50:       {metrics.box.map50:.4f}")
    print(f"mAP@50-95:    {metrics.box.map:.4f}")
    print(f"Precision:    {metrics.box.mp:.4f}")
    print(f"Recall:       {metrics.box.mr:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
