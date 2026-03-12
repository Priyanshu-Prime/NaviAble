import os
import sys
import re
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GROQ_API_KEY, PROJECT_ROOT

import pandas as pd
from datasets import load_dataset
from groq import Groq

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not set. Add it to your .env file.")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)
MODEL_ID = "llama-3.1-8b-instant"

TARGET_ONES_NEEDED = 330
OUTPUT_FILE = str(PROJECT_ROOT / "new_mined_data.csv")

print("Downloading Yelp dataset...")
dataset = load_dataset("yelp_review_full", split="train")
df = pd.DataFrame(dataset)

print("Filtering for accessibility keywords...")
keywords = [
    r"wheelchair", r"ramp", r"handicap", r"ada compliant", r"accessible",
    r"elevator", r"paving", r"braille", r"tactile", r"grab bar",
    r"threshold", r"narrow", r"clearance", r"handrail", r"steps", r"stairs",
]
pattern = re.compile("|".join(keywords), re.IGNORECASE)

df_targeted = df[df["text"].str.contains(pattern, na=False)]
df_unseen = df_targeted.iloc[1000:].copy()

print(f"Found {len(df_unseen)} fresh reviews.")

if not os.path.exists(OUTPUT_FILE):
    pd.DataFrame(columns=["text", "llm_label"]).to_csv(OUTPUT_FILE, index=False)

ones_found = 0
print("\nStarting the hunt with AUTO-SAVE enabled! You can safely stop this at any time.\n")

for index, row in df_unseen.iterrows():
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

        temp_df = pd.DataFrame([{"text": review_text, "llm_label": label}])
        temp_df.to_csv(OUTPUT_FILE, mode="a", header=False, index=False)

        if label == 1:
            ones_found += 1
            print(
                f"Saved Genuine! (Total 1s: {ones_found}/{TARGET_ONES_NEEDED}) | Snippet: {review_text[:40]}..."
            )
        else:
            print("Trash filtered (0). Saved to dataset.")

        if ones_found >= TARGET_ONES_NEEDED:
            print("\nTarget reached! Stopping the hunt.")
            break

    except Exception as e:
        print(f"API Error: {e}")

    time.sleep(2.0)

print(f"\nDONE! All data is securely saved in '{OUTPUT_FILE}'.")
