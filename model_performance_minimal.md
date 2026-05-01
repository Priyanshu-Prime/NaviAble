# Model Performance (Minimal)

- Source: `image_model_metrics_all_runs.csv`
- Total YOLO runs analyzed: 18

## Best by mAP50-95 (overall)

| Metric | Value |
|---|---:|
| Run | `runs/detect/overfit_test` |
| Precision | 0.86086 |
| Recall | 0.82614 |
| F1 (from P/R) | 0.84314 |
| mAP50 | 0.81788 |
| mAP50-95 | 0.75571 |
| Epoch (best mAP50-95) | 99 |

## Final Candidate Run

| Metric | Value |
|---|---:|
| Run | `NaviAble_Final/yolo_finetune_aug2` |
| Precision | 0.86216 |
| Recall | 0.71563 |
| F1 (from P/R) | 0.78209 |
| mAP50 | 0.79945 |
| mAP50-95 | 0.52617 |
| Epoch (best mAP50-95) | 47 |

## Other Available Metrics

- Per-epoch training/validation losses exist in each run `results.csv`: `train/box_loss`, `train/cls_loss`, `train/dfl_loss`, `val/box_loss`, `val/cls_loss`, `val/dfl_loss`.
- Precision-Recall/F1 curves and confusion matrices are available in `runs/detect/val*` folders.

> Note: F1 is not directly logged in `results.csv`; it is computed here from precision and recall.
