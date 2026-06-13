"""
conftest.py - pytest fixtures for Embodied Robot Brain
"""
import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sample_research_topic():
    return "基于深度学习的医学影像诊断"


@pytest.fixture
def sample_user_profile():
    return {
        "user_id": "test_user_123",
        "name": "测试用户",
        "major": "计算机科学",
        "research_interests": ["AI", "医学影像"],
        "skill_level": "intermediate",
    }


@pytest.fixture
def sample_research_session():
    return {
        "session_id": "test_session_001",
        "user_profile": {
            "user_id": "test_user_123",
            "name": "测试用户",
            "major": "计算机科学",
            "research_interests": ["AI", "医学影像"],
        },
        "research_topic": "Transformer在医学影像中的应用",
        "goals": ["完成文献调研", "设计实验方案", "撰写论文"],
        "status": "active",
    }


@pytest.fixture
def sample_literature_search_request():
    return {
        "query": "深度学习医学影像分割",
        "mode": "hybrid",
        "max_results": 10,
        "filters": {
            "year_from": 2020,
            "year_to": 2024,
            " journals": ["Nature", "Science", "IEEE TMI"],
        },
    }


@pytest.fixture
def sample_experiment_design_request():
    return {
        "research_question": "如何提高U-Net在医学影像分割中的准确率？",
        "hypothesis": "引入注意力机制可提升分割准确率",
        "constraints": ["计算资源有限", "数据集规模中等"],
        "reflection_iterations": 3,
    }


@pytest.fixture
def sample_tcm_herb_pairs():
    return [
        {"herb_a": "甘草", "herb_b": "甘遂", "conflict_type": "十八反", "error_value": 1.0},
        {"herb_a": "乌头", "herb_b": "贝母", "conflict_type": "十八反", "error_value": 1.0},
        {"herb_a": "藜芦", "herb_b": "人参", "conflict_type": "十八反", "error_value": 1.0},
        {"herb_a": "硫黄", "herb_b": "朴硝", "conflict_type": "十九畏", "error_value": 0.7},
        {"herb_a": "水银", "herb_b": "砒霜", "conflict_type": "十九畏", "error_value": 0.7},
    ]


@pytest.fixture
def sample_physics_gate_config():
    return {
        "delta_initial": 0.05,
        "delta_relaxed": 0.10,
        "retry_threshold": 3,
        "constraint_library": "tcm",
    }


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    mock = AsyncMock()
    mock.generate_response.return_value = {
        "content": "这是LLM生成的测试响应",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }
    return mock


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    mock = MagicMock()
    mock.session.return_value.__enter__ = MagicMock()
    mock.session.return_value.__exit__ = MagicMock()
    return mock


@pytest.fixture
def mock_milvus_client():
    """Mock Milvus client for testing."""
    mock = MagicMock()
    mock.search.return_value = [
        {"id": 1, "distance": 0.85, "entity": {"title": "测试论文1"}},
        {"id": 2, "distance": 0.75, "entity": {"title": "测试论文2"}},
    ]
    return mock


@pytest.fixture
def sample_conflict_detection_result():
    return {
        "conflicts_found": 3,
        "conflict_types": {
            "type_i": 1,
            "type_ii": 1,
            "type_iii": 1,
        },
        "details": [
            {
                "type": "type_i",
                "description": "方法不一致",
                "severity": "high",
                "papers": ["paper_001", "paper_002"],
            },
            {
                "type": "type_ii",
                "description": "性能差距",
                "severity": "medium",
                "papers": ["paper_003", "paper_004"],
            },
            {
                "type": "type_iii",
                "description": "理论矛盾",
                "severity": "low",
                "papers": ["paper_005", "paper_006"],
            },
        ],
    }


@pytest.fixture
def sample_credibility_score():
    return {
        "overall_score": 0.85,
        "dimensions": {
            "methodology": 0.90,
            "reproducibility": 0.80,
            "statistical_rigor": 0.85,
            "novelty": 0.85,
        },
        "confidence_interval": [0.80, 0.90],
    }
