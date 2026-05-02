# Phase 04c — NLP Failure Handling

## Goal

Define which failures the NLP wrapper handles internally vs. which it
lets propagate. The bar is intentionally lower than vision (03f) — text
inputs are simpler than image inputs, and most failure modes here are
boot-time, not request-time.

## Prerequisites

- Phase 04a–b merged.

## Deliverables

### Tokenizer / model mismatch — fail at startup

Already covered by the warm-up call in 04b. Don't add a runtime check
that defends against this; it would mask the real signal at boot.

### Single-token / very short inputs

A one-character review is valid input to the model and produces some
probability. **Don't second-guess it here.** The Trust Score downstream
is the right place for "low-quality text drags the contribution into
HIDDEN."

A review that is `"."` or `"!"` clears `min_length=1` and reaches the
wrapper. Score it like any other input.

### Empty input — must never happen

```python
async def score(self, text: str) -> float:
    return await asyncio.to_thread(self._infer, text)
```

If `text == ""` somehow reaches `_infer`, the tokenizer will raise.
Let it. Phase 02c's `min_length=1` is the contract; a violation is a
programmer error and the right response is a loud crash, not a silent
`0.0`.

### CUDA OOM under concurrent load

The model is small; this is unlikely in practice. If profiling on real
traffic shows it happens:

- First mitigation: dynamic batching (see 04d).
- Last resort: surface as `NlpUnavailable` and have the verify endpoint
  return `503`.

For the first cut, do **not** add either. Document the observed
behaviour first, then mitigate.

## Acceptance criteria

- [ ] `nlp.score(".")` returns a probability in `[0, 1]` without
      raising. (No special-case in the wrapper.)
- [ ] `nlp.score("")` raises (the schema prevents this from ever
      happening in production).
- [ ] No silent `try: ... except: return 0.0` block exists in
      `services/nlp.py` — fail loudly is the rule.
- [ ] Logs from a successful inference do not include the full review
      text. Length is fine; the body is not (PII).

## Pitfalls / notes

- **Threading:** PyTorch on CPU is multi-threaded by default and spawns
  one thread per core for matrix ops. With multiple `to_thread` calls
  in flight this can cause oversubscription. If profiling shows context
  switching dominating CPU, set `torch.set_num_threads(1)` at app start.
  Don't pre-emptively set it — measure first.
- **Don't log the review text at INFO.** It can contain PII. Log
  `len(text)` and the resulting score instead.
- **`CancelledError`** from `asyncio.gather` (phase 06) must propagate.
  Don't swallow it inside `_infer`.
