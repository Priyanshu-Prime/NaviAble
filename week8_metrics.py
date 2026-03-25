import pandas as pd
from transformers import pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore")

def generate_week8_report():
    print("Loading NaviAble Final Dataset...")
    try:
        df = pd.read_csv("NaviAble_Final_Training_Data.csv")
    except FileNotFoundError:
        print("Error: Could not find 'NaviAble_Final_Training_Data.csv'")
        return

    texts = df['text'].tolist()
    true_labels = df['label'].tolist()

    print("Loading NaviAble Integrity Module (RoBERTa)...")
    model_path = "./NaviAble_RoBERTa_Final"
    
    try:
        # Using device=0 to utilize your GTX 1650 Ti for faster inference
        classifier = pipeline("text-classification", model=model_path, tokenizer=model_path, device=0)
    except Exception as e:
        print(f"Loading to GPU failed, falling back to CPU. Error: {e}")
        classifier = pipeline("text-classification", model=model_path, tokenizer=model_path)

    pred_labels = []
    
    print("\nEvaluating Model on Dataset...")
    # Process reviews with a progress bar
    for text in tqdm(texts, desc="Scoring Reviews"):
        # Truncate to 512 tokens to prevent length errors on massive reviews
        result = classifier(text, truncation=True, max_length=512)[0]
        pred_labels.append(1 if result['label'] == 'LABEL_1' else 0)

    # Calculate core metrics
    acc = accuracy_score(true_labels, pred_labels)
    prec = precision_score(true_labels, pred_labels)
    rec = recall_score(true_labels, pred_labels)
    f1 = f1_score(true_labels, pred_labels)

    # Print the Terminal Report
    print("\n" + "="*50)
    print(" WEEK 8: NAVIABLE PERFORMANCE METRICS ")
    print("="*50)
    print(f"Accuracy  : {acc * 100:.2f}%")
    print(f"Precision : {prec * 100:.2f}%")
    print(f"Recall    : {rec * 100:.2f}%")
    print(f"F1-Score  : {f1 * 100:.2f}%")
    print("="*50)

    # Generate the Confusion Matrix Graphic
    cm = confusion_matrix(true_labels, pred_labels)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['0 (Generic/Fake)', '1 (Genuine)'], 
                yticklabels=['0 (Generic/Fake)', '1 (Genuine)'],
                annot_kws={"size": 16})
    
    plt.title('NaviAble NLP Confusion Matrix (LLM-Distilled Model)', fontsize=14, fontweight='bold')
    plt.ylabel('Actual Label (Ground Truth)', fontsize=12)
    plt.xlabel('Predicted Label (AI Decision)', fontsize=12)
    
    output_file = 'week8_confusion_matrix.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ SUCCESS: Confusion matrix visual saved as '{output_file}'")

if __name__ == "__main__":
    generate_week8_report()