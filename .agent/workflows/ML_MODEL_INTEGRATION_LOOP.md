# Workflow: ML Model Integration

Execute this loop when asked to connect the pre-trained `.pt` or Hugging Face models.

1. **Dependency Verification**: Ensure `torch`, `ultralytics`, and `transformers` are isolated in `requirements.txt`.
2. **Hardware Mapping Check**: Write code to explicitly check `torch.cuda.is_available()`. Log the device being used.
3. **Singleton Instantiation**: Write the `lifespan` context manager in `main.py` to load the models into memory ONCE. 
4. **Mock Testing**: Before wiring the endpoint, write an offline Python script passing a dummy image/string to verify model outputs.
5. **Error Boundaries**: Wrap inference calls in try/except blocks. Catch `RuntimeError` (often OOM) and implement a graceful fallback or 503 HTTP response.