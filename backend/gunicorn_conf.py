"""
Gunicorn Configuration for Production Deployment
工业级配置：4 workers, 2 threads, 60s timeout
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8013"
backlog = 2048

# Worker processes - 工业级标准：CPU核心数*2 + 1
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
threads = 2  # 每个worker 2线程

# Timeouts
timeout = 60  # 60s超时
graceful_timeout = 30
keepalive = 5

# Memory limits - 防止内存泄漏
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# Process naming
proc_name = "embodied-robot-brain"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Preload app - 在fork worker前加载应用，减少内存使用
preload_app = True

# Worker hooks for health check
def on_starting(server):
    """服务器启动前"""
    server.log.info("Starting gunicorn server")

def on_reload(server):
    """服务器重载前"""
    server.log.info("Reloading gunicorn server")

def worker_int(worker):
    """Worker接收SIGINT"""
    worker.log.info(f"Worker {worker.pid} received INT signal")

def worker_abort(worker):
    """Worker接收SIGABRT"""
    worker.log.warning(f"Worker {worker.pid} received SIGABRT signal")
