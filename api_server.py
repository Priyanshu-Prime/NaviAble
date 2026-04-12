"""Backward-compatible entrypoint.

Use `app.main:app` (or `./run_api.sh`) for normal runs.
This module stays only to support older commands like `uvicorn api_server:app`.
"""

from app.main import app
