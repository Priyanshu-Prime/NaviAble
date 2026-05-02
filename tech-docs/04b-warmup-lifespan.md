# Phase 04b — NLP Lifespan Warm-up

## Goal

Pay the model-load and first-forward-pass cost during boot, not on the
first user request. Same pattern as the vision warm-up in 03e.

## Prerequisites

- Phase 04a merged: `RobertaNlpService` is functional.
- Phase 02b merged: `create_app()` supports `lifespan`.

## Deliverables

Inside the `lifespan` context manager:

```python
nlp = RobertaNlpService(Path(settings.roberta_checkpoint_dir))
await nlp.score("test review with a ramp")
app.state.nlp = nlp
```

The warm-up text is short and uses words from the training distribution
(`ramp`, `accessibility`-adjacent). It does not need to score above any
threshold — the goal is to exercise the codepath, not to assert a value.

### Fail-fast on tokenizer/model mismatch

If `tokenizer.from_pretrained` and `model.from_pretrained` disagree on
vocab size, the failure surfaces as a tensor-shape error on the warm-up
call. That is exactly when you want the failure: at boot, before the
first user request, with a stack trace logged to ops.

Do **not** wrap the warm-up in a try/except that quietly continues. A
process that "boots" with a broken NLP module is a worse outage than a
process that fails to boot.

## Acceptance criteria

- [ ] App boot logs include `nlp.warmup.complete` before the server is
      marked ready.
- [ ] First real `/verify` request completes in roughly the same time as
      the second (within 20%).
- [ ] `app.state.nlp` is a `RobertaNlpService` instance after lifespan
      startup.
- [ ] Lifespan crashes loudly with a clear error when the checkpoint
      directory is missing or vocabulary-mismatched.

## Pitfalls / notes

- Vision warm-up (03e) and NLP warm-up run sequentially inside lifespan.
  Don't parallelise them — they're off the request path, and serial is
  simpler.
- Don't add a separate `/healthz` check that re-runs warm-up. `lifespan`
  is the contract; `/healthz` (phase 02f) only pings the DB.
