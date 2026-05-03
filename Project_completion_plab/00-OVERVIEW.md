# NaviAble — Project Completion Plan (Overview)

> **One-line product description.**
> NaviAble is a mobile, Google-Maps-powered, AI-verified accessibility directory:
> a wheelchair-using visitor opens the app, sees Google places around them,
> sees which ones the community has *verified* as accessible (trust score, photos,
> reviews) — and can add their own contribution (photo + review + auto-detected
> location) which is then scored by YOLOv11 (does the photo really show a ramp?)
> and RoBERTa (is the review a genuine description?), fused into a Trust Score,
> and persisted to PostGIS.

This plan **completes** the existing repo. Models, ML services, fusion logic,
PostGIS schema, `/verify` endpoint, `/contributions/nearby` endpoint, and a
Flutter Web demo all already exist (see `tech-docs/00-overview.md`). What's
missing for the **finished product** the user asked for:

| Gap | What's needed |
|---|---|
| Mobile platforms | Flutter project has no `android/`, `ios/` folders — must add and configure |
| Google Maps | UI is form-only today; needs `google_maps_flutter` map screen |
| Google Places | No place search / nearby places at all — must integrate Places API |
| Place-keyed data | `contributions` is keyed only by `lat/lng`; we need a `places` table keyed by Google `place_id` so multiple contributions roll up to one place |
| Aggregate scoring | UI needs to show one trust score *per place* (not per contribution) |
| EXIF GPS extraction | Photo upload doesn't read EXIF GPS; add server-side fallback chain |
| Re-training loop | PUBLIC contributions never feed back to model training; need export pipeline |
| Place detail UI | No screen showing all reviews/photos/score for one place |
| Search bar | No way to search a specific place by name/address |

This plan delivers all of it.

---

## Target architecture (after completion)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Flutter mobile app (Android + iOS)                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ MapScreen    │  │ SearchScreen │  │ ContributeFlow│ │ PlaceDetailScreen│  │
│  │ (GoogleMap)  │  │ (Places auto)│  │ (camera+EXIF) │ │ (reviews+score)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────────┼───────────┘
          │  HTTPS / multipart                                    │
          ▼                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FastAPI backend                                                             │
│  /api/v1/places/nearby      — Google Places + DB merge                      │
│  /api/v1/places/search      — Google Places autocomplete passthrough        │
│  /api/v1/places/{place_id}  — Aggregated trust + paginated contributions    │
│  /api/v1/verify             — image+review → YOLO+RoBERTa → trust score     │
│  /api/v1/contributions/nearby — (kept) raw pin discovery                    │
│  /api/v1/training/export    — YOLO + RoBERTa dataset dump (PUBLIC only)     │
│                                                                             │
│  Services                                                                   │
│  ├── google_places.py  (httpx client, ttl-cached)                           │
│  ├── geocoding.py      (reverse-geocode lat/lng → address)                  │
│  ├── exif.py           (Pillow EXIF GPS extraction)                         │
│  ├── vision.py  (existing YOLOv11)                                          │
│  ├── nlp.py     (existing RoBERTa)                                          │
│  └── fusion.py  (existing 60/40)                                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL + PostGIS                                                        │
│  places           — keyed by google_place_id, stores aggregate scores       │
│  contributions    — (extended) FK → places.id                               │
│  training_exports — bookkeeping for retraining cycles                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase plan (8 files, each = ~1 prompt)

These are ordered. Phase N assumes phase N-1 is merged.

