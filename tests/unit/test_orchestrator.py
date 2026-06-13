"""
Orchestrator单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.orchestrator import Orchestrator


class TestOrchestrator:
    """Orchestrator测试"""

    def test_init(self):
        """测试初始化"""
        orchestrator = Orchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'agents')
        assert hasattr(orchestrator, 'event_bus')

    def test_agent_registration(self):
        """测试代理注册"""
        orchestrator = Orchestrator()
        # 验证默认代理已注册
        assert 'literature' in orchestrator.agents
        assert 'experiment' in orchestrator.agents
        assert 'progress' in orchestrator.agents
        assert 'validator' in orchestrator.agents

    async def test_route_request(self):
        """测试请求路由"""
        orchestrator = Orchestrator()
        request = {
            'type': 'literature_search',
            'query': '深度学习',
        }
        result = await orchestrator.route_request(request)
        assert 'agent' in result
        assert result['agent'] == 'literature'

    async def test_parallel_execution(self):
        """测试并行执行"""
        orchestrator = Orchestrator()
        tasks = [
            {'agent': 'literature', 'task': 'search'},
            {'agent': 'experiment', 'task': 'design'},
            {'agent': 'progress', 'task': 'update'},
        ]
        results = await orchestrator.execute_parallel(tasks)
        assert isinstance(results, list)
        assert len(results) == 3

    async def test_sequential_execution(self):
        """测试顺序执行"""
        orchestrator = Orchestrator()
        tasks = [
            {'agent': 'literature', 'task': 'search'},
            {'agent': 'experiment', 'task': 'design'},
        ]
        results = await orchestrator.execute_sequential(tasks)
        assert isinstance(results, list)
        assert len(results) == 2

    async def test_event_handling(self):
        """测试事件处理"""
        orchestrator = Orchestrator()
        event = {
            'type': 'research_completed',
            'data': {'session_id': 'test_001'},
        }
        result = await orchestrator.handle_event(event)
        assert 'handled' in result
        assert result['handled'] is True

    async def test_agent_state_management(self):
        """测试代理状态管理"""
        orchestrator = Orchestrator()
        # 获取所有代理状态
        states = await orchestrator.get_agent_states()
        assert isinstance(states, dict)
        assert 'literature' in states
        assert 'experiment' in states

    async def test_research_session(self):
        """测试研究会话"""
        orchestrator = Orchestrator()
        session_config = {
            'user_profile': {'name': '测试用户'},
            'research_topic': '深度学习',
            'goals': ['文献调研', '实验设计'],
        }
        session = await orchestrator.create_research_session(session_config)
        assert 'session_id' in session
        assert 'status' in session

    async def test_session_management(self):
        """测试会话管理"""
        orchestrator = Orchestrator()
        # 创建会话
        session = await orchestrator.create_research_session({
            'user_profile': {'name': '测试用户'},
            'research_topic': '测试主题',
        })
        session_id = session['session_id']

        # 获取会话状态
        status = await orchestrator.get_session_status(session_id)
        assert 'session_id' in status
        assert 'status' in status

    async def test_timeout_management(self):
        """测试超时管理"""
        orchestrator = Orchestrator()
        # 设置超时
        orchestrator.set_timeout(5.0)

        # 测试超时处理
        async def slow_task():
            import asyncio
            await asyncio.sleep(10)
            return "完成"

        with pytest.raises(TimeoutError):
            await orchestrator.execute_with_timeout(slow_task())

    async def test_error_recovery(self):
        """测试错误恢复"""
        orchestrator = Orchestrator()
        # 模拟代理失败
        with patch.object(orchestrator.agents['literature'], 'search', side_effect=Exception("代理失败")):
            result = await orchestrator.handle_agent_failure('literature', 'search')
            assert 'recovered' in result
            assert 'fallback' in result

    async def test_load_balancing(self):
        """测试负载均衡"""
        orchestrator = Orchestrator()
        # 创建多个任务
        tasks = [
            {'agent': 'literature', 'task': f'search_{i}'}
            for i in range(10)
        ]
        distribution = orchestrator.distribute_tasks(tasks)
        assert 'literature' in distribution
        assert len(distribution['literature']) == 10

    async def test_priority_queue(self):
        """测试优先级队列"""
        orchestrator = Orchestrator()
        tasks = [
            {'priority': 'low', 'task': 'task_1'},
            {'priority': 'high', 'task': 'task_2'},
            {'priority': 'medium', 'task': 'task_3'},
        ]
        sorted_tasks = orchestrator.prioritize_tasks(tasks)
        assert sorted_tasks[0]['priority'] == 'high'
        assert sorted_tasks[-1]['priority'] == 'low'

    async def test_caching(self):
        """测试缓存"""
        orchestrator = Orchestrator()
        # 缓存结果
        key = 'test_key'
        value = {'result': 'test_value'}
        await orchestrator.cache_result(key, value)

        # 获取缓存
        cached = await orchestrator.get_cached_result(key)
        assert cached == value

    async def test_metrics_collection(self):
        """测试指标收集"""
        orchestrator = Orchestrator()
        metrics = await orchestrator.collect_metrics()
        assert 'agent_states' in metrics
        assert 'task_counts' in metrics
        assert 'performance' in metrics

    async def test_logging(self):
        """测试日志记录"""
        orchestrator = Orchestrator()
        # 记录事件
        await orchestrator.log_event('test_event', {'data': 'test'})

        # 获取日志
        logs = await orchestrator.get_logs()
        assert len(logs) > 0

    async def test_configuration(self):
        """测试配置"""
        orchestrator = Orchestrator()
        config = orchestrator.get_config()
        assert 'max_parallel_tasks' in config
        assert 'timeout' in config
        assert 'retry_count' in config

    async def test_error_handling(self):
        """测试错误处理"""
        orchestrator = Orchestrator()
        # 测试无效请求
        with pytest.raises(ValueError):
            await orchestrator.route_request({})

    async def test_performance(self):
        """测试性能"""
        import time
        orchestrator = Orchestrator()
        start = time.time()
        await orchestrator.get_agent_states()
        end = time.time()
        # 获取状态应该在1秒内完成
        assert end - start < 1.0

    async def test_concurrent_sessions(self):
        """测试并发会话"""
        import asyncio
        orchestrator = Orchestrator()

        async def create_session(i):
            return await orchestrator.create_research_session({
                'user_profile': {'name': f'用户{i}'},
                'research_topic': f'主题{i}',
            })

        # 并发创建多个会话
        tasks = [create_session(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert 'session_id' in result
