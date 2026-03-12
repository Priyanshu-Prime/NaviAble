import os
import sys
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ROBERTA_FINAL_DIR

from transformers import pipeline

warnings.filterwarnings("ignore")


def run_comparison():
    print("Loading NaviAble Integrity Module (LLM-Distilled RoBERTa)...")

    model_path = str(ROBERTA_FINAL_DIR)

    try:
        classifier = pipeline(
            "text-classification", model=model_path, tokenizer=model_path
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    test_cases = [
        {
            "type": "Generic Praise (Accessibility Washing)",
            "text": "This restaurant is completely wheelchair accessible and the food is great!",
            "expected": "0 (Flagged/Generic)",
            "regex_behavior": "Would incorrectly PASS because it contains 'accessible' and 'wheelchair'.",
        },
        {
            "type": "True Physical Detail",
            "text": "The main entrance is flat, but the bathroom doors are too narrow to roll a wheelchair through.",
            "expected": "1 (Genuine Detail)",
            "regex_behavior": "Might FAIL if 'narrow' wasn't in the exact keyword list.",
        },
        {
            "type": "Negative/Irrelevant Context using Keywords",
            "text": "I had to walk up three flights of stairs because the elevator was broken.",
            "expected": "0 (Flagged/Negative)",
            "regex_behavior": "Would incorrectly PASS because it contains 'stairs' and 'elevator'.",
        },
    ]

    print("\n" + "=" * 75)
    print(" MODEL COMPARISON & CAPABILITY TEST ")
    print("=" * 75)

    for i, test in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test['type']}")
        print(f'Review Text: "{test["text"]}"')

        result = classifier(test["text"])[0]

        if result["label"] == "LABEL_1":
            model_pred = "1 (Genuine Detail)"
        else:
            model_pred = "0 (Flagged/Generic)"

        confidence = round(result["score"] * 100, 2)

        print(f"  Model Prediction: {model_pred} ({confidence}%)")
        print(f"  Expected:         {test['expected']}")
        print(f"  Regex Would:      {test['regex_behavior']}")


if __name__ == "__main__":
    run_comparison()
