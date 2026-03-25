# NaviAble — AI-Powered Accessibility Verification Platform

NaviAble is a community-driven accessibility platform built for the **IIIT Trichy Final Year Project (Team 7)**.  It uses a **Dual-AI Verification Architecture** — YOLOv11 for physical infrastructure detection and a fine-tuned RoBERTa model for review authenticity — to combat "accessibility washing" and give specially-abled users trustworthy information about whether a location is genuinely accessible.

---

## Running the Full Demo (5 minutes)

### Backend

```bash
cd backend/
pip install -r requirements.txt

# Demo mode — realistic synthetic results, no GPU required
NAVIABLE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

Windows PowerShell:
```powershell
$env:NAVIABLE_DEMO_MODE="true"
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

### Frontend Web App

In a second terminal:

```bash
cd frontend/
npm install
npm run dev
```

Open **http://localhost:5173** — upload a photo, write a review, and watch the Dual-AI pipeline return a Trust Score with YOLO bounding boxes.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    NaviAble Platform                         │
│                                                              │
│  ┌─────────────┐      POST /api/v1/verify                    │
│  │  React Web  │─────────────────────────────────►┐          │
│  │  Frontend   │◄────────────────────────────────┐│          │
│  └─────────────┘      VerificationResponse       ││          │
│                                                  ││          │
│  ┌───────────────────────────────────────────────┼┼───────┐  │
│  │              FastAPI Backend                  ││       │  │
│  │                                               ││       │  │
│  │  asyncio.gather() ──────────────────────────► ┘│       │  │
│  │       │                                        │       │  │
│  │       ├──► asyncio.to_thread ──► YOLOv11 ──► Vision   │  │
│  │       │                         (ramps,        Result  │  │
│  │       │                          handrails…)   │       │  │
│  │       │                                        │       │  │
│  │       └──► asyncio.to_thread ──► RoBERTa ──► NLP      │  │
│  │                                 (genuine vs    Result  │  │
│  │                                  generic)      │       │  │
│  │                                                │       │  │
│  │  Trust Score = 0.60×vision + 0.40×NLP ◄───────┘       │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
NaviAble/
├── backend/                       # FastAPI backend (Python)
│   ├── app/
│   │   ├── main.py                # App entry, CORS, lifespan
│   │   ├── core/config.py         # Env-var settings (DEMO_MODE, CORS)
│   │   ├── api/routers/
│   │   │   ├── verify.py          # POST /api/v1/verify
│   │   │   └── health.py          # GET /health
│   │   ├── schemas/verify.py      # Pydantic v2 response models
│   │   └── services/ml.py         # YoloVisionService + RobertaNLPService
│   ├── tests/
│   │   └── test_verify_api.py     # 23 TDD unit tests (all passing)
│   ├── requirements.txt
│   └── README.md                  # Backend docs
│
├── frontend/                      # React + Vite web demo
│   ├── src/
│   │   ├── App.jsx                # Root component + state machine
│   │   ├── App.css                # All styles
│   │   ├── api/client.js          # API client (fetchHealth, verifyAccessibility)
│   │   └── components/
│   │       ├── SubmitForm.jsx     # Drag-drop upload + text form
│   │       ├── Results.jsx        # Full results panel
│   │       ├── TrustScoreMeter.jsx# SVG circular gauge
│   │       └── DetectionViewer.jsx# Image + YOLO bounding boxes
│   ├── package.json
│   └── README.md                  # Frontend docs
│
├── yolo/                          # YOLOv11 training scripts
├── nlp/                           # RoBERTa training scripts
├── .agent/                        # AI agent context and workflows
└── README.md                      # This file
```

---

## Model Performance

| Model    | Metric           | Value    |
|----------|------------------|----------|
| YOLOv11  | mAP@0.5          | 47.29 %  |
| YOLOv11  | Precision        | 58.99 %  |
| YOLOv11  | Recall           | 46.34 %  |
| YOLOv11  | Training Epochs  | 25       |
| RoBERTa  | Val Accuracy     | 87.65 %  |
| RoBERTa  | Training Epochs  | 5        |
| RoBERTa  | Dataset Size     | 402 rows |

---

## Trust Score Formula

```
NaviAble Trust Score = 0.60 × mean(YOLO confidence) + 0.40 × RoBERTa confidence
```

| Range     | Interpretation                     |
|-----------|------------------------------------|
| ≥ 0.70    | Strong evidence of accessibility   |
| 0.40–0.69 | Partial evidence                   |
| < 0.40    | Insufficient evidence              |

---

## Backend API Reference

| Endpoint              | Method | Description                              |
|-----------------------|--------|------------------------------------------|
| `/api/v1/verify`      | POST   | Dual-AI verification (multipart/form)    |
| `/health`             | GET    | Backend health + ML service status       |
| `/docs`               | GET    | Swagger UI                               |
| `/redoc`              | GET    | ReDoc                                    |

See `backend/README.md` for full request/response schemas and environment variables.

---

## Environment Variables

| Variable             | Default | Description                                  |
|----------------------|---------|----------------------------------------------|
| `NAVIABLE_DEMO_MODE` | `false` | Return synthetic results without model weights |
| `YOLO_MODEL_PATH`    | `./models/yolov11_naviable.pt` | YOLOv11 weights path |
| `ROBERTA_MODEL_DIR`  | `./NaviAble_RoBERTa_Final`     | RoBERTa model dir    |
| `ROBERTA_DEVICE`     | `cpu`   | `cpu` or `cuda`                              |

---

## ML Training Scripts

### YOLO Object Detection

```bash
# Prepare dataset
python yolo/convert_annotations.py
python yolo/split_data.py

# Train (25 epochs, GTX 1650 Ti)
python yolo/train_yolo.py
```

### RoBERTa NLP Engine

```bash
# Build dataset (LLM Knowledge Distillation via Groq API)
python nlp/generate_llm_labels.py
python nlp/merge_data.py

# Train (5 epochs)
python nlp/train_roberta.py

# Interactive testing
python nlp/test_roberta.py
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- GPU optional (NVIDIA GTX 1650 Ti or better for real model inference)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend unreachable | Ensure `uvicorn` is running on port 8000 |
| Empty detection results | Set `NAVIABLE_DEMO_MODE=true` |
| CUDA OOM | Set `ROBERTA_DEVICE=cpu` (default) |
| Frontend CORS error | Check `NAVIABLE_CORS_ORIGINS` includes your frontend origin |
| Virtual env activation (Windows) | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## Resources

- [Ultralytics YOLOv11 Docs](https://docs.ultralytics.com/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vite.dev/)

---

*IIIT Trichy B.Tech CSE Final Year Project 2024 — Team 7*

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
