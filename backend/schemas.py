"""
Pydantic schemas for API request/response models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LiteratureSearchMode(str, Enum):
    RAG = "rag"
    WEB = "web"
    HYBRID = "hybrid"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


# ---- Request Models ----
class LiteratureQuery(BaseModel):
    query: str
    mode: LiteratureSearchMode = LiteratureSearchMode.HYBRID
    max_results: int = 10
    year_from: Optional[int] = None


class ExperimentDesignRequest(BaseModel):
    research_question: str
    hypothesis: Optional[str] = None
    constraints: List[str] = []
    available_resources: List[str] = []
    reflection_iterations: int = 3


class ProgressUpdate(BaseModel):
    task_id: str
    status: TaskStatus
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    notes: str = ""


class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    name: str = "大学生用户"
    major: str = ""
    research_interests: List[str] = []


class ResearchSessionCreate(BaseModel):
    user_profile: UserProfile
    research_topic: str
    goals: List[str] = []


# ---- Response Models ----
class Paper(BaseModel):
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    relevance_score: float = 0.0
    citations: int = 0


class LiteratureResponse(BaseModel):
    query: str
    mode: str
    papers: List[Dict[str, Any]]
    synthesis: str
    knowledge_graph: Dict[str, Any]
    errors: List[str] = []


class ExperimentIteration(BaseModel):
    iteration: int
    design: Dict[str, Any]
    review_notes: str
    review_score: float
    issues: List[str]


class ExperimentResponse(BaseModel):
    research_question: str
    hypothesis: Optional[str]
    iterations: List[ExperimentIteration]
    final_design: Dict[str, Any]
    reflection_score: float
    total_iterations: int


class TaskInfo(BaseModel):
    task_id: str
    title: str
    track: str
    status: str
    progress: float
    subtasks: List[Dict[str, Any]] = []


class ProgressResponse(BaseModel):
    session_id: str
    tasks: Dict[str, TaskInfo]
    milestones: Dict[str, Any]
    estimated_completion: Optional[str]
    dual_track_summary: Dict[str, Any]
    last_updated: str


class ResearchSessionResponse(BaseModel):
    session_id: str
    user_id: str
    research_topic: str
    goals: List[str]
    status: str
    stages: Dict[str, Any]
    knowledge_graph: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None


class ChatMessage(BaseModel):
    message: str
    agent: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    timestamp: str
