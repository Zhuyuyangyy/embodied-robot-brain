"""
Prometheus metrics for FastAPI application
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Agent metrics
AGENT_TASK_COUNT = Counter(
    "agent_tasks_total",
    "Total agent tasks",
    ["agent_id", "task_type", "status"]
)

AGENT_TASK_DURATION = Histogram(
    "agent_task_duration_seconds",
    "Agent task duration in seconds",
    ["agent_id", "task_type"]
)

# Knowledge graph metrics
KG_NODE_COUNT = Gauge(
    "kg_nodes_total",
    "Total number of knowledge graph nodes",
    ["type"]
)

KG_EDGE_COUNT = Gauge(
    "kg_edges_total",
    "Total number of knowledge graph edges",
    ["relation_type"]
)

# Session metrics
ACTIVE_SESSIONS = Gauge(
    "active_sessions",
    "Number of active research sessions"
)


class MetricsMiddleware:
    """Middleware to collect Prometheus metrics for all requests"""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        
        import time
        start = time.perf_counter()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status = message.get("status", 200)
                REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status).inc()
            await send(message)
            
        await self.app(scope, receive, send_wrapper)
        duration = time.perf_counter() - start
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)