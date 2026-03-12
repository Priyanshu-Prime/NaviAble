import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

import pandas as pd
import re
from datasets import load_dataset

print("Loading the full 650,000 cached reviews...")
dataset = load_dataset("yelp_review_full", split="train")
df = pd.DataFrame(dataset)

spatial_keywords = [
    r"inch", r"cm", r"degree", r"steep", r"grab bar", r"tactile",
    r"heavy door", r"paving", r"width", r"clearance", r"braille",
    r"ramp slope", r"handrail", r"threshold", r"narrow", r"wheelchair",
    r"accessible", r"steps", r"stairs",
]
pattern = re.compile("|".join(spatial_keywords), re.IGNORECASE)


def auto_label(text):
    if pattern.search(str(text)):
        return 1
    return 0


print("Scanning all 650,000 rows for spatial specificity...")
df["label"] = df["text"].apply(auto_label)

df_label_1 = df[df["label"] == 1]
df_label_0 = df[df["label"] == 0]

print(f"Total Specific Reviews found: {len(df_label_1)}")
print(f"Total Generic Reviews found: {len(df_label_0)}")

SAMPLE_SIZE = 4000

print(f"Extracting {SAMPLE_SIZE} of each for a perfectly balanced 50/50 dataset...")
balanced_df = pd.concat(
    [
        df_label_1.sample(n=SAMPLE_SIZE, random_state=42),
        df_label_0.sample(n=SAMPLE_SIZE, random_state=42),
    ]
)

balanced_df = balanced_df.sample(frac=1, random_state=42).reset_index(drop=True)
balanced_df = balanced_df[["text", "label"]]

output_path = PROJECT_ROOT / "production_roberta_balanced.csv"
balanced_df.to_csv(output_path, index=False)

print("\n--- BALANCING COMPLETE ---")
print(f"Total Rows: {len(balanced_df)}")
print(f"Label 0: {len(balanced_df[balanced_df['label'] == 0])}")
print(f"Label 1: {len(balanced_df[balanced_df['label'] == 1])}")
print(f"Saved as '{output_path}'.")
