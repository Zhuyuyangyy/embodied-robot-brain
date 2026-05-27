"""
核心配置 - 智能原生教育科研助手
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "智能原生教育——Multi-Agent科研助手"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # 数据库 (Neo4j) - 连接池配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_POOL_SIZE: int = 5  # 最小连接数
    NEO4J_MAX_OVERFLOW: int = 20  # 最大连接数
    NEO4J_POOL_TIMEOUT: int = 30  # 连接池超时(秒)

    # Milvus向量数据库
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "research_papers"

    # LLM配置 (Claude/GPT-4) - 工业级超时和重试
    LLM_PROVIDER: str = "anthropic"  # anthropic / openai
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 30  # 30秒超时

    # 滑动窗口限流 - 三层
    RATE_LIMIT_MAX_REQUESTS: int = 100  # 全局限流
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    RATE_LIMIT_BURST: int = 20  # 突发限流
    RATE_LIMIT_BURST_WINDOW: float = 10.0
    RATE_LIMIT_PER_IP: int = 30  # 单IP限流
    RATE_LIMIT_PER_IP_WINDOW: float = 60.0

    # CORS - 白名单域名，不允许 *
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 日志 - Loguru
    LOG_LEVEL: str = "INFO"

    # Redis (可选，用于分布式)
    REDIS_URL: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
