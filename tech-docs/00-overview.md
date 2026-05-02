# NaviAble — Implementation Plan: Overview & Index

This folder is the build plan for NaviAble: a crowdsourced accessibility-discovery
platform that pairs a Flutter Web client with a FastAPI backend, runs every
contribution through two independent AI verifiers (YOLOv11 vision, RoBERTa text),
and fuses their scores into a single Trust Score before persisting to a
PostGIS-enabled PostgreSQL database.

The docs in this folder are sequenced. Each document is a self-contained build
phase with goal, prerequisites, deliverables, and acceptance criteria. Work
through them in order; later phases assume earlier phases are merged and
green.

---

## What is NaviAble (one paragraph)

A user opens the app, takes a photo of a ramp / stairs / handrail at a public
place, types a one-line review, gives a star rating, and submits with their
GPS location. The backend runs the photo through a YOLOv11 detector and the
text through a fine-tuned RoBERTa classifier *concurrently*, fuses the two
scores using a fixed 60/40 (vision/text) weighting, and routes the
contribution into one of three buckets:

| Trust Score   | Status   | What the user sees                                  |
|---------------|----------|-----------------------------------------------------|
| `>= 0.70`     | `PUBLIC` | Pin appears on the map immediately                  |
| `0.40–0.69`   | `CAVEAT` | Pin appears with a warning marker; queued for mods  |
| `< 0.40`      | `HIDDEN` | Stored, never deleted, hidden from public view      |

The map view queries contributions spatially ("within X metres of me") via
PostGIS and renders pins differentiated by confidence band.

---

## Architecture (target end state)

```
┌──────────────────────────┐    multipart/form-data     ┌──────────────────────────────┐
│   Flutter Web client     │ ─────────────────────────► │   FastAPI app                │
│  (Riverpod + Dio)        │                            │   - Pydantic v2 validation   │
│                          │ ◄───── JSON ───────────────│   - asyncio.gather fan-out   │
└──────────────────────────┘                            │                              │
                                                        │   ┌──────────┐  ┌─────────┐  │
                                                        │   │ Vision   │  │  NLP    │  │
                                                        │   │ YOLOv11  │  │ RoBERTa │  │
                                                        │   │ wrapper  │  │ wrapper │  │
                                                        │   └────┬─────┘  └────┬────┘  │
                                                        │        │             │       │
                                                        │        ▼             ▼       │
                                                        │   ┌────────────────────────┐ │
                                                        │   │ Late Fusion +          │ │
                                                        │   │ Trust Score + Routing  │ │
                                                        │   └────────────┬───────────┘ │
                                                        └────────────────┼─────────────┘
                                                                         ▼
                                                       ┌──────────────────────────────┐
                                                       │  PostgreSQL + PostGIS        │
                                                       │  contributions table         │
                                                       │  GIST index on geometry      │
                                                       └──────────────────────────────┘
```

Key non-negotiables (from the spec):

- The endpoint is **fully async**. Vision and NLP run concurrently via
  `asyncio.to_thread` + `asyncio.gather`. The user-facing latency is the
  *slower* of the two model calls, not their sum.
- Validation lives at the **edge** (Pydantic v2). Malformed requests are
  rejected with `422` before any model runs.
- Low-confidence contributions are **never silently deleted** — they are
  retained in the DB with `visibility_status = HIDDEN` for future
  re-evaluation.
- The frontend itself must be **WCAG 2.1 AA** compliant. An accessibility
  platform that fails an accessibility audit is not shippable.

---

## Build phases (read in order)

| #  | Doc                                              | Outcome                                                         |
|----|--------------------------------------------------|-----------------------------------------------------------------|
| 01 | [Database & PostGIS](./01-database-postgis.md)   | `contributions` table, GIST index, spatial query helper         |
| 02 | [Backend foundation](./02-backend-foundation.md) | FastAPI app, settings, Pydantic schemas, layout, error handlers |
| 03 | [Vision module](./03-vision-module-yolov11.md)   | YOLOv11 wrapper with perceptual-hash cache, score per class     |
| 04 | [NLP module](./04-nlp-module-roberta.md)         | RoBERTa wrapper returning `P(LABEL_1)`                          |
| 05 | [Trust Score & fusion](./05-trust-score-fusion.md)| 60/40 late fusion, status routing, single source of truth      |
| 06 | [Verify endpoint](./06-verify-endpoint.md)       | `POST /api/v1/verify` — orchestration, persistence, response    |
| 07 | [Discovery endpoint](./07-discovery-endpoint.md) | `GET /api/v1/contributions/nearby` — spatial query              |
| 08 | [Frontend foundation](./08-frontend-foundation.md)| Flutter Web bootstrap, Riverpod, Dio, theme, WCAG baseline     |
| 09 | [Contribution flow](./09-frontend-contribution-flow.md)| Form → upload → AsyncValue → result feedback              |
| 10 | [Map & discovery view](./10-frontend-map-discovery.md)| Geospatial pins differentiated by confidence band          |
| 11 | [Testing & QA](./11-testing-and-qa.md)           | Unit + integration tests, target ≥23 backend tests              |
| 12 | [Deployment & runbook](./12-deployment-and-runbook.md)| `run.sh`, env, model weights, observability, rollback      |

---

## Current state of the repo (as of this plan)

Some scaffolding already exists and the plan builds on it rather than starting
from scratch:

- `backend/app/main.py`, `backend/app/api/routers/verify.py`,
  `backend/app/services/ml.py` — partial backend exists; phases 02-06 will
  refactor and complete.
- `backend/app/api/routers/predict.py` — earlier prediction endpoint, may be
  retired once `/verify` is the canonical path.
- `frontend/lib/` — Flutter project with `api/`, `models/`, `providers/`,
  `screens/`, `theme/`, `widgets/` directories already present.
- `YoloModel11/` — training scripts and weights live here. The runtime
  inference wrapper in phase 03 loads weights from this folder (do not
  duplicate weight files into `backend/`).
- `NaviAble_RoBERTa_Final/` — fine-tuned RoBERTa checkpoint for the NLP
  wrapper in phase 04.
- `IMPLEMENTATION_SUMMARY.md`, `QUICK_START.md`, `YOLO_INTEGRATION_GUIDE.md`
  — pre-existing notes; treat as historical context, not as the plan of
  record. **This `tech-docs/` folder supersedes them.**

Each phase doc has a "Current state" section that calls out what already
exists vs. what is still missing, so you can resume mid-stream without
re-reading the whole codebase.

---

## How to use these docs

1. Pick the next phase that is not yet complete.
2. Read the **Goal**, **Prerequisites**, and **Acceptance criteria** sections
   first — they define "done" for that phase.
3. Implement against the **Deliverables** list. Treat the deliverable list as
   the contract; do not silently add scope.
4. Verify against the acceptance criteria before opening a PR.
5. Update the phase's "Current state" section in that doc as part of the PR
   so the next person knows where to pick up.

If a phase is blocked by a missing decision, write the decision and its
rationale into that phase's doc — these docs are the project's working
memory.
