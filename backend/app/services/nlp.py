"""NLP service — RoBERTa text-integrity classifier."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)


class NlpService(Protocol):
    async def score(self, text: str) -> float: ...


class StubNlpService:
    async def score(self, text: str) -> float:
        return 0.5


class NlpUnavailable(RuntimeError):
    """NLP model is unavailable — infrastructure failure."""


class RobertaNlpService:
    def __init__(self, checkpoint_dir: Path, *, device: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(checkpoint_dir))
        self._model.eval()
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        # Read LABEL_1 index from checkpoint — never hard-code as 1
        self._label1_index = self._model.config.label2id.get("LABEL_1", 1)

    async def score(self, text: str) -> float:
        """Return P(LABEL_1) for the given review text."""
        return await asyncio.to_thread(self._infer, text)

    def _infer(self, text: str) -> float:
        import torch

        if not text:
            raise ValueError("Empty text reached NLP service — schema validation failure")

        tokens = self._tokenizer(
            text,
            truncation=True,
            max_length=256,
            padding=False,
            return_tensors="pt",
        ).to(self._device)

        with torch.inference_mode():
            logits = self._model(**tokens).logits
        probs = torch.softmax(logits, dim=-1)[0]
        return float(probs[self._label1_index].item())
