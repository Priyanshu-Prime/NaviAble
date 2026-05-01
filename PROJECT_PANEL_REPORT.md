# NaviAble — Project Panel Report

**Consolidated from all repository Markdown documentation** (root README, `conference_reference.md`, frontend/backend READMEs, YOLO ramp tooling, and `.agent/` architecture and presentation guidance).  
**Purpose**: one document for review panels, posters, demos, and stakeholder briefings.

---

## 1. Executive summary

**NaviAble** is a **dual-AI accessibility verification platform** that combines **YOLOv11** (physical infrastructure in images) and **fine-tuned RoBERTa** (genuine vs generic accessibility reviews) to produce a single **NaviAble Trust Score**. It targets **“accessibility washing”**—places or reviews that claim accessibility without evidence.

**Institution & context**: IIIT Trichy B.Tech CSE **Final Year Project — Team 7** (community-driven accessibility enhancement).

**End-to-end flow**: **Flutter Web** → **FastAPI** (`POST /api/v1/verify`) → concurrent **YOLO + RoBERTa** → structured JSON + trust score.

---

## 2. Progress and deliverables (what is built)

| Area | Status / artifact (per docs) |
|------|------------------------------|
| **Vision** | YOLOv11 training pipeline and class vocabulary (ramps, stairs, steps, handrails / guard rails, etc.); inference integrated in backend |
| **NLP** | RoBERTa fine-tuned on distilled/labelled review data; `LABEL_0` generic / washing vs `LABEL_1` genuine / spatially specific |
| **Backend** | FastAPI app: `POST /api/v1/verify`, `GET /health`, Swagger/ReDoc; Pydantic v2 schemas; ML services with `asyncio.gather` + `asyncio.to_thread` |
| **Frontend** | Flutter Web: image + review form, Riverpod state, Dio client, Trust Score gauge, NLP and detection cards, WCAG-oriented theme |
| **Quality** | **23** pytest unit tests for verify API (mocked ML, no GPU weights required) — documented as all passing |
| **Demo path** | **`NAVIABLE_DEMO_MODE=true`**: synthetic realistic outputs without model weights (UI, conference, CI) |
| **GIS / ramps** | Shapefile tooling (`Ramps_v2/Sidewalk_Ramps_2010/`): overlay previews, export, YOLO-style labels for georeferenced tiles (see `yolo/README_ramp_shapefile.md`) |
| **Documentation** | Main README, conference reference, per-package READMEs, API contract in `.agent/architecture/` |

**Planned / blueprint (not necessarily fully implemented in code—called out in `.agent/` docs)**  
PostgreSQL for users/locations/reviews; blob/S3-style image storage; Alembic; optional **CLIP hybrid** vision path (`ENABLE_HYBRID_CLIP` in frontend README).

---

## 3. Metrics (panel-ready numbers)

Use these **exact** figures in slides or tables (do not round up for appearance; per academic guidance in-repo).

### 3.1 YOLOv11 (vision)

| Metric | Value |
|--------|------:|
| mAP@0.5 | **47.29%** |
| Precision | **58.99%** |
| Recall | **46.34%** |
| Training epochs | **25** |

### 3.2 RoBERTa (NLP)

| Metric | Value |
|--------|------:|
| Validation accuracy | **87.65%** |
| Training epochs | **5** |
| Dataset size (reported) | **402 rows** |

### 3.3 Fusion — NaviAble Trust Score

```
Trust Score = 0.60 × mean(YOLO feature confidences) + 0.40 × RoBERTa confidence
```

| Score range | Interpretation |
|-------------|----------------|
| ≥ 0.70 | Strong evidence of accessibility |
| 0.40–0.69 | Partial evidence |
| < 0.40 | Insufficient evidence |

**Narrative for panels** (from `conference_reference.md`): emphasize the **end-to-end multimodal system**, not a single model in isolation—for example: *combined YOLO physical detection and RoBERTa review authenticity with the metrics above as supporting evidence*.

**Architecture note (blueprint)**  
`.agent/architecture/SYSTEM_DESIGN.md` also describes capping maximum trust when no object is detected; confirm implementation in code if a panel asks for exact fusion rules.

---

## 4. Product and domain knowledge

### 4.1 Problem

- Venues may **claim** accessibility without **physical** features (ramps, rails, usable approaches).
- **Generic reviews** (“great and accessible”) can mislead users who need **specific, verifiable** detail.

### 4.2 Solution (dual-AI)

1. **Vision**: Evidence of accessibility-related structures in the uploaded image.  
2. **NLP**: Distinguishes **genuine physical/spatial description** from **generic praise** (accessibility washing in text).  
3. **Trust score**: Merges both modalities so **image evidence is weighted higher (60%)** than text (40%).

### 4.3 Practical uses

- **Accessibility verification** for user-submitted image + review.  
- **Audit support** (ramps, stairs, handrails, entrances—scope depends on trained classes).  
- **Triage / prioritization**: low trust → manual review or flagging.  
- **Community reporting** toward a more reliable accessibility dataset over time.  
- **Demos & teaching**: demo mode without GPU or weights.

