#!/usr/bin/env python3
"""
YOLOv11 Inference Script for Stair and Ramp Detection
"""

from ultralytics import YOLO
import cv2
import os
from pathlib import Path

def run_inference_single(image_path, model_path, conf=0.5):
    """Run inference on a single image"""
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        print(f"⚠️  Train the model first: python scripts/train.py")
        return None

    print(f"🔍 Running inference on: {image_path}")
    model = YOLO(model_path)
    results = model.predict(source=image_path, conf=conf, save=True, project=os.path.expanduser("./results"), name='single')

    print(f"✅ Inference complete!")
    return results

def run_inference_batch(images_dir, model_path, conf=0.5):
    """Run inference on all images in a directory"""
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        print(f"⚠️  Train the model first: python scripts/train.py")
        return None

    if not os.path.exists(images_dir):
        print(f"❌ Images directory not found: {images_dir}")
        return None

    img_count = len([f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"🔍 Running inference on {img_count} images from: {images_dir}")

    model = YOLO(model_path)
    results = model.predict(
        source=images_dir,
        conf=conf,
        save=True,
        project=os.path.expanduser("./results"),
        name='batch',
        exist_ok=True
    )

    print(f"✅ Batch inference complete!")
    print(f"📂 Results saved to: ./results/batch")
    return results

def run_inference_video(video_path, model_path, conf=0.5):
    """Run inference on a video"""
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        print(f"⚠️  Train the model first: python scripts/train.py")
        return None

    print(f"🎥 Running inference on video: {video_path}")
    model = YOLO(model_path)
    results = model.predict(
        source=video_path,
        conf=conf,
        save=True,
        project=os.path.expanduser("./results"),
        name='video'
    )

    print(f"✅ Video inference complete!")
    return results

if __name__ == "__main__":
    # Set paths (relative to script location)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    model_path = str(project_root / "runs" / "stair_ramp_detection" / "weights" / "best.pt")
    test_images = str(project_root / "dataset" / "test" / "images")

    print("=" * 60)
    print("YOLOv11 Stair & Ramp Detection - Inference")
    print("=" * 60)

    # Run batch inference
    run_inference_batch(test_images, model_path, conf=0.5)
