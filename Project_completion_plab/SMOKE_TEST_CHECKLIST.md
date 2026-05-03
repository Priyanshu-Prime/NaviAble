# Pre-release smoke test (full stack)

Before each demo / release. Each line is a manual click; expected outcome
is in italics.

## A. Backend boots
- [ ] `docker compose down -v && docker compose up -d` — *DB healthy in <10s*
- [ ] `cd backend && alembic upgrade head` — *no errors*
- [ ] `GOOGLE_PLACES_API_KEY=$KEY ./run.sh -b` — *log shows `naviable.ready`*
- [ ] `curl http://127.0.0.1:8000/healthz` — *`{"status":"ok"}`*

## B. Backend endpoints
- [ ] `curl 'http://127.0.0.1:8000/api/v1/places/search?query=Starbucks'` → *≥1 prediction*
- [ ] `curl 'http://127.0.0.1:8000/api/v1/places/nearby?latitude=12.97&longitude=77.59&radius_m=500'`
       → *list of places with `aggregate_trust` numeric*
- [ ] `curl 'http://127.0.0.1:8000/api/v1/places/<unknown_gid>'` → *upserts row, returns `contributions: []`*

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
