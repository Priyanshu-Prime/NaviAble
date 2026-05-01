# Image Model Metrics Summary (YOLO runs)

- Total runs with `results.csv`: 18
- Full table: `image_model_metrics_all_runs.csv`

## Top 10 by best mAP50-95

| run                                  |   epochs_recorded | data                                                                                 |   imgsz |   batch |   best_epoch_by_mAP50_95 |   best_precision |   best_recall |   best_mAP50 |   best_mAP50_95 |
|:-------------------------------------|------------------:|:-------------------------------------------------------------------------------------|--------:|--------:|-------------------------:|-----------------:|--------------:|-------------:|----------------:|
| runs/detect/overfit_test             |               100 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_overfit.yaml                |     640 |       8 |                       99 |          0.86086 |       0.82614 |      0.81788 |         0.75571 |
| NaviAble_Final/yolo_finetune_aug2    |                50 | data_aug.yaml                                                                        |     640 |       8 |                       47 |          0.86216 |       0.71563 |      0.79945 |         0.52617 |
| NaviAble_Final/yolo_finetune_aug     |               100 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data.yaml                        |     640 |      16 |                       98 |          0.74559 |       0.67087 |      0.74408 |         0.50703 |
| runs/detect/ramp_full_bal_classaware |                25 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_train_aug_classbal.yaml     |     640 |       8 |                       25 |          0.84329 |       0.40166 |      0.47247 |         0.31602 |
| runs/detect/ramp_aug2_classbal_long  |                30 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_train_aug_cp2_classbal.yaml |     640 |       8 |                       27 |          0.82311 |       0.41111 |      0.45861 |         0.31042 |
| runs/detect/ramp_full_v2             |                50 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_ramps_v2.yaml               |     640 |       8 |                       50 |          0.84359 |       0.40325 |      0.44579 |         0.30086 |
| runs/detect/fast_train               |                20 | NaviAble_Dataset/data.yaml                                                           |     320 |       8 |                       20 |          0.35366 |       0.36365 |      0.37587 |         0.24541 |
| runs/detect/ramp_balanced_cp         |                25 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_train_aug_cp.yaml           |     640 |       8 |                       23 |          0.76085 |       0.41658 |      0.41834 |         0.24005 |
| runs/detect/mid_train_balanced       |                47 | data_train_aug_cp3_classbal.yaml                                                     |     512 |      12 |                       27 |          0.75894 |       0.32401 |      0.35361 |         0.21182 |
| ramp_priority_v2                     |                33 | /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/data_ramps_v2.yaml               |     640 |       8 |                       32 |          0.32218 |       0.38872 |      0.34889 |         0.19567 |