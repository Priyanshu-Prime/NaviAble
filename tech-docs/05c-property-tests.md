# Phase 05c — Property Tests for Fusion

## Goal

Two universal properties of the fusion module that cheap example-based
tests can miss:

1. The output of `compute_trust_score` is always in `[0, 1]` for any
   inputs in `[0, 1]`.
2. `assign_status` is total over `[0, 1]` — no input maps to `None` or
   raises.

Property tests via Hypothesis are the right shape: a few lines of code,
hundreds of generated cases, immediate signal if a future refactor
breaks an invariant.

## Prerequisites

- Phase 05a merged.
- Phase 05b merged (the settings validator means tests use a fixture
  with valid weights).
- `hypothesis` added to dev dependencies.

## Deliverables

In `backend/tests/services/test_fusion_properties.py`:

```python
import pytest
from hypothesis import given, strategies as st

from app.services.fusion import assign_status, compute_trust_score


@pytest.fixture
def settings():
    # phase 11 will provide a shared test_settings fixture; until then,
    # construct one inline with vision_weight=0.6, nlp_weight=0.4.
    ...


@given(v=st.floats(0, 1, allow_nan=False), n=st.floats(0, 1, allow_nan=False))
def test_trust_score_in_unit_interval(v, n, settings):
    s = compute_trust_score(v, n, settings=settings)
    assert 0.0 <= s <= 1.0


@given(s=st.floats(0, 1, allow_nan=False))
def test_status_partition_is_total(s):
    # every score in [0, 1] maps to exactly one status; no exception
    status = assign_status(s)
    assert status in {"PUBLIC", "CAVEAT", "HIDDEN"}


@given(v=st.floats(0, 1, allow_nan=False), n=st.floats(0, 1, allow_nan=False))
def test_trust_score_monotone_in_each_argument(v, n, settings):
    base = compute_trust_score(v, n, settings=settings)
    if v + 0.01 <= 1.0:
        bumped = compute_trust_score(v + 0.01, n, settings=settings)
        assert bumped >= base
    if n + 0.01 <= 1.0:
        bumped = compute_trust_score(v, n + 0.01, settings=settings)
        assert bumped >= base
```

The monotonicity test catches a class of bugs (sign flip, swapped
weights) that the unit-interval test misses.

## Acceptance criteria

- [ ] All three property tests pass over Hypothesis's default 100
      examples.
- [ ] A deliberate bug (e.g. negate one weight) makes at least one
      property test fail — verify locally before merging the suite.
- [ ] Tests run in under 1 second total. Property tests on pure-Python
      arithmetic are fast.

## Pitfalls / notes

- `allow_nan=False` matters. `compute_trust_score(nan, 0.5)` is
  `ValueError` (out of `[0, 1]`), and Hypothesis would flag that as a
  property failure. We exclude NaN at the strategy level because NaN
  in scores is a separate concern (vision/NLP contracts) and is not
  what these tests are checking.
- Don't over-fit the monotonicity test. The `+ 0.01` step avoids
  rounding artifacts at the `round(..., 4)` boundary. Smaller steps
  produce flaky failures.
- Property tests live next to fusion in the test tree. Phase 11's wider
  test plan picks them up automatically; don't move them into a special
  "properties" subdirectory.
