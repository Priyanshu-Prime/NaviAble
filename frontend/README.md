# NaviAble — Flutter Web Frontend

This is the Flutter Web frontend for **NaviAble**, the Dual-AI Accessibility
Verification Platform (IIIT Trichy Final Year Project – Team 7).

## Architecture at a Glance

```
lib/
├── main.dart                  # Entry point — ProviderScope + NaviAbleApp
├── theme/
│   └── app_theme.dart         # WCAG AA colour palette + MaterialTheme
├── models/
│   └── verification_models.dart   # API response data classes
├── api/
│   └── api_client.dart        # Dio HTTP client with logging interceptor
├── providers/
│   └── verify_provider.dart   # Riverpod state management (idle/loading/success/error)
├── widgets/
│   ├── submit_form.dart       # Image picker + review text field
│   ├── trust_score_gauge.dart # Animated circular Trust Score gauge
│   ├── nlp_result_card.dart   # RoBERTa NLP analysis result card
│   └── detection_result_card.dart  # YOLO vision detection result card
└── screens/
    └── home_screen.dart       # Responsive two-column layout
```

## Quick Start

### Prerequisites

| Tool | Min Version |
|------|-------------|
| Flutter SDK | 3.22.0 |
| Dart SDK | 3.3.0 |
| Chrome / Edge | latest |

Install Flutter: https://docs.flutter.dev/get-started/install

### Run in Development

```bash
# 1. Start the FastAPI backend first (from the repo root)
cd ../backend
NAVIABLE_DEMO_MODE=true ENABLE_HYBRID_CLIP=false uvicorn app.main:app --reload --port 8000

# 2. In a new terminal, install Flutter deps and run the web app
cd ../frontend
flutter pub get
flutter run -d chrome
```

The app opens at `http://localhost:PORT` (Flutter picks an available port).

### Point to a Different Backend

```bash
flutter run -d chrome \
  --dart-define=API_BASE_URL=http://your-server:8000
```

### Build for Production

```bash
flutter build web --release \
  --dart-define=API_BASE_URL=https://your-production-api.example.com
# Output in build/web/ — serve with any static file server.
```

### Run Tests

```bash
flutter test
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **flutter_riverpod** for state | Compile-time safe, testable, no boilerplate |
| **dio** for HTTP | Interceptors for JWT (future), request logging for ML latency benchmarking |
| **flutter_image_compress** | Pre-compress images before upload to prevent CUDA OOM on GTX 1650 Ti (4 GB VRAM) |
| Sealed `VerifyState` union | Exhaustive switch in UI, no null checks, clear state graph |
| `Semantics()` on every widget | WCAG AA / screen-reader compliance (`.agent` mandate) |
| `--dart-define=API_BASE_URL` | Same build artifact targets dev / staging / prod without recompile |

## Accessibility Compliance

Every interactive widget is wrapped in a `Semantics()` node with a descriptive
`label`. All buttons meet the **48 dp minimum touch-target** size. Colour
contrast ratios meet **WCAG AA** (4.5:1 for body text).

## Environment Variables (compile-time)

| `--dart-define` key | Default | Description |
|---------------------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | FastAPI backend base URL |

If you want the backend to use the CLIP hybrid classifier instead of YOLO-only
vision, start it with `ENABLE_HYBRID_CLIP=true` (it is safe to leave it off
for quick demo startup).

