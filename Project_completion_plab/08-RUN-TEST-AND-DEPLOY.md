# Phase 08 — Run, test, deploy, and the retraining loop

**Status:** not started
**Depends on:** phases 01–07 merged (full stack is functional end-to-end)
**Affects:** `run.sh`, `.env.example`, `MOBILE_TEST_GUIDE.md`, new `RETRAINING_RUNBOOK.md`

## Goal

Tie everything together: a single `./run.sh` that boots the DB, backend,
and a chosen mobile target; a clear cookbook for getting / restricting
Google API keys; a smoke-test plan that exercises every critical path; and
a runbook for cutting a retraining dataset and folding the improved model
back into production.

---

## Deliverables

### 1. Update `.env.example`

Append:

```bash
# ── Google API keys ────────────────────────────────────────────────────
# Server-side (Places API + Geocoding API). NEVER embedded in the app.
GOOGLE_PLACES_API_KEY=

# Admin token for /api/v1/training/export.
ADMIN_TOKEN=changeme-dev-only

# ── Aggregate scoring ─────────────────────────────────────────────────
TRUST_RECENCY_HALF_LIFE_DAYS=180
NEARBY_DEFAULT_RADIUS_M=800
NEARBY_MAX_RADIUS_M=10000
```

### 2. Update `run.sh`

Add a friendly menu step for mobile targets and pass `API_BASE_URL`
correctly per target. Find the existing "device choice" block and replace
with:

```bash
if [[ -z "$FLUTTER_DEVICE" ]]; then
  echo ""
  echo "Available devices:"
  flutter devices 2>/dev/null | grep -v "^$" | tail -n +2
  echo ""
  echo "Choose a device (Ctrl+C to exit):"
  echo "  1) chrome  (web)"
  echo "  2) macos   (desktop)"
  echo "  3) android (emulator or USB) — uses 10.0.2.2 to reach host backend"
  echo "  4) ios     (simulator) — uses localhost"
  echo "  5) physical device on Wi-Fi (you set API_BASE_URL=http://<lan-ip>:8000)"
  read -p "Enter choice (default: 1): " device_choice
  case "$device_choice" in
    1|"") FLUTTER_DEVICE="chrome" ;;
    2)    FLUTTER_DEVICE="macos" ;;
    3)
      FLUTTER_DEVICE="$(flutter devices --machine | python3 -c "import json,sys;[print(d['id']) for d in json.load(sys.stdin) if 'android' in d.get('targetPlatform','').lower()]" | head -1)"
      API_BASE_URL="http://10.0.2.2:${BACKEND_PORT}"
      ;;
    4)
      FLUTTER_DEVICE="$(flutter devices --machine | python3 -c "import json,sys;[print(d['id']) for d in json.load(sys.stdin) if 'ios' in d.get('targetPlatform','').lower()]" | head -1)"
      API_BASE_URL="http://localhost:${BACKEND_PORT}"
      ;;
    5)
      read -p "Enter device ID: " FLUTTER_DEVICE
      LAN_IP=$(ifconfig | awk '/inet /{print $2}' | grep -v 127.0.0.1 | head -1)
      API_BASE_URL="${API_BASE_URL:-http://${LAN_IP}:${BACKEND_PORT}}"
      echo "Using API_BASE_URL=$API_BASE_URL"
      ;;
    *)
      read -p "Enter device ID: " FLUTTER_DEVICE
      ;;
  esac
fi
```

Make sure the final `flutter run` invocation uses `$API_BASE_URL`:

```bash
flutter run -d "$FLUTTER_DEVICE" --dart-define=API_BASE_URL="$API_BASE_URL"
```

### 3. Get and restrict the Google API keys

Each key is restricted to the smallest surface that works. Three keys total:

