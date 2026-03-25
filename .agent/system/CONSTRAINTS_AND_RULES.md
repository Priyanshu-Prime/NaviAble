# Autonomous Execution Constraints

## 1. Machine Learning Boundaries
- **NO TRAINING**: The YOLOv11 and RoBERTa models are ALREADY trained. The Vision model ran for 25 epochs. The NLP model underwent a rigorous 2-phase Ablation Study ending in a 402-row distilled dataset. DO NOT write code to retrain them. Your domain is **Inference, Deployment, and Serving**.

## 2. Hardware & Resource Management
- **VRAM Limits**: Target hardware is a GTX 1650 Ti (4GB VRAM). You MUST implement memory-efficient PyTorch inference. Models must be singletons. Implement `.to('cpu')` fallbacks if CUDA runs out of memory (OOM).
- **Concurrency**: ML inference blocks the Python GIL. You MUST use `asyncio.to_thread()` or `concurrent.futures.ThreadPoolExecutor` in FastAPI to prevent blocking concurrent web requests.

## 3. Frontend Strictness (Flutter)
- **Accessibility First**: Every interactive Flutter widget MUST be wrapped in a `Semantics()` widget. Hard requirement. Use high-contrast color themes and support dynamic font scaling.

## 4. Code Quality & Academic Rigor
- **Defensive Programming**: Implement exhaustive `try/except` blocks for all API calls and ML inferences.
- **Documentation**: Write PEP-8 compliant Python. Every class and function must have detailed docstrings explaining *why* the approach was chosen (e.g., "Using async to prevent YOLO inference from blocking the event loop").