#!/usr/bin/env python3
"""
Download YOLOv11n model weights (required for training)
Run this once before training to download the pretrained weights
"""

from ultralytics import YOLO
import os

def download_model():
    print("🔽 Downloading YOLOv11n pretrained weights...")
    print("⏳ This will take a minute or two on first run...")

    try:
        # This will download the model from Ultralytics servers
        model = YOLO('yolov11n')
        print("✅ Model downloaded successfully!")
        print(f"📂 Model stored in: {os.path.expanduser('~')}/yolo_models/")
        return True
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False

if __name__ == "__main__":
    download_model()
