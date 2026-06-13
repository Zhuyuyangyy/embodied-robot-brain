"""
Research Validator单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.research_validator import ResearchValidator


class TestResearchValidator:
    """Research Validator测试"""

    def test_init(self):
        """测试初始化"""
        validator = ResearchValidator()
        assert validator is not None
        assert hasattr(validator, 'name')
        assert validator.name == 'research_validator'

    def test_agent_state(self):
        """测试代理状态"""
        validator = ResearchValidator()
        assert validator.state == 'idle'

    async def test_validate_research(self):
        """测试验证研究"""
        validator = ResearchValidator()
        research_data = {
            'literature': {'papers': [{'title': '论文1'}]},
            'experiment': {'design': {'method': 'Deep Learning'}},
            'progress': {'completion': 80},
        }
        result = await validator.validate_research(research_data)
        assert 'overall_score' in result
        assert 'validation_details' in result

    async def test_evidence_alignment(self):
        """测试证据对齐"""
        validator = ResearchValidator()
        evidence = [
            {'claim': '深度学习有效', 'support': ['论文1', '论文2']},
            {'claim': 'Transformer更好', 'support': ['论文3']},
        ]
        alignment = await validator.check_evidence_alignment(evidence)
        assert 'alignment_score' in alignment
        assert 'consistency' in alignment

    async def test_conflict_detection(self):
        """测试冲突检测"""
        validator = ResearchValidator()
        papers = [
            {'id': 'p1', 'findings': '方法A准确率95%'},
            {'id': 'p2', 'findings': '方法A准确率85%'},
        ]
        conflicts = await validator.detect_conflicts(papers)
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0

    async def test_credibility_scoring(self):
        """测试可信度评分"""
        validator = ResearchValidator()
        paper = {
            'title': '测试论文',
            'journal': 'Nature',
            'citations': 100,
            'sample_size': 1000,
        }
        score = await validator.score_credibility(paper)
        assert 'overall' in score
        assert 'dimensions' in score
        assert 'methodology' in score['dimensions']
        assert 'reproducibility' in score['dimensions']

    async def test_synthesis(self):
        """测试综合分析"""
        validator = ResearchValidator()
        findings = [
            {'source': '论文1', 'finding': '发现1'},
            {'source': '论文2', 'finding': '发现2'},
        ]
        synthesis = await validator.synthesize(findings)
        assert 'summary' in synthesis
        assert 'key_insights' in synthesis
        assert 'recommendations' in synthesis

    async def test_three_layer_conflict_detection(self):
        """测试三层冲突检测"""
        validator = ResearchValidator()
        # Type-I: 方法不一致
        papers_type1 = [
            {'method': 'CNN', 'dataset': 'DatasetA', 'accuracy': 0.95},
            {'method': 'CNN', 'dataset': 'DatasetA', 'accuracy': 0.85},
        ]
        conflicts = await validator.detect_conflicts(papers_type1)
        assert any(c['type'] == 'type_i' for c in conflicts)

        # Type-II: 性能差距
        papers_type2 = [
            {'method': 'MethodA', 'dataset': 'DatasetA', 'accuracy': 0.95},
            {'method': 'MethodB', 'dataset': 'DatasetA', 'accuracy': 0.75},
        ]
        conflicts = await validator.detect_conflicts(papers_type2)
        assert any(c['type'] == 'type_ii' for c in conflicts)

        # Type-III: 理论矛盾
        papers_type3 = [
            {'theory': '理论A', 'conclusion': '结论1'},
            {'theory': '理论A', 'conclusion': '相反结论'},
        ]
        conflicts = await validator.detect_conflicts(papers_type3)
        assert any(c['type'] == 'type_iii' for c in conflicts)

    async def test_four_dimensional_scoring(self):
        """测试四维评分"""
        validator = ResearchValidator()
        paper = {
            'methodology': '严格',
            'reproducibility': '高',
            'statistical_rigor': '强',
            'novelty': '高',
        }
        score = await validator.score_credibility(paper)
        assert 'methodology' in score['dimensions']
        assert 'reproducibility' in score['dimensions']
        assert 'statistical_rigor' in score['dimensions']
        assert 'novelty' in score['dimensions']

    async def test_validation_pipeline(self):
        """测试验证流水线"""
        validator = ResearchValidator()
        research = {
            'topic': '深度学习',
            'literature': {'papers': []},
            'experiment': {'design': {}},
        }
        pipeline = await validator.run_validation_pipeline(research)
        assert 'stages' in pipeline
        assert 'final_score' in pipeline

    async def test_generate_validation_report(self):
        """测试生成验证报告"""
        validator = ResearchValidator()
        validation_results = {
            'score': 0.85,
            'conflicts': [],
            'recommendations': [],
        }
        report = await validator.generate_report(validation_results)
        assert 'summary' in report
        assert 'details' in report
        assert 'recommendations' in report

    async def test_cross_validation(self):
        """测试交叉验证"""
        validator = ResearchValidator()
        findings = [
            {'source': '研究1', 'result': '结果A'},
            {'source': '研究2', 'result': '结果A'},
            {'source': '研究3', 'result': '结果B'},
        ]
        cross_val = await validator.cross_validate(findings)
        assert 'consistency' in cross_val
        assert 'agreement_rate' in cross_val

    async def test_statistical_validation(self):
        """测试统计验证"""
        validator = ResearchValidator()
        data = {
            'sample_size': 1000,
            'p_value': 0.001,
            'confidence_interval': [0.85, 0.95],
            'effect_size': 0.5,
        }
        validation = await validator.validate_statistics(data)
        assert 'is_significant' in validation
        assert 'power' in validation

    async def test_meta_analysis(self):
        """测试元分析"""
        validator = ResearchValidator()
        studies = [
            {'effect_size': 0.5, 'sample_size': 100},
            {'effect_size': 0.6, 'sample_size': 200},
            {'effect_size': 0.4, 'sample_size': 150},
        ]
        meta = await validator.meta_analysis(studies)
        assert 'pooled_effect' in meta
        assert 'heterogeneity' in meta

    async def test_error_handling(self):
        """测试错误处理"""
        validator = ResearchValidator()
        # 测试无效数据
        with pytest.raises(ValueError):
            await validator.validate_research({})

    async def test_performance(self):
        """测试性能"""
        import time
        validator = ResearchValidator()
        start = time.time()
        await validator.validate_research({
            'literature': {'papers': []},
            'experiment': {'design': {}},
        })
        end = time.time()
        # 验证应该在5秒内完成
        assert end - start < 5.0

    async def test_concurrent_validations(self):
        """测试并发验证"""
        import asyncio
        validator = ResearchValidator()

        async def validate_task(i):
            return await validator.validate_research({
                'literature': {'papers': [{'title': f'论文{i}'}]},
                'experiment': {'design': {'method': f'方法{i}'}},
            })

        # 并发执行多个验证
        tasks = [validate_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert 'overall_score' in result
