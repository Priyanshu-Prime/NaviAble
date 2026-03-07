import pandas as pd
import numpy as np
import evaluate
import torch
from datasets import Dataset
from transformers import (
    RobertaTokenizer, 
    RobertaForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    DataCollatorWithPadding
)

def train_integrity_module():
    # 1. Load and prepare dataset
    print("Step 1: Loading NaviAble Dataset...")
    try:
        df = pd.read_csv("accessibility_reviews.csv")
    except FileNotFoundError:
        print("Error: accessibility_reviews.csv not found. Please run your data generation script first.")
        return

    raw_dataset = Dataset.from_pandas(df)
    # Split: 80% Train, 20% Validation
    ds_split = raw_dataset.train_test_split(test_size=0.2, seed=42)

    # 2. Tokenization Setup
    print("Step 2: Initializing Tokenizer...")
    model_ckpt = "roberta-base"
    tokenizer = RobertaTokenizer.from_pretrained(model_ckpt)

    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=128)

    tokenized_ds = ds_split.map(tokenize_function, batched=True)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # 3. Model Initialization
    print("Step 3: Loading Pre-trained RoBERTa weights...")
    # NOTE: The 'Missing'/'Unexpected' warnings here are normal and expected 
    # as we transition from Language Modeling to Classification.
    model = RobertaForSequenceClassification.from_pretrained(model_ckpt, num_labels=2)

    # 4. Metrics Definition
    accuracy_metric = evaluate.load("accuracy")
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return accuracy_metric.compute(predictions=predictions, references=labels)

    # 5. Audited Training Arguments
    print("Step 4: Configuring Trainer...")
    training_args = TrainingArguments(
        output_dir="./NaviAble_RoBERTa_Checkpoints",
        eval_strategy="epoch",          # Modern replacement for evaluation_strategy
        save_strategy="epoch",          # Must match eval_strategy for load_best_model
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=5,
        weight_decay=0.01,
        load_best_model_at_end=True,    # Ensures final model is the most accurate
        metric_for_best_model="accuracy",
        report_to="none",               # Modern replacement for logging_dir
        fp16=torch.cuda.is_available(), # Uses GPU acceleration if available
        push_to_hub=False
    )

    # 6. Training Execution
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_ds["train"],
        eval_dataset=tokenized_ds["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    print("Step 5: Starting Training (Integrity Module)...")
    trainer.train()

    # 7. Save Final Verified Model
    trainer.save_model("./NaviAble_RoBERTa_Final")
    tokenizer.save_pretrained("./NaviAble_RoBERTa_Final")
    print("\nSUCCESS: Model saved to ./NaviAble_RoBERTa_Final")

if __name__ == "__main__":
    train_integrity_module()