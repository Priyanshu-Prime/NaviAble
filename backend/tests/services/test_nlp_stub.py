"""Tests for NLP service stubs."""
import asyncio
import pytest
from app.services.nlp import StubNlpService


def test_stub_returns_float():
    svc = StubNlpService()
    result = asyncio.run(svc.score("any text"))
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0
