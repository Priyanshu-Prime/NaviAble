import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ROBERTA_FINAL_DIR

import torch
from transformers import pipeline

warnings.filterwarnings("ignore")


def _resolve_model_path() -> str:
    """
    Resolve which model to load:
    1) If NAVIABLE_ROBERTA_MODEL is set, use it (either HF repo id or local dir).
    2) Else if local trained dir exists (ROBERTA_FINAL_DIR with config.json), use it.
    3) Else fall back to 'roberta-base' (downloads from Hugging Face).
    """
    env_override = os.getenv("NAVIABLE_ROBERTA_MODEL")
    if env_override:
        print(f"Using NAVIABLE_ROBERTA_MODEL={env_override}")
        return env_override

    trained_dir = Path(ROBERTA_FINAL_DIR)
    if trained_dir.is_dir() and (trained_dir / "config.json").exists():
        return str(trained_dir)

    print(
        "Local trained model not found or incomplete; falling back to 'roberta-base'.\n"
        "To use a local trained model, train first:\n"
        "  python3 nlp/train_roberta.py\n"
        "Or set NAVIABLE_ROBERTA_MODEL to a local path or HF repo id."
    )
    return "roberta-base"


def interactive_integrity_engine():
    model_id_or_path = _resolve_model_path()
    device = 0 if torch.cuda.is_available() else -1

    print("Loading NaviAble Integrity Module (RoBERTa)...")
    try:
        classifier = pipeline(
            "text-classification",
            model=model_id_or_path,
            tokenizer=model_id_or_path,
            device=device,
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("\n" + "=" * 50)
    print(" NAVIABLE INTEGRITY ENGINE : LIVE TEST ")
    print(" Type 'exit' to quit.")
    print("=" * 50)

    while True:
        user_input = input("\nType a location review: ")

        if user_input.lower() == "exit":
            print("Shutting down Integrity Engine...")
            break

        if len(user_input.strip()) < 5:
            print("Review too short. Try a full sentence.")
            continue

        result = classifier(user_input)[0]

        if result["label"] == "LABEL_1":
            status = "VERIFIED GENUINE (Spatial Details Detected)"
        else:
            status = "FLAGGED: GENERIC (Accessibility Washing)"

        confidence = round(result["score"] * 100, 2)

        print("-" * 50)
        print(f"Result: {status}")
        print(f"Confidence: {confidence}%")
        print("-" * 50)


if __name__ == "__main__":
    interactive_integrity_engine()
