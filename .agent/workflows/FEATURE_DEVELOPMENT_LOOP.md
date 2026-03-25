# Workflow: End-to-End Feature Development

Execute this loop sequentially when asked to build platform features.

1. **Schema Definition (Backend)**: Define Pydantic models in `schemas.py` and SQLAlchemy models in `models.py`.
2. **Service Layer (Backend)**: Implement the business logic or ML inference wrappers in `services/`. Ensure async non-blocking execution.
3. **API Routing (Backend)**: Wire the service to a FastAPI endpoint. Test it.
4. **Data Models (Frontend)**: Generate Dart data classes with `json_serializable` or `freezed` to match the FastAPI JSON contract.
5. **API Client (Frontend)**: Implement the Dio repository call.
6. **State (Frontend)**: Write the Riverpod provider to manage loading/success/error states.
7. **UI View (Frontend)**: Build the Flutter UI. Immediately implement `Semantics` wrappers for TalkBack/VoiceOver compatibility.