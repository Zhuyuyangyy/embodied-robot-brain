"""
API集成测试
"""
import pytest
from httpx import AsyncClient
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_research_session(client):
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
async def test_literature_search(client):
    """测试文献检索"""
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
async def test_experiment_design(client):
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
async def test_chat(client):
    """测试对话接口"""
    request = {
        "message": "我想了解关于强化学习的研究",
        "agent": "literature",
    }
    resp = await client.post("/api/v1/research/chat", json=request)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data["agent"] == "literature"


@pytest.mark.asyncio
async def test_rate_limit(client):
    """测试限流"""
    # 发送多个请求测试限流
    for i in range(5):
        resp = await client.get("/health")
        assert resp.status_code == 200
