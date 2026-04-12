# NaviAble Conference Reference

## 1. Project Summary

**NaviAble** is a dual-AI accessibility verification platform that combines:

- a **YOLOv11 vision model** for detecting physical accessibility structures in images, and
- a **RoBERTa text classifier** for checking whether user-written accessibility reviews contain genuine physical detail.

The system is designed for real-world accessibility auditing, user-submitted verification, and detection of “accessibility washing” where text claims do not match the physical environment.

At a system level, the workflow is:

`Flutter Web Frontend → FastAPI Backend → YOLOv11 + RoBERTa → Composite Trust Score`

The backend exposes `POST /api/v1/verify`, which receives:

- `text_review`
- `location_id`
- `image`

and returns a structured verification result with:

- NLP authenticity analysis
- YOLO detection analysis
- NaviAble Trust Score

---

## 2. Model Architecture

### 2.1 Vision Model: YOLOv11

The vision model is a lightweight object detector trained to identify accessibility-related physical features from images. In the current project, the main class vocabulary includes accessibility infrastructure such as:

- ramps
- stairs
- steps
- handrails / guard rails

The model is used to detect where accessibility-relevant structures exist in the uploaded image.

### 2.2 NLP Model: RoBERTa

The NLP model is a fine-tuned RoBERTa classifier that determines whether a review contains **genuine physical accessibility detail** or only generic praise.

This helps catch cases where a review sounds positive but does not contain real evidence of accessibility.

### 2.3 Trust Score Fusion

The final verification result uses a weighted fusion of the two modalities:

```text
Trust Score = 0.60 × vision confidence + 0.40 × NLP confidence
```

This weighting gives slightly more importance to the physical evidence in the image, while still allowing the review text to influence the final score.

---

## 3. How the System Works

### 3.1 Frontend Interaction

The Flutter frontend lets a user:

1. upload a location image,
2. enter an accessibility review,
3. submit the verification request,
4. view the output cards and final trust score.

### 3.2 Backend Processing

When the request reaches the FastAPI backend:

1. the uploaded image is validated,
2. the text review is sent to RoBERTa,
3. the image is sent to YOLOv11,
4. both inference calls run concurrently,
5. the response is assembled into a single JSON payload.

### 3.3 Response Interpretation

The returned result shows:

- detected accessibility features,
- confidence for each detected feature,
- NLP genuineness classification,
- the final NaviAble Trust Score.

### 3.4 Demo Mode

For development or hardware-limited environments, the backend can run in **demo mode**. In this mode, the system returns realistic synthetic outputs without requiring trained weights. This is useful for:

- local testing
- UI demos
- conference demonstrations
- CI / reproducibility checks

---

## 4. Practical Uses

NaviAble is useful in several accessibility-related settings:

### 4.1 Accessibility Verification

The platform can help verify whether a place is actually accessible by checking both:

- what the image shows, and
- what the user claims in text.

### 4.2 Audit Support

It can assist in quick accessibility audits for:

- ramps
- stairs
- handrails / guard rails
- door approaches and entrances

### 4.3 Detection of Accessibility Washing

Some places may advertise themselves as accessible, but the review text may be vague or misleading. The RoBERTa component helps detect this mismatch.

### 4.4 Assistive Reporting and Triage

The trust score can be used to:

- prioritize manual review,
- flag low-confidence submissions,
- support community-based accessibility reporting,
- create a more reliable accessibility dataset over time.

---

## 5. Dataset and Ramp Context

### 5.1 Vision Dataset

The vision model uses a YOLO-format accessibility dataset prepared in the project under `NaviAble_Dataset/`. The project docs show the main vision benchmark as a **25-epoch YOLOv11 training run**.

### 5.2 NLP Dataset

The RoBERTa model was trained on a balanced dataset of **402 rows**.

### 5.3 GIS Ramp Layer

The repository also includes a GIS ramp source under `Ramps_v2/Sidewalk_Ramps_2010/`.

