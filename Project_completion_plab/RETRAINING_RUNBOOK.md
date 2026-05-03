# NaviAble retraining runbook

Run this **monthly** or whenever PUBLIC contributions cross +500 since
the last cut.

## 1. Cut a fresh dataset

```bash
cd backend
ADMIN_TOKEN=$(grep ADMIN_TOKEN ../.env | cut -d= -f2)
python -m app.cli.training_export \
  --since "$(psql -U naviable -d naviable -h localhost -p 5432 -tAc \
                "SELECT COALESCE(MAX(cutoff_ended_at)::text, '2025-01-01') FROM training_exports;")" \
  --notes "monthly cut $(date +%Y-%m)"
```

## 2. Sanity-check the data

```bash
cd backend/training_exports/<latest>
ls yolo/images | wc -l        # >= 50 for a useful YOLO step
wc -l roberta/train.csv       # >= 100 for a useful RoBERTa step
```

## 3. Vision retraining (YOLOv11)

```bash
cd YoloModel11
python scripts/train.py --data ../backend/training_exports/<latest>/yolo/data.yaml \
                       --weights runs/stair_ramp_m4_v1/weights/best.pt \
                       --epochs 30 --imgsz 1280 --project runs --name stair_ramp_m5_v1
```

Validate against `NaviAble_Dataset/test`. mAP@0.5 should not drop more
than 3 points; if it does, blend the export with the original training
set instead of replacing it.

## 4. NLP retraining (RoBERTa)

Concatenate the export CSV with `accessibility_reviews.csv` (the original
seed). Half-half mix is a good starting point.

```bash
cd backend
python -m app.cli.roberta_cli train \
  --csv ../accessibility_reviews.csv,../backend/training_exports/<latest>/roberta/train.csv \
  --output ../NaviAble_RoBERTa_Final_v2 --epochs 3
```

## 5. Promote new weights

```bash
# Update .env
sed -i.bak 's|YOLO_WEIGHTS_PATH=.*|YOLO_WEIGHTS_PATH=YoloModel11/runs/stair_ramp_m5_v1/weights/best.pt|' .env
sed -i.bak 's|ROBERTA_CHECKPOINT_DIR=.*|ROBERTA_CHECKPOINT_DIR=NaviAble_RoBERTa_Final_v2|' .env

# Restart stack
./stop.sh && ./run.sh -b
```

## 6. Smoke-test scoring

Re-submit a known-good photo from the dataset:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/verify \
  -F "image=@NaviAble_Dataset/valid/images/<known>.jpg" \
  -F "review=Wide ramp at the side entrance, flat surface." \
  -F "rating=4" \
  -F "latitude=12.9716" -F "longitude=77.5946" | jq '.trust_score'
```

Trust score should be within ±0.05 of the previous model's score on the
same input. Big swings — investigate before keeping the new weights.

## 7. Record the cut

```bash
docker exec naviable-postgis psql -U naviable -d naviable -c \
  "UPDATE training_exports SET notes = notes || ' [PROMOTED]' WHERE id = '<id>';"
```
