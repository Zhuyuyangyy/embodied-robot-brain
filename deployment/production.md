# Embodied Robot Brain - 生产部署文档

## 环境变量

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false

# 服务配置
HOST=0.0.0.0
PORT=8013

# Neo4j数据库
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j
NEO4J_POOL_SIZE=5
NEO4J_MAX_OVERFLOW=20

# Milvus向量数据库
MILVUS_HOST=milvus
MILVUS_PORT=19530

# LLM配置
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
LLM_MODEL=claude-sonnet-4-20250514
LLM_TIMEOUT=30

# 限流配置
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60.0
RATE_LIMIT_PER_IP=30

# CORS白名单
CORS_ORIGINS=["https://your-domain.com","https://app.your-domain.com"]

# 日志
LOG_LEVEL=INFO

# Redis（可选，分布式部署用）
REDIS_URL=redis://redis:6379/0
```

## 启动命令

### 方式1: Gunicorn（推荐生产环境）

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 使用gunicorn启动（4 workers, 2 threads）
gunicorn main:app \
    -c gunicorn_conf.py \
    --bind 0.0.0.0:8013 \
    --workers 4 \
    --threads 2 \
    --timeout 60

# 或使用简写
gunicorn main:app -c gunicorn_conf.py
```

### 方式2: Docker Compose

```bash
# 构建并启动所有服务
docker-compose -f deployment/docker-compose.yml up -d

# 查看日志
docker-compose -f deployment/docker-compose.yml logs -f backend

# 重启服务
docker-compose -f deployment/docker-compose.yml restart backend
```

### 方式3: Kubernetes

```bash
kubectl apply -f deployment/k8s/
```

## Nginx 配置

```nginx
upstream embodied_robot_brain {
    least_conn;
    server 127.0.0.1:8013 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8014 weight=1 max_fails=3 fail_timeout=30s backup;
}

# IPO缓存配置
proxy_cache_path /var/cache/nginx/embodied_robot_brain 
    levels=1:2 
    keys_zone=embodied_cache:10m 
    max_size=1g 
    inactive=60m;

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    location / {
        proxy_pass http://embodied_robot_brain;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # IPO缓存
        proxy_cache embodied_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_key "$scheme$request_method$host$request_uri";
        add_header X-Cache-Status $upstream_cache_status;
    }

    location /metrics {
        proxy_pass http://embodied_robot_brain;
        proxy_set_header Host $host;
        
        # 限制访问（仅内部网络或监控服务）
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        deny all;
    }

    location /health {
        proxy_pass http://embodied_robot_brain;
        access_log off;
    }
}
```

## 健康检查

### Liveness Probe

```bash
# 检查服务是否存活
curl -f http://localhost:8013/health/live
```

### Readiness Probe

```bash
# 检查服务是否就绪（可接受流量）
curl -f http://localhost:8013/health/ready
```

### Kubernetes 配置

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8013
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8013
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

## 监控指标

访问 `http://localhost:8013/metrics` 获取Prometheus指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `research_assistant_http_requests_total` | Counter | HTTP请求总数 |
| `research_assistant_http_request_duration_seconds` | Histogram | 请求延迟分布 |
| `research_assistant_http_active_requests` | Gauge | 当前活跃请求数 |
| `research_assistant_llm_calls_total` | Counter | LLM调用总数 |
| `research_assistant_llm_call_duration_seconds` | Histogram | LLM调用延迟 |
| `research_assistant_llm_tokens_total` | Counter | Token使用量 |
| `research_assistant_agent_tasks_total` | Counter | Agent任务总数 |
| `research_assistant_kg_nodes_total` | Gauge | 知识图谱节点数 |

## 限流说明

三层滑动窗口限流：

1. **全局限流**: 100请求/分钟（所有IP总和）
2. **单IP限流**: 30请求/分钟（每个IP）
3. **突发限流**: 20请求/10秒（每个IP）

当触发限流时，返回 `429 Too Many Requests`，响应头包含：
- `Retry-After`: 等待秒数
- `X-RateLimit-Limit`: 限流阈值
- `X-RateLimit-Remaining`: 剩余请求数

## 日志

使用Loguru结构化日志，格式：

```
2026-05-02 16:30:00.123 | INFO     | abc123def4567890 | → GET /api/v1/research
2026-05-02 16:30:00.456 | INFO     | abc123def4567890 | ← GET /api/v1/research 200 123.4ms
```

- `abc123def4567890`: 请求ID（X-Request-ID header）
- 请求ID贯穿整个请求链路

## 数据库连接池

Neo4j连接池配置：
- `pool_size=5`: 最小5个连接
- `max_overflow=20`: 最多20个额外连接
- `pool_timeout=30`: 获取连接超时30秒

## CORS配置

生产环境CORS白名单（非`*`）：
```python
CORS_ORIGINS = [
    "https://your-domain.com",
    "https://app.your-domain.com",
]
```
