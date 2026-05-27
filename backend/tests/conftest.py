"""
conftest.py - pytest fixtures
"""
import pytest


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
