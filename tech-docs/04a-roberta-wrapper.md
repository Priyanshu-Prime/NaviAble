# Phase 04a — `RobertaNlpService` Wrapper

## Goal

The class shape and inference path for the RoBERTa text-integrity
classifier. Loads tokenizer + model once, exposes `score(text) -> float`,
and runs the blocking forward pass via `asyncio.to_thread`.

## Prerequisites

- Phase 02e merged: `NlpService` Protocol exists.
- Fine-tuned RoBERTa checkpoint at `NaviAble_RoBERTa_Final/`.

## Deliverables

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

Decision points worth recording:

- **`max_length=256`.** Accessibility reviews are short. 256 covers the
  long tail with negligible truncation; halving it would speed inference
  but truncate the long restaurant reviews the report flags as the
  hardest-to-classify cases.
- **`torch.inference_mode()`** is preferred over `torch.no_grad()` on
  modern PyTorch — slightly faster, and reflects intent.
- **`label2id` lookup** — the LABEL_1 index is read from the checkpoint,
  not hard-coded as `1`. If the model is retrained with a different
  label mapping, this code does not silently invert.

## Acceptance criteria

- [ ] `nlp.score("there is a steep ramp at the back entrance")` returns
      a probability `> 0.7`.
- [ ] `nlp.score("the food was great and the service was quick")`
      returns a probability `< 0.3`.
- [ ] `nlp.score("great ramp, if you enjoy climbing it")` (the report's
      sarcasm test case) returns `< 0.5`.
- [ ] Score is always in `[0, 1]` — no NaNs, no negatives, no values > 1.
- [ ] Two consecutive calls do not reload the model (assert via timing
      or by patching `from_pretrained`).

## Pitfalls / notes

- **Do not surface `LABEL_0`/`LABEL_1` strings outside this module.**
  They're an artefact of checkpoint naming. The only thing leaving the
  module is a probability.
- **Tokenizer caching:** `AutoTokenizer.from_pretrained` may hit the
  HuggingFace cache. In CI, set `TRANSFORMERS_OFFLINE=1` and ship the
  local checkpoint so tests don't reach the internet.
- **Don't validate empty input here.** Phase 02c rejects empty review
  upstream. If `_infer("")` ever runs, that is a programmer error and an
  exception is the right response.
