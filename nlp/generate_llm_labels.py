import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GROQ_API_KEY, PROJECT_ROOT

import pandas as pd
from groq import Groq

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not set. Add it to your .env file.")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)
MODEL_ID = "llama-3.1-8b-instant"

print("Loading reviews for AI Distillation via Groq...")
input_path = PROJECT_ROOT / "targeted_accessibility_reviews.csv"
try:
    df = pd.read_csv(input_path)
except FileNotFoundError:
    print(f"Error: Could not find '{input_path}'.")
    sys.exit(1)

df_subset = df.head(1000).copy()
llm_labels = []

print(f"\n--- Starting Groq API Labeling (Model: {MODEL_ID}) ---")
print("Target: 1,000 rows.")
print("Speed: 20 Requests Per Minute (Safe Buffer).")
print("Estimated Time: ~50 minutes.\n")

for index, row in df_subset.iterrows():
    review_text = str(row["text"])

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise data labeling assistant. Reply ONLY with the number 1 or 0.",
                },
                {
                    "role": "user",
                    "content": f"Does this review mention POSITIVE physical accessibility (ramps, elevators, wheelchair access)? \nReview: {review_text[:500]}",
                },
            ],
            model=MODEL_ID,
            temperature=0.1,
            max_tokens=10,
        )

        result = chat_completion.choices[0].message.content.strip()
        label = 1 if "1" in result else 0
        llm_labels.append(label)
        print(f"Row {index+1}/1000 | Label: {label} | Review: {review_text[:40]}...")

    except Exception as e:
        print(f"Error on row {index+1}: {e}")
        llm_labels.append(0)

    time.sleep(2.0)

df_subset["llm_label"] = llm_labels
output_path = PROJECT_ROOT / "gold_standard_labels_groq.csv"
df_subset.to_csv(output_path, index=False)

print(f"\nSUCCESS: Groq Distillation complete! File saved as '{output_path}'.")
