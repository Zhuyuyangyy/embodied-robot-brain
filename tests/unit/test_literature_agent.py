"""
Literature Agent单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.literature_agent import LiteratureAgent


class TestLiteratureAgent:
    """Literature Agent测试"""

    def test_init(self):
        """测试初始化"""
        agent = LiteratureAgent()
        assert agent is not None
        assert hasattr(agent, 'name')
        assert agent.name == 'literature_agent'

    def test_agent_state(self):
        """测试代理状态"""
        agent = LiteratureAgent()
        assert agent.state == 'idle'

    async def test_search_literature(self):
        """测试文献搜索"""
        agent = LiteratureAgent()
        request = {
            'query': '深度学习医学影像分割',
            'mode': 'hybrid',
            'max_results': 5,
        }
        result = await agent.search(request)
        assert 'papers' in result
        assert 'total_count' in result
        assert 'search_time' in result

    async def test_search_modes(self):
        """测试不同搜索模式"""
        agent = LiteratureAgent()
        modes = ['keyword', 'semantic', 'hybrid']

        for mode in modes:
            request = {
                'query': '深度学习',
                'mode': mode,
                'max_results': 3,
            }
            result = await agent.search(request)
            assert 'papers' in result

    async def test_search_with_filters(self):
        """测试带过滤器的搜索"""
        agent = LiteratureAgent()
        request = {
            'query': 'Transformer',
            'mode': 'hybrid',
            'max_results': 10,
            'filters': {
                'year_from': 2020,
                'year_to': 2024,
                'journals': ['Nature', 'Science'],
            },
        }
        result = await agent.search(request)
        assert 'papers' in result

    async def test_generate_review(self):
        """测试生成文献综述"""
        agent = LiteratureAgent()
        papers = [
            {'title': '论文1', 'abstract': '摘要1'},
            {'title': '论文2', 'abstract': '摘要2'},
        ]
        review = await agent.generate_review(papers)
        assert 'summary' in review
        assert 'key_findings' in review
        assert 'research_gaps' in review

    async def test_extract_keywords(self):
        """测试关键词提取"""
        agent = LiteratureAgent()
        text = "深度学习在医学影像分割中的应用研究"
        keywords = await agent.extract_keywords(text)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    async def test_build_knowledge_graph(self):
        """测试构建知识图谱"""
        agent = LiteratureAgent()
        papers = [
            {'title': '论文1', 'authors': ['作者1'], 'citations': ['论文2']},
            {'title': '论文2', 'authors': ['作者2'], 'citations': []},
        ]
        graph = await agent.build_knowledge_graph(papers)
        assert 'nodes' in graph
        assert 'edges' in graph
        assert len(graph['nodes']) == 2

    async def test_citation_network(self):
        """测试引用网络分析"""
        agent = LiteratureAgent()
        papers = [
            {'id': 'p1', 'citations': ['p2', 'p3']},
            {'id': 'p2', 'citations': ['p3']},
            {'id': 'p3', 'citations': []},
        ]
        network = await agent.analyze_citation_network(papers)
        assert 'centrality' in network
        assert 'clusters' in network

    async def test_research_trend_analysis(self):
        """测试研究趋势分析"""
        agent = LiteratureAgent()
        papers = [
            {'year': 2020, 'topic': 'CNN'},
            {'year': 2021, 'topic': 'Transformer'},
            {'year': 2022, 'topic': 'Vision Transformer'},
            {'year': 2023, 'topic': 'Diffusion Model'},
        ]
        trends = await agent.analyze_trends(papers)
        assert 'emerging_topics' in trends
        assert 'declining_topics' in trends

    async def test_paper_quality_assessment(self):
        """测试论文质量评估"""
        agent = LiteratureAgent()
        paper = {
            'title': '测试论文',
            'abstract': '这是一个测试摘要',
            'journal': 'Nature',
            'citations': 100,
        }
        quality = await agent.assess_quality(paper)
        assert 'score' in quality
        assert 'dimensions' in quality

    async def test_semantic_search(self):
        """测试语义搜索"""
        agent = LiteratureAgent()
        query = "如何提高医学影像分割的准确率？"
        results = await agent.semantic_search(query, top_k=5)
        assert isinstance(results, list)
        assert len(results) <= 5

    async def test_keyword_extraction(self):
        """测试关键词提取"""
        agent = LiteratureAgent()
        text = """
        深度学习在医学影像分割中的应用取得了显著进展。
        卷积神经网络(CNN)和Transformer架构被广泛使用。
        """
        keywords = await agent.extract_keywords(text)
        assert isinstance(keywords, list)
        assert any('深度学习' in kw for kw in keywords)

    async def test_paper_summarization(self):
        """测试论文摘要生成"""
        agent = LiteratureAgent()
        paper = {
            'title': '测试论文',
            'abstract': '这是一篇关于深度学习的论文...',
            'full_text': '完整的论文内容...',
        }
        summary = await agent.summarize_paper(paper)
        assert 'summary' in summary
        assert 'key_points' in summary

    async def test_research_gap_identification(self):
        """测试研究空白识别"""
        agent = LiteratureAgent()
        papers = [
            {'title': '论文1', 'abstract': '研究了CNN'},
            {'title': '论文2', 'abstract': '研究了Transformer'},
        ]
        gaps = await agent.identify_gaps(papers)
        assert isinstance(gaps, list)
        assert len(gaps) > 0

    async def test_multi_language_support(self):
        """测试多语言支持"""
        agent = LiteratureAgent()
        # 测试中文查询
        result_cn = await agent.search({
            'query': '深度学习',
            'mode': 'keyword',
            'max_results': 3,
        })
        assert 'papers' in result_cn

        # 测试英文查询
        result_en = await agent.search({
            'query': 'deep learning',
            'mode': 'keyword',
            'max_results': 3,
        })
        assert 'papers' in result_en

    async def test_error_handling(self):
        """测试错误处理"""
        agent = LiteratureAgent()
        # 测试无效查询
        with pytest.raises(ValueError):
            await agent.search({
                'query': '',
                'mode': 'invalid',
                'max_results': -1,
            })

    async def test_performance(self):
        """测试性能"""
        import time
        agent = LiteratureAgent()
        start = time.time()
        await agent.search({
            'query': '深度学习',
            'mode': 'keyword',
            'max_results': 10,
        })
        end = time.time()
        # 搜索应该在5秒内完成
        assert end - start < 5.0
