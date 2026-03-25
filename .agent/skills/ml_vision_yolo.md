# Skill: YOLOv11 Vision Integration

## Purpose
Handle physical infrastructure detection logic.

## Execution Directives
1. **Initialization**: `from ultralytics import YOLO`. Load `./models/yolov11_naviable.pt`.
2. **Inference Pipeline**: 
   - Receive OpenCV image array.
   - Run `results = model(image, conf=0.5, iou=0.45)`.
   - Parse `results[0].boxes`. Extract `cls` (class ID), `conf` (confidence), and `xyxy` (bounding box coordinates).
3. **Output Standardization**: Map class IDs to human-readable strings (e.g., `0: 'Ramp'`, `1: 'Handrail'`). Return a clean dictionary to the API router.