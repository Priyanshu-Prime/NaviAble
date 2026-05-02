# Phase 04d — Dynamic Batching (Deferred)

## Goal

**This phase is intentionally not built yet.** This document captures
the option, its motivation, and the decision criteria so it isn't
re-discovered six months from now.

## Status

Deferred. Do **not** build in the first cut.

## What it would be

Collect inbound `score` calls into a small batch over a short window
(~5–10 ms), run them as a single forward pass, then dispatch
per-request results back to their callers.

```python
# Sketch, not to be implemented yet.
class BatchingNlpService:
    async def score(self, text: str) -> float:
        future = self._enqueue(text)
        return await future

    async def _flush_loop(self):
        while True:
            batch = await self._collect(window_ms=8, max_size=32)
            results = await asyncio.to_thread(self._infer_batch, [t for t, _ in batch])
            for (_, fut), score in zip(batch, results):
                fut.set_result(score)
```

Tokenisation pads to the longest input in the batch. CUDA forwards 32
short sequences in roughly the time of one — a 2–4× throughput win at
the cost of ~5–10 ms added latency.

## Why deferred

- The simple per-request path is correct and easy to reason about.
- Real load patterns are unknown until phase 11's load tests.
- Batching adds an inflight queue, a flush task, and a cancellation
  story (when one client disconnects, do you cancel its slot or let
  the batch run?) — all of which is wasted work if MVP traffic doesn't
  warrant it.

## When to pick this back up

Build only when **all three** are true:

1. p99 NLP latency exceeds budget on production traffic.
2. CPU/GPU utilisation on the inference host is below ~40% — i.e. the
   bottleneck is per-call overhead, not raw compute.
3. Concurrent in-flight `/verify` requests regularly exceed `~8`.

If only (1) holds, scale horizontally instead.

## Pitfalls when it does get built

- **Cancellation:** if the caller disconnects mid-batch, do not cancel
  the running forward pass. Cancel the future delivery; let the batch
  finish so other callers still get answers.
- **Max batch size matters more than max wait.** Bigger batches help
  throughput but inflate p99 latency. Cap at ~32 sequences for RoBERTa-
  base-sized models on CPU.
- **Don't batch across users.** The model has no notion of identity, so
  this is fine for correctness; just call it out so a future privacy
  review doesn't have to re-discover it.
