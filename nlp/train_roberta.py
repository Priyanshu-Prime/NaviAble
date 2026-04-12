import os
import sys
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PROJECT_ROOT, ROBERTA_CHECKPOINTS_DIR, ROBERTA_FINAL_DIR

import pandas as pd
import numpy as np
import torch
from datasets import Dataset
from transformers import (
    RobertaTokenizer,
    RobertaForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)


def train_integrity_module():
    print("Step 1: Loading NaviAble Dataset...")
    input_path = PROJECT_ROOT / "NaviAble_Final_Training_Data.csv"
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Error: {input_path} not found. Please run the data pipeline first.")
        return

    raw_dataset = Dataset.from_pandas(df)
    ds_split = raw_dataset.train_test_split(test_size=0.2, seed=42)

    print("Step 2: Initializing Tokenizer...")
    model_ckpt = "roberta-base"
    tokenizer = RobertaTokenizer.from_pretrained(model_ckpt)

    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=128)

    tokenized_ds = ds_split.map(tokenize_function, batched=True)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    print("Step 3: Loading Pre-trained RoBERTa weights...")
    model = RobertaForSequenceClassification.from_pretrained(model_ckpt, num_labels=2)

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        accuracy = float((predictions == labels).mean())
        return {"accuracy": accuracy}

    print("Step 4: Configuring Trainer...")
    ta_params = inspect.signature(TrainingArguments.__init__).parameters
    training_kwargs = {
        "output_dir": str(ROBERTA_CHECKPOINTS_DIR),
        "save_strategy": "epoch",
        "learning_rate": 2e-5,
        "per_device_train_batch_size": 8,
        "per_device_eval_batch_size": 8,
        "num_train_epochs": 5,
        "weight_decay": 0.01,
        "load_best_model_at_end": True,
        "metric_for_best_model": "accuracy",
        "report_to": "none",
        "fp16": torch.cuda.is_available(),
        "push_to_hub": False,
    }
    if "eval_strategy" in ta_params:
        training_kwargs["eval_strategy"] = "epoch"
    else:
        training_kwargs["evaluation_strategy"] = "epoch"

    training_args = TrainingArguments(**training_kwargs)

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": tokenized_ds["train"],
        "eval_dataset": tokenized_ds["test"],
        "data_collator": data_collator,
        "compute_metrics": compute_metrics,
    }
    trainer_params = inspect.signature(Trainer.__init__).parameters
    if "processing_class" in trainer_params:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    print("Step 5: Starting Training (Integrity Module)...")
    trainer.train()

    trainer.save_model(str(ROBERTA_FINAL_DIR))
    tokenizer.save_pretrained(str(ROBERTA_FINAL_DIR))
    print(f"\nSUCCESS: Model saved to {ROBERTA_FINAL_DIR}")


if __name__ == "__main__":
    train_integrity_module()
