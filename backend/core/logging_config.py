"""
Structured logging with request ID tracing - 工业级日志配置
Loguru替代标准logging，request_id贯穿所有请求
"""
import sys
import re
import uuid
from datetime import datetime
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from loguru import logger
import sys as _sys

# Request ID context variable for tracing
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class _InterceptHandler:
    """Intercept standard logging and redirect to loguru"""
    def __init__(self):
        self._logger = logger
        
    def __call__(self, message):
        # Parse standard log record
        record = message.record
        level = record["level"].name
        msg = record["message"]
        name = record["name"]
        extra = record.get("extra", {})
        
        # Map to loguru
        loguru_logger = logger.bind(
            logger=name,
            **{k: v for k, v in extra.items() if k not in ["request_id", "method", "path", "status_code", "duration_ms"]}
        )
        
        if level == "INFO":
            loguru_logger.info(msg)
        elif level == "WARNING":
            loguru_logger.warning(msg)
        elif level == "ERROR":
            loguru_logger.error(msg)
        elif level == "DEBUG":
            loguru_logger.debug(msg)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


def setup_logging(level: str = "INFO") -> None:
    """Setup structured logging for the application using Loguru"""
    # Remove default handler
    logger.remove()
    
    # Console handler with structured format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[request_id]:-<16}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        _sys.stdout,
        format=log_format,
        level=level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Redirect standard logging to loguru
    import logging
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all HTTP requests with timing and request ID (Loguru)"""

    EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        import time

        req_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        if not req_id:
            req_id = str(uuid.uuid4())[:16]

        token = request_id_var.set(req_id)
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "-"

        # Use loguru for request logging
        req_logger = logger.bind(request_id=req_id, method=request.method, path=request.url.path, client_ip=client_ip)
        req_logger.info(f"-> {request.method} {request.url.path}")

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            log_level = "info" if response.status_code < 400 else "warning"
            if response.status_code >= 500:
                log_level = "error"

            resp_logger = logger.bind(
                request_id=req_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            resp_logger.log(log_level, f"<- {request.method} {request.url.path} {response.status_code} {duration_ms:.1f}ms")

            response.headers["X-Request-ID"] = req_id
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.bind(
                request_id=req_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            ).exception(f"X {request.method} {request.url.path} error: {exc}")
            raise
        finally:
            request_id_var.reset(token)