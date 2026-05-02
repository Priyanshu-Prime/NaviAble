# Phase 03b — Class-Score Aggregation

## Goal

Reduce the per-class detections from YOLO into a single `score: float` in
`[0, 1]` for fusion (phase 05). The choice of reduction is a documented
design decision, not a magic line.

## Prerequisites

- Phase 03a merged: `_infer` produces a `dict[str, list[Detection]]`.

## Deliverables

```python
def _aggregate_score(detections_by_class: dict[str, list[Detection]]) -> float:
    """Return the max confidence across all detected target-class boxes,
    or 0.0 if nothing was detected above threshold."""
    confidences = [
        d.confidence
        for boxes in detections_by_class.values()
        for d in boxes
    ]
    return max(confidences, default=0.0)
```

Use **`max`**, not `mean`. Rationale, recorded so it is not silently
re-decided:

- A photo with one obvious ramp and zero of the other classes should
  score high. Averaging zeros into the result dilutes a confident
  detection.
- A photo with several borderline detections does **not** earn extra
  credit by averaging — fusion with NLP is the right place for "many
  weak signals" to be tempered.
- If a future iteration wants per-class weights (a ramp matters more
  than a handrail for wheelchair access), the change lands here, with a
  recorded rationale.

## Acceptance criteria

- [ ] `_aggregate_score({})` → `0.0`.
- [ ] `_aggregate_score({"ramp": [Detection(confidence=0.91, ...)]})` → `0.91`.
- [ ] `_aggregate_score({"ramp": [c=0.4], "stairs": [c=0.85]})` → `0.85`.
- [ ] Result is always in `[0, 1]`.

## Pitfalls / notes

- The reduction is **part of the spec**, not an implementation detail.
  Changing it requires updating phase 05 in the same PR — fusion's
  trust-score boundaries are calibrated against `max` semantics.
- Do not filter classes here. The threshold filter belongs in `_infer`;
  by the time aggregation runs, every detection has already cleared
  threshold.
- Don't return `None` when there are no detections. Downstream code
  expects a number; `0.0` is the correct "we saw nothing" signal.
