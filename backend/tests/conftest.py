"""
Pytest configuration for the NaviAble backend test suite.

This module registers a session-scoped fixture that monkey-patches both
ML service singletons on ``app.state`` before the FastAPI lifespan starts.
Individual tests can override these app-level stubs by simply reassigning
``client.app.state.yolo_service`` / ``client.app.state.roberta_service``
inside their own ``with TestClient(app) as client:`` context.
"""

from __future__ import annotations

import pytest
