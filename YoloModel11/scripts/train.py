#!/usr/bin/env python3
"""
YOLOv10 Training Script for Stair and Ramp Detection
Classes: ramp, stair
"""

from ultralytics import YOLO
import os
from pathlib import Path
import torch

def main():
    # Set paths (relative to script location)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    dataset_path = str(project_root / "dataset" / "data.yaml")
    models_dir = str(project_root / "models")
    runs_dir = str(project_root / "runs")

    # Create directories if they don't exist
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)

    # Check device
    device = 0 if torch.cuda.is_available() else 'cpu'
    print(f"🖥️  Device: {'GPU' if device == 0 else 'CPU'}")

    # Load YOLOv10n model (nano - good balance of speed/accuracy)
    # Options: yolov10n (nano), yolov10s (small), yolov10m (medium), yolov10l (large), yolov10x (xlarge)
    print("📦 Loading YOLOv10n pretrained model...")
    model = YOLO('yolov10n.pt')

    # Train the model
    print("🚀 Starting training...")
    print(f"📊 Dataset: {dataset_path}")
    print(f"📈 Training Configuration:")
    print(f"   - Epochs: 150")
    print(f"   - Image Size: 640x640")
    print(f"   - Batch Size: 16")
    print(f"   - Device: GPU (if available)")

    results = model.train(
        data=dataset_path,
        epochs=150,
        imgsz=640,
        device=device,  # Auto-detected GPU or CPU
        batch=16,
        patience=25,  # Early stopping patience
        save=True,
        project=runs_dir,
        name='stair_ramp_detection',
        exist_ok=True,
        verbose=True,
        plots=True,
        mosaic=1.0,
        augment=True,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        flipud=0.5,
        fliplr=0.5,
        perspective=0.0,
        warmup_epochs=3,
        warmup_momentum=0.8,
    )

    print(f"\n✅ Training complete!")
    print(f"📂 Results saved to: {results.save_dir}")
    print(f"🏆 Best model: {results.save_dir}/weights/best.pt")

if __name__ == "__main__":
    main()
