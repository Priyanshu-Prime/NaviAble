# Skill: Flutter Application Development

## Purpose
Build the cross-platform mobile frontend with a strict focus on screen-reader compatibility and smooth UX.

## Execution Directives
1. **State Management**: Use `flutter_riverpod`. Keep UI strictly separated from business logic. Providers should handle API calls and loading states.
2. **API Layer**: Use the `dio` package. Implement `Interceptors` to automatically attach JWT tokens and log request/response times (critical for benchmarking ML latency).
3. **Accessibility Mandate**: 
   - Wrap images in `Semantics(image: true, label: 'Description of accessibility feature')`.
   - Ensure buttons have `minTouchTargetSize` of at least 48x48 logical pixels.
4. **Data Optimization**: Use `flutter_image_compress` before uploading images to FastAPI. High-res images will crash the YOLO model on the 4GB VRAM GPU.