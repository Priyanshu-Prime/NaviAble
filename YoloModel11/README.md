# YOLOv11 Stair & Ramp Detection Model

A YOLOv11 object detection model trained to detect stairs and ramps for accessibility analysis.

## Dataset Information

📊 **Dataset Overview:**
- **Total Images:** 11,173 (9,244 train + 1,345 val + 584 test)
- **Classes:** 2 (Ramp, Stair)
- **Format:** YOLO format (.txt files with normalized bounding boxes)
- **Source:** Roboflow - Stair and Ramp Detection Dataset v2

### Class Distribution
- **Ramps:** ~648 instances in training set (Class 0)
- **Stairs:** ~550 instances in training set (Class 1)

### Sample Images
The dataset contains real-world images of stairs and ramps from various angles and lighting conditions, suitable for accessibility assessment.

## Project Structure

```
YoloModel11/
├── dataset/                      # Extracted dataset
│   ├── train/                   # Training set (9,244 images)
│   │   ├── images/
│   │   └── labels/
│   ├── valid/                   # Validation set (1,345 images)
│   │   ├── images/
│   │   └── labels/
│   ├── test/                    # Test set (584 images)
│   │   ├── images/
│   │   └── labels/
│   └── data.yaml                # Dataset configuration
├── models/                       # Trained model weights
├── runs/                         # Training outputs and checkpoints
│   └── stair_ramp_detection/    # Default training run
│       ├── weights/
│       │   ├── best.pt          # Best model
│       │   └── last.pt          # Last checkpoint
│       ├── results.csv
│       ├── confusion_matrix.png
│       └── results/
├── scripts/                      # Python scripts
│   ├── train.py                 # Training script
│   ├── inference.py             # Inference script
│   ├── validate.py              # Validation script
│   └── analyze_dataset.py       # Dataset analysis
├── checkpoints/                  # Additional checkpoints
└── results/                      # Inference results
```

## Quick Start

### 1. Install Dependencies

```bash
pip install ultralytics opencv-python pillow numpy pyyaml torch torchvision
```

### 2. Analyze Dataset

```bash
cd YoloModel11
python scripts/analyze_dataset.py
```

### 3. Train the Model

```bash
cd YoloModel11
python scripts/train.py
```

**Training Parameters:**
- Model: YOLOv11n (nano)
- Epochs: 150
- Batch Size: 16
- Image Size: 640x640
- Early Stopping: Patience 25 epochs
- Device: GPU (if available)

**Training Output:**
- Best weights: `runs/stair_ramp_detection/weights/best.pt`
- Training metrics: `runs/stair_ramp_detection/results.csv`
- Plots: `runs/stair_ramp_detection/results/`

### 4. Validate Model

```bash
cd YoloModel11
python scripts/validate.py
```

Returns metrics:
- mAP@50
- mAP@50-95
- Precision
- Recall

### 5. Run Inference

#### On Test Dataset:
```bash
python scripts/inference.py
```

#### On Single Image:
```python
from scripts.inference import run_inference_single
run_inference_single(
    "path/to/image.jpg",
    "runs/stair_ramp_detection/weights/best.pt"
)
```

#### On Video:
```python
from scripts.inference import run_inference_video
run_inference_video(
    "path/to/video.mp4",
    "runs/stair_ramp_detection/weights/best.pt"
)
```

#### On Directory:
```python
from scripts.inference import run_inference_batch
run_inference_batch(
    "path/to/images/",
    "runs/stair_ramp_detection/weights/best.pt"
)
```

## Model Variants

The training script uses `yolov11n` (nano). You can modify it for other variants:

| Model | Parameters | Speed | Accuracy |
|-------|-----------|-------|----------|
| yolov11n | 2.6M | Fastest | Good |
| yolov11s | 9.2M | Fast | Better |
| yolov11m | 20.1M | Medium | Very Good |
| yolov11l | 25.3M | Slow | Excellent |
| yolov11x | 56.7M | Slowest | Best |

## Expected Performance

For 2-class detection (ramp/stair) with 9k+ training images:
- **mAP@50:** 0.85-0.95 (good)
- **Precision:** 0.85-0.90
- **Recall:** 0.80-0.90
- **Inference Speed:** ~15-30ms per image (GPU)

## Troubleshooting

### CUDA/GPU Issues
```bash
# Check if GPU is available
python -c "import torch; print(torch.cuda.is_available())"

# If False, training will default to CPU (slower but works)
```

### Out of Memory (OOM)
Reduce batch size in `scripts/train.py`:
```python
batch=8  # or 4 for smaller GPUs
```

### Training is Slow
- Use a smaller model variant (currently using nano which is fastest)
- Reduce image size: `imgsz=416`
- Use GPU instead of CPU

## Files Generated During Training

- `best.pt` - Best model weights (use this for inference)
- `last.pt` - Last epoch weights
- `results.csv` - Training metrics
- `confusion_matrix.png` - Class confusion matrix
- `results/` - Training plots (loss, precision, recall, etc.)

## References

- [YOLOv11 Documentation](https://docs.ultralytics.com/models/yolov11/)
- [YOLOv11 GitHub](https://github.com/ultralytics/ultralytics)
- [Original Dataset](https://universe.roboflow.com/peggy-cikj6/stair-and-ramp-qukcn/dataset/2)

## Notes

- All paths are now relative to the project directory
- Dataset is already extracted and ready to use
- Model will be trained from a pretrained YOLOv11n base (transfer learning)
- Training will create a new run each time unless `exist_ok=True` is set
