# Phase 05a — Fusion Module

## Goal

Replace the stubs from phase 02e with the actual late-fusion logic:
weighted combination of vision and NLP scores, mapped to one of three
visibility statuses.

## Prerequisites

- Phase 02e merged: stubs `compute_trust_score` and `assign_status` exist.
- Phase 02a merged: `Settings` exposes `vision_weight` and `nlp_weight`.

## Deliverables

`backend/app/services/fusion.py`:

```python
def compute_trust_score(vision: float, nlp: float, *, settings: Settings) -> float:
    if not (0.0 <= vision <= 1.0):
        raise ValueError(f"vision score out of range: {vision}")
    if not (0.0 <= nlp <= 1.0):
        raise ValueError(f"nlp score out of range: {nlp}")
    score = settings.vision_weight * vision + settings.nlp_weight * nlp
    return round(score, 4)


def assign_status(trust_score: float) -> Literal["PUBLIC", "CAVEAT", "HIDDEN"]:
    if trust_score >= 0.70:
        return "PUBLIC"
    if trust_score >= 0.40:
        return "CAVEAT"
    return "HIDDEN"
```

Details that look small but matter:

- **Weights live in `settings`, not as constants.** The 60/40 split is a
  design choice with a recorded rationale (see 05d), not a magic number.
  An experiment that wants 70/30 is a one env-var change.
- **Range validation crashes loudly.** Vision and NLP are *contracted* to
  return values in `[0, 1]`. A violation is a bug in those modules and
  the right response here is `ValueError`, not silent garbage.
- **`round(..., 4)`** keeps the stored score readable. Without it,
  `0.7000000000000001` shows up in the DB and threshold queries get
  flaky.
- **`>= 0.70` is `PUBLIC`, `>= 0.40` is `CAVEAT`** — both inclusive of
  their lower bound. The spec table is unambiguous; do not invert.

## Acceptance criteria

- [ ] `compute_trust_score(0.8, 0.5, settings=...)` returns exactly
      `0.68` (`0.6*0.8 + 0.4*0.5`).
- [ ] `assign_status(0.70)` → `"PUBLIC"`.
- [ ] `assign_status(0.40)` → `"CAVEAT"`.
- [ ] `assign_status(0.39)` → `"HIDDEN"`.
- [ ] `compute_trust_score(-0.1, 0.5, ...)` raises `ValueError` with a
      message that includes the offending value.
- [ ] `compute_trust_score(1.1, 0.5, ...)` raises `ValueError`.

## Pitfalls / notes

- **`HIDDEN` is real, not soft-deleted.** Discovery (phase 07) filters
  by status; there is no `deleted_at` column. Don't conflate.
- **No moderator override here.** A moderator promoting a `CAVEAT` to
  `PUBLIC` is a separate operation that updates the column directly.
  Fusion is for scoring at submission time only.
- **Floats are floats.** Test for exactness only after the explicit
  `round(..., 4)`. Hand-typed `0.6*0.7 + 0.4*0.7` is not exactly `0.7`
  in IEEE 754; the rounding makes the test stable.
- This module imports nothing heavy — no torch, no transformers, no
  ultralytics. Keep it that way; the verify endpoint imports fusion on
  every request.
