# Phase 12 — Deployment & Runbook

## Goal

Make the system runnable by anyone with a checkout, in either local-dev
or demo mode, with one command. Document the operational concerns —
where weights live, what env vars matter, how to roll back when a model
regresses, what to watch.

This phase has the lowest engineering content and the highest leverage:
the demo to a panel or stakeholder is what matters in May 2026, and a
broken five-minute-before-demo deploy will overshadow good engineering.

## Prerequisites

- Phases 01–11 merged. CI green.

## Current state

- `run.sh` exists at repo root. This phase rewrites it to be the single
  entry point.
- `backend/uploads/` is committed (so the directory exists in fresh
  clones; the contents are gitignored).

## Deliverables

### 1. `run.sh` — the one command

```bash
#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-help}"
case "$cmd" in
  setup)    # one-time: bring up DB, install deps, run migrations
    docker compose up -d postgres
    python -m venv .venv && source .venv/bin/activate
    pip install -r backend/requirements.txt
    pushd frontend && flutter pub get && dart run build_runner build && popd
    alembic upgrade head
    ;;
  backend)  # run the FastAPI app
    source .venv/bin/activate
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ;;
  frontend) # run flutter web on chrome
    cd frontend && flutter run -d chrome --web-port 5173
    ;;
  test)     # full test suite
    source .venv/bin/activate
    pytest backend/tests
    cd frontend && flutter test
    ;;
  demo)     # production-ish local: build static, serve with backend
    source .venv/bin/activate
    pushd frontend && flutter build web --release && popd
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ;;
  help|*)
    cat <<EOF
NaviAble runner.
  ./run.sh setup     - one-time setup (DB, deps, migrations)
  ./run.sh backend   - run the FastAPI dev server
  ./run.sh frontend  - run Flutter Web in Chrome
  ./run.sh test      - run all tests
  ./run.sh demo      - serve the built frontend through the backend (single port)
EOF
    ;;
esac
```

The "demo" mode is the one used in front of the panel: a single
`localhost:8000` serves both the API and the static Flutter bundle. No
two-terminal dance, no "but it worked on my machine."

### 2. `docker-compose.yml` (root)

Two services for MVP — Postgres and (optionally) the backend itself.
Keep the frontend out of compose; Flutter's hot-reload story is better
when run directly on the host.

### 3. `.env.example`

Every settings field from phase 02 must appear here with a safe default
or a comment marking it as required:

```
# Database
DATABASE_URL=postgresql+psycopg://naviable:naviable_dev@localhost:5432/naviable

# Model weights
YOLO_WEIGHTS_PATH=YoloModel11/runs/detect/best/weights/best.pt
ROBERTA_CHECKPOINT_DIR=NaviAble_RoBERTa_Final

# Inference
VISION_THRESHOLD=0.205
VISION_WEIGHT=0.60
NLP_WEIGHT=0.40

# Uploads
UPLOAD_DIR=backend/uploads
MAX_IMAGE_BYTES=10485760
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp

# Frontend (compile-time)
API_BASE_URL=http://localhost:8000
```

### 4. Where weights live

- YOLOv11 weights: `YoloModel11/runs/detect/<run_name>/weights/best.pt`.
  The `<run_name>` is recorded in this doc per release.
- RoBERTa checkpoint: `NaviAble_RoBERTa_Final/`.
- Both are too large for git. Document size, expected sha256, and the
  source location (Drive folder, S3 bucket — wherever the team
  actually keeps them) in this doc.
- A `scripts/fetch_weights.sh` downloads them from the recorded source
  and verifies sha256.

### 5. Observability (light)

For the demo, nothing fancy — but the basics:

- `structlog` JSON output in production mode (set via env).
- Every request logs: `request_id`, `method`, `path`, `status`,
  `duration_ms`, `vision_score`, `nlp_score`, `trust_score` (when
  applicable).
