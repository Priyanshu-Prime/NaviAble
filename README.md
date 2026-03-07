# NaviAble - Object Detection & Review Integrity for Accessibility

NaviAble is a dual-module accessibility system combining **YOLO object detection** with a **RoBERTa-based NLP integrity engine** to support safer navigation and trustworthy accessibility information.

### Module 1: Object Detection (YOLO)
Identifies accessibility-related obstacles and features in images/video:
- **Steps** - Detect stairs and steps
- **Stairs** - Multi-step stairways
- **Ramps** - Alternative accessible pathways
- **Grab Bars** - Handrails and support structures

### Module 2: Review Integrity Engine (RoBERTa)
A fine-tuned RoBERTa classifier that flags generic "accessibility-washed" reviews vs. spatially specific genuine reviews:
- **LABEL_0** - Flagged as generic / accessibility washing
- **LABEL_1** - Verified as genuine / spatially specific

This project helps create safer navigation systems for people with mobility challenges.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Project Structure](#project-structure)
4. [Using Your Own Dataset](#using-your-own-dataset)
5. [Running Inference](#running-inference)
6. [Training the YOLO Model](#training-the-yolo-model)
7. [NLP Integrity Module](#nlp-integrity-module)
8. [Roboflow Dataset Integration](#roboflow-dataset-integration)
9. [Utilities](#utilities)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start, make sure you have:
- **Python 3.8 or higher** (check with `python --version`)
- **pip** (Python package manager, usually comes with Python)
- **Git** (optional, for version control)

### Check Your Python Installation
```powershell
python --version
pip --version
```

---

## Setup Instructions

### Step 1: Clone or Download the Project

If you have this project as a ZIP file, extract it to your desired location. If using Git:
```powershell
git clone <repository-url>
cd NaviAble_Project
```

### Step 2: Create a Virtual Environment

A virtual environment keeps your project dependencies isolated. Navigate to the project folder in PowerShell and run:

```powershell
python -m venv venv
```

This creates a `venv/` folder containing all necessary Python files.

### Step 3: Activate the Virtual Environment

**On Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` appear at the beginning of your command prompt.

> **Troubleshooting**: If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 4: Install Dependencies

With the virtual environment activated, install all required packages:

**Option A: Using requirements.txt (Recommended)**
```powershell
pip install -r requirements.txt
```

**Option B: Install individually**
```powershell
pip install ultralytics opencv-python pyyaml pillow
pip install transformers datasets evaluate pandas roboflow
```

This installs:
- **ultralytics** - YOLO detection framework
- **opencv-python** - Image processing
- **pyyaml** - Dataset configuration files
- **pillow** - Advanced image operations
- **torch/torchvision** - Deep learning backends
- **transformers** - Hugging Face library for RoBERTa
- **datasets** - Hugging Face dataset utilities
- **evaluate** - Model evaluation metrics
- **pandas** - Data manipulation for NLP dataset
- **roboflow** - Dataset download from Roboflow

### Step 5: Verify Installation

Test if everything is installed correctly:
```powershell
python -c "from ultralytics import YOLO; print('Installation successful!')"
```

---

## Project Structure

```
NaviAble_Project/
├── README.md                      # This file
├── .gitignore                     # Git configuration
├── requirements.txt               # All Python dependencies
├── data.yaml                      # Dataset configuration (original)
│
├── yolo11n.pt                     # Pre-trained YOLO11 nano model
├── yolov8n.pt                     # Pre-trained YOLOv8 nano model
│
│── ── YOLO Scripts ──
├── convert_annotations.py         # Convert XML annotations to YOLO format
├── split_data.py                  # Split dataset into train/val
├── train_dataset_2.py             # Train YOLO on Roboflow dataset
├── dataset_2.py                   # Download dataset from Roboflow
│
│── ── NLP Scripts ──
├── generate_nlp_data.py           # Generate accessibility_reviews.csv
├── train_roberta.py               # Fine-tune RoBERTa integrity classifier
├── test_roberta.py                # Test the trained RoBERTa model
├── accessibility_reviews.csv      # Generated NLP training data
│
├── dataset/                       # Your raw annotated dataset
│   ├── wm_annotations.xml         # Annotations in XML format
│   └── images/                    # Raw image files
│
├── NaviAble_Dataset/              # Processed dataset (train/val split)
│   ├── images/
│   │   ├── train/                 # Training images
│   │   └── val/                   # Validation images
│   └── labels/
│       ├── train/                 # Training labels (YOLO format)
│       └── val/                   # Validation labels (YOLO format)
│
├── stair-and-ramp-2/              # Roboflow-downloaded dataset
│   ├── data.yaml
│   ├── train/
│   ├── valid/
│   └── test/
│
├── labels_out/                    # Converted label files (temporary)
│
├── runs/                          # YOLO training and inference results
│   └── detect/
│       ├── NaviAble_v11/          # YOLO11 training run
│       ├── NaviAble_v83/          # YOLOv8 training run
│       └── NaviAble_Week5/        # Week 5 comparative run
│
├── NaviAble_RoBERTa/              # RoBERTa intermediate checkpoints
├── NaviAble_RoBERTa_Checkpoints/  # RoBERTa training checkpoints
├── NaviAble_RoBERTa_Final/        # Final trained RoBERTa model
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer.json
│   ├── tokenizer_config.json
│   └── training_args.bin
│
└── venv/                          # Virtual environment (auto-created)
```

---

## Using Your Own Dataset

### Step 1: Prepare Your Images

1. Create a folder: `dataset/images/`
2. Place all your images (.jpg, .png) in this folder

### Step 2: Create Annotations

You have two options:

#### Option A: Using a Labeling Tool
Use **Roboflow** or **LabelImg** to annotate your images:
1. Download and install [LabelImg](https://github.com/heartexplorer/labelImg)
2. Set the format to **YOLO**
3. Annotate your images
4. Export labels as `.txt` files

#### Option B: Convert from XML
If you have XML annotations (like `wm_annotations.xml`):

1. Edit `convert_annotations.py` and update the classes list to match your objects:
   ```python
   classes = ["your_class_1", "your_class_2", "your_class_3"]
   ```

2. Run the conversion:
   ```powershell
   python convert_annotations.py
   ```

### Step 3: Split Your Dataset

Once you have images and labels, split them into training and validation sets:

```powershell
python split_data.py
```

This script:
- Matches images with their labels
- Creates train/val folders
- Defaults to 80% training / 20% validation

### Step 4: Update data.yaml

Edit `data.yaml` with your dataset path and classes:

```yaml
path: C:/your/path/to/NaviAble_Dataset

train: images/train
val: images/val

nc: 4                              # Number of classes
names: ['class1', 'class2', 'class3', 'class4']  # Class names in order
```

---

## Running Inference

### Option 1: Run Detection on Images

```powershell
python -c "
from ultralytics import YOLO

# Load model
model = YOLO('yolo11n.pt')

# Run inference
results = model.predict(source='path/to/your/image.jpg', conf=0.5)

# Save results
results[0].save('detection_result.jpg')
print('Detection complete!')
"
```

### Option 2: Run Detection on a Folder

```powershell
python -c "
from ultralytics import YOLO

model = YOLO('yolo11n.pt')
results = model.predict(source='path/to/images/folder', conf=0.5)
"
```

### Option 3: Run Detection on Video

```powershell
python -c "
from ultralytics import YOLO

model = YOLO('yolo11n.pt')
results = model.predict(source='path/to/video.mp4', conf=0.5)
"
```

### Confidence Threshold
- `conf=0.5` - Detections with 50%+ confidence (adjust as needed)
- Higher value = fewer but more confident detections
- Lower value = more detections, including uncertain ones

---

## Training the YOLO Model

### Train on Your Dataset

```powershell
python -c "
from ultralytics import YOLO

# Load pre-trained model
model = YOLO('yolo11n.pt')

# Train
results = model.train(
    data='data.yaml',
    epochs=100,
    imgsz=640,
    device=0,  # Use GPU (change to 'cpu' if no GPU available)
    patience=20
)
"
```

### Training Parameters
- **epochs** - Number of training cycles (default: 100)
- **imgsz** - Image size in pixels (default: 640)
- **device** - 0 for GPU, 'cpu' for CPU
- **patience** - Stop early if no improvement after N epochs

### Monitor Training

Training results are saved in `runs/detect/train/`:
- `results.csv` - Metrics over epochs
- `confusion_matrix.png` - Classification performance
- `best.pt` - Best model weights

---

## NLP Integrity Module

The NaviAble Integrity Engine uses a fine-tuned **RoBERTa** model to classify accessibility reviews as either genuinely detailed or generic "accessibility washing".

### Step 1: Generate Training Data

```powershell
python generate_nlp_data.py
```

This creates `accessibility_reviews.csv` with labeled samples:
- **Label 0** - Generic / accessibility-washed reviews (e.g., "Fully accessible, 5 stars!")
- **Label 1** - Genuine / spatially specific reviews (e.g., "The ramp has a 1:12 slope with handrails at 34 inches")

### Step 2: Train the RoBERTa Classifier

```powershell
python train_roberta.py
```

This fine-tunes `roberta-base` for 5 epochs and saves results to:
- `NaviAble_RoBERTa_Checkpoints/` - Intermediate checkpoints
- `NaviAble_RoBERTa_Final/` - Best performing model

### Step 3: Test the Model

```powershell
python test_roberta.py
```

Runs the trained model against sample reviews and displays confidence scores:
```
NAVIABLE INTEGRITY ENGINE RESULTS
========================================
Review: "Everything is fully accessible, 5 stars!"
Result: FLAGGED: GENERIC / WASHING (98.5% confidence)

Review: "The entrance has a 1:12 slope ramp with handrails at 34 inches height."
Result: VERIFIED GENUINE (97.2% confidence)
```

---

## Roboflow Dataset Integration

Use `dataset_2.py` to download an annotated stair-and-ramp dataset from Roboflow:

```powershell
python dataset_2.py
```

This downloads the dataset into `stair-and-ramp-2/` in YOLOv8 format with train/valid/test splits.

### Train YOLO on the Roboflow Dataset

```powershell
python train_dataset_2.py
```

This trains YOLO11 on the downloaded Roboflow dataset for 25 epochs and saves results to `NaviAble_Week5/`.

> **Note**: `dataset_2.py` contains a Roboflow API key. Do **not** commit this file with your real key — use environment variables or a `.env` file for production use.

---

## Utilities

### Convert XML Annotations to YOLO Format

Edit the classes in the script, then run:
```powershell
python convert_annotations.py
```

This creates `.txt` files in `labels_out/` with normalized bounding box coordinates.

### Split Dataset into Train/Val

```powershell
python split_data.py
```

By default uses 80/20 split. Edit the script to customize.

---

## Troubleshooting

### Virtual Environment Won't Activate
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

### Dependencies Installation Fails
```powershell
pip install --upgrade pip
pip install ultralytics opencv-python pyyaml pillow
```

### CUDA/GPU not detected
Install for CPU instead:
```powershell
python -c "from ultralytics import YOLO; model = YOLO('yolo11n.pt'); model.train(data='data.yaml', device='cpu')"
```

### Model file too large
Pre-trained models are downloaded on first use. Check your internet connection and disk space.

---

## Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created (`python -m venv venv`)
- [ ] Virtual environment activated (`.\venv\Scripts\Activate.ps1`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Prepare your dataset (images + annotations)
- [ ] Run `convert_annotations.py` if needed
- [ ] Run `split_data.py` to create train/val split
- [ ] Update `data.yaml` with correct paths and classes
- [ ] Run YOLO inference or training
- [ ] Run `generate_nlp_data.py` to create NLP training data
- [ ] Run `train_roberta.py` to train the integrity classifier
- [ ] Run `test_roberta.py` to verify the NLP model

---

## Additional Resources

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [YOLO Format Explanation](https://roboflow.com/formats/yolo-darknet-txt)
- [LabelImg for Annotation](https://github.com/heartexplabs/labelImg)
- [Hugging Face Transformers Documentation](https://huggingface.co/docs/transformers/)
- [RoBERTa Paper](https://arxiv.org/abs/1907.11692)
- [Roboflow Documentation](https://docs.roboflow.com/)

---

## Support

For issues or questions:
1. Check the [Ultralytics GitHub Issues](https://github.com/ultralytics/ultralytics/issues)
2. Review the troubleshooting section above
3. Verify your dataset format matches YOLO requirements

---

**Happy detecting! 🎯**
