import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

import pandas as pd
import re
from datasets import load_dataset

print("Downloading 10,000 real location reviews from Hugging Face...")
dataset = load_dataset("yelp_review_full", split="train[:10000]")
df = pd.DataFrame(dataset)

print(f"Successfully downloaded {len(df)} reviews!")

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


print("Applying spatial specificity labels to all 10,000 rows...")
df["label"] = df["text"].apply(auto_label)
df = df[["text", "label"]]

output_path = PROJECT_ROOT / "production_roberta_dataset.csv"
df.to_csv(output_path, index=False)

label_counts = df["label"].value_counts()
print("\n--- DATASET GENERATION COMPLETE ---")
print(f"Total Rows: {len(df)}")
print(f"Generic Reviews (Label 0): {label_counts.get(0, 0)}")
print(f"Specific Reviews (Label 1): {label_counts.get(1, 0)}")
print(f"File saved as '{output_path}'.")
