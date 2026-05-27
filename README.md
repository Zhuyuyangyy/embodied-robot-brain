#embodied-robot-brain - Multi-Agent Research Assistant

## 项目概述

基于Agent架构的大学生个性化科研助手，实现从文献发现→实验方案生成→进度智能追踪的全链路闭环。

## 技术栈

- **后端**: Python + LangGraph + FastAPI + Neo4j + Milvus
- **前端**: Vue3 + Three.js + GSAP
- **LLM**: Claude/GPT-4 API
- **部署**: Docker + Gunicorn

## 快速启动

### 后端
```bash
cd backend
pip install -r requirements.txt
python main.py        # 启动主服务 (端口8013)
```

### 前端
```bash
cd frontend
npm install
npm run dev           # 开发服务器
```

## 核心Agent

| Agent | 文件 | 功能 |
|-------|------|------|
| LiteratureAgent | agents/literature_agent.py | 文献检索与综述 |
| ExperimentAgent | agents/experiment_agent.py | 实验方案设计 |
| ProgressAgent | agents/progress_agent.py | 进度追踪管理 |
| Orchestrator | agents/orchestrator.py | 任务编排协调 |

## API端点

- `POST /api/research/sessions` - 创建研究会话
- `GET /api/research/sessions/{id}` - 获取会话状态
- `POST /api/research/literature/search` - 文献检索
- `POST /api/research/experiment/design` - 实验设计
- `GET /api/research/progress/{session_id}` - 进度仪表板
- `POST /api/research/chat` - 通用对话

## 健康检查

- `GET /health` - 健康状态
- `GET /health/ready` - 就绪检查
- `GET /health/live` - 存活检查
- `GET /metrics` - Prometheus指标