| # | File | Outcome |
|---|---|---|
| 00 | `00-OVERVIEW.md` (this file) | Architecture, gap analysis, prompt sequence |
| 01 | `01-DATABASE-AND-MIGRATIONS.md` | `places` table, `contributions.place_id` FK, `training_exports` table; alembic migration |
| 02 | `02-BACKEND-PLACES-API.md` | Google Places service, `/places/nearby`, `/places/search`, `/places/{id}` endpoints, EXIF + geocoding helpers |
| 03 | `03-BACKEND-VERIFY-EXTENSIONS.md` | `/verify` accepts `place_id` (or resolves from coords/EXIF/address), aggregate update on commit, `/training/export` endpoint |
| 04 | `04-FLUTTER-MOBILE-BOOTSTRAP.md` | Add Android+iOS platforms, wire Google Maps + Places API keys, install all plugins, permissions, project routing skeleton |
| 05 | `05-FLUTTER-MAP-AND-SEARCH.md` | `MapScreen` with Google Map, current location, nearby place markers tinted by trust, search bar, debounced viewport queries |
| 06 | `06-FLUTTER-CONTRIBUTE-FLOW.md` | Camera/gallery capture → EXIF GPS extraction → place autocomplete fallback → review form → submit → trust-score result card |
| 07 | `07-FLUTTER-PLACE-DETAIL.md` | Place detail screen: aggregated score, image carousel, paginated reviews, "Add your review" CTA |
| 08 | `08-RUN-TEST-AND-DEPLOY.md` | `run.sh` updates, env keys, real-device testing, smoke test commands, retraining loop runbook |

---

## How to execute this plan (prompt template)

For each phase, paste the file contents into a fresh Claude Code prompt with this header:

> *"Read `Project_completion_plab/0X-PHASE.md` and implement everything in the
> Deliverables section. Only edit/create the files listed. Verify against the
> Acceptance Criteria block before stopping. Run the smoke commands shown at
> the bottom of the file."*

The phase docs are self-contained — code blocks are concrete, not pseudo-code,
and file paths are absolute under the repo root. **Do not skip the
Acceptance Criteria block** — it's the contract for "phase done."

If a phase is half-finished, edit its "Status" line at the top and re-run.

---

## Conventions (apply across all phases)

- **Backend Python style.** Type-hinted, async-first, Pydantic v2 schemas, `Settings` injected via `Depends(get_settings)`, no globals beyond the `lru_cache`d settings, no swallowed exceptions — log + re-raise as `HTTPException` with the right status.
- **Flutter style.** Riverpod for state, Dio for HTTP, `AsyncValue` everywhere (no `bool isLoading`). Material 3, dark+light themes, WCAG 2.1 AA contrast, `Semantics(...)` on every interactive element.
- **Coordinate ordering.** PostGIS / GeoJSON: `(lng, lat)`. Flutter `LatLng` and Google Maps: `(lat, lng)`. Convert at the boundary — never inline.
- **Place identity.** Google `place_id` is the canonical key. Two contributions at the same Google place merge under one `places` row even if their submitted lat/lng differ by a few metres.
- **Trust aggregation.** Per-place trust = mean of contribution trust scores weighted by recency (half-life 180 days). Updated transactionally on each verify (see phase 03).
- **API key safety.** The Maps SDK Android/iOS key is embedded in the app binary (necessary for tile rendering), but the **Places API** key is server-side only. Front end calls *our* `/places/*` endpoints, which proxy Google. This keeps the powerful key off-device.
- **Re-training data.** Only `PUBLIC` contributions feed exports. `CAVEAT` and `HIDDEN` are retained but excluded from the training set — adding a low-trust contribution to training would amplify noise.

---

## What "done" looks like (acceptance for the whole project)

A user on an Android or iOS phone can:

1. Open the app and see a Google map centred on their GPS location.
2. See pins for nearby places. Each pin is tinted by accessibility trust:
   green (high), yellow (caveat), grey (no data yet).
3. Tap a pin → see the place's aggregated trust, photos, written reviews.
4. Tap "Search" → autocomplete a place by name → see its detail page.
5. Tap "Add review" → take a photo → write a review → submit. The app reads
   GPS from EXIF if present, else from the device, else asks for an address.
6. See the result: Trust Score, vision/NLP breakdown, list of detected
   features. A `PUBLIC` result is immediately visible to other users.
7. Operator runs `python -m app.cli.training_export --since 2025-01-01` and
   gets a clean YOLO + RoBERTa dataset of all PUBLIC contributions added
   since that date — ready to feed into the next training cycle.

When all 8 phases are complete and their acceptance boxes ticked, the app is
shippable to the Play Store / App Store.
