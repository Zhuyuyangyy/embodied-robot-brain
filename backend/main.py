"""
智能原生教育 - Multi-Agent大学生个性化科研助手
FastAPI主入口 - 工业级标准

R2 note: this module is now a thin shim that re-exports ``app`` from
``app.py`` (the single canonical entry point). Existing references such
as ``uvicorn main:app`` continue to work, but the real application is
defined in :mod:`app`. See ``backend/app.py`` for the full
implementation (security headers, rate limiting, Prometheus, CORS
whitelist, structured logging, etc.).
"""
from app import app  # noqa: F401  -- re-exported for backwards compat
from app import *  # noqa: F401,F403  -- re-export public symbols


if __name__ == "__main__":
    # Delegate to the canonical entry point. Use ``app:app`` explicitly
    # so users do not see two different module:app strings in logs.
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8013,
        reload=False,
    )
