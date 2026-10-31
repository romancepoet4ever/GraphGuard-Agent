import os

# === 强行禁用 LangSmith ===
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["LANGCHAIN_PROJECT"] = ""
# ==========================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from api.routers import traces, live
from src.utils.logger import setup_logger

settings = get_settings()
logger = setup_logger()
optional_router_status = {}


def _try_import_optional_router(module_name: str, router_name: str):
    try:
        module = __import__(module_name, fromlist=[router_name])
        optional_router_status[module_name] = "enabled"
        return getattr(module, router_name)
    except Exception as exc:
        optional_router_status[module_name] = f"disabled: {exc.__class__.__name__}: {exc}"
        logger.warning(f"Optional router disabled: {module_name} ({exc})")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AgentGraph Sentinel...")
    yield
    # 如需关闭时清理资源，在此添加


app = FastAPI(
    title=settings.APP_NAME,
    description="2026 CISCN Competition Entry - AgentGraph Sentinel",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in os.getenv(
        "GRAPHGUARD_CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://127.0.0.1:8501,http://localhost:8501",
    ).split(",") if item.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(traces.router)
app.include_router(live.router)

detection_router = _try_import_optional_router("api.routers.detection", "router")
if detection_router is not None:
    app.include_router(detection_router)

visualization_router = _try_import_optional_router("api.routers.visualization", "router")
if visualization_router is not None:
    app.include_router(visualization_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "model_provider": "OpenRouter" if settings.OPENROUTER_API_KEY else ("OpenAI" if settings.OPENAI_API_KEY else "Mock/Local"),
        "routers": {"api.routers.traces": "enabled", "api.routers.live": "enabled", **optional_router_status},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
