"""
Experiment Agent单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.experiment_agent import ExperimentAgent


class TestExperimentAgent:
    """Experiment Agent测试"""

    def test_init(self):
        """测试初始化"""
        agent = ExperimentAgent()
        assert agent is not None
        assert hasattr(agent, 'name')
        assert agent.name == 'experiment_agent'

    def test_agent_state(self):
        """测试代理状态"""
        agent = ExperimentAgent()
        assert agent.state == 'idle'

    async def test_design_experiment(self):
        """测试实验设计"""
        agent = ExperimentAgent()
        request = {
            'research_question': '如何提高U-Net在医学影像分割中的准确率？',
            'hypothesis': '引入注意力机制可提升分割准确率',
            'constraints': ['计算资源有限', '数据集规模中等'],
            'reflection_iterations': 2,
        }
        result = await agent.design_experiment(request)
        assert 'iterations' in result
        assert 'final_design' in result
        assert 'improvements' in result

    async def test_reflexive_loop(self):
        """测试反思循环"""
        agent = ExperimentAgent()
        design = {
            'method': 'U-Net with Attention',
            'dataset': 'Medical Segmentation Decathlon',
            'metrics': ['Dice', 'HD95'],
        }
        iterations = await agent.reflexive_loop(design, max_iterations=3)
        assert isinstance(iterations, list)
        assert len(iterations) <= 3

    async def test_generate_design(self):
        """测试生成实验设计"""
        agent = ExperimentAgent()
        question = "如何提高图像分类准确率？"
        design = await agent.generate_design(question)
        assert 'method' in design
        assert 'dataset' in design
        assert 'metrics' in design

    async def test_review_design(self):
        """测试审查实验设计"""
        agent = ExperimentAgent()
        design = {
            'method': 'ResNet-50',
            'dataset': 'ImageNet',
            'metrics': ['Accuracy', 'Top-5 Accuracy'],
            'batch_size': 32,
            'learning_rate': 0.001,
        }
        review = await agent.review_design(design)
        assert 'strengths' in review
        assert 'weaknesses' in review
        assert 'suggestions' in review

    async def test_propose_improvements(self):
        """测试提出改进建议"""
        agent = ExperimentAgent()
        design = {
            'method': 'ResNet-50',
            'issues': ['过拟合', '训练速度慢'],
        }
        improvements = await agent.propose_improvements(design)
        assert isinstance(improvements, list)
        assert len(improvements) > 0

    async def test_generate_hypothesis(self):
        """测试生成假设"""
        agent = ExperimentAgent()
        question = "为什么Transformer在视觉任务中表现良好？"
        hypothesis = await agent.generate_hypothesis(question)
        assert 'hypothesis' in hypothesis
        assert 'rationale' in hypothesis
        assert 'testable' in hypothesis

    async def test_design_ablation_study(self):
        """测试消融实验设计"""
        agent = ExperimentAgent()
        components = ['Attention', 'Skip Connection', 'Batch Normalization']
        ablation = await agent.design_ablation_study(components)
        assert 'experiments' in ablation
        assert 'baseline' in ablation
        assert len(ablation['experiments']) == len(components)

    async def test_validate_design(self):
        """测试验证实验设计"""
        agent = ExperimentAgent()
        design = {
            'method': 'U-Net',
            'dataset': 'Medical Segmentation Decathlon',
            'metrics': ['Dice'],
            'sample_size': 100,
        }
        validation = await agent.validate_design(design)
        assert 'is_valid' in validation
        assert 'issues' in validation

    async def test_generate_protocol(self):
        """测试生成实验协议"""
        agent = ExperimentAgent()
        design = {
            'method': 'Deep Learning',
            'steps': ['数据预处理', '模型训练', '评估'],
        }
        protocol = await agent.generate_protocol(design)
        assert 'steps' in protocol
        assert 'timeline' in protocol
        assert 'resources' in protocol

    async def test_estimate_resources(self):
        """测试资源估算"""
        agent = ExperimentAgent()
        design = {
            'model': 'ResNet-50',
            'dataset_size': 1000000,
            'epochs': 100,
        }
        resources = await agent.estimate_resources(design)
        assert 'gpu_hours' in resources
        assert 'memory_gb' in resources
        assert 'storage_gb' in resources

    async def test_generate_evaluation_plan(self):
        """测试生成评估计划"""
        agent = ExperimentAgent()
        design = {
            'metrics': ['Accuracy', 'Precision', 'Recall', 'F1'],
            'validation': '5-fold Cross Validation',
        }
        eval_plan = await agent.generate_evaluation_plan(design)
        assert 'metrics' in eval_plan
        assert 'validation_strategy' in eval_plan
        assert 'statistical_tests' in eval_plan

    async def test_error_handling(self):
        """测试错误处理"""
        agent = ExperimentAgent()
        # 测试无效请求
        with pytest.raises(ValueError):
            await agent.design_experiment({
                'research_question': '',
                'hypothesis': '',
            })

    async def test_performance(self):
        """测试性能"""
        import time
        agent = ExperimentAgent()
        start = time.time()
        await agent.design_experiment({
            'research_question': '测试问题',
            'hypothesis': '测试假设',
            'constraints': [],
            'reflection_iterations': 1,
        })
        end = time.time()
        # 设计应该在10秒内完成
        assert end - start < 10.0

    async def test_concurrent_designs(self):
        """测试并发设计"""
        import asyncio
        agent = ExperimentAgent()

        async def design_task(i):
            return await agent.design_experiment({
                'research_question': f'问题{i}',
                'hypothesis': f'假设{i}',
                'constraints': [],
                'reflection_iterations': 1,
            })

        # 并发执行多个设计任务
        tasks = [design_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert 'iterations' in result
