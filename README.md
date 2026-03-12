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
4. [YOLO Object Detection](#yolo-object-detection)
5. [NLP Integrity Module](#nlp-integrity-module)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.8+** (`python --version`)
- **pip** (Python package manager)
- **Git**
- **CUDA-capable GPU** (optional, for faster training)

---

## Setup Instructions

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd NaviAble_Project
```

### 2. Create & Activate Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your API keys:
```
GROQ_API_KEY=your_groq_api_key_here
ROBOFLOW_API_KEY=your_roboflow_api_key_here
```

> **Important**: `.env` is gitignored and will never be committed.

### 5. Verify Installation

```powershell
python -c "from config import *; print('Setup OK')"
```

---

## Project Structure

```
NaviAble_Project/
├── README.md                      # This file
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment variables template
├── requirements.txt               # Python dependencies
├── config.py                      # Centralized configuration (loads .env)
├── data.yaml                      # YOLO dataset configuration
│
├── yolo/                          # YOLO Object Detection module
│   ├── convert_annotations.py     # Convert XML annotations → YOLO format
│   ├── split_data.py              # Split dataset into train/val (80/20)
│   ├── download_roboflow.py       # Download dataset from Roboflow API
│   └── train_yolo.py              # Train YOLOv11n on downloaded dataset
│
├── nlp/                           # NLP Review Integrity module
│   ├── generate_synthetic_data.py # Generate synthetic training samples
│   ├── generate_review_data.py    # Download & auto-label 10K Yelp reviews
│   ├── get_targeted_reviews.py    # Filter reviews for accessibility keywords
│   ├── balance_data.py            # Balance 650K reviews into 8K dataset
│   ├── generate_llm_labels.py     # Label 1K reviews via Groq LLM API
│   ├── mine_real_data.py          # Auto-mine genuine accessibility reviews
│   ├── merge_data.py              # Merge & balance all mined datasets
│   ├── train_roberta.py           # Fine-tune RoBERTa classifier (5 epochs)
│   ├── test_roberta.py            # Interactive CLI for testing predictions
│   ├── compare_models.py          # Compare RoBERTa vs regex baseline
│   └── plot_metrics.py            # Generate training loss/accuracy graphs
│
├── dataset/                       # Raw images & XML annotations (gitignored)
├── NaviAble_Dataset/              # Processed train/val split (gitignored)
├── labels_out/                    # Converted YOLO labels (gitignored)
├── stair-and-ramp-2/              # Roboflow dataset (gitignored)
├── runs/                          # YOLO training outputs (gitignored)
├── NaviAble_RoBERTa_Checkpoints/  # RoBERTa training checkpoints (gitignored)
├── NaviAble_RoBERTa_Final/        # Final trained RoBERTa model (gitignored)
└── venv/                          # Virtual environment (gitignored)
```

All API keys are loaded from `.env` via the centralized `config.py` module — no secrets are stored in source code.

---

## YOLO Object Detection

### Prepare Your Dataset

1. Place images in `dataset/images/`
2. Convert XML annotations to YOLO format:
   ```powershell
   python yolo/convert_annotations.py
   ```
3. Split into train/val sets:
   ```powershell
   python yolo/split_data.py
   ```
4. Update `data.yaml` with your class names if needed.

### Download Roboflow Dataset (Alternative)

```powershell
python yolo/download_roboflow.py
```

### Train YOLO

```powershell
python yolo/train_yolo.py
```

### Run Inference

```powershell
python -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
results = model.predict(source='path/to/image.jpg', conf=0.5)
results[0].save('result.jpg')
"
```

---

## NLP Integrity Module

### Data Pipeline

The NLP pipeline builds training data in stages. Run them in order:

```powershell
# Step 1: Generate synthetic samples (quick baseline)
python nlp/generate_synthetic_data.py

# Step 2: Download & auto-label 10K Yelp reviews
python nlp/generate_review_data.py

# Step 3: Filter for accessibility-specific reviews
python nlp/get_targeted_reviews.py

# Step 4: Balance the full 650K dataset
python nlp/balance_data.py

# Step 5: Label reviews with Groq LLM (requires GROQ_API_KEY)
python nlp/generate_llm_labels.py

# Step 6: Mine more genuine reviews (requires GROQ_API_KEY)
python nlp/mine_real_data.py

# Step 7: Merge and balance all datasets
python nlp/merge_data.py
```

### Train the Model

```powershell
python nlp/train_roberta.py
```

Fine-tunes `roberta-base` for 5 epochs. Model saved to `NaviAble_RoBERTa_Final/`.

### Test the Model

```powershell
python nlp/test_roberta.py
```

Interactive CLI — type any review text and get a prediction with confidence score.

### Compare RoBERTa vs Regex

```powershell
python nlp/compare_models.py
```

### Plot Training Metrics

```powershell
python nlp/plot_metrics.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Virtual env won't activate | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| pip install fails | `pip install --upgrade pip` then retry |
| CUDA not detected | Add `device='cpu'` to training calls |
| Missing API key error | Ensure `.env` exists with valid keys (see Setup step 4) |
| Model file not found | Run the training script first to generate the model |

---

## Resources

- [Ultralytics YOLO Docs](https://docs.ultralytics.com/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [RoBERTa Paper](https://arxiv.org/abs/1907.11692)
- [Roboflow Docs](https://docs.roboflow.com/)
