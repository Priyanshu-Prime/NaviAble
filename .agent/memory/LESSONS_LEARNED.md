# Agent Memory & Lessons Learned

This file is the autonomous agent's long-term memory. It contains project-specific quirks, resolved bugs, and architectural decisions made during development to prevent repeating mistakes.

## 1. Machine Learning & Hardware
- *Example*: (Date) Discovered that loading YOLOv11 and RoBERTa simultaneously on a 4GB VRAM GPU causes CUDA OutOfMemory. 
  - *Fix*: Implemented sequential loading or moved RoBERTa strictly to CPU if VRAM is exceeded.

## 2. Backend & FastAPI
- (Empty - waiting for first agent reflection)

## 3. Frontend & Flutter
- (Empty - waiting for first agent reflection)

## 4. Dependencies & Environment
- (Empty - waiting for first agent reflection)