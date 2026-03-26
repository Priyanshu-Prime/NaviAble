# NaviAble — Backend API

FastAPI backend for the **NaviAble** Dual-AI Accessibility Verification Platform.

The backend exposes a single primary endpoint (`POST /api/v1/verify`) that accepts a user-submitted image + text review and runs both a **YOLOv11 vision model** (physical infrastructure detection) and a **RoBERTa NLP classifier** (review authenticity) concurrently, returning a composite **NaviAble Trust Score**.

---

## Architecture Overview

```
POST /api/v1/verify
        │
        ├──► asyncio.to_thread → YoloVisionService.predict(image_bytes)
        │         └──► Detects: ramps, handrails, doorways, etc.
        │
        └──► asyncio.to_thread → RobertaNLPService.classify(text)
                  └──► Labels: "Genuine Physical Detail" vs "Generic Praise"

Trust Score = 0.60 × mean_vision_confidence + 0.40 × nlp_confidence
```

Both ML calls run **concurrently** using `asyncio.gather` so total latency equals `max(vision_time, nlp_time)` rather than the sum.  The synchronous, CPU/GPU-bound inference methods are dispatched via `asyncio.to_thread` to avoid blocking the async event loop.

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py                   # FastAPI app, lifespan, CORS
│   ├── core/
│   │   └── config.py             # Settings from environment variables
│   ├── api/
│   │   └── routers/
│   │       ├── verify.py         # POST /api/v1/verify
│   │       └── health.py         # GET /health
│   ├── schemas/
│   │   └── verify.py             # Pydantic v2 response models
│   └── services/
│       └── ml.py                 # YoloVisionService, RobertaNLPService
├── tests/
│   └── test_verify_api.py        # 23 TDD unit tests
├── requirements.txt
└── pytest.ini
```

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
cd backend/
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run in Demo Mode (no model weights required)

Demo mode returns realistic synthetic results so you can see the full pipeline in action without GPU hardware or trained weights.

```bash
NAVIABLE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell:
```powershell
$env:NAVIABLE_DEMO_MODE="true"
uvicorn app.main:app --reload --port 8000
```

### 4. Run with Real Models

Place the trained weights in the following locations:
- `backend/models/yolov11_naviable.pt` — YOLOv11 weights
- `backend/NaviAble_RoBERTa_Final/` — HuggingFace model directory

```bash
uvicorn app.main:app --reload --port 8000
```

---

## API Reference

### `POST /api/v1/verify`

Runs the Dual-AI verification pipeline.

**Request** (multipart/form-data):

| Field         | Type   | Description                              |
|---------------|--------|------------------------------------------|
| `text_review` | string | User's written review of the location    |
| `location_id` | UUID   | Identifier of the location being reviewed |
| `image`       | file   | JPEG or PNG photo of the location (≤10 MB) |

**Response** (200 OK):

```json
{
  "status": "success",
  "data": {
    "nlp_analysis": {
      "is_genuine": true,
      "confidence": 0.87,
      "label": "Genuine Physical Detail"
    },
    "vision_analysis": {
      "objects_detected": 2,
      "features": [
        {"class": "ramp",     "confidence": 0.62, "bbox": [10, 20, 150, 200]},
        {"class": "handrail", "confidence": 0.55, "bbox": [15, 25, 140, 190]}
      ]
    },
    "naviable_trust_score": 0.699
  }
}
```

**Error responses:**

| Code | Condition                                          |
|------|----------------------------------------------------|
| 400  | Unsupported image MIME type or file > 10 MB        |
| 422  | Missing required form fields                       |
| 503  | ML inference service temporarily unavailable        |

---

### `GET /health`

Returns service status for monitoring and the frontend connectivity check.

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "demo_mode": true,
  "services": {
    "yolo": "stub",
    "roberta": "stub"
  }
}
```

`"stub"` means no model weights are loaded; `"loaded"` means real inference is available.

---

## Environment Variables

| Variable               | Default                          | Description                                         |
|------------------------|----------------------------------|-----------------------------------------------------|
| `NAVIABLE_DEMO_MODE`   | `false`                          | Return synthetic results when models are absent     |
| `NAVIABLE_CORS_ORIGINS`| `http://localhost:5173,...`       | Comma-separated list of allowed CORS origins         |
| `YOLO_MODEL_PATH`      | `./models/yolov11_naviable.pt`   | Path to YOLOv11 `.pt` weights                       |
| `ROBERTA_MODEL_DIR`    | `./NaviAble_RoBERTa_Final`       | Path to HuggingFace model directory                 |
| `ROBERTA_DEVICE`       | `cpu`                            | `cpu`, `cuda`, or CUDA device index (`0`)           |

Create a `.env` file in the `backend/` directory to set these persistently:

```env
NAVIABLE_DEMO_MODE=true
NAVIABLE_CORS_ORIGINS=http://localhost:5173
```

---

## Running Tests

```bash
cd backend/
pytest -v
```

All 23 tests run without model weights or GPU — ML services are mocked.

---

## Trust Score Formula

```
trust_score = 0.60 × mean(vision_feature_confidences) + 0.40 × nlp_confidence
```

- **60 % weight on Vision**: Physical evidence (ramp, handrail, etc.) is harder to fake.
- **40 % weight on NLP**: Text analysis catches accessibility washing but is easier to game.
- Score range: `[0.0, 1.0]`
  - `≥ 0.70` — High confidence: genuine accessible location
  - `0.40–0.69` — Moderate: some evidence present
  - `< 0.40` — Low: insufficient evidence

---

## Interactive Docs

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
