from transformers import pipeline
import torch

def verify_reviews():
    model_path = "./NaviAble_RoBERTa_Final"
    
    # Check if GPU is available for faster testing
    device = 0 if torch.cuda.is_available() else -1
    
    try:
        print("Loading NaviAble Integrity Module...")
        classifier = pipeline(
            "text-classification", 
            model=model_path, 
            tokenizer=model_path,
            device=device
        )
    except Exception as e:
        print(f"Error: Could not load model. Ensure training finished successfully. {e}")
        return

    test_samples = [
        "Everything is fully accessible, 5 stars!", # Generic / Washing
        "The entrance has a 1:12 slope ramp with handrails at 34 inches height." # Genuine / Specific
    ]

    print("\n" + "="*40)
    print("NAVIABLE INTEGRITY ENGINE RESULTS")
    print("="*40)

    for text in test_samples:
        result = classifier(text)[0]
        # Map label names back to human-readable status
        status = "VERIFIED GENUINE" if result['label'] == 'LABEL_1' else "FLAGGED: GENERIC / WASHING"
        score = round(result['score'] * 100, 2)
        
        print(f"\nReview: \"{text}\"")
        print(f"Result: {status} ({score}% confidence)")

if __name__ == "__main__":
    verify_reviews()