- A simple `/api/v1/metrics` endpoint behind a feature flag exposes
  Prometheus-format counters: requests, error rates, model-call
  latency histograms. Out of scope for the panel demo but a one-hour
  add when the project grows.

### 6. Backup / data retention

The DB is small for MVP. Daily `pg_dump` to a local backup folder is
sufficient. Document the command:

```bash
docker compose exec postgres pg_dump -U naviable naviable > backups/$(date +%Y%m%d).sql
```

Image files (`backend/uploads/`) are not backed up beyond the host
filesystem in MVP. If a contributor uploads sensitive content by
accident, a deletion procedure exists:

```sql
UPDATE contributions SET visibility_status = 'HIDDEN' WHERE id = '...';
```

— never `DELETE`. The retention rule from phase 05 stands: low-trust
data stays in the DB.

### 7. Rollback plan

If a model swap (vision or NLP) regresses:

1. Revert the env var (`YOLO_WEIGHTS_PATH` or
   `ROBERTA_CHECKPOINT_DIR`) to the previous version.
2. Restart the backend (`./run.sh backend`).
3. The previous lifespan warmup loads the old weights cleanly.

No DB migration is needed for a model rollback — the schema is
model-agnostic. This is one of the wins of the late-fusion design.

### 8. Demo dry-run checklist

Run this checklist 24 hours before any panel demo:

- [ ] `./run.sh setup` from a fresh clone of `main` succeeds.
- [ ] `./run.sh test` is green.
- [ ] `./run.sh demo` boots, the map shows seeded pins, the
      contribution flow returns a sensible Trust Score on a known-good
      sample.
- [ ] Submit one fixture image and confirm: row in DB, file on disk,
      result card shows `vision_score`, `nlp_score`, and Trust Score.
- [ ] WCAG audit checklist (phase 11) re-run.
- [ ] Network tab shows `X-Request-ID` round-trip.
- [ ] All env vars in `.env` match values committed in
      `.env.example` (no leftover dev tokens).
- [ ] Backup taken of the demo DB.

### 9. README at repo root

A short README that points people here:

> NaviAble: a crowdsourced accessibility-discovery platform.
> See `tech-docs/00-overview.md` for the build plan.
> See `tech-docs/12-deployment-and-runbook.md` for how to run it.

The historical READMEs (`backend/README.md`, `frontend/README.md`,
`IMPLEMENTATION_SUMMARY.md`, `QUICK_START.md`,
`YOLO_INTEGRATION_GUIDE.md`) get a one-line note linking to this
folder, then are kept as-is for archival reference.

## Acceptance criteria

- [ ] A fresh clone, plus `./run.sh setup` and `./run.sh demo`, brings
      up a working local NaviAble at `http://localhost:8000`.
- [ ] The demo dry-run checklist above passes end to end.
- [ ] All env vars are documented in `.env.example`; nothing is required
      but not listed.
- [ ] A model rollback is performed in a staging environment as a
      drill — confirm it's a < 1-minute operation.
- [ ] At least one DB backup exists in `backups/` and can be restored
      via `psql -f backups/<date>.sql` into a fresh DB.

## Pitfalls / notes

- **Don't ship weights through git.** Even `git lfs` becomes painful
  fast. The `scripts/fetch_weights.sh` flow is annoying but correct.
- **Don't run the demo through `flutter run`.** Use the
  `flutter build web --release` artifact served by FastAPI. `flutter run`
  hot-reload is for development; in front of a panel it is one
  package-resolution failure away from disaster.
- **Time zones.** Postgres `timestamptz` is right; do not use plain
  `timestamp`. The frontend renders local time but the DB stores UTC.
- **Don't pre-optimise hosting.** A single VM with the docker-compose
  stack is enough for the demo and the first month of real use. K8s
  comes later, not now.
- **The point of this phase is "boring."** A flashy deploy story is a
  liability the day before a panel demo. Optimise for "works without
  thinking about it."
