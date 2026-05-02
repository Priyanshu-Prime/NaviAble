# Phase 06e — Response Shape & Frontend Contract

## Goal

The `ContributionResponse` body intentionally surfaces the raw vision
and NLP scores plus the per-class detections, not just the final trust
score. The frontend uses these to explain results to the user. This
phase locks in the contract.

## Prerequisites

- Phase 02c merged: `ContributionResponse` schema defined.
- Phase 06a merged: endpoint constructs the response.

## Deliverables

### Response body

```json
{
  "id": "f3c8…",
  "trust_score": 0.72,
  "vision_score": 0.87,
  "nlp_score": 0.5,
  "visibility_status": "PUBLIC",
  "detected_features": {
    "ramp": [{"confidence": 0.91, "bbox": [0.12, 0.34, 0.55, 0.78]}],
    "handrail": [{"confidence": 0.62, "bbox": [0.20, 0.10, 0.40, 0.90]}]
  }
}
```

### Why each field is in the response

- **`trust_score`** — the headline number the user sees.
- **`vision_score`** — frontend renders "we saw a ramp at 87%
  confidence." Without this, the trust score is opaque.
- **`nlp_score`** — frontend renders "your text scored 64%
  accessibility-relevant." Calibrates user expectations for future
  contributions.
- **`detected_features`** — frontend draws bounding boxes on the
  uploaded image. Without these, the user can't tell what the model
  saw.
- **`visibility_status`** — drives the success-screen copy ("your
  contribution is live" vs. "queued for moderator review" vs. "saved
  but not displayed").

### What is **not** in the response

- The image bytes / a thumbnail URL. The frontend already has the
  bytes locally; round-tripping them wastes bandwidth.
- The persisted location geometry. The frontend already submitted lat/
  lon; echoing them adds nothing.
- Any moderator-visible field (e.g. internal notes). This response is
  user-facing.

## Acceptance criteria

- [ ] Every successful `/verify` response includes all six top-level
      fields.
- [ ] `detected_features` is always a JSON object (possibly empty
      `{}`), never `null`.
- [ ] `bbox` arrays are length-4 floats in `[0, 1]`.
- [ ] A future "API hardening" PR cannot strip `vision_score`,
      `nlp_score`, or `detected_features` without updating the frontend
      result screen — call this out in the PR template.

## Pitfalls / notes

- **Don't strip these fields in a future "minimise payload" pass
  without checking the frontend first.** The frontend (phase 09)
  depends on them for the result screen. Removing them breaks UX, not
  just types.
- The `id` is a UUID. The frontend uses it to deep-link
  `/contribution/<id>` later (phase 09 stretch). Don't switch to an
  integer or a hash.
- `confidence` and `trust_score` are both floats in `[0, 1]`. Don't let
  rounding drift make them inconsistent — phase 03d clamps boxes,
  phase 05a rounds the trust score.
