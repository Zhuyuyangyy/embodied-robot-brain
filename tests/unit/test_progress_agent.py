"""
Progress Agent单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.progress_agent import ProgressAgent


class TestProgressAgent:
    """Progress Agent测试"""

    def test_init(self):
        """测试初始化"""
        agent = ProgressAgent()
        assert agent is not None
        assert hasattr(agent, 'name')
        assert agent.name == 'progress_agent'

    def test_agent_state(self):
        """测试代理状态"""
        agent = ProgressAgent()
        assert agent.state == 'idle'

    async def test_create_plan(self):
        """测试创建计划"""
        agent = ProgressAgent()
        literature_results = {
            'papers': [{'title': '论文1'}, {'title': '论文2'}],
            'gaps': ['研究空白1'],
        }
        experiment_results = {
            'design': {'method': 'Deep Learning'},
            'iterations': 3,
        }
        plan = await agent.create_plan(literature_results, experiment_results)
        assert 'milestones' in plan
        assert 'timeline' in plan
        assert 'tasks' in plan

    async def test_update_progress(self):
        """测试更新进度"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        task_id = 'task_001'
        progress = {
            'status': 'in_progress',
            'completion': 50,
            'notes': '进展顺利',
        }
        result = await agent.update_progress(session_id, task_id, progress)
        assert 'updated' in result
        assert result['updated'] is True

    async def test_get_progress(self):
        """测试获取进度"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        progress = await agent.get_progress(session_id)
        assert 'overall_completion' in progress
        assert 'tasks' in progress
        assert 'milestones' in progress

    async def test_detect_blockers(self):
        """测试检测阻塞项"""
        agent = ProgressAgent()
        tasks = [
            {'id': 'task_1', 'status': 'completed'},
            {'id': 'task_2', 'status': 'blocked', 'blocker': '等待数据'},
            {'id': 'task_3', 'status': 'in_progress'},
        ]
        blockers = await agent.detect_blockers(tasks)
        assert isinstance(blockers, list)
        assert len(blockers) > 0

    async def test_manage_milestones(self):
        """测试管理里程碑"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        milestones = [
            {'id': 'ms_1', 'name': '文献调研完成', 'due_date': '2024-01-15'},
            {'id': 'ms_2', 'name': '实验设计完成', 'due_date': '2024-01-30'},
        ]
        result = await agent.manage_milestones(session_id, milestones)
        assert 'created' in result
        assert result['created'] == 2

    async def test_generate_digital_twin(self):
        """测试生成数字孪生"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        twin = await agent.generate_digital_twin(session_id)
        assert 'knowledge_graph' in twin
        assert 'progress_map' in twin
        assert 'dependencies' in twin

    async def test_predict_completion(self):
        """测试预测完成时间"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        current_progress = {
            'completed_tasks': 5,
            'total_tasks': 10,
            'average_time_per_task': 2.5,
        }
        prediction = await agent.predict_completion(current_progress)
        assert 'estimated_days' in prediction
        assert 'confidence' in prediction

    async def test_generate_report(self):
        """测试生成报告"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        report = await agent.generate_report(session_id)
        assert 'summary' in progress
        assert 'achievements' in progress
        assert 'challenges' in progress
        assert 'next_steps' in progress

    async def test_track_dependencies(self):
        """测试跟踪依赖关系"""
        agent = ProgressAgent()
        tasks = [
            {'id': 'task_1', 'depends_on': []},
            {'id': 'task_2', 'depends_on': ['task_1']},
            {'id': 'task_3', 'depends_on': ['task_1', 'task_2']},
        ]
        dependencies = await agent.track_dependencies(tasks)
        assert 'graph' in dependencies
        assert 'critical_path' in dependencies

    async def test_allocate_resources(self):
        """测试资源分配"""
        agent = ProgressAgent()
        tasks = [
            {'id': 'task_1', 'priority': 'high', 'estimated_hours': 10},
            {'id': 'task_2', 'priority': 'medium', 'estimated_hours': 5},
            {'id': 'task_3', 'priority': 'low', 'estimated_hours': 3},
        ]
        allocation = await agent.allocate_resources(tasks)
        assert 'assignments' in allocation
        assert 'schedule' in allocation

    async def test_risk_assessment(self):
        """测试风险评估"""
        agent = ProgressAgent()
        project = {
            'tasks': [
                {'id': 'task_1', 'risk': 'high'},
                {'id': 'task_2', 'risk': 'low'},
            ],
            'timeline': 30,
        }
        risks = await agent.assess_risks(project)
        assert 'high_risks' in risks
        assert 'mitigation_strategies' in risks

    async def test_optimize_schedule(self):
        """测试优化进度安排"""
        agent = ProgressAgent()
        tasks = [
            {'id': 'task_1', 'duration': 5, 'dependencies': []},
            {'id': 'task_2', 'duration': 3, 'dependencies': ['task_1']},
            {'id': 'task_3', 'duration': 4, 'dependencies': ['task_1']},
        ]
        optimized = await agent.optimize_schedule(tasks)
        assert 'schedule' in optimized
        assert 'critical_path' in optimized
        assert 'total_duration' in optimized

    async def test_notify_stakeholders(self):
        """测试通知利益相关者"""
        agent = ProgressAgent()
        session_id = 'test_session_001'
        notification = {
            'type': 'milestone_reached',
            'message': '文献调研完成',
            'recipients': ['user_123'],
        }
        result = await agent.notify_stakeholders(session_id, notification)
        assert 'sent' in result
        assert result['sent'] is True

    async def test_error_handling(self):
        """测试错误处理"""
        agent = ProgressAgent()
        # 测试无效会话ID
        with pytest.raises(ValueError):
            await agent.get_progress('')

    async def test_performance(self):
        """测试性能"""
        import time
        agent = ProgressAgent()
        start = time.time()
        await agent.get_progress('test_session')
        end = time.time()
        # 获取进度应该在1秒内完成
        assert end - start < 1.0

    async def test_concurrent_updates(self):
        """测试并发更新"""
        import asyncio
        agent = ProgressAgent()

        async def update_task(i):
            return await agent.update_progress(
                'test_session',
                f'task_{i}',
                {'status': 'completed', 'completion': 100}
            )

        # 并发执行多个更新
        tasks = [update_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert result['updated'] is True
