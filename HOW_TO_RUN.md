# NaviAble — How to Run

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Model weights (see below)

## 1. Clone & set up Python environment

```bash
git clone <repo>
cd NaviAble
python -m venv backend/.venv
source backend/.venv/bin/activate        # Windows: backend\.venv\Scripts\activate
pip install -r backend/requirements.txt
```

## 2. Start the database

```bash
docker compose up -d
```

PostGIS runs on `localhost:5432`. Wait ~10 s for the health check to pass:
```bash
docker compose ps   # Status should show "healthy"
```

## 3. Configure environment

```bash
cp .env.example .env
# Edit .env to set:
#   YOLO_WEIGHTS_PATH  — path to YoloModel11/runs/.../best.pt
#   ROBERTA_CHECKPOINT_DIR — path to NaviAble_RoBERTa_Final/
```

Default `.env` values already point to the expected paths relative to the repo root.

## 4. Run database migrations

```bash
cd backend
alembic upgrade head
cd ..
```

## 5. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The server is ready when you see `naviable.ready` in the logs.

**Without model weights** — the app starts in stub mode (stubs return 0.5 for both scores) and all endpoints work:

```bash
# Weights missing → automatic stub mode, no flag needed
uvicorn app.main:app --reload --port 8000
```

## 6. Test the API

### Health check
```bash
curl http://localhost:8000/healthz
# {"status":"ok","db":"ok"}
```

### Submit a contribution
```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -F "image=@/path/to/ramp.jpg" \
  -F "review=There is a gentle ramp at the back entrance" \
  -F "latitude=12.9716" \
  -F "longitude=77.5946" \
  -F "rating=4"
```

Response:
```json
{
  "id": "...",
  "trust_score": 0.68,
  "vision_score": 0.87,
  "nlp_score": 0.41,
  "visibility_status": "CAVEAT",
  "detected_features": {"ramp": [{"confidence": 0.87, "bbox": [0.1, 0.2, 0.6, 0.9]}]}
}
```

### Find nearby contributions
```bash
curl "http://localhost:8000/api/v1/contributions/nearby?latitude=12.9716&longitude=77.5946&radius_m=500"
```

### Interactive API docs
Open http://localhost:8000/docs in a browser.

## 7. Run tests

```bash
cd backend
python -m pytest tests/ -v
```

Tests that require a live PostGIS (health, verify integration) are skipped automatically when the DB is not running.

## Visibility status logic

| Trust Score | Status | What it means |
|------------|--------|---------------|
| ≥ 0.70 | `PUBLIC` | Shown on map immediately |
| 0.40–0.69 | `CAVEAT` | Shown with warning, queued for moderation |
| < 0.40 | `HIDDEN` | Stored, never shown publicly |

Trust Score = `0.60 × vision_score + 0.40 × nlp_score`

## Model weights

| Model | Path | Notes |
|-------|------|-------|
| YOLOv11 | `YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt` | Auto-detected; falls back to stub |
| RoBERTa | `NaviAble_RoBERTa_Final/` | HuggingFace checkpoint dir; falls back to stub |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://naviable:naviable_dev@localhost:5432/naviable` | Postgres+PostGIS URL |
| `YOLO_WEIGHTS_PATH` | `YoloModel11/runs/stair_ramp_m4_v1/weights/best.pt` | Path to YOLO weights |
| `ROBERTA_CHECKPOINT_DIR` | `NaviAble_RoBERTa_Final` | Path to RoBERTa checkpoint |
| `VISION_THRESHOLD` | `0.205` | YOLO detection confidence threshold |
| `VISION_WEIGHT` | `0.60` | Vision score weight in trust fusion |
| `NLP_WEIGHT` | `0.40` | NLP score weight in trust fusion |
| `UPLOAD_DIR` | `backend/uploads` | Local upload storage dir |
| `MAX_IMAGE_BYTES` | `10485760` | Max upload size (10 MB) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base URL for image links |
| `NAVIABLE_CORS_ORIGINS` | `*` | Comma-separated CORS origins |
