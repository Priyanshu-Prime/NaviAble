#!/usr/bin/env python3
"""
YOLOv10 Training Script: Optimized for MacBook Pro M4 (MPS)
Classes: ramp, stair
"""

import os
import torch
from pathlib import Path
from ultralytics import YOLO

def main():
    # 1. Path Management
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Relative paths - adjust these if your folder names differ
    dataset_path = str(project_root / "dataset" / "data.yaml")
    runs_dir = str(project_root / "runs")

    os.makedirs(runs_dir, exist_ok=True)

    # 2. Hardware Selection (M4 Optimization)
    if torch.backends.mps.is_available():
        device = 'mps'
        print("🚀 Hardware Detected: Apple Silicon (MPS)")
    elif torch.cuda.is_available():
        device = 0
        print("🚀 Hardware Detected: NVIDIA GPU (CUDA)")
    else:
        device = 'cpu'
        print("⚠️  Hardware Detected: CPU (Training will be slow)")

    # 3. Model Initialization
    # Loading YOLOv10n (Nano) for high speed and mobile-readiness
    print("📦 Loading YOLOv10n pretrained weights...")
    model = YOLO('yolov10n.pt')

    # 4. Starting Training
    # Batch size of 32-64 is usually the sweet spot for M4 chips
    print(f"🔥 Training starting at 640x640 on {device}...")

    results = model.train(
        data=dataset_path,
        epochs=150,           # 150 is solid for 11k images
        imgsz=640,            # Standard for YOLOv10 architecture
        device=device,
        batch=32,             # Higher batch size takes advantage of M4's Unified Memory
        workers=8,            # Uses M4 efficiency cores for data loading
        patience=25,          # Stop if no improvement for 25 epochs
        save=True,
        project=runs_dir,
        name='stair_ramp_m4_v1',
        exist_ok=True,

        # Hyperparameters for structural recognition
        mosaic=1.0,           # Helps with small-to-medium object detection
        mixup=0.1,            # Prevents overfitting on similar textures
        augment=True,
        flipud=0.5,           # Stairs/Ramps look similar regardless of vertical flip
        fliplr=0.5,

        # Advanced optimizations
        amp=True,             # Automatic Mixed Precision for speed
        val=True,             # Validate every epoch
        plots=True            # Save training charts
    )

    print("\n" + "="*40)
    print("✅ TRAINING FINISHED")
    print(f"📂 Results saved to: {results.save_dir}")
    print(f"🏆 Best weights: {results.save_dir}/weights/best.pt")
    print("="*40)

if __name__ == "__main__":
    main()