### 4.4 API surface (high level)

| Endpoint | Role |
|----------|------|
| `POST /api/v1/verify` | Multipart: `text_review`, `location_id`, `image` → NLP + vision + `naviable_trust_score` |
| `GET /health` | Health, version, demo mode, ML service status (`stub` vs `loaded`) |
| `/docs`, `/redoc` | Interactive API docs |

---

## 5. Technical stack (for a panel “how” slide)

| Layer | Stack |
|-------|--------|
| Frontend | Flutter Web, Riverpod, Dio, `flutter_image_compress`, WCAG AA-oriented theme, `Semantics` on widgets |
| Backend | FastAPI, Pydantic v2, concurrent ML via thread offload |
| ML | Ultralytics YOLOv11, Hugging Face Transformers / RoBERTa |
| Training / data | YOLO scripts under `yolo/`; NLP pipeline under `nlp/` (Groq LLM labelling, merging, etc.—see main README) |
| GIS | NYC-style sidewalk ramp shapefile + `ramp_shapefile_tools.py` for overlays and label export |

**Environment highlights**  
`NAVIABLE_DEMO_MODE`, `YOLO_MODEL_PATH`, `ROBERTA_MODEL_DIR`, `ROBERTA_DEVICE`, CORS origins; frontend `API_BASE_URL` via `--dart-define`.

---

## 6. Limitations and future work (intellectual honesty for panels)

From `conference_reference.md`:

- Vision dataset is **small** vs large public detection benchmarks.  
- **Ramp** class is especially hard; **class imbalance** matters.  
- Shapefile data is **not** YOLO-ready imagery—needs **georeferenced alignment** for training labels.  
- Trust score is a **fixed weighted heuristic**, not a learned calibrated fusion.  
- Real-world variance: region, angle, lighting.

**Suggested future work** (same source): larger/diverse imagery, learned fusion, better geo-alignment, more classes (elevators, tactile paving, etc.), evaluation on **external** datasets.

---

## 7. Academic / defense angles (from `.agent` presentation guidance)

- **“Clever Hans” / keyword memorization**: contrast weaker supervision with **LLM knowledge distillation** (Groq) forcing **semantic** learning.  
- **Dual-AI synergy**: vision and NLP **compensate** (e.g. blurry image + strong specific text still affects the combined score in the designed pipeline).  
- **Figures to show**: architecture diagram; YOLO boxes; RoBERTa genuine vs generic example; trust score UI; optional GIS overlay.

---

## 8. Team and roles (documented)

- **Team 7**, IIIT Trichy; lead developer named in `.agent/system/IDENTITY_AND_PURPOSE.md` (**Priyanshu Makwana**).  
- **Target dev profile**: Windows, GTX 1650 Ti, PowerShell venvs (informs VRAM and CPU fallback choices).

---

## 9. Panel checklist — quick copy for a one-slide “status”

- [ ] **One-liner**: Dual-AI accessibility verification (YOLO + RoBERTa) → Trust Score.  
- [ ] **Demo**: Flutter + FastAPI, demo mode optional.  
- [ ] **Numbers**: YOLO mAP@0.5 47.29%, P/R, RoBERTa val acc 87.65%, 402-row NLP set.  
- [ ] **Formula**: 0.6 vision + 0.4 NLP; interpret bands ≥0.7 / 0.4–0.69 / <0.4.  
- [ ] **Uses**: verification, audits, washing detection, triage.  
- [ ] **Honest limits**: small data, ramps hard, heuristic fusion, domain shift.  
- [ ] **Next steps**: data scale, fusion, geo, new classes, external eval.

---

## 10. Source index (Markdown files read for this report)

| Path | Role |
|------|------|
| `README.md` | Main overview, metrics, structure, setup, trust formula |
| `conference_reference.md` | Conference narrative, uses, limitations, figures, citation-style paragraph |
| `frontend/README.md` | Flutter layout, a11y, env defines, hybrid CLIP flag |
| `backend/README.md` | API detail, health JSON, env vars, tests count, trust interpretation |
| `yolo/README_ramp_shapefile.md` | GIS ramp tooling commands |
| `.github/copilot-instructions.md` | Agent bootstrap pointer to `.agent/` |
| `.agent/architecture/SYSTEM_DESIGN.md`, `API_CONTRACTS.md` | Trust engine notes, JSON contract |
| `.agent/system/*.md` | Identity, constraints, academic framing |
| `.agent/memory/LESSONS_LEARNED.md` | OOM / GPU lessons template |
| `.agent/workflows/*.md` | Feature, ML integration, academic reporting, reflection loops |
| `.agent/skills/*.md` | YOLO, RoBERTa, Flutter, FastAPI directives |

*Excluded from synthesis*: `.pytest_cache/README.md` (generic pytest cache text, not project-specific).

---

*Generated to support project panels and external summaries. Update this file when metrics or scope change.*
