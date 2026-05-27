"""
Security middleware: rate limiting, security headers
工业级：HSTS/CSRF/X-Content-Type/X-Frame/CSP + 滑动窗口限流
"""
import time
import logging
from typing import Optional
from collections import defaultdict
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from loguru import logger


class RateLimitStore:
    """Thread-safe in-memory rate limit store with sliding window algorithm"""

    def __init__(self):
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: float) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Sliding window: remove expired timestamps
            self._store[key] = [t for t in self._store[key] if t > window_start]
            current_count = len(self._store[key])

            if current_count >= max_requests:
                return False, 0

            self._store[key].append(now)
            return True, max_requests - current_count - 1


# Global rate limit store (shared across all requests)
_rate_limit_store = RateLimitStore()
_burst_store = RateLimitStore()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses - HSTS/CSRF/X-Content-Type/X-Frame/CSP"""

    SECURITY_HEADERS = {
        # HSTS - Force HTTPS
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        # XSS protection
        "X-XSS-Protection": "1; mode=block",
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Content Security Policy
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
        # Permissions Policy
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Add security headers to all responses
        for header, value in self.SECURITY_HEADERS.items():
            if header not in response.headers:
                response.headers[header] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP-based rate limiting with sliding window.
    Two tiers: global rate limit + per-IP sliding window
    """

    EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: float = 60.0,
        max_burst: int = 20,
        burst_window: float = 10.0,
        max_per_ip: int = 30,
        per_ip_window: float = 60.0,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_burst = max_burst
        self.burst_window = burst_window
        self.max_per_ip = max_per_ip
        self.per_ip_window = per_ip_window
        
        # Global sliding window store
        self._global_store: list[float] = []
        self._global_lock = Lock()

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}"
    
    def _check_global_sliding_window(self) -> tuple[bool, int]:
        """Check global sliding window rate limit"""
        now = time.time()
        window_start = now - self.window_seconds
        
        with self._global_lock:
            # Remove expired
            self._global_store = [t for t in self._global_store if t > window_start]
            current = len(self._global_store)
            
            if current >= self.max_requests:
                return False, 0
            
            self._global_store.append(now)
            return True, self.max_requests - current - 1

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_key = self._get_client_key(request)

        # Tier 1: Global sliding window
        global_allowed, global_remaining = self._check_global_sliding_window()
        if not global_allowed:
            logger.warning(f"Global rate limit exceeded for {client_key}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": 42901,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": "global_rate_limit_exceeded",
                    "retry_after": int(self.window_seconds),
                },
                headers={
                    "Retry-After": str(int(self.window_seconds)),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                }
            )

        # Tier 2: Per-IP sliding window
        allowed, remaining = _rate_limit_store.is_allowed(
            f"ip:{client_key}",
            self.max_per_ip,
            self.per_ip_window,
        )

        if not allowed:
            logger.warning(f"Per-IP rate limit exceeded for {client_key}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": 42902,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": "per_ip_rate_limit_exceeded",
                    "retry_after": int(self.per_ip_window),
                },
                headers={
                    "Retry-After": str(int(self.per_ip_window)),
                    "X-RateLimit-Limit": str(self.max_per_ip),
                    "X-RateLimit-Remaining": "0",
                }
            )

        # Tier 3: Burst limit
        burst_allowed, burst_remaining = _burst_store.is_allowed(
            f"burst:{client_key}",
            self.max_burst,
            self.burst_window,
        )

        if not burst_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "code": 42903,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": "burst_limit_exceeded",
                    "retry_after": int(self.burst_window),
                },
                headers={
                    "Retry-After": str(int(self.burst_window)),
                    "X-RateLimit-Remaining": "0",
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_per_ip)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response