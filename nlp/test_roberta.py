import os
import sys
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ROBERTA_FINAL_DIR

import torch
from transformers import pipeline

warnings.filterwarnings("ignore")


def interactive_integrity_engine():
    model_path = str(ROBERTA_FINAL_DIR)
    device = 0 if torch.cuda.is_available() else -1

    print("Loading NaviAble Integrity Module (RoBERTa)...")
    try:
        classifier = pipeline(
            "text-classification",
            model=model_path,
            tokenizer=model_path,
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
