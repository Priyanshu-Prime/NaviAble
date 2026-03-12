import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("yolo11n.pt")

    dataset_yaml = str(PROJECT_ROOT / "stair-and-ramp-2" / "data.yaml")

    print("Starting YOLO Training on Roboflow Dataset...")
    results = model.train(
        data=dataset_yaml,
        epochs=25,
        imgsz=640,
        device="cuda",
        project="NaviAble_Week5",
        name="YOLOv11_Roboflow_Dataset",
        batch=8,
        workers=2,
    )

    print("Training Complete! Check the 'NaviAble_Week5' folder for your graphs.")
