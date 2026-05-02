# Phase 04 — Text Integrity Module (RoBERTa)

## Goal

Implement the production wrapper around the LLM-distilled RoBERTa classifier
described in Section 3.6 of the report. The wrapper takes a string and
returns one number — the probability in `[0, 1]` that the string contains
genuine accessibility information.

That probability becomes the NLP side of the late-fusion equation in phase 05.

## Prerequisites

- Phase 02 merged: `NlpService` Protocol exists.
- Fine-tuned RoBERTa checkpoint at `NaviAble_RoBERTa_Final/` — confirm with
  the NLP sub-team. Report numbers to beat: accuracy 92.79%, F1 93.08%,
  recall 97.01%.

## Spec details

| Field    | Value                                                       |
|----------|-------------------------------------------------------------|
| Input    | `str` (review text). Empty rejected upstream by Pydantic.   |
| Labels   | `LABEL_0` (generic / irrelevant), `LABEL_1` (genuine)       |
| Output   | `float` ∈ `[0, 1]` — `P(LABEL_1)`                           |

Empty string handling: the spec says "Empty text must be rejected upstream."
The schema in phase 02 enforces `min_length=1`. The wrapper does not need a
defensive empty check — if it ever sees `""`, that is a programmer error
and an exception is the right response.

## Current state

- `NaviAble_RoBERTa_Final/` has the trained model.
- `nlp/` directory has training-time scripts; runtime code does not live
  there. The runtime wrapper is a fresh module under `backend/app/services/nlp.py`.

## Deliverables

### 1. The wrapper module

`backend/app/services/nlp.py`:

```python
class RobertaNlpService:
    def __init__(self, checkpoint_dir: Path, *, device: str | None = None):
        self._tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint_dir))
        self._model.eval()
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        # LABEL_0 -> generic, LABEL_1 -> genuine accessibility insight
        self._label1_index = self._model.config.label2id.get("LABEL_1", 1)

    async def score(self, text: str) -> float:
        return await asyncio.to_thread(self._infer, text)

    @torch.inference_mode()
    def _infer(self, text: str) -> float:
        tokens = self._tokenizer(
            text,
            truncation=True,
            max_length=256,
            padding=False,
            return_tensors="pt",
        ).to(self._device)
        logits = self._model(**tokens).logits
        probs = torch.softmax(logits, dim=-1)[0]
        return float(probs[self._label1_index].item())
```

Key choices:
- `max_length=256` — accessibility reviews are short. 256 covers the
  long tail with negligible truncation; halving it would speed inference
  but truncate the long restaurant reviews that the report flags as the
  hardest-to-classify cases.
- `torch.inference_mode()` is preferred over `torch.no_grad()` on
  modern PyTorch — slightly faster, and reflects intent.
- The LABEL_1 index is read from `config.label2id`, not hard-coded as
  `1`. If the checkpoint is ever retrained with a different label
  mapping, this code does not silently invert.

### 2. Warm-up at app start

Same pattern as vision — load and run one inference inside `lifespan` so
the first real request does not pay the model-load cost:

```python
nlp = RobertaNlpService(settings.roberta_checkpoint_dir)
await nlp.score("test review with a ramp")
app.state.nlp = nlp
```

### 3. Failure modes

- **Tokenizer mismatch**: if `tokenizer.from_pretrained` and
  `model.from_pretrained` disagree on vocab size, fail at startup, not
  per-request. The `lifespan` warmup is sufficient — do not add a
  health check that quietly tolerates this.
- **Single-token inputs**: a one-character review is valid input to the
  model and will produce some probability. Don't second-guess it here;
  the Trust Score downstream is the right place to absorb low-quality
  text.
- **CUDA OOM under concurrent load**: the model is small; this is
  unlikely. If it happens in practice, batch inside the wrapper rather
  than dropping requests. Out of scope for the first cut.

### 4. Optional: dynamic batching (deferred)

The simple path runs one tokenisation + one forward pass per request.
Under load this is wasteful; a small async batcher (collect requests for
up to ~10 ms, run them as one batch, return individual results) is a
2–4x throughput win. **Do not build this in phase 04.** Ship the simple
path first and revisit only if profiling on real traffic shows it's
needed. Recording the option here so it is not re-discovered later.

## Acceptance criteria

- [ ] `nlp.score("there is a steep ramp at the back entrance")` returns
      a probability `> 0.7`.
- [ ] `nlp.score("the food was great and the service was quick")`
      returns a probability `< 0.3`.
- [ ] `nlp.score("great ramp, if you enjoy climbing it")` (the report's
      sarcasm test case) returns `< 0.5` — this is what motivated the
      LLM-distilled labels.
- [ ] Score is always in `[0, 1]` — no NaNs, no negatives, no values > 1.
- [ ] Two consecutive calls to `score` do not reload the model (assert
      via timing or by patching `from_pretrained`).
- [ ] Calling `score("")` raises (it should never happen — schema
      blocks it). Do not silently return `0.0`.

## Pitfalls / notes

- **Tokenizer caching**: `AutoTokenizer.from_pretrained` reads from the
  HuggingFace cache. In CI, set `TRANSFORMERS_OFFLINE=1` and ship the
  cache or the local `NaviAble_RoBERTa_Final` so the tests do not hit
  the internet.
- **Threading model**: PyTorch on CPU is multi-threaded by default and
  spawns one thread per core for matrix ops. With multiple `to_thread`
  calls in flight, this can cause oversubscription. Set
  `torch.set_num_threads(1)` at app start if profiling shows context
  switching dominating CPU.
- **Do not surface `LABEL_0`/`LABEL_1` strings to the rest of the
  codebase.** They are an artefact of the checkpoint naming. The only
  thing leaving this module is a probability. Keep the abstraction
  clean.
