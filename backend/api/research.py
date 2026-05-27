"""
API routes for research assistant
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from schemas import (
    LiteratureQuery,
    ExperimentDesignRequest,
    ProgressUpdate,
    ResearchSessionCreate,
    ChatMessage,
    LiteratureResponse,
    ExperimentResponse,
    ProgressResponse,
    ResearchSessionResponse,
    ChatResponse,
)
from agents.orchestrator import orchestrator, ResearchStage
from agents.literature_agent import LiteratureMode
from agents.progress_agent import TaskStatus

from loguru import logger

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/sessions", response_model=ResearchSessionResponse)
async def create_research_session(request: ResearchSessionCreate):
    """
    创建完整的研究会话
    启动：文献发现 → 实验设计 → 进度计划
    """
    try:
        result = await orchestrator.start_research_session(
            user_id=request.user_profile.user_id,
            research_topic=request.research_topic,
            goals=request.goals,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create research session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_research_session(session_id: str):
    """获取研究会话状态"""
    try:
        insights = await orchestrator.get_research_insights(session_id)
        return insights
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get research session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/literature/search")
async def search_literature(query: LiteratureQuery):
    """
    文献检索（RAG + Web搜索）
    """
    try:
        from agents.literature_agent import LiteratureAgent
        agent = LiteratureAgent()
        result = await agent.search(
            query=query.query,
            mode=LiteratureMode(query.mode.value),
            max_results=query.max_results,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Literature search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiment/design")
async def design_experiment(request: ExperimentDesignRequest):
    """
    实验设计（Chain-of-Design Loop反思回路）
    """
    try:
        from agents.experiment_agent import ExperimentDesignAgent
        agent = ExperimentDesignAgent()
        result = await agent.design_experiment(
            research_question=request.research_question,
            hypothesis=request.hypothesis,
            constraints=request.constraints,
            available_resources=request.available_resources,
            reflection_iterations=request.reflection_iterations,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Experiment design failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{session_id}")
async def get_progress_dashboard(session_id: str):
    """
    获取进度仪表板
    """
    try:
        dashboard = await orchestrator.progress_agent.get_dashboard(session_id)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progress/{session_id}/update")
async def update_progress(session_id: str, update: ProgressUpdate):
    """
    更新任务进度
    """
    try:
        result = await orchestrator.progress_agent.update_task_status(
            session_id=session_id,
            task_id=update.task_id,
            status=TaskStatus(update.status.value),
            progress=update.progress_percent,
            notes=update.notes,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(message: ChatMessage):
    """
    通用对话接口
    """
    try:
        # 简单的对话路由，实际可扩展为意图识别
        response_text = f"收到消息: {message.message}"
        if message.agent:
            response_text = f"[{message.agent}] {response_text}"

        return ChatResponse(
            response=response_text,
            agent=message.agent or "orchestrator",
            timestamp=__import__('datetime').datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
