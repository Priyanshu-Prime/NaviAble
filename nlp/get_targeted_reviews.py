import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

import pandas as pd
import re
from datasets import load_dataset

print("Downloading the 650,000 Yelp reviews...")
dataset = load_dataset("yelp_review_full", split="train")
df = pd.DataFrame(dataset)

strict_keywords = [
    r"wheelchair", r"ramp", r"handicap", r"ada compliant", r"accessible", r"elevator",
]
pattern = re.compile("|".join(strict_keywords), re.IGNORECASE)

print("Hunting for actual accessibility reviews... (This takes about 10 seconds)")
df_targeted = df[df["text"].str.contains(pattern, na=False)]

print(f"Found {len(df_targeted)} highly relevant reviews!")

df_final = df_targeted.head(1000).copy()

output_path = PROJECT_ROOT / "targeted_accessibility_reviews.csv"
df_final[["text"]].to_csv(output_path, index=False)
print(f"Saved to '{output_path}'.")
