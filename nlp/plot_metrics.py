import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ROBERTA_CHECKPOINTS_DIR

import matplotlib.pyplot as plt


def generate_training_graphs():
    state_file = ROBERTA_CHECKPOINTS_DIR / "checkpoint-205" / "trainer_state.json"

    try:
        with open(state_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Could not find {state_file}. Please check the folder path!")
        return

    log_history = data.get("log_history", [])

    epochs_train = []
    loss_train = []
    epochs_eval = []
    loss_eval = []
    accuracy_eval = []

    for log in log_history:
        if "loss" in log and "eval_loss" not in log:
            epochs_train.append(log["epoch"])
            loss_train.append(log["loss"])
        elif "eval_loss" in log:
            epochs_eval.append(log["epoch"])
            loss_eval.append(log["eval_loss"])
            if "eval_accuracy" in log:
                accuracy_eval.append(log["eval_accuracy"])

    plt.figure(figsize=(10, 6))
    plt.plot(epochs_train, loss_train, label="Training Loss", color="blue", marker="o")
    plt.plot(epochs_eval, loss_eval, label="Validation Loss", color="red", marker="x")
    plt.title("Model Loss Over Epochs (LLM-Distilled Dataset)")
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    plt.savefig("distilled_loss_graph.png")
    print("Saved Loss Graph -> distilled_loss_graph.png")
    plt.close()

    if accuracy_eval:
        plt.figure(figsize=(10, 6))
        plt.plot(
            epochs_eval,
            accuracy_eval,
            label="Validation Accuracy",
            color="green",
            marker="s",
        )
        plt.title("Model Accuracy Over Epochs (LLM-Distilled Dataset)")
        plt.xlabel("Epochs")
        plt.ylabel("Accuracy")
        plt.legend()
        plt.grid(True)
        plt.savefig("distilled_accuracy_graph.png")
        print("Saved Accuracy Graph -> distilled_accuracy_graph.png")
        plt.close()


if __name__ == "__main__":
    generate_training_graphs()
