# System Architecture Blueprint

## The NaviAble Trust Score Engine
The core innovation of this platform is the algorithmic combination of Vision and NLP.

**Flow**:
1. User uploads a review containing Text ($T$) and an Image ($I$).
2. NLP Engine processes $T$ -> Outputs $NLP_{conf}$ (0.0 to 1.0).
3. Vision Engine processes $I$ -> Outputs $VIS_{conf}$ (Highest bounding box confidence, 0.0 to 1.0).
4. **Trust Score Calculation**: 
   - Base Formula: $Trust Score = (W_1 \times NLP_{conf}) + (W_2 \times VIS_{conf})$
   - Weights: $W_1 = 0.4$, $W_2 = 0.6$ (Vision is prioritized as it proves physical existence).
   - If $VIS_{conf}$ is 0 (no object detected), cap the maximum $Trust Score$ at 0.5 regardless of text.

## Data Persistence Strategy
- **PostgreSQL**: Stores `User`, `Location`, `Review` (Text, Image URL, Trust Score, Extracted Features).
- **Blob Storage**: Images are saved to local disk (or S3 mock) and served as static files via FastAPI.