Important note:

- this layer is **not an image dataset**,
- it is a **shapefile / GIS feature layer**, and
- it is used for **overlay previews** and **label export support**.

That means it is useful for map-based analysis and for bridging GIS data into training workflows, but it is **not directly usable as YOLO image input** without georeferenced imagery.

### 5.4 Ramp Tooling

The repo includes utilities to work with the GIS ramp layer, including:

- overlay preview generation,
- shapefile export,
- YOLO-style label export for georeferenced tiles.

This helps connect the spatial ramp layer to the image-based detector pipeline.

---

## 6. Conference-Ready Metrics

These are the strongest project-level metrics reported in the repository documentation:

| Model | Metric | Value |
|---|---:|---:|
| YOLOv11 | mAP@0.5 | **47.29 %** |
| YOLOv11 | Precision | **58.99 %** |
| YOLOv11 | Recall | **46.34 %** |
| YOLOv11 | Training Epochs | **25** |
| RoBERTa | Validation Accuracy | **87.65 %** |
| RoBERTa | Training Epochs | **5** |
| RoBERTa | Dataset Size | **402 rows** |

### Suggested way to report the main result

For a conference paper, the strongest main claim is not just one model in isolation, but the **end-to-end dual-AI accessibility verification system**.

A concise result statement could be:

> NaviAble demonstrates an end-to-end accessibility verification workflow that combines YOLOv11-based physical feature detection with RoBERTa-based review authenticity scoring, achieving 47.29% mAP@0.5 on vision and 87.65% validation accuracy on text classification.

---

## 7. Limitations

A fair conference discussion should mention the following limitations:

- the vision dataset is relatively small compared with large-scale detection benchmarks,
- ramp detection remains the hardest class and is sensitive to class imbalance,
- shapefile data requires aligned imagery before it can be used as detection labels,
- the final Trust Score is a weighted heuristic rather than a learned calibrated fusion model,
- performance may vary across regions, camera angles, and lighting conditions.

---

## 8. Future Work

Recommended next steps for a stronger paper or extended system:

1. **Expand the image dataset** with more ramps, steps, stairs, and handrails from diverse locations.
2. **Calibrate the Trust Score** using a learned fusion model instead of a fixed weighted sum.
3. **Improve geospatial alignment** so ramp shapefile data can be used more directly in training.
4. **Add more accessibility classes**, such as elevators, tactile paving, accessible entrances, and door widths.
5. **Evaluate on external datasets** to show generalization beyond the current collection.

---

## 9. Citation Target / Short Paper Summary

If you need a one-paragraph summary for a paper abstract or project poster:

> NaviAble is a dual-AI accessibility verification platform that combines YOLOv11 for physical infrastructure detection and RoBERTa for review authenticity classification. The system processes user-submitted images and reviews through a FastAPI backend and Flutter frontend, producing a composite Trust Score that prioritizes physical evidence while detecting misleading or generic accessibility claims. The current system reports 47.29% YOLOv11 mAP@0.5, 58.99% precision, 46.34% recall, and 87.65% RoBERTa validation accuracy.

---

## 10. Recommended Figures for a Conference Paper

If you are preparing slides or a paper, include these figures:

- **System architecture diagram**: Flutter → FastAPI → YOLO + RoBERTa → Trust Score
- **YOLO detection example**: ramp / stair / handrail bounding boxes
- **RoBERTa classification example**: genuine vs generic review text
- **Trust Score output card**: combined final score
- **Dataset / GIS overlay figure**: ramp shapefile overlay preview

---

## 11. Final Takeaway

NaviAble is best presented as a **multi-modal accessibility intelligence system**:

- YOLO handles the physical scene,
- RoBERTa handles the semantic review claim,
- the Trust Score merges both into a single actionable output.

For conference framing, emphasize the **end-to-end accessibility verification pipeline**, and use the individual model metrics as supporting evidence.

