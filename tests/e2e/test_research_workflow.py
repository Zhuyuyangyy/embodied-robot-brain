"""
端到端研究工作流测试
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


class TestResearchWorkflow:
    """研究工作流端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_research_workflow(self, client):
        """测试完整研究工作流"""
        # 1. 创建研究会话
        session_request = {
            "user_profile": {
                "user_id": "e2e_user",
                "name": "端到端测试用户",
                "major": "计算机科学",
                "research_interests": ["深度学习", "医学影像"],
            },
            "research_topic": "基于深度学习的医学影像分割",
            "goals": ["文献调研", "实验设计", "论文撰写"],
        }
        session_resp = await client.post("/api/v1/research/sessions", json=session_request)
        assert session_resp.status_code == 200
        session_data = session_resp.json()
        session_id = session_data["session_id"]

        # 2. 进行文献搜索
        literature_request = {
            "query": "深度学习医学影像分割",
            "mode": "hybrid",
            "max_results": 10,
        }
        lit_resp = await client.post("/api/v1/research/literature/search", json=literature_request)
        assert lit_resp.status_code == 200
        lit_data = lit_resp.json()
        assert "papers" in lit_data

        # 3. 设计实验
        experiment_request = {
            "research_question": "如何提高U-Net在医学影像分割中的准确率？",
            "hypothesis": "引入注意力机制可提升分割准确率",
            "constraints": ["计算资源有限", "数据集规模中等"],
            "reflection_iterations": 2,
        }
        exp_resp = await client.post("/api/v1/research/experiment/design", json=experiment_request)
        assert exp_resp.status_code == 200
        exp_data = exp_resp.json()
        assert "iterations" in exp_data

        # 4. 创建进度计划
        progress_request = {
            "session_id": session_id,
            "literature_results": lit_data,
            "experiment_results": exp_data,
        }
        prog_resp = await client.post("/api/v1/research/progress/plan", json=progress_request)
        assert prog_resp.status_code == 200
        prog_data = prog_resp.json()
        assert "milestones" in prog_data

        # 5. 更新进度
        update_request = {
            "session_id": session_id,
            "task_id": "literature_review",
            "progress": {
                "status": "completed",
                "completion": 100,
                "notes": "文献调研完成",
            },
        }
        update_resp = await client.post("/api/v1/research/progress/update", json=update_request)
        assert update_resp.status_code == 200
        assert update_resp.json()["updated"] is True

        # 6. 获取知识图谱
        kg_resp = await client.get(f"/api/v1/research/progress/knowledge-graph/{session_id}")
        assert kg_resp.status_code == 200
        kg_data = kg_resp.json()
        assert "nodes" in kg_data
        assert "edges" in kg_data

        # 7. 检查会话状态
        session_status_resp = await client.get(f"/api/v1/research/sessions/{session_id}")
        assert session_status_resp.status_code == 200
        session_status = session_status_resp.json()
        assert session_status["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_literature_to_experiment_workflow(self, client):
        """测试文献到实验的工作流"""
        # 1. 文献搜索
        lit_request = {
            "query": "Transformer医学影像",
            "mode": "semantic",
            "max_results": 5,
        }
        lit_resp = await client.post("/api/v1/research/literature/search", json=lit_request)
        assert lit_resp.status_code == 200
        lit_data = lit_resp.json()

        # 2. 基于文献结果设计实验
        exp_request = {
            "research_question": "如何将Transformer应用于医学影像分割？",
            "hypothesis": "Vision Transformer可以捕获全局特征",
            "constraints": ["需要大量标注数据"],
            "reflection_iterations": 2,
        }
        exp_resp = await client.post("/api/v1/research/experiment/design", json=exp_request)
        assert exp_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, client):
        """测试多代理协调"""
        # 检查所有代理状态
        states_resp = await client.get("/api/v1/orchestrator/states")
        assert states_resp.status_code == 200
        states = states_resp.json()

        # 验证所有代理都已注册
        assert "literature" in states
        assert "experiment" in states
        assert "progress" in states
        assert "validator" in states

        # 获取事件历史
        events_resp = await client.get("/api/v1/orchestrator/events")
        assert events_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, client):
        """测试错误恢复工作流"""
        # 1. 尝试获取不存在的会话
        resp = await client.get("/api/v1/research/sessions/nonexistent")
        assert resp.status_code == 404

        # 2. 创建新会话
        session_request = {
            "user_profile": {"name": "恢复测试用户"},
            "research_topic": "错误恢复测试",
        }
        session_resp = await client.post("/api/v1/research/sessions", json=session_request)
        assert session_resp.status_code == 200

        # 3. 验证系统仍然正常工作
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_concurrent_research_sessions(self, client):
        """测试并发研究会话"""
        import asyncio

        async def create_session(i):
            request = {
                "user_profile": {"name": f"用户{i}"},
                "research_topic": f"主题{i}",
            }
            return await client.post("/api/v1/research/sessions", json=request)

        # 并发创建多个会话
        tasks = [create_session(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # 验证所有会话都创建成功
        for resp in responses:
            assert resp.status_code == 200
            assert "session_id" in resp.json()

    @pytest.mark.asyncio
    async def test_websocket_integration(self, client):
        """测试WebSocket集成"""
        async with client.websocket_connect("/ws/e2e_test") as websocket:
            # 接收初始状态
            initial_data = await websocket.receive_json()
            assert "agent_states" in initial_data

            # 发送订阅请求
            await websocket.send_json({
                "type": "subscribe",
                "channels": ["agent_states", "research_updates"],
            })

            # 接收订阅确认
            sub_response = await websocket.receive_json()
            assert sub_response["type"] == "subscribed"

    @pytest.mark.asyncio
    async def test_research_session_with_validation(self, client):
        """测试带验证的研究会话"""
        # 1. 创建会话
        session_request = {
            "user_profile": {
                "name": "验证测试用户",
                "research_interests": ["深度学习"],
            },
            "research_topic": "深度学习模型验证",
            "goals": ["文献调研", "实验设计", "结果验证"],
        }
        session_resp = await client.post("/api/v1/research/sessions", json=session_request)
        assert session_resp.status_code == 200
        session_id = session_resp.json()["session_id"]

        # 2. 进行文献搜索
        lit_request = {
            "query": "深度学习模型验证",
            "mode": "hybrid",
            "max_results": 5,
        }
        lit_resp = await client.post("/api/v1/research/literature/search", json=lit_request)
        assert lit_resp.status_code == 200

        # 3. 设计实验
        exp_request = {
            "research_question": "如何验证深度学习模型的泛化能力？",
            "hypothesis": "交叉验证可以评估模型泛化能力",
            "constraints": ["数据集有限"],
            "reflection_iterations": 1,
        }
        exp_resp = await client.post("/api/v1/research/experiment/design", json=exp_request)
        assert exp_resp.status_code == 200

        # 4. 创建进度计划
        progress_request = {
            "session_id": session_id,
            "literature_results": lit_resp.json(),
            "experiment_results": exp_resp.json(),
        }
        prog_resp = await client.post("/api/v1/research/progress/plan", json=progress_request)
        assert prog_resp.status_code == 200

        # 5. 验证最终状态
        final_resp = await client.get(f"/api/v1/research/sessions/{session_id}")
        assert final_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_performance_under_load(self, client):
        """测试负载下的性能"""
        import time

        # 快速发送多个请求
        start = time.time()
        tasks = []
        for i in range(20):
            tasks.append(client.get("/health"))

        # 等待所有请求完成
        responses = []
        for task in tasks:
            resp = await task
            responses.append(resp)

        end = time.time()

        # 验证所有请求都成功
        for resp in responses:
            assert resp.status_code == 200

        # 验证性能（20个请求应该在5秒内完成）
        assert end - start < 5.0

    @pytest.mark.asyncio
    async def test_data_consistency(self, client):
        """测试数据一致性"""
        # 1. 创建会话
        session_request = {
            "user_profile": {"name": "一致性测试用户"},
            "research_topic": "数据一致性测试",
        }
        session_resp = await client.post("/api/v1/research/sessions", json=session_request)
        session_id = session_resp.json()["session_id"]

        # 2. 更新进度
        update_request = {
            "session_id": session_id,
            "task_id": "task_1",
            "progress": {"status": "completed", "completion": 100},
        }
        await client.post("/api/v1/research/progress/update", json=update_request)

        # 3. 验证数据一致性
        session_resp = await client.get(f"/api/v1/research/sessions/{session_id}")
        session_data = session_resp.json()
        assert session_data["session_id"] == session_id

        # 4. 获取进度
        kg_resp = await client.get(f"/api/v1/research/progress/knowledge-graph/{session_id}")
        assert kg_resp.status_code == 200
