# 🚀 Quick Start - NaviAble with YOLOv10

## Start the System

```bash
./run.sh
```

This starts:
- ✅ Backend on http://localhost:8000
- ✅ Frontend on http://localhost:5173

---

## Use the System

### Option 1: Web Interface (Recommended) ⭐

**Open**: http://localhost:8000

This is the easiest way to use the system:
1. Click "Upload & Predict"
2. Drag-and-drop an image
3. See detected ramps/stairs with confidence scores
4. Fill out the review form
5. Submit

---

### Option 2: API Endpoints

#### Predict (YOLOv10) ✅
```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -F "image=@photo.jpg"
```

**Response**:
```json
{
  "prediction_id": "abc123",
  "objects_detected": 2,
  "features": [
    {"class": "ramp", "confidence": 0.876, "bbox": [50, 150, 400, 450]},
    {"class": "stair", "confidence": 0.823, "bbox": [100, 200, 350, 500]}
  ]
}
```

#### Submit Review
```bash
curl -X POST http://localhost:8000/api/v1/submit-review \
  -F "prediction_id=abc123" \
  -F "location_name=Main Street" \
  -F "location_type=entrance" \
  -F "review_text=Good ramp access" \
  -F "accessibility_rating=5" \
  -F "detected_features=[...]"
```

#### Verify (Dual-AI) ❌
```bash
# This endpoint requires RoBERTa which is not available
# Use /api/v1/predict instead
```

---

## What Works

✅ **YOLOv10 Predictions**
- Detects ramps and stairs
- 83.7% accuracy (mAP@50)
- Real-time inference

✅ **Web Interface**
- Beautiful UI at http://localhost:8000
- Image upload with drag-and-drop
- Confidence scores displayed
- Review submission

✅ **Data Storage**
- Images saved to `uploads/images/`
- Predictions saved as JSON
- Reviews saved as JSON

---

## What Doesn't Work

❌ **RoBERTa NLP Service**
- Failed to initialize
- `/api/v1/verify` endpoint unavailable
- Use `/api/v1/predict` instead

---

## Model Performance

```
Trained YOLOv10 (Epoch 32)
├─ mAP@50:     0.837 (83.7%)
├─ mAP@50-95:  0.611 (61.1%)
├─ Precision:  0.874 (87.4%)
└─ Recall:     0.877 (87.7%)

Classes: Ramp & Stair
Device: Apple Silicon (MPS)
```

---

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill the process
kill -9 <PID>

# Try again
./run.sh
```

### Slow predictions
- First prediction: 2-3 seconds (model warmup)
- Subsequent: ~1 second (on MPS)
- This is normal!

### Can't upload images
- Check file format: PNG or JPG only
- Check file size: max 10MB
- Check network: ensure localhost:8000 is accessible

---

## Data Location

```
uploads/
├── images/2026-05-02/          # Photos
├── predictions/2026-05-02/     # Detection results
└── reviews/2026-05-02/         # User reviews
```

All files are organized by date for easy export and retraining.

---

## Next Steps

1. ✅ Test with sample images
2. ✅ Submit reviews for each image
3. ✅ Collect real-world data
4. ✅ Use collected data for model improvement
5. ✅ Deploy to production

---

## Support

If something doesn't work:
1. Check http://localhost:8000/health (should return status: "healthy")
2. Look at backend logs for errors
3. Use web interface instead of API (simpler debugging)
4. Read YOLO_INTEGRATION_GUIDE.md for technical details

---

**Status**: ✅ Ready to detect accessibility features!
