"""Interactive terminal CLI for RoBERTa using the same backend service path."""

from __future__ import annotations

import sys

from app.core.config import settings
from app.services.ml import RobertaNLPService


def run() -> None:
    """Start an interactive loop that classifies review text."""
    service = RobertaNLPService(model_dir=settings.roberta_model_dir)
    service.initialize()

    print("=" * 60)
    print(" NaviAble Backend RoBERTa CLI")
    print(f" model_dir={service.model_dir}")
    print(" Type a review and press Enter. Type 'exit' to quit.")
    print("=" * 60)

    while True:
        try:
            text = input("\nreview> ").strip()
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
            continue
        except EOFError:
            # In non-interactive mode (piped stdin), EOF means input is finished.
            if not sys.stdin.isatty():
                print("\nInput stream ended. Exiting RoBERTa CLI...")
                break
            print("\nUse 'exit' to quit.")
            continue

        if text.lower() in {"exit", "quit"}:
            print("Exiting RoBERTa CLI...")
            break

        if len(text) < 5:
            print("Please enter at least 5 characters.")
            continue

        result = service.classify(text)
        print("-" * 60)
        print(f"label      : {result['label']}")
        print(f"is_genuine : {result['is_genuine']}")
        print(f"confidence : {result['confidence']}")
        print("-" * 60)


if __name__ == "__main__":
    run()

