# Phase 03d — Bounding-Box Normalisation

## Goal

Every bounding box leaving the vision wrapper is in normalised
coordinates `[0, 1]` along each axis. Pixel boxes do not survive image
resizing on the frontend; normalised boxes do.

## Prerequisites

- Phase 03a merged: `_infer` produces detection objects with raw
  Ultralytics coordinates.

## Deliverables

### Output shape

Each `FeatureDetection` is:

```python
class FeatureDetection(BaseModel):
    confidence: float                          # 0..1
    bbox: tuple[float, float, float, float]    # x1, y1, x2, y2 normalised
```

### Conversion in `_infer`

Ultralytics returns boxes in pixel space relative to the model's input
size. Convert to normalised xy-pairs against the **original** image
dimensions:

```python
img_w, img_h = original_size
for box in result.boxes:
    x1, y1, x2, y2 = box.xyxy[0].tolist()
    bbox = (x1 / img_w, y1 / img_h, x2 / img_w, y2 / img_h)
```

Ultralytics also exposes `box.xyxyn` (already normalised); use it if
available and the resize semantics match. Verify against a fixture
before relying on it — Ultralytics versions have shifted on this.

### Clamping

Clamp each coordinate to `[0, 1]` after division:

```python
def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))
```

Off-by-one rounding can produce `1.0000001`, which fails downstream
validation. Clamp once, here.

## Acceptance criteria

- [ ] All boxes returned satisfy `0.0 <= x1 < x2 <= 1.0` and
      `0.0 <= y1 < y2 <= 1.0`.
- [ ] A bounding box on a 4000×3000 photo is returned in the same
      normalised coordinates as the same crop on a 800×600 thumbnail.
- [ ] No `NaN` or `inf` in any coordinate.

## Pitfalls / notes

- **Get the right reference dimensions.** Ultralytics may resize the
  input internally; the boxes can come back relative to either the
  resized tensor or the original. Always normalise against the original
  image size as Pillow reports it.
- Don't return floats with more than ~4 decimals. Boxes are visual; the
  precision noise in the trailing digits is meaningless and inflates
  payloads. `round(v, 4)` per coordinate is enough.
- Frontend (phase 10) expects `(x1, y1, x2, y2)`. Don't switch to
  `(x, y, w, h)` here without updating the schema in 02c and the map
  view contract.
