"""
API集成测试
"""
import pytest
from httpx import AsyncClient
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "service" in data
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        """测试就绪检查"""
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_check(self, client):
        """测试存活检查"""
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        """测试指标端点"""
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]


class TestResearchSessionEndpoints:
    """研究会话端点测试"""

    @pytest.mark.asyncio
    async def test_create_research_session(self, client):
        """测试创建研究会话"""
        request = {
            "user_profile": {
                "user_id": "test_user",
                "name": "测试用户",
                "major": "计算机科学",
                "research_interests": ["AI", "Machine Learning"],
            },
            "research_topic": "Transformer在医学影像中的应用",
            "goals": ["完成文献调研", "设计实验方案"],
        }
        resp = await client.post("/api/v1/research/sessions", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["research_topic"] == "Transformer在医学影像中的应用"

    @pytest.mark.asyncio
    async def test_get_research_session(self, client):
        """测试获取研究会话"""
        # 先创建会话
        create_request = {
            "user_profile": {"name": "测试用户"},
            "research_topic": "测试主题",
        }
        create_resp = await client.post("/api/v1/research/sessions", json=create_request)
        session_id = create_resp.json()["session_id"]

        # 获取会话
        resp = await client.get(f"/api/v1/research/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_create_session_validation(self, client):
        """测试创建会话验证"""
        # 缺少必填字段
        request = {
            "user_profile": {"name": "测试用户"},
            # 缺少research_topic
        }
        resp = await client.post("/api/v1/research/sessions", json=request)
        assert resp.status_code == 422  # 验证错误

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, client):
        """测试获取不存在的会话"""
        resp = await client.get("/api/v1/research/sessions/nonexistent")
        assert resp.status_code == 404


class TestLiteratureEndpoints:
    """文献端点测试"""

    @pytest.mark.asyncio
    async def test_literature_search(self, client):
        """测试文献搜索"""
        request = {
            "query": "深度学习医学影像分割",
            "mode": "hybrid",
            "max_results": 5,
        }
        resp = await client.post("/api/v1/research/literature/search", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert "papers" in data or "knowledge_graph" in data

    @pytest.mark.asyncio
    async def test_literature_review(self, client):
        """测试文献综述"""
        request = {
            "query": "Transformer在医学影像中的应用",
            "mode": "hybrid",
            "max_results": 10,
            "generate_review": True,
        }
        resp = await client.post("/api/v1/research/literature/review", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert "papers" in data
        assert "review" in data

    @pytest.mark.asyncio
    async def test_literature_search_modes(self, client):
        """测试不同搜索模式"""
        modes = ["keyword", "semantic", "hybrid"]
        for mode in modes:
            request = {
                "query": "深度学习",
                "mode": mode,
                "max_results": 3,
            }
            resp = await client.post("/api/v1/research/literature/search", json=request)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_literature_search_validation(self, client):
        """测试文献搜索验证"""
        # 无效模式
        request = {
            "query": "深度学习",
            "mode": "invalid",
            "max_results": 5,
        }
        resp = await client.post("/api/v1/research/literature/search", json=request)
        assert resp.status_code == 422


class TestExperimentEndpoints:
    """实验端点测试"""

    @pytest.mark.asyncio
    async def test_experiment_design(self, client):
        """测试实验设计"""
        request = {
            "research_question": "如何提高U-Net在医学影像分割中的准确率？",
            "hypothesis": "引入注意力机制可提升分割准确率",
            "constraints": ["计算资源有限", "数据集规模中等"],
            "reflection_iterations": 2,
        }
        resp = await client.post("/api/v1/research/experiment/design", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert "iterations" in data
        assert "final_design" in data

    @pytest.mark.asyncio
    async def test_experiment_design_validation(self, client):
        """测试实验设计验证"""
        # 缺少必填字段
        request = {
            "research_question": "测试问题",
            # 缺少hypothesis
        }
        resp = await client.post("/api/v1/research/experiment/design", json=request)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_experiment_iterations(self, client):
        """测试实验迭代"""
        request = {
            "research_question": "测试问题",
            "hypothesis": "测试假设",
            "constraints": [],
            "reflection_iterations": 3,
        }
        resp = await client.post("/api/v1/research/experiment/design", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["iterations"]) == 3


class TestProgressEndpoints:
    """进度端点测试"""

    @pytest.mark.asyncio
    async def test_create_progress_plan(self, client):
        """测试创建进度计划"""
        request = {
            "session_id": "test_session",
            "literature_results": {"papers": []},
            "experiment_results": {"design": {}},
        }
        resp = await client.post("/api/v1/research/progress/plan", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert "milestones" in data
        assert "timeline" in data

    @pytest.mark.asyncio
    async def test_update_progress(self, client):
        """测试更新进度"""
        request = {
            "session_id": "test_session",
            "task_id": "task_001",
            "progress": {
                "status": "in_progress",
                "completion": 50,
                "notes": "进展顺利",
            },
        }
        resp = await client.post("/api/v1/research/progress/update", json=request)
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] is True

    @pytest.mark.asyncio
    async def test_get_knowledge_graph(self, client):
        """测试获取知识图谱"""
        resp = await client.get("/api/v1/research/progress/knowledge-graph/test_session")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data


class TestOrchestratorEndpoints:
    """编排器端点测试"""

    @pytest.mark.asyncio
    async def test_get_agent_states(self, client):
        """测试获取代理状态"""
        resp = await client.get("/api/v1/orchestrator/states")
        assert resp.status_code == 200
        data = resp.json()
        assert "literature" in data
        assert "experiment" in data
        assert "progress" in data
        assert "validator" in data

    @pytest.mark.asyncio
    async def test_get_event_history(self, client):
        """测试获取事件历史"""
        resp = await client.get("/api/v1/orchestrator/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data


class TestRateLimiting:
    """限流测试"""

    @pytest.mark.asyncio
    async def test_rate_limit(self, client):
        """测试限流"""
        # 发送多个请求测试限流
        for i in range(5):
            resp = await client.get("/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, client):
        """测试限流超限"""
        # 发送大量请求触发限流
        for i in range(100):
            resp = await client.get("/health")
            if resp.status_code == 429:
                # 触发限流
                assert "rate limit" in resp.json()["message"].lower()
                break


class TestSecurityHeaders:
    """安全头测试"""

    @pytest.mark.asyncio
    async def test_security_headers(self, client):
        """测试安全头"""
        resp = await client.get("/health")
        assert resp.status_code == 200
        # 检查安全头
        assert "X-Content-Type-Options" in resp.headers
        assert "X-Frame-Options" in resp.headers
        assert "X-XSS-Protection" in resp.headers


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_404_error(self, client):
        """测试404错误"""
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_405_error(self, client):
        """测试405错误"""
        resp = await client.put("/health")
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_validation_error(self, client):
        """测试验证错误"""
        resp = await client.post("/api/v1/research/sessions", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data


class TestWebSocket:
    """WebSocket测试"""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, client):
        """测试WebSocket连接"""
        async with client.websocket_connect("/ws/test_client") as websocket:
            # 发送消息
            await websocket.send_json({"type": "ping"})

            # 接收响应
            data = await websocket.receive_json()
            assert data["type"] == "pong"

    @pytest.mark.asyncio
    async def test_websocket_agent_state_updates(self, client):
        """测试WebSocket代理状态更新"""
        async with client.websocket_connect("/ws/test_client") as websocket:
            # 接收初始状态
            data = await websocket.receive_json()
            assert "agent_states" in data
