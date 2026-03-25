from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.middleware import RequestLoggingMiddleware, app_exception_handler

# Import all domain models so SQLAlchemy can resolve relationships
import app.domains.auth.models  # noqa: F401
import app.domains.workspace.models  # noqa: F401
import app.domains.memory_space.models  # noqa: F401
import app.domains.source.models  # noqa: F401
import app.domains.memory.models  # noqa: F401
import app.domains.ai.models  # noqa: F401

app = FastAPI(title="Project Memory", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_middleware(RequestLoggingMiddleware)

# --- API v1 ---
from fastapi import APIRouter

api_v1 = APIRouter(prefix="/api/v1")


@api_v1.get("/health")
def health_check():
    return {"status": "ok"}


from app.domains.auth.router import router as auth_router
from app.domains.workspace.router import router as workspace_router
from app.domains.memory_space.router import router as memory_space_router
from app.domains.source.router import router as source_router
from app.domains.memory.router import router as memory_router

api_v1.include_router(auth_router)
api_v1.include_router(workspace_router)
api_v1.include_router(memory_space_router)
api_v1.include_router(source_router)
api_v1.include_router(memory_router)

app.include_router(api_v1)
