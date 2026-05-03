# Phase 11 — Testing & Quality Assurance

## Goal

Get the project to a place where any contributor can change a non-trivial
piece of code and the test suite tells them whether they broke something
within a couple of minutes. The report's Section 5.4 mentions a 23-test
suite around the verify endpoint as the reliability bar; this phase
formalises that suite, adds the corresponding frontend coverage, and
sets up CI so it runs on every push.

## Prerequisites

- Phases 01–10 either merged or stubbed. Tests can be written against
  unmerged code as long as the contracts in earlier docs are stable.

## Coverage targets

| Area                          | Target                                |
|-------------------------------|---------------------------------------|
| Backend unit                  | ≥ 80% line coverage on `services/`    |
| Backend integration (verify)  | ≥ 23 tests across the error matrix    |
| Backend integration (nearby)  | ≥ 8 tests covering filters and limits |
| Frontend widget               | every Riverpod provider has at least 1 test |
| Frontend integration          | golden-path contribution flow tested  |
| Manual WCAG audit             | passes on every shipped screen        |

The "23 tests" number is not arbitrary — it matches the report's
record of the suite that was actually deployed. Treat it as the floor.

## Backend tests

### Layout

```
backend/tests/
├── conftest.py              # fixtures: app, async client, test DB, fake services
├── unit/
│   ├── test_fusion.py       # phase 05
│   ├── test_uploads.py      # phase 02 image validation
│   ├── test_vision_cache.py # phase 03 phash cache
│   └── test_schemas.py      # Pydantic boundary cases
├── integration/
│   ├── test_verify.py       # the ≥23 tests below
│   └── test_nearby.py       # spatial queries
└── fixtures/
    ├── images/              # ramp.jpg, blank.jpg, corrupt.jpg, oversized.jpg
    └── reviews.json         # genuine/sarcastic/generic samples
```

### `conftest.py` essentials

```python
@pytest_asyncio.fixture
async def app(monkeypatch):
    # Override settings for tests (test DB, threshold, weights).
    # Replace VisionService and NlpService with deterministic fakes
    # so test outcomes do not depend on model weights or hardware.
    ...

@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def db_session(test_engine):
    async with AsyncSession(test_engine) as s:
        yield s
        await s.rollback()
```

A real PostgreSQL+PostGIS test database (separate schema or DB) is
required for spatial query tests — there is no in-memory substitute that
implements `ST_DWithin`. Spin up via `docker compose -f
docker-compose.test.yml up -d` in CI.

### The 23-test verify suite

Map directly to phase 06's error matrix plus orchestration concerns:

1. happy path → `201`, `PUBLIC` band
2. happy path with low scores → `201`, `HIDDEN`
3. happy path with mid scores → `201`, `CAVEAT`
4. missing `image` → `422`
5. missing `review` → `422`
6. missing `latitude` → `422`
7. missing `longitude` → `422`
8. missing `rating` → `422`
9. empty `review` after strip → `422`
10. `rating=0` → `422`
11. `rating=6` → `422`
12. `latitude=91` → `422`
13. `longitude=-181` → `422`
14. `image` content-type `text/plain` → `415`
15. oversize image → `413`
16. corrupt JPEG bytes → `201`, `vision_score=0`, `HIDDEN`
17. vision raises `VisionUnavailable` → `503`
18. NLP raises `NlpUnavailable` → `503`
19. DB write fails → `503`, no orphaned upload on disk
20. concurrency: with both fakes sleeping 1 s, total time < 1.5 s
21. concurrency: cancelling one cancels the other (no zombie tasks)
22. duplicate submission of identical photo → vision cache hits second
    time (assert one inference, two requests)
23. row persisted with correct PostGIS WKT (`ST_AsText` matches input)

Each test is short. Use parametrize where the input shape is the only
thing that changes (cases 4–8 and 10–13 collapse to two `parametrize`
blocks).

### Property tests for fusion

From phase 05. Run with Hypothesis over 1 000 examples in CI. Fast and
catches off-by-one boundary errors that the example-based suite
misses.

