# Phase 02c — Pydantic v2 Schemas

## Goal

Define every request and response shape the API surfaces, in one place,
with edge-validation rules that downstream services can trust.

## Prerequisites

- Phase 02a merged: `Settings` exists.

## Deliverables

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


class FeatureDetection(BaseModel):
    confidence: float
    bbox: tuple[float, float, float, float]   # x1, y1, x2, y2 normalised


class ContributionResponse(BaseModel):
    id: UUID
    trust_score: float
    vision_score: float
    nlp_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT", "HIDDEN"]
    detected_features: dict[str, list[FeatureDetection]]


class NearbyQuery(BaseModel):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]
    radius_m: Annotated[float, Field(gt=0, le=10_000)]
    include_caveat: bool = True


class ContributionPin(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    trust_score: float
    visibility_status: Literal["PUBLIC", "CAVEAT"]   # HIDDEN never appears
    rating: int
    text_note: str
    image_url: str | None


class NearbyResponse(BaseModel):
    items: list[ContributionPin]
```

The `min_length=1` on `review` is the spec's "empty text must be rejected
upstream" rule. **Do not duplicate** this check inside the NLP module —
the service can trust its input.

`ContributionPin.visibility_status` is `Literal["PUBLIC", "CAVEAT"]`, **not**
including `HIDDEN`. The discovery endpoint never returns hidden rows;
encoding that in the type prevents a future bug.

## Acceptance criteria

- [ ] Boundary tests pass for latitude `-90`, `0`, `90`; reject `90.0001`
      and `-90.0001`.
- [ ] Boundary tests pass for rating `1`, `5`; reject `0`, `6`.
- [ ] `review="   "` is rejected after `strip_whitespace`.
- [ ] `radius_m=10000` accepted; `10001` rejected.
- [ ] `ContributionPin` cannot be constructed with `visibility_status="HIDDEN"`
      (type/runtime check fails).

## Pitfalls / notes

- Use `Annotated[..., Field(...)]`, not the legacy `field: float = Field(...)`
  form. Both work in v2 but `Annotated` plays better with `mypy` and
  `typing.get_type_hints`.
- Don't add a top-level `from_orm` config — use `model_config =
  ConfigDict(from_attributes=True)` only on response schemas that are
  populated from ORM rows.
- Keep request and response schemas in the same file. They evolve together
  and splitting them adds import gymnastics for no payoff.
