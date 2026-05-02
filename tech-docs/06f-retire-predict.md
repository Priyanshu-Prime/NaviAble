# Phase 06f — Retire `predict.py`

## Goal

Two endpoints doing similar things is a footgun. Once `/verify` is the
canonical path and the frontend uses it, delete the legacy `/predict`
router and its registration.

## Prerequisites

- Phases 06a–e merged.
- Frontend (phase 09) has shipped its switch to `/verify`. Verify the
  cutover **before** opening this PR; deleting `/predict` while a
  client still calls it produces 404s in production.

## Deliverables

### Code changes

1. Delete `backend/app/api/routers/predict.py`.
2. Remove the `predict` import and `app.include_router(predict.router)`
   call from `backend/app/main.py` (or `create_app`).
3. Search the repo for any remaining references and remove or update:
   - `grep -r "predict" backend/app`
   - `grep -r "/predict" frontend/lib`
   - `grep -r "predict" tech-docs`

### Tests

- Delete any tests that exercise `/predict` directly.
- Add a contract test: `GET /api/v1/predict` (or whatever path it had)
  returns `404` after the change. This pins the deletion in place.

### Rollout sequencing

This must happen **in the same PR that switches the frontend**, not as
a follow-up. A cleanup PR ships only after both:

1. The frontend is on `/verify` in the released artifact.
2. Logs show zero hits to `/predict` for at least 24 hours.

## Acceptance criteria

- [ ] `predict.py` no longer exists in `backend/app/api/routers/`.
- [ ] `main.py` does not import or register a `predict` router.
- [ ] No test references `/predict`. The negative contract test for the
      404 is in place.
- [ ] No frontend code references `/predict`.
- [ ] Deploy logs show no traffic to `/predict` post-cutover.

## Pitfalls / notes

- **Don't leave it behind "just in case."** Stale endpoints rot and
  diverge from the canonical path. If a rollback is needed, `git
  revert` is the answer, not a parallel endpoint.
- If a third-party integration somehow calls `/predict` (unlikely but
  worth grepping for), coordinate cutover before deletion. Surface this
  during PR review by including the search output as PR description
  evidence.
- The deletion is one-way. Once merged and deployed, the path is gone.
  That's the point.