### Spatial query tests

For `nearby`:

- Insert 5 fixture rows at known offsets from a test centre point.
- Query at radius 100 m, 1 km, 10 km — assert correct subset returned
  in distance order each time.
- Insert one `HIDDEN` row inside the radius — assert it never appears.
- `radius_m=0` → `422`. `radius_m=10001` → `422`.
- `include_caveat=false` excludes `CAVEAT` rows.

## Frontend tests

### Widget tests

`frontend/test/`:

- `contribute_screen_test.dart`: pump the screen with a fake API
  client; verify submit-disabled until form is complete; verify each
  `AsyncValue` state renders the expected UI; verify result card shows
  the trust score the fake returns.
- `map_screen_test.dart`: pump with fake nearby data; verify pin counts
  match; verify a `HIDDEN` pin in fixture data does not render (defence
  in depth — backend should never send one).
- Provider tests for every `@riverpod` provider — at minimum, one test
  per provider that asserts it returns the expected value given a
  mocked dependency.

### Integration test (golden path)

`integration_test/` runs against the dev backend (or a containerised
copy):

1. Open the app.
2. Tap "Add accessibility data."
3. Stub `image_picker` to return a fixture image.
4. Type review, choose rating, grant location (mock `geolocator`).
5. Submit.
6. Assert the result card shows a Trust Score and one of the three
   states.
7. Tap "Submit another," verify form resets.

This test is the closest the team gets to "did the whole stack work?"
Run it in CI on every PR — slow, but high signal.

## CI

GitHub Actions, two workflows:

### `.github/workflows/backend.yml`

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env: { ... }
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r backend/requirements.txt
      - run: alembic upgrade head
      - run: pytest backend/tests --cov=backend/app --cov-fail-under=80
```

### `.github/workflows/frontend.yml`

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: cd frontend && flutter pub get
      - run: cd frontend && dart run build_runner build --delete-conflicting-outputs
      - run: cd frontend && flutter analyze
      - run: cd frontend && flutter test
```

Cache pip and pub dependencies. Fail fast.

## WCAG audit

A manual audit of every shipped screen against WCAG 2.1 AA, recorded as
a checklist in this doc per release:

- [ ] All interactive elements have visible focus indicators.
- [ ] All non-decorative images have semantic labels.
- [ ] Colour is never the only signal (the `PUBLIC`/`CAVEAT` pin
      differentiation uses both colour and shape).
- [ ] All text meets 4.5:1 contrast against its background.
- [ ] All form fields have associated labels (not just placeholders).
- [ ] All time-sensitive states have non-visual feedback (announcements
      for screen readers).
- [ ] The app is fully usable with keyboard alone.
- [ ] The app is fully usable at 200% zoom in the browser.

Treat this checklist as a release gate. Failing items block ship —
they are not "follow-up tickets."

## Acceptance criteria

- [ ] `pytest backend/tests` runs all suites green; coverage on
      `backend/app/services/` is ≥ 80%.
- [ ] The 23+ verify integration tests are present and named per the
      list above.
- [ ] `flutter test` runs all widget and integration tests green.
- [ ] CI workflows run on every push and PR; merges blocked on failure.
- [ ] WCAG checklist is completed and recorded for the current release
      candidate.

## Pitfalls / notes

- **Don't load real model weights in unit tests.** Tests should fake
  `VisionService` and `NlpService`. Loading YOLOv11 + RoBERTa per test
  turns a 30-second suite into a 30-minute one.
- **Async tests need `pytest-asyncio` configured to `asyncio_mode = auto`.**
  Without that, every test needs `@pytest.mark.asyncio`. Configure once
  in `pytest.ini`.
- **Flutter Web `integration_test`** is more fragile than mobile —
  some browser APIs (geolocation, camera) require permission prompts
  that the test runner can't dismiss. Mock these at the package
  boundary, not the browser boundary.
- **Coverage is a floor, not a target.** 80% line coverage on services
  catches drift; chasing 100% leads to tests that assert their own
  mocks. Spend energy on the verify integration suite instead.
