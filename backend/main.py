"""
智能原生教育 - Multi-Agent大学生个性化科研助手
FastAPI主入口 - 工业级标准
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from core.config import settings
from core.logging_config import setup_logging, RequestLoggingMiddleware, request_id_var, get_request_id
from core.security import SecurityHeadersMiddleware, RateLimitMiddleware
from core.metrics import MetricsMiddleware
from api.research import router as research_router

from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(
        "智能原生教育科研助手启动中...",
        extra={"version": settings.VERSION, "env": settings.ENVIRONMENT}
    )
    yield
    logger.info("科研助手关闭中...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于Agent架构的大学生个性化科研助手 - 文献发现→实验方案生成→进度智能追踪",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ---- Middleware Stack (order matters!) ----
# 1. Security headers (outermost - applies to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS (before other middleware)
# NEVER use "*" in production - must whitelist specific domains
cors_origins = settings.CORS_ORIGINS if not settings.DEBUG else settings.CORS_ORIGINS + ["http://localhost:3000", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
)

# 3. Metrics (track all requests)
app.add_middleware(MetricsMiddleware)

# 4. Rate limiting (global + per-IP sliding window)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    max_burst=settings.RATE_LIMIT_BURST,
    burst_window=settings.RATE_LIMIT_BURST_WINDOW,
    max_per_ip=30,
    per_ip_window=60.0,
)

# 5. Request logging with request_id
app.add_middleware(RequestLoggingMiddleware)


# ---- Unified Error Handling ----
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一HTTPException格式：{code, message, request_id}"""
    req_id = get_request_id() or "unknown"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """统一异常格式：{code: 500, message, request_id}"""
    req_id = get_request_id() or "unknown"
    logger.exception(f"Unhandled exception: {exc}", extra={"request_id": req_id})
    return JSONResponse(
        status_code=500,
        content={
            "code": 50000,
            "message": "服务器内部错误，请稍后再试",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id}
    )


# ---- Health Checks ----
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/ready")
async def readiness_check():
    return {"status": "ready"}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


# ---- Prometheus metrics endpoint ----
@app.get("/metrics")
async def metrics():
    from core.metrics import REQUEST_COUNT, REQUEST_LATENCY
    from starlette.responses import Response
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---- API Routes ----
app.include_router(research_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8013,
        reload=settings.DEBUG,
    )
