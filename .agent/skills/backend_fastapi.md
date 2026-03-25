# Skill: FastAPI Backend Engineering

## Purpose
Build the highly concurrent API Gateway, handle routing, database ORM, and ML model serving.

## Execution Directives
1. **Directory Structure**: Strictly use this structure:
   - `app/api/routers/` (FastAPI APIRouters)
   - `app/core/` (Config, Security, DB session)
   - `app/models/` (SQLAlchemy Models)
   - `app/schemas/` (Pydantic v2 Models)
   - `app/services/` (ML singletons, Business logic)
2. **Database Engine**: Use asynchronous SQLAlchemy (`ext.asyncio`). Use Alembic for migrations.
3. **State Management**: Load ML models into `app.state.yolo_model` and `app.state.roberta_model` during `@asynccontextmanager def lifespan(app: FastAPI)` to ensure they are loaded into GPU memory exactly once.
4. **Image Handling**: Stream incoming `UploadFile` payloads directly into memory buffers (`io.BytesIO`) to avoid disk I/O latency before passing to YOLO.