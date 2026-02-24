# NaviAble - Object Detection for Accessibility

NaviAble is an object detection system based on YOLOv8/YOLO11 that identifies accessibility-related obstacles and features, including:
- **Steps** - Detect stairs and steps
- **Stairs** - Multi-step stairways
- **Ramps** - Alternative accessible pathways
- **Grab Bars** - Handrails and support structures

This project helps create safer navigation systems for people with mobility challenges.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Project Structure](#project-structure)
4. [Using Your Own Dataset](#using-your-own-dataset)
5. [Running Inference](#running-inference)
6. [Training the Model](#training-the-model)
7. [Utilities](#utilities)

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
```

This installs:
- **ultralytics** - YOLO detection framework
- **opencv-python** - Image processing
- **pyyaml** - Dataset configuration files
- **pillow** - Advanced image operations
- **torch/torchvision** - Deep learning backends

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
├── data.yaml                      # Dataset configuration
│
├── yolo11n.pt                     # Pre-trained YOLO11 nano model
├── yolov8n.pt                     # Pre-trained YOLOv8 nano model
│
├── convert_annotations.py         # Convert XML annotations to YOLO format
├── split_data.py                  # Split dataset into train/val
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
├── labels_out/                    # Converted label files (temporary)
│
├── runs/                          # Training and inference results
│   └── detect/
│       └── NaviAble_v11/          # Results from latest run
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

## Training the Model

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
- [ ] Dependencies installed (`pip install ultralytics opencv-python pyyaml pillow`)
- [ ] Prepare your dataset (images + annotations)
- [ ] Run `convert_annotations.py` if needed
- [ ] Run `split_data.py` to create train/val split
- [ ] Update `data.yaml` with correct paths and classes
- [ ] Run inference or training

---

## Additional Resources

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [YOLO Format Explanation](https://roboflow.com/formats/yolo-darknet-txt)
- [LabelImg for Annotation](https://github.com/heartexplorer/labelImg)

---

## Support

For issues or questions:
1. Check the [Ultralytics GitHub Issues](https://github.com/ultralytics/ultralytics/issues)
2. Review the troubleshooting section above
3. Verify your dataset format matches YOLO requirements

---

**Happy detecting! 🎯**
