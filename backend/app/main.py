from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.middleware import RequestLoggingMiddleware, app_exception_handler

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


# Future domain routers:
# from app.domains.auth.router import router as auth_router
# api_v1.include_router(auth_router)

app.include_router(api_v1)
