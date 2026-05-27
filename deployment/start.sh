#!/bin/bash
# Production deployment script

set -e

echo "=== 智能原生教育科研助手 - 启动脚本 ==="

# Check environment
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "警告: 未设置 LLM API密钥，将使用模拟模式"
fi

# Install dependencies
echo "安装依赖..."
cd backend
pip install -r requirements.txt

# Run tests
echo "运行测试..."
pytest tests/ -v

# Start server
echo "启动服务 (端口8013)..."
echo "  - 健康检查: http://localhost:8013/health"
echo "  - API文档:  http://localhost:8013/docs"
echo "  - 指标:     http://localhost:8013/metrics"

uvicorn main:app --host 0.0.0.0 --port 8013 --workers 4
