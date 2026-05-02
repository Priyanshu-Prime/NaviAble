# Phase 02a — Settings via `pydantic-settings`

## Goal

Provide a typed `Settings` object that reads `.env`, exposes every value the
rest of the app needs (database URL, model paths, fusion weights, upload
limits), and is cached so tests can override it cleanly.

## Prerequisites

- Phase 01 merged: `DATABASE_URL` in the canonical form is in `.env.example`.
- Python 3.11, `.venv` active.

## Deliverables

`backend/app/core/config.py`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    yolo_weights_path: str = "YoloModel11/runs/.../best.pt"   # phase 03 nails the exact path
    roberta_checkpoint_dir: str = "NaviAble_RoBERTa_Final"

    vision_threshold: float = 0.205   # spec value, do not change without sign-off
    vision_weight: float = 0.60
    nlp_weight: float = 0.40

    upload_dir: str = "backend/uploads"
    max_image_bytes: int = 10 * 1024 * 1024
    allowed_image_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

The `lru_cache` guarantees a single instance per process. Tests override via
FastAPI's dependency-override mechanism — never by mutating the cached object.

## Acceptance criteria

- [ ] Importing `Settings()` with no `.env` and no env vars raises a clear
      error for missing `database_url` (not a generic `ValidationError`
      buried in a stack trace).
- [ ] `get_settings()` returns the same instance across calls within a test.
- [ ] A test that overrides `get_settings` via `app.dependency_overrides`
      sees its override on the next request.

## Pitfalls / notes

- Pydantic v2 only — no `class Config`, no `pydantic.v1`.
- Phase 05 will add a `model_validator(mode="after")` that asserts
  `vision_weight + nlp_weight == 1.0`. Leave the field shape unchanged so
  that validator is a one-line addition.
- Do not put secrets in defaults. `database_url` has no default on purpose —
  a fresh checkout must set it.
