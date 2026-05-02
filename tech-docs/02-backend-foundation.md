# Phase 02 — Backend Foundation (FastAPI)

## Goal

Stand up the FastAPI application skeleton: settings, app factory, router
registration, error handling, request-correlation IDs, and the Pydantic v2
schemas that every endpoint will use. Phase 06 (verify) and phase 07
(discovery) plug into this skeleton; the AI wrapper modules (phases 03 and
04) plug into a service layer this phase defines.

This phase does **not** implement business endpoints — it makes the
endpoints in later phases short and focused.

## Prerequisites

- Phase 01 merged: schema, session helper, and `find_nearby` exist.
- Python 3.11, `.venv` active.

## Current state

- `backend/app/main.py` exists but is incomplete. Treat it as a starting
  point, not as the target.
- `backend/app/api/routers/{verify,predict,health}.py` exist; only `health`
  is expected to survive unchanged. `verify.py` is rewritten in phase 06;
  `predict.py` is removed once `verify` is the canonical path.
- `backend/app/services/ml.py` exists; phases 03 and 04 split its
  responsibilities cleanly into `services/vision.py` and `services/nlp.py`.
- `backend/app/schemas/` directory should hold all Pydantic v2 models.

## Deliverables

### 1. Settings via `pydantic-settings`

`backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    yolo_weights_path: str = "YoloModel11/runs/.../best.pt"  # phase 03 nails the exact path
    roberta_checkpoint_dir: str = "NaviAble_RoBERTa_Final"

    vision_threshold: float = 0.205   # spec value, do not change without sign-off
    vision_weight: float = 0.60
    nlp_weight: float = 0.40

    upload_dir: str = "backend/uploads"
    max_image_bytes: int = 10 * 1024 * 1024
    allowed_image_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")
```

A single `get_settings()` cached via `functools.lru_cache` so tests can
override.

### 2. App factory

`backend/app/main.py` exposes `create_app()` and a module-level `app`
instance. Responsibilities:

- Register routers (`health`, later: `verify`, `nearby`).
- Install CORS middleware (allow Flutter Web dev origin in dev only).
- Install a request-ID middleware that reads `X-Request-ID` from the
  client and generates one if absent. Echo it on every response and in
  every log line.
- Install a global exception handler that turns unhandled errors into
  `500` with the request ID in the body — never leak stack traces.
- Mount `/static` for served images (dev only; prod uses a CDN/object
  store).

### 3. Pydantic v2 schemas

`backend/app/schemas/contribution.py`:

```python
class ContributionCreate(BaseModel):
    """Validates the multipart payload at the API edge.

    Fields here mirror the form fields, not the DB columns — the file
    itself is handled separately by FastAPI's UploadFile.
    """
    review: Annotated[str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]
    rating: Annotated[int, Field(ge=1, le=5)]

class ContributionResponse(BaseModel):
    id: UUID
    trust_score: float
    vision_score: float
    nlp_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT", "HIDDEN"]
    detected_features: dict[str, list[FeatureDetection]]

class FeatureDetection(BaseModel):
    confidence: float
    bbox: tuple[float, float, float, float]   # x1, y1, x2, y2 normalised

class NearbyQuery(BaseModel):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]
    radius_m: Annotated[float, Field(gt=0, le=10_000)]
    include_caveat: bool = True

class NearbyResponse(BaseModel):
    items: list[ContributionPin]

class ContributionPin(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    trust_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT"]    # HIDDEN never appears
    rating: int
    text_note: str
    image_url: str | None
```

Empty `review` is rejected by `min_length=1` — this is the spec's
"empty text must be rejected upstream" rule. Do not duplicate the check
inside the NLP module.

### 4. Image validation helper

`backend/app/core/uploads.py`:

```python
async def validate_and_persist_upload(
    file: UploadFile, *, settings: Settings
) -> Path:
    # 1. Check content_type in allowed_image_types.
    # 2. Stream bytes, abort if > max_image_bytes.
    # 3. Sniff magic bytes — content_type can be lied about.
    # 4. Persist to settings.upload_dir under a UUID filename.
    # 5. Return the saved Path.
```

Magic-byte check (Pillow opening + `Image.verify()` is sufficient) catches
the case where a client sends a `.jpg` extension on a non-image payload.

### 5. Service-layer interfaces

Define the contracts that phases 03–05 will implement, so this phase can
ship with stub implementations and tests can mock them.

`backend/app/services/vision.py`:

```python
class VisionService(Protocol):
    async def score(self, image_path: Path) -> VisionResult: ...

class VisionResult(BaseModel):
    score: float                                  # max-confidence across target classes
    detections: dict[str, list[FeatureDetection]] # keyed by class
    image_phash: int
```

`backend/app/services/nlp.py`:

```python
class NlpService(Protocol):
    async def score(self, text: str) -> float:    # P(LABEL_1)
        ...
```

`backend/app/services/fusion.py`:

```python
def compute_trust_score(vision: float, nlp: float, *, settings: Settings) -> float: ...
def assign_status(trust: float) -> Literal["PUBLIC", "CAVEAT", "HIDDEN"]: ...
```

Provide stub implementations that return constants for now — phases 03/04/05
replace them with real ones. The verify endpoint in phase 06 should not
care that the stubs were ever there.

### 6. Health endpoint

`GET /healthz` returns `{"status": "ok", "db": "ok" | "fail"}`. The DB
check pings the connection but does not run a query — keep it cheap so
load balancers can poll at high frequency.

### 7. Logging

Use `structlog` (or stdlib `logging` with a JSON formatter). Every log
line carries `request_id`. No `print()` calls in committed code.

## Acceptance criteria

- [ ] `uvicorn backend.app.main:app --reload` boots cleanly with no
      warnings about missing env vars (after copying `.env.example` to
      `.env`).
- [ ] `GET /healthz` returns `200` with `db: ok` when Postgres is up.
- [ ] Sending non-JSON to a JSON endpoint or omitting required fields
      yields `422` with a clean Pydantic error body — never a `500`.
- [ ] Sending a `text/plain` payload to a multipart endpoint yields `415`
      or `422`, not `500`.
- [ ] `X-Request-ID` round-trips: a client-supplied ID appears in the
      response header and in every log line for that request.
- [ ] An oversized upload (`max_image_bytes + 1`) is rejected with `413`.
- [ ] All schemas have unit tests for boundary values (latitude `90`,
      `90.0001`, rating `0`, `1`, `5`, `6`).

## Pitfalls / notes

- **Pydantic v2, not v1.** Use `Annotated[..., Field(...)]` and
  `model_config`, not `class Config`. Do not import from
  `pydantic.v1` — that keeps the project on the right side of the
  ecosystem.
- **`UploadFile` does not enforce size.** FastAPI streams the upload; the
  oversize check has to happen as you read it, not after. Read in chunks
  with a running counter.
- **Don't validate inside the model code.** Validation belongs at the
  API edge in Pydantic, not redundantly inside `services/nlp.py`. A
  service module that gets a value from the API should be able to trust
  it.
