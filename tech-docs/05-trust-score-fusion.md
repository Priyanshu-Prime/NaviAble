# Phase 05 — Trust Score & Late-Fusion Engine

## Goal

Replace the stubs in `services/fusion.py` (from phase 02) with the actual
late-fusion logic from Section 3.9 of the report. This is a tiny module
in lines of code — but it is the single most important piece of business
logic in the system, and getting the boundaries right matters.

## Spec

```
Trust Score = (0.60 * Vision Score) + (0.40 * NLP Score)
```

| Trust Score band | Status   | What it means                                           |
|------------------|----------|---------------------------------------------------------|
| `>= 0.70`        | `PUBLIC` | Shown to users immediately, no caveat                   |
| `0.40 .. 0.69`   | `CAVEAT` | Stored, surfaced with warning, queued for moderator     |
| `< 0.40`         | `HIDDEN` | Stored, never displayed publicly, retained in DB        |

**Never** drop a low-confidence contribution. The retention rule is from
Section 3.4.2 of the report — a low-trust contribution today might be
the only evidence the system has about a particular venue tomorrow, and
deleting it forecloses any future use.

## Prerequisites

- Phase 02 merged: `compute_trust_score` and `assign_status` are
  importable as stubs.
- Phase 03 and phase 04 either merged or available as mocks. This phase
  does not depend on real model output — only on the contract.

## Deliverables

### 1. The fusion module

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

A few details that look small but matter:

- The weights are **not** hard-coded. They live in `settings` (see
  phase 02). The 60/40 split is a design choice with a recorded
  rationale, not a magic number. If a future experiment finds 70/30
  is better on real traffic, the change is one env var, not a code
  diff.
- `compute_trust_score` validates its inputs. The vision and NLP
  modules are supposed to return values in `[0, 1]`, but a failure to
  uphold that contract should crash here loudly, not silently produce
  garbage Trust Scores. The validation is cheap.
- `round(..., 4)` keeps the stored score readable. Without it, you get
  things like `0.7000000000000001` in the database, which makes
  threshold queries flaky.
- `assign_status` uses `>= 0.70` for `PUBLIC` and `>= 0.40` for
  `CAVEAT`. Exactly `0.70` is `PUBLIC`, exactly `0.40` is `CAVEAT` —
  both are inclusive of their lower bound. The spec table is
  unambiguous on this; do not invert.

### 2. Settings invariants

Add a validator on `Settings`:

```python
@model_validator(mode="after")
def weights_sum_to_one(self) -> "Settings":
    total = self.vision_weight + self.nlp_weight
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"vision_weight + nlp_weight must equal 1.0, got {total}")
    return self
```

If someone sets `VISION_WEIGHT=0.7` and forgets to update
`NLP_WEIGHT=0.3`, the app fails to boot. That is what we want — a
silent 1.05 weighting would inflate every Trust Score in the DB until
someone noticed.

### 3. Property tests

This is one of the few places where property-based tests pay off
trivially. Add to phase 11's test plan:

```python
@given(v=st.floats(0, 1), n=st.floats(0, 1))
def test_trust_score_in_unit_interval(v, n):
    s = compute_trust_score(v, n, settings=test_settings)
    assert 0.0 <= s <= 1.0

@given(s=st.floats(0, 1))
def test_status_partition_is_total(s):
    # every score in [0, 1] maps to exactly one status
    assign_status(s)  # must not raise
```

### 4. Decision log

Phase 05 also writes a short decision log entry into the doc, captured
once and never edited without sign-off:

> 2026-05-02: Vision/NLP weighting set to 60/40 per Section 3.9 of the
> project report. Rationale: a photograph is harder to fabricate than a
> sentence, and the vision output most directly answers whether a
> feature physically exists. The NLP score at 40% retains enough
> influence to drag a contribution below the public-display threshold
> when the two signals disagree strongly. Sweep of 70/30 and 50/50
> during development showed 60/40 gave the best moderator-rated balance
> between false-positive suppression and contribution acceptance.

The decision log is the kind of context that disappears from a
codebase otherwise — keeping it next to the code it justifies is the
point of this folder.

## Acceptance criteria

- [ ] `compute_trust_score(0.8, 0.5, settings=...)` returns exactly
      `0.68` (`0.6*0.8 + 0.4*0.5`).
- [ ] `assign_status(0.70)` returns `"PUBLIC"`. `assign_status(0.40)`
      returns `"CAVEAT"`. `assign_status(0.39)` returns `"HIDDEN"`.
- [ ] `compute_trust_score(-0.1, 0.5, ...)` raises `ValueError`.
- [ ] Booting the app with `VISION_WEIGHT=0.7` and `NLP_WEIGHT=0.4`
      fails with a clear settings error.
- [ ] Property tests above pass over 1 000 random samples.

## Pitfalls / notes

- **Floats are floats.** Do not test for exact equality at threshold
  boundaries with hand-typed decimals. `compute_trust_score(0.5, 0.5,
  ...)` should be `0.5`, but `0.6*0.7 + 0.4*0.7` is not exactly `0.7`
  in IEEE 754 — the rounding to 4 decimals at the end is what makes
  this stable.
- **`HIDDEN` is real, not soft-deleted.** Discovery queries (phase 07)
  filter by status; they do not need a `deleted_at` column. Do not
  conflate the two concepts.
- **No moderator override here.** A moderator promoting a
  `CAVEAT` contribution to `PUBLIC` is a separate operation that
  updates the `visibility_status` column directly — fusion is for
  scoring at submission time only.