| Key | Restrictions | Where it lives |
|---|---|---|
| Maps SDK Android | API: "Maps SDK for Android". App: package `ai.naviable` + your debug & release SHA-1. | `frontend/android/local.properties` (git-ignored) |
| Maps SDK iOS | API: "Maps SDK for iOS". App: bundle id `ai.naviable`. | `frontend/ios/Runner/AppDelegate.swift` (or `.xcconfig`) |
| Places + Geocoding (server) | APIs: "Places API", "Geocoding API". IP restriction: your backend host(s). | `.env` server-side — `GOOGLE_PLACES_API_KEY` |

```bash
# Get debug SHA-1 (keystore Flutter generates):
keytool -list -v \
  -alias androiddebugkey \
  -keystore ~/.android/debug.keystore \
  -storepass android -keypass android | grep SHA1
```

Paste that into the Cloud Console → APIs & Services → Credentials → the
Android Maps key → "Application restrictions" → "Add an item".

### 4. Smoke test plan

Save as `Project_completion_plab/SMOKE_TEST_CHECKLIST.md`:

```markdown
# Pre-release smoke test (full stack)

Before each demo / release. Each line is a manual click; expected outcome
is in italics.

## A. Backend boots
- [ ] `docker compose down -v && docker compose up -d` — *DB healthy in <10s*
- [ ] `cd backend && alembic upgrade head` — *no errors*
- [ ] `GOOGLE_PLACES_API_KEY=$KEY ./run.sh -b` — *log shows `naviable.ready`*
- [ ] `curl http://127.0.0.1:8000/healthz` — *`{"status":"ok"}`*

## B. Backend endpoints
- [ ] `curl '/api/v1/places/search?query=Starbucks'` → *≥1 prediction*
- [ ] `curl '/api/v1/places/nearby?latitude=12.97&longitude=77.59&radius_m=500'`
       → *list of places with `aggregate_trust` numeric*
- [ ] `curl /api/v1/places/<unknown_gid>` → *upserts row, returns `contributions: []`*

## C. Mobile app (Android emulator)
- [ ] App launches, map renders centred on user/Bangalore — *pins appear within 2s*
- [ ] Pan map → markers refresh once after 400 ms idle — *no spam in Dio log*
- [ ] Toggle "Verified only" — *amber and grey markers vanish*
- [ ] Tap marker → bottom sheet → "View details" — *Place detail loads*
- [ ] Search "Phoenix Marketcity Bangalore" — *autocomplete appears, tap → detail*
- [ ] FAB "Add review" → contribute screen — *photo, location, review, rating*
- [ ] Camera capture (with mock GPS in emulator) — *EXIF badge appears*
- [ ] Submit → loading → result card with Trust % and feature chips
- [ ] Result card "Submit another" → form resets

## D. Persistence & aggregates
- [ ] Submit two PUBLIC contributions to the same place
- [ ] `SELECT contribution_count, public_count, aggregate_trust FROM places ORDER BY updated_at DESC LIMIT 1;`
       → *count=2, aggregate ≈ mean of the two trust scores*
- [ ] Refresh map → marker turns green for that place

## E. Retraining
- [ ] `python -m app.cli.training_export --since 2025-01-01`
       → *prints export id, writes `backend/training_exports/<stamp>/`*
- [ ] Inspect `manifest.json` — counts match the `training_exports` row
- [ ] `cat backend/training_exports/<stamp>/yolo/data.yaml` — *valid YOLO yaml*

## F. Failure modes
- [ ] Stop backend → app shows banner; map markers stop refreshing — *no crash*
- [ ] Wrong Maps key → blank tiles + logcat "Authorization failure"
- [ ] Empty `GOOGLE_PLACES_API_KEY` → `/places/search` returns 503 — *frontend shows error toast*
```

### 5. Retraining runbook

Save as `Project_completion_plab/RETRAINING_RUNBOOK.md`:

```markdown
# NaviAble retraining runbook

Run this **monthly** or whenever PUBLIC contributions cross +500 since
the last cut.

## 1. Cut a fresh dataset
```bash
cd backend
ADMIN_TOKEN=$(grep ADMIN_TOKEN ../.env | cut -d= -f2)
python -m app.cli.training_export \
  --since "$(psql -U naviable -d naviable -h localhost -p 5434 -tAc \
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
```

