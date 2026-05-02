# Phase 05b — Settings Invariants

## Goal

Crash at boot if the fusion weights do not sum to `1.0`. A silent `1.05`
or `0.95` weighting would either inflate or deflate every Trust Score
in the database — discoverable only when someone notices the histogram
shifted.

## Prerequisites

- Phase 02a merged: `Settings` defines `vision_weight` and `nlp_weight`.
- Phase 05a merged: fusion uses these settings.

## Deliverables

Add a `model_validator(mode="after")` to `Settings`:

```python
from pydantic import model_validator

class Settings(BaseSettings):
    # ... existing fields

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "Settings":
        total = self.vision_weight + self.nlp_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"vision_weight + nlp_weight must equal 1.0, got {total} "
                f"(vision={self.vision_weight}, nlp={self.nlp_weight})"
            )
        return self
```

The `1e-6` tolerance is for floating-point noise from env var parsing
(`"0.6"` and `"0.4"` round-trip cleanly, but `0.1 + 0.2 != 0.3` lurks).

## Acceptance criteria

- [ ] Booting with `VISION_WEIGHT=0.7` and `NLP_WEIGHT=0.4` fails with a
      clear settings error that names both values and their sum.
- [ ] Booting with `VISION_WEIGHT=0.6` and `NLP_WEIGHT=0.4` boots
      cleanly.
- [ ] Booting with `VISION_WEIGHT=0.6000001` and `NLP_WEIGHT=0.4` boots
      cleanly (tolerance covers float noise).
- [ ] The error surface is from `Settings()` instantiation, not from a
      runtime check inside `compute_trust_score`. The validator is the
      single source of truth.

## Pitfalls / notes

- Use `mode="after"` so the individual field validators (range checks
  on each weight) run first. A negative weight should report "weight
  out of range," not "weights don't sum to 1."
- Don't add a CLI flag to override this check. If a future experiment
  needs unequal weighting that doesn't sum to 1 (a normalised softmax,
  say), revisit fusion's design — don't bypass the invariant.
- The validator runs once per `Settings()` construction. Combined with
  `@lru_cache` on `get_settings`, that's once per process. No
  performance worry.
