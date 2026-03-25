# Skill: RoBERTa NLP Integrity Engine

## Purpose
Filter generic praise and identify semantically genuine accessibility descriptions.

## Execution Directives
1. **Initialization**: Use Hugging Face `pipeline("text-classification", model="./NaviAble_RoBERTa_Final", device=0 if torch.cuda.is_available() else -1)`.
2. **Preprocessing**: Ensure inputs are truncated to 512 tokens. Sanitize text (remove emojis, excess whitespace) before inference.
3. **Classification Logic**: The model outputs logits. Apply Softmax. 
   - Label 0: Generic/Invalid context.
   - Label 1: Genuine physical detail.
   - Return the probability score of Label 1 to the API router.