### 6. Update `MOBILE_TEST_GUIDE.md`

Replace section "Device Options" with:

```markdown
### 1. Android emulator
```bash
./run.sh
# Choose 3 (android)
```
- Backend reachable via `10.0.2.2:8000` (run.sh sets this automatically).
- Mock GPS via Extended Controls → Location → "Set location"

### 2. iOS Simulator
```bash
./run.sh
# Choose 4 (ios)
```
- Backend reachable via `localhost:8000`
- Mock GPS via Xcode → Debug → Simulate Location

### 3. Physical device (Wi-Fi)
```bash
./run.sh
# Choose 5 (physical)
```
- Backend must be reachable on your Mac's LAN IP — open the firewall.
- iOS device may complain about a self-signed cert; we use plain HTTP in
  dev so this is fine.

### 4. Chrome / macOS
Same as before. Web has no GPS unless you grant location and supports a
single Maps API key shared with mobile (you'll need to enable "Maps
JavaScript API" — not just the SDK ones).
```

### 7. Production deployment notes (optional but recommended)

Append to `Project_completion_plab/08-RUN-TEST-AND-DEPLOY.md` or a separate
`PRODUCTION_NOTES.md`:

- Run backend behind a reverse proxy (nginx or Caddy) terminating TLS.
  Mobile apps should never hit plain HTTP in prod — Android 9+ and iOS
  ATS reject it by default.
- The `uploads/` directory is local-disk for MVP. For production, swap
  to S3 + CloudFront. Update `validate_and_persist_upload` to write to
  S3 and `_compose_image_url` to return the CDN URL.
- The TTL cache in `GooglePlacesService` is per-process. Behind a load
  balancer, deploy one Redis instance and cache there instead. (Or just
  rely on the 60-second client-side `Cache-Control` we already set.)
- Set `NAVIABLE_CORS_ORIGINS` to the exact domains of your deployed apps,
  not `*`. Mobile apps don't honour CORS, but a future web client will.
- Bind the admin endpoint behind a separate `/admin` path that only
  internal IPs can reach. The `X-Admin-Token` is belt-and-braces, not a
  substitute for network-level isolation.

---

## Acceptance criteria

- [ ] `./run.sh` with the new menu starts the full stack on Android emulator.
- [ ] `./run.sh` likewise on iOS Simulator.
- [ ] All five sections (A–F) of the smoke test pass on a clean DB.
- [ ] The runbook produces a valid YOLO + RoBERTa cut from a manually-seeded
      database (3+ PUBLIC contributions).
- [ ] Updating `YOLO_WEIGHTS_PATH` in `.env` and restarting the backend
      causes the new weights to load (visible in startup logs).

## Pitfalls

- **Android cleartext traffic blocked.** If you skip the
  `network_security_config.xml` step in phase 04, `http://10.0.2.2:8000`
  fails silently with a `CLEARTEXT_NOT_PERMITTED` exception that only
  shows in `adb logcat`. The error to the user is just "Network error".
- **iOS App Transport Security.** For `localhost`, ATS is permissive; for
  a LAN IP, you may need an `NSAppTransportSecurity` exception in
  `Info.plist`. For prod, terminate TLS — that's the proper fix.
- **Maps key SHA-1 confusion.** Debug builds use `~/.android/debug.keystore`,
  release builds use your release keystore. The Cloud Console restriction
  must include both, or release builds show blank tiles.
- **Quota exhaustion.** Google Places returns `OVER_QUERY_LIMIT` rather
  than HTTP 429. Our service raises `GooglePlacesUnavailable` for that —
  the frontend shows a 503 toast. If demos coincide with billing-cap day,
  this is the first thing to check.
- **Retraining feedback loop.** PUBLIC contributions feed retraining;
  retraining changes scores; new scores re-classify edge cases. If
  unchecked, this can drift the model. Reserve a fixed validation set
  (`NaviAble_Dataset/valid/`) and **never** add to it from production.
