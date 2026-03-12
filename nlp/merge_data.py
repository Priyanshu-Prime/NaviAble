import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT

import pandas as pd


def merge_and_balance():
    print("Loading original Groq dataset...")
    try:
        df1 = pd.read_csv(PROJECT_ROOT / "gold_standard_labels_groq.csv")
    except FileNotFoundError:
        print("Error: Could not find 'gold_standard_labels_groq.csv'")
        return

    print("Loading newly mined Groq dataset...")
    try:
        df2 = pd.read_csv(PROJECT_ROOT / "new_mined_data.csv")
    except FileNotFoundError:
        print("Error: Could not find 'new_mined_data.csv'")
        return

    combined_df = pd.concat([df1, df2], ignore_index=True)
    print(f"Total combined rows before balancing: {len(combined_df)}")

    df_ones = combined_df[combined_df["llm_label"] == 1]
    df_zeros = combined_df[combined_df["llm_label"] == 0]

    total_ones = len(df_ones)
    print(f"Total Genuine Reviews (1s) collected: {total_ones}")
    print(f"Total Generic/Negative Reviews (0s) collected: {len(df_zeros)}")

    print(f"\nBalancing dataset to {total_ones} Genuine vs {total_ones} Generic...")
    df_zeros_sampled = df_zeros.sample(n=total_ones, random_state=42)

    final_df = pd.concat([df_ones, df_zeros_sampled])
    final_df = final_df.sample(frac=1, random_state=42).reset_index(drop=True)

    if "label" in final_df.columns:
        final_df = final_df.drop(columns=["label"])

    final_df = final_df.rename(columns={"llm_label": "label"})
    final_df = final_df[["text", "label"]]

    output_filename = PROJECT_ROOT / "NaviAble_Final_Training_Data.csv"
    final_df.to_csv(output_filename, index=False)

    print(f"\nSUCCESS: Authentic, perfectly balanced dataset saved as '{output_filename}'")
    print(f"Final dataset size: {len(final_df)} rows.")


if __name__ == "__main__":
    merge_and_balance()
