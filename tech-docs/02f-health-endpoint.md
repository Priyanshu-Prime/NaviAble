# Phase 02f — Health Endpoint

## Goal

`GET /healthz` for load balancers and uptime checks. Returns fast,
returns honest, never blocks behind heavy work.

## Prerequisites

- Phase 02a merged: `Settings` exists.
- Phase 02b merged: `create_app()` registers routers.
- Phase 01 merged: async engine and session factory exist.

## Deliverables

`backend/app/api/routers/health.py`:

```python
router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthz(engine: AsyncEngine = Depends(get_engine)) -> dict:
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok", "db": "ok" if db_ok else "fail"}
```

The DB check is a single `SELECT 1` on a fresh connection. It's cheap
enough that a 1 Hz LB probe does not move the needle, and honest enough
that "db: ok" actually reflects the connection pool's health.

## Acceptance criteria

- [ ] `GET /healthz` returns `200` with `{"status": "ok", "db": "ok"}`
      when Postgres is up.
- [ ] With Postgres stopped, `GET /healthz` returns `200` with
      `{"status": "ok", "db": "fail"}` — the app is still up; only the
      DB sub-check failed.
- [ ] Latency under 20 ms when Postgres is healthy (hand-timed in dev).
- [ ] Calling `/healthz` 100 times in a tight loop does not exhaust the
      connection pool.

## Pitfalls / notes

- **Do not** report `503` when the DB is down. `/healthz` says "the
  process is alive"; if the DB is dependent for liveness in some
  deployments, add a separate `/readyz` instead. Mixing the two semantics
  bites later.
- No business queries here. `SELECT 1` only. A query that touches
  `contributions` will get slow as the table grows and turn the LB probe
  into an outage trigger.
- Keep this endpoint un-prefixed (`/healthz`, not `/api/v1/healthz`).
  LB / k8s tooling expects the conventional path.
