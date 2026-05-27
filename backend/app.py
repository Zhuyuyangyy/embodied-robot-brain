"""
Multi-Agent Research Assistant - FastAPI Backend
Port: 8013
"""
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from agents.research_validator import ResearchValidatorAgent
from rag.knowledge_graph import KnowledgeGraphManager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ============================================================
# App Initialization
# ============================================================
app = FastAPI(
    title="Multi-Agent Research Assistant",
    version="1.0.0",
    description="智能原生教育——Multi-Agent大学生个性化科研助手"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Enums and Models
# ============================================================
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class AgentType(str, Enum):
    LITERATURE = "literature"
    EXPERIMENT = "experiment"
    PROGRESS = "progress"
    ORCHESTRATOR = "orchestrator"

class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class LiteratureSearchMode(str, Enum):
    RAG = "rag"
    WEB = "web"
    HYBRID = "hybrid"

# ---- Request/Response Models ----
class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "大学生用户"
    major: str = ""
    research_interests: List[str] = []
    skill_level: str = "intermediate"  # beginner, intermediate, advanced

class LiteratureQuery(BaseModel):
    query: str
    mode: LiteratureSearchMode = LiteratureSearchMode.HYBRID
    max_results: int = 10
    year_from: Optional[int] = None
    filters: Dict[str, Any] = {}

class ExperimentDesignRequest(BaseModel):
    research_question: str
    hypothesis: Optional[str] = None
    constraints: List[str] = []
    available_resources: List[str] = []
    reflection_iterations: int = 3

class ProgressUpdate(BaseModel):
    task_id: str
    status: TaskStatus
    progress_percent: float = 0.0
    notes: str = ""
    artifacts: Dict[str, Any] = {}

class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    agent: Optional[AgentType] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class ResearchSessionCreate(BaseModel):
    user_profile: UserProfile
    research_topic: str
    goals: List[str] = []

class ResearchSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_profile: UserProfile
    research_topic: str
    goals: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    literature_agent_state: Dict[str, Any] = {}
    experiment_agent_state: Dict[str, Any] = {}
    progress_agent_state: Dict[str, Any] = {}

# ============================================================
# In-Memory State Storage (replace with Redis/DB in production)
# ============================================================
sessions: Dict[str, ResearchSession] = {}
agent_workers: Dict[str, Dict[str, Any]] = {}
event_queue: asyncio.Queue = asyncio.Queue()
connection_manager: Dict[str, List[WebSocket]] = {}

# ============================================================
# Agent State Machines
# ============================================================
class AgentStateMachine:
    """Base state machine for agents with async event handling"""
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = "idle"  # idle, initializing, ready, working, waiting, error
        self.history: List[Dict[str, Any]] = []
        self.subscribers: List[WebSocket] = []
        
    async def transition(self, new_state: str, context: Dict[str, Any] = None):
        old_state = self.state
        self.state = new_state
        event = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "old_state": old_state,
            "new_state": new_state,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        self.history.append(event)
        await self.broadcast(event)
        
    async def broadcast(self, event: Dict[str, Any]):
        msg = json.dumps({"type": "agent_state", "data": event})
        dead = []
        for ws in self.subscribers:
            try:
                await ws.send_text(msg)
            except:
                dead.append(ws)
        for ws in dead:
            self.subscribers.remove(ws)

# ============================================================
# Literature Agent (RAG + Web)
# ============================================================
class LiteratureAgent:
    """
    文献Agent: 支持RAG检索和Web搜索双模式
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state_machine = AgentStateMachine(agent_id, AgentType.LITERATURE)
        self.rag_index_loaded = False
        
    async def initialize(self):
        """初始化文献Agent - 加载RAG索引"""
        await self.state_machine.transition("initializing")
        # Simulate loading RAG index
        await asyncio.sleep(0.1)
        self.rag_index_loaded = True
        await self.state_machine.transition("ready")
        
    async def search_literature(
        self, 
        query: str, 
        mode: LiteratureSearchMode = LiteratureSearchMode.HYBRID,
        max_results: int = 10,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行文献检索"""
        await self.state_machine.transition("working", {"query": query})
        
        results = {
            "query": query,
            "mode": mode,
            "papers": [],
            "web_results": [],
            "synthesis": "",
            "knowledge_graph_nodes": []
        }
        
        # RAG Search (vector similarity in Milvus)
        if mode in [LiteratureSearchMode.RAG, LiteratureSearchMode.HYBRID]:
            rag_results = await self._rag_search(query, max_results)
            results["papers"] = rag_results
            
        # Web Search (ArXiv + general web)
        if mode in [LiteratureSearchMode.WEB, LiteratureSearchMode.HYBRID]:
            web_results = await self._web_search(query, max_results)
            results["web_results"] = web_results
            
        # Build knowledge graph nodes from results
        results["knowledge_graph_nodes"] = self._extract_kg_nodes(results["papers"] + results["web_results"])
        
        # Generate synthesis
        results["synthesis"] = self._generate_synthesis(query, results)
        
        await self.state_machine.transition("ready", {"found": len(results["papers"])})
        return results
        
    async def _rag_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Milvus向量检索"""
        # Simulate RAG search - in production would call Milvus
        await asyncio.sleep(0.05)
        return [
            {
                "paper_id": f"paper_{i}",
                "title": f"[RAG] {query}相关研究论文 {i+1}",
                "authors": [f"作者{i+1}A", f"作者{i+1}B"],
                "year": 2023 - (i % 5),
                "venue": "Nature/Science/IEEE"[(i % 3)],
                "abstract": f"本文研究了{query}的相关方法，提出了一种创新性的解决方案...",
                "relevance_score": round(0.95 - i * 0.05, 2),
                "citations": (100 - i * 10),
                "methods": ["方法论A", "方法论B"][i % 2:i % 2 + 1],
                "key_findings": [f"发现{i+1}A", f"发现{i+1}B"]
            }
            for i in range(min(limit, 3))
        ]
        
    async def _web_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Web搜索(ArXiv API + 爬虫)"""
        await asyncio.sleep(0.05)
        return [
            {
                "source": "arxiv",
                "paper_id": f"arxiv_{i}",
                "title": f"[Web] {query}最新进展 {i+1}",
                "authors": [f"研究者{i+1}"],
                "year": 2024,
                "url": f"https://arxiv.org/abs/2401.{i:05d}",
                "abstract": f"预印本：关于{query}的最新研究发现...",
                "relevance_score": round(0.88 - i * 0.06, 2),
                "categories": ["cs.AI", "cs.LG"]
            }
            for i in range(min(limit, 2))
        ]
        
    def _extract_kg_nodes(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从论文中提取知识图谱节点"""
        nodes = []
        methods_set = set()
        for p in papers:
            for m in p.get("methods", []):
                if m not in methods_set:
                    methods_set.add(m)
                    nodes.append({
                        "id": f"method_{m}",
                        "type": "method",
                        "label": m,
                        "properties": {"frequency": 1}
                    })
        return nodes
        
    def _generate_synthesis(self, query: str, results: Dict[str, Any]) -> str:
        """生成文献综合分析"""
        total = len(results["papers"]) + len(results["web_results"])
        return (
            f"针对「{query}」的文献调研完成，共发现{total}篇相关文献。"
            f"其中RAG检索获得{len(results['papers'])}篇，向Web搜索获得{len(results['web_results'])}篇。"
            f"建议重点关注方法论A，其在该领域被广泛引用且与您的研究高度相关。"
        )

# ============================================================
# Experiment Design Agent (Chain-of-Design Loop)
# ============================================================
class ExperimentDesignAgent:
    """
    实验设计Agent: 反思式Chain-of-Design Loop
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state_machine = AgentStateMachine(agent_id, AgentType.EXPERIMENT)
        self.design_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        await self.state_machine.transition("initializing")
        await asyncio.sleep(0.1)
        await self.state_machine.transition("ready")
        
    async def design_experiment(
        self,
        research_question: str,
        hypothesis: Optional[str] = None,
        constraints: List[str] = [],
        available_resources: List[str] = [],
        reflection_iterations: int = 3
    ) -> Dict[str, Any]:
        """执行反思式实验设计循环"""
        await self.state_machine.transition("working", {"question": research_question})
        
        design = {
            "research_question": research_question,
            "hypothesis": hypothesis,
            "iterations": [],
            "final_design": {},
            "reflection_score": 0.0,
            "KG_updates": []
        }
        
        current_design = {
            "title": f"实验设计：{research_question[:30]}...",
            "objectives": [],
            "methodology": "",
            "hypothesis": hypothesis,
            "variables": {"independent": [], "dependent": [], "controlled": []},
            "procedure": [],
            "expected_outcomes": [],
            "risk_mitigation": []
        }
        
        # Chain-of-Design Loop: 设计→评审→反思→改进
        for i in range(reflection_iterations):
            iteration = {
                "iteration": i + 1,
                "design_snapshot": current_design.copy(),
                "reflection_notes": "",
                "improvements": [],
                "score": 0.0
            }
            
            # Step 1: 生成/更新设计
            current_design = await self._generate_design_step(
                research_question, hypothesis, constraints, 
                available_resources, current_design, i
            )
            
            # Step 2: 自我评审
            review = await self._self_review(current_design, research_question)
            iteration["reflection_notes"] = review["notes"]
            iteration["score"] = review["score"]
            
            # Step 3: 基于评审改进
            improvements = await self._propose_improvements(
                current_design, review, constraints, available_resources
            )
            iteration["improvements"] = improvements
            
            # 应用改进
            for imp in improvements:
                current_design = self._apply_improvement(current_design, imp)
            
            # 提取知识图谱更新
            kg_update = self._extract_design_kg(current_design, i)
            design["KG_updates"].append(kg_update)
            
            design["iterations"].append(iteration)
            
        design["final_design"] = current_design
        design["reflection_score"] = sum(it["score"] for it in design["iterations"]) / len(design["iterations"])
        
        await self.state_machine.transition("ready")
        return design
        
    async def _generate_design_step(
        self, question: str, hypothesis: Optional[str],
        constraints: List[str], resources: List[str],
        current: Dict[str, Any], iter_idx: int
    ) -> Dict[str, Any]:
        """生成设计步骤"""
        design = current.copy()
        
        if iter_idx == 0:
            design["objectives"] = [
                f"验证{hypothesis[:50] if hypothesis else question[:30]}的有效性",
                "对比现有基线方法",
                "分析关键影响因素"
            ]
            design["methodology"] = "实验法 + 定量分析"
            design["variables"]["independent"] = ["参数A", "参数B"]
            design["variables"]["dependent"] = ["准确率", "效率"]
            design["variables"]["controlled"] = ["数据集", "硬件环境"]
            design["procedure"] = [
                {"step": 1, "action": "准备数据集", "duration": "1天"},
                {"step": 2, "action": "实现基线", "duration": "3天"},
                {"step": 3, "action": "运行实验", "duration": "5天"},
                {"step": 4, "action": "结果分析", "duration": "2天"}
            ]
            design["expected_outcomes"] = ["准确率提升5%以上", "训练时间降低20%"]
            design["risk_mitigation"] = [
                {"risk": "数据不足", "mitigation": "使用数据增强"},
                {"risk": "过拟合", "mitigation": "交叉验证"}
            ]
        else:
            # 后续迭代细化
            design["procedure"].append(
                {"step": len(design["procedure"]) + 1, 
                 "action": f"反思改进步骤{iter_idx}", "duration": "1天"}
            )
            
        return design
        
    async def _self_review(self, design: Dict[str, Any], question: str) -> Dict[str, Any]:
        """自我评审设计"""
        await asyncio.sleep(0.02)
        
        issues = []
        score = 0.8
        
        if len(design.get("procedure", [])) < 3:
            issues.append("实验流程过于简单")
            score -= 0.1
        if not design.get("hypothesis"):
            issues.append("缺少明确假设")
            score -= 0.15
        if not design.get("risk_mitigation"):
            issues.append("缺少风险预案")
            score -= 0.1
            
        return {
            "score": max(score, 0.5),
            "notes": f"评审意见：{'；'.join(issues) if issues else '设计基本合理，可进一步优化'}",
            "issues": issues
        }
        
    async def _propose_improvements(
        self, design: Dict[str, Any], review: Dict[str, Any],
        constraints: List[str], resources: List[str]
    ) -> List[Dict[str, Any]]:
        """基于评审提出改进建议"""
        improvements = []
        
        for issue in review.get("issues", []):
            if "流程" in issue:
                improvements.append({
                    "type": "procedure",
                    "description": "增加对照实验组",
                    "action": "添加step: 设计对照组实验"
                })
            if "假设" in issue:
                improvements.append({
                    "type": "hypothesis", 
                    "description": "补充明确假设",
                    "action": "细化假设为可检验形式"
                })
                
        return improvements
        
    def _apply_improvement(self, design: Dict[str, Any], imp: Dict[str, Any]) -> Dict[str, Any]:
        """应用改进"""
        d = design.copy()
        if imp["type"] == "hypothesis":
            d["hypothesis"] = design.get("hypothesis") or "优化后假设：X与Y正相关"
        return d
        
    def _extract_design_kg(self, design: Dict[str, Any], iter_idx: int) -> Dict[str, Any]:
        """提取设计过程的知识图谱更新"""
        return {
            "iteration": iter_idx + 1,
            "nodes": [
                {"id": f"exp_{design['title'][:10]}", "type": "experiment", "label": design['title']},
                * [{"id": f"obj_{o[:20]}", "type": "objective", "label": o} 
                   for o in design.get("objectives", [])[:2]]
            ],
            "edges": []
        }

# ============================================================
# Progress Management Agent (Digital Twin KG)
# ============================================================
class ProgressAgent:
    """
    进度管理Agent: 数字孪生知识图谱 + 异步双轨管理
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state_machine = AgentStateMachine(agent_id, AgentType.PROGRESS)
        self.knowledge_graph: Dict[str, Any] = {
            "nodes": [],
            "edges": [],
            "tasks": {},
            "milestones": {}
        }
        
    async def initialize(self):
        await self.state_machine.transition("initializing")
        await asyncio.sleep(0.1)
        await self.state_machine.transition("ready")
        
    async def create_research_plan(
        self, 
        session_id: str,
        literature_results: Dict[str, Any],
        experiment_design: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于文献和实验设计创建研究计划"""
        await self.state_machine.transition("working")
        
        # 构建数字孪生知识图谱
        kg = self._build_digital_twin_kg(literature_results, experiment_design)
        self.knowledge_graph = kg
        
        # 生成任务时间线
        timeline = self._generate_timeline(experiment_design)
        
        plan = {
            "session_id": session_id,
            "knowledge_graph": kg,
            "timeline": timeline,
            "milestones": self._define_milestones(experiment_design),
            "alerts": [],
            "recommendations": []
        }
        
        await self.state_machine.transition("ready", {"tasks": len(timeline["tasks"])})
        return plan
        
    async def update_progress(
        self, 
        session_id: str, 
        task_id: str, 
        update: ProgressUpdate
    ) -> Dict[str, Any]:
        """更新任务进度"""
        if session_id in sessions:
            session = sessions[session_id]
            if "progress" not in session.progress_agent_state:
                session.progress_agent_state["progress"] = {}
            session.progress_agent_state["progress"][task_id] = update.dict()
            session.updated_at = datetime.now()
            
        # 重新计算知识图谱中的状态
        kg_update = await self._recalc_kg_on_update(session_id, task_id, update)
        
        # 检查是否需要提醒
        alerts = self._check_alerts(task_id, update)
        
        return {
            "task_id": task_id,
            "kg_update": kg_update,
            "alerts": alerts,
            "next_recommendations": self._get_next_recommendations(task_id)
        }
        
    async def _recalc_kg_on_update(
        self, session_id: str, task_id: str, update: ProgressUpdate
    ) -> Dict[str, Any]:
        """根据进度更新重新计算KG"""
        await asyncio.sleep(0.01)
        return {
            "updated_node_id": f"task_{task_id}",
            "new_status": update.status.value,
            "progress": update.progress_percent,
            "connected_nodes": []
        }
        
    def _check_alerts(self, task_id: str, update: ProgressUpdate) -> List[str]:
        """检查是否触发预警"""
        alerts = []
        if update.progress_percent > 0 and update.progress_percent < 30:
            alerts.append("任务进度较慢，请关注")
        if update.status == TaskStatus.FAILED:
            alerts.append("任务失败，需要介入")
        return alerts
        
    def _get_next_recommendations(self, task_id: str) -> List[str]:
        """获取下一步建议"""
        return [
            f"任务{task_id}完成后，建议启动相关验证实验",
            "注意记录实验过程中的异常情况"
        ]
        
    def _build_digital_twin_kg(
        self, 
        lit_results: Dict[str, Any], 
        exp_design: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建数字孪生知识图谱"""
        kg = {
            "nodes": [
                {"id": "root", "type": "research", "label": "研究项目", "status": "active"},
                {"id": "literature", "type": "phase", "label": "文献调研", "status": "completed"},
                {"id": "experiment", "type": "phase", "label": "实验设计", "status": "completed"},
                {"id": "execution", "type": "phase", "label": "实验执行", "status": "pending"},
                {"id": "writing", "type": "phase", "label": "论文撰写", "status": "pending"}
            ],
            "edges": [
                {"from": "root", "to": "literature", "relation": "contains"},
                {"from": "root", "to": "experiment", "relation": "contains"},
                {"from": "root", "to": "execution", "relation": "contains"},
                {"from": "root", "to": "writing", "relation": "contains"},
                {"from": "literature", "to": "experiment", "relation": "feeds_into"}
            ],
            "tasks": {},
            "metrics": {"completion_rate": 0.4, "on_time_rate": 0.95, "risk_level": "low"}
        }
        
        # 添加文献节点
        for paper in lit_results.get("papers", [])[:5]:
            kg["nodes"].append({
                "id": paper["paper_id"],
                "type": "literature",
                "label": paper["title"][:40],
                "properties": {"relevance": paper.get("relevance_score", 0.8)}
            })
            kg["edges"].append({
                "from": "literature",
                "to": paper["paper_id"],
                "relation": "includes"
            })
            
        # 添加实验节点
        for obj in exp_design.get("final_design", {}).get("objectives", []):
            kg["nodes"].append({
                "id": f"obj_{obj[:15]}",
                "type": "objective",
                "label": obj[:40]
            })
            
        return kg
        
    def _generate_timeline(self, exp_design: Dict[str, Any]) -> Dict[str, Any]:
        """生成任务时间线"""
        tasks = []
        start = datetime.now()
        
        for step in exp_design.get("final_design", {}).get("procedure", []):
            task = {
                "task_id": f"task_{step['step']}",
                "name": step["action"],
                "status": TaskStatus.PENDING,
                "progress": 0.0,
                "planned_duration": step.get("duration", "1天"),
                "actual_duration": None,
                "dependencies": [f"task_{step['step']-1}"] if step["step"] > 1 else [],
                "start_time": (start + timedelta(days=sum(
                    int(t.get("planned_duration", "1天").replace("天",""))
                    for t in tasks[-3:]
                ))).isoformat() if tasks else start.isoformat()
            }
            tasks.append(task)
            
        return {
            "tasks": {t["task_id"]: t for t in tasks},
            "gantt": tasks,
            "total_estimated_days": sum(
                int(t.get("planned_duration", "1天").replace("天",""))
                for t in tasks
            )
        }
        
    def _define_milestones(self, exp_design: Dict[str, Any]) -> List[Dict[str, Any]]:
        """定义里程碑"""
        return [
            {
                "id": "milestone_1",
                "name": "文献综述完成",
                "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
                "status": "completed"
            },
            {
                "id": "milestone_2",
                "name": "实验方案确定",
                "deadline": (datetime.now() + timedelta(days=14)).isoformat(),
                "status": "completed"
            },
            {
                "id": "milestone_3",
                "name": "初步实验结果",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
                "status": "pending"
            },
            {
                "id": "milestone_4",
                "name": "论文初稿",
                "deadline": (datetime.now() + timedelta(days=60)).isoformat(),
                "status": "pending"
            }
        ]

# ============================================================
# Orchestrator - Agent调度引擎
# ============================================================
class Orchestrator:
    """
    Agent调度引擎：基于消息队列和事件驱动
    """
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.event_history: List[Dict[str, Any]] = []
        self.orchestrator_state = AgentStateMachine("orchestrator", AgentType.ORCHESTRATOR)
        
    async def register_agent(self, agent_id: str, agent: Any):
        self.agents[agent_id] = agent
        await self._emit_event("agent_registered", {"agent_id": agent_id, "type": type(agent).__name__})
        
    async def dispatch_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """调度任务到对应Agent"""
        await self._emit_event("task_dispatched", {"type": task_type, "payload": payload})
        
        if task_type == "literature_search":
            agent = self.agents.get("literature_agent")
            result = await agent.search_literature(**payload)
        elif task_type == "literature_validate":
            validator = self.agents.get("validator_agent")
            if not validator:
                raise ValueError("validator_agent not registered")
            result = await validator.validate(**payload)
        elif task_type == "literature_review":
            # 联合流程：检索 → 验证
            lit_agent = self.agents.get("literature_agent")
            validator = self.agents.get("validator_agent")
            if not lit_agent or not validator:
                raise ValueError("literature_agent or validator_agent not registered")
            search_result = await lit_agent.search_literature(**payload)
            papers = search_result.get("papers", [])
            if papers:
                validate_result = await validator.validate(
                    papers,
                    user_query=payload.get("query", ""),
                    top_k=payload.get("top_k", 5)
                )
                result = {"search": search_result, "validation": validate_result}
            else:
                result = search_result
        elif task_type == "experiment_design":
            agent = self.agents.get("experiment_agent")
            result = await agent.design_experiment(**payload)
        elif task_type == "progress_update":
            agent = self.agents.get("progress_agent")
            result = await agent.update_progress(**payload)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
        await self._emit_event("task_completed", {"type": task_type, "result_summary": str(result)[:100]})
        return result
        
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.event_history.append(event)
        
    async def get_agent_states(self) -> Dict[str, str]:
        result = {}
        for aid, agent in self.agents.items():
            try:
                result[aid] = agent.state_machine.state
            except (AttributeError, KeyError):
                result[aid] = "idle"
        return result

# ============================================================
# Global Orchestrator Instance
# ============================================================
orchestrator = Orchestrator()

# ============================================================
# API Routes
# ============================================================

@app.on_event("startup")
async def startup():
    """初始化所有Agent"""
    # Create agents
    lit_agent = LiteratureAgent("lit_001")
    exp_agent = ExperimentDesignAgent("exp_001")
    prg_agent = ProgressAgent("prg_001")

    # Create KG (shared across agents)
    kg = KnowledgeGraphManager()
    await kg.initialize()

    # Create validator agent (depends on KG)
    val_agent = ResearchValidatorAgent("val_001", kg=kg)

    # Register
    await orchestrator.register_agent("literature_agent", lit_agent)
    await orchestrator.register_agent("experiment_agent", exp_agent)
    await orchestrator.register_agent("progress_agent", prg_agent)
    await orchestrator.register_agent("validator_agent", val_agent)

    # Initialize
    await asyncio.gather(
        lit_agent.initialize() if hasattr(lit_agent, 'initialize') else asyncio.sleep(0),
        exp_agent.initialize() if hasattr(exp_agent, 'initialize') else asyncio.sleep(0),
        prg_agent.initialize() if hasattr(prg_agent, 'initialize') else asyncio.sleep(0),
        val_agent.initialize() if hasattr(val_agent, 'initialize') else asyncio.sleep(0),
    )
    agent_workers["literature_agent"] = {"status": "ready", "agent": lit_agent}
    agent_workers["experiment_agent"] = {"status": "ready", "agent": exp_agent}
    agent_workers["progress_agent"] = {"status": "ready", "agent": prg_agent}
    agent_workers["validator_agent"] = {"status": "ready", "agent": val_agent}
    
    print("[Startup] All agents initialized successfully")

# ---- Session Management ----

@app.post("/api/sessions", response_model=ResearchSession)
async def create_session(request: ResearchSessionCreate):
    """创建新的研究会话"""
    session = ResearchSession(
        user_profile=request.user_profile,
        research_topic=request.research_topic,
        goals=request.goals
    )
    sessions[session.session_id] = session
    return session

@app.get("/api/sessions")
async def list_sessions():
    """列出所有会话"""
    return {"sessions": [
        {
            "session_id": sid,
            "research_topic": s.research_topic,
            "status": s.status,
            "created_at": s.created_at.isoformat()
        }
        for sid, s in sessions.items()
    ]}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[session_id]

# ---- Literature Agent ----

@app.post("/api/literature/search")
async def search_literature(query: LiteratureQuery):
    """文献检索"""
    agent = agent_workers.get("literature_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Literature agent not ready")
        
    results = await agent.search_literature(
        query=query.query,
        mode=query.mode,
        max_results=query.max_results,
        filters=query.filters
    )
    return results

@app.post("/api/literature/review")
async def review_literature(query: LiteratureQuery):
    """
    文献检索 + 验证联合接口
    等价于 dispatch_task("literature_review", ...)
    返回检索结果 + 证据对齐 + 冲突检测 + 可信度评分 + 综合结论
    """
    lit_agent = agent_workers.get("literature_agent", {}).get("agent")
    val_agent = agent_workers.get("validator_agent", {}).get("agent")
    if not lit_agent or not val_agent:
        raise HTTPException(503, "Agent not ready")

    # Step 1: 检索
    search_result = await lit_agent.search_literature(
        query=query.query,
        mode=query.mode,
        max_results=query.max_results,
        filters=query.filters
    )
    papers = search_result.get("papers", [])

    if not papers:
        return {"search": search_result, "validation": None}

    # Step 2: 验证
    validate_result = await val_agent.validate(
        papers,
        user_query=query.query,
        top_k=query.max_results
    )

    return {"search": search_result, "validation": validate_result}


@app.get("/api/literature/agent/state")
async def get_literature_agent_state():
    """获取文献Agent状态"""
    agent = agent_workers.get("literature_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Agent not found")
    return {
        "state": agent.state_machine.state,
        "history": agent.state_machine.history[-10:]
    }

# ---- Experiment Design Agent ----

@app.post("/api/experiment/design")
async def design_experiment(request: ExperimentDesignRequest):
    """实验设计"""
    agent = agent_workers.get("experiment_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Experiment agent not ready")
        
    design = await agent.design_experiment(
        research_question=request.research_question,
        hypothesis=request.hypothesis,
        constraints=request.constraints,
        available_resources=request.available_resources,
        reflection_iterations=request.reflection_iterations
    )
    return design

@app.get("/api/experiment/agent/state")
async def get_experiment_agent_state():
    """获取实验设计Agent状态"""
    agent = agent_workers.get("experiment_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Agent not found")
    return {
        "state": agent.state_machine.state,
        "history": agent.state_machine.history[-10:]
    }

# ---- Progress Agent ----

@app.post("/api/progress/plan")
async def create_progress_plan(session_id: str):
    """创建研究计划"""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
        
    session = sessions[session_id]
    lit_agent = agent_workers.get("literature_agent", {}).get("agent")
    exp_agent = agent_workers.get("experiment_agent", {}).get("agent")
    prg_agent = agent_workers.get("progress_agent", {}).get("agent")
    
    if not all([lit_agent, exp_agent, prg_agent]):
        raise HTTPException(503, "Agents not ready")
    
    # 先做文献检索
    lit_results = await lit_agent.search_literature(
        query=session.research_topic,
        mode=LiteratureSearchMode.HYBRID,
        max_results=10
    )
    
    # 再做实验设计
    exp_design = await exp_agent.design_experiment(
        research_question=session.research_topic,
        hypothesis=None,
        reflection_iterations=3
    )
    
    # 创建进度计划
    plan = await prg_agent.create_research_plan(session_id, lit_results, exp_design)
    
    # 更新session状态
    session.status = TaskStatus.RUNNING
    session.literature_agent_state = {"last_search": lit_results}
    session.experiment_agent_state = {"last_design": exp_design}
    session.progress_agent_state = {"plan": plan}
    
    return plan

@app.post("/api/progress/update")
async def update_progress(update: ProgressUpdate):
    """更新任务进度"""
    agent = agent_workers.get("progress_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Progress agent not ready")
        
    result = await agent.update_progress(
        session_id=update.task_id.split("_")[0] if "_" in update.task_id else "default",
        task_id=update.task_id,
        update=update
    )
    return result

@app.get("/api/progress/knowledge-graph/{session_id}")
async def get_knowledge_graph(session_id: str):
    """获取知识图谱"""
    agent = agent_workers.get("progress_agent", {}).get("agent")
    if not agent:
        raise HTTPException(503, "Agent not ready")
    return agent.knowledge_graph

# ---- Orchestrator ----

@app.get("/api/orchestrator/states")
async def get_orchestrator_states():
    """获取所有Agent状态"""
    return await orchestrator.get_agent_states()

@app.get("/api/orchestrator/events")
async def get_event_history(limit: int = Query(20, le=100)):
    """获取事件历史"""
    return {"events": orchestrator.event_history[-limit:]}

# ---- WebSocket for real-time updates ----

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(ws: WebSocket, client_id: str):
    await ws.accept()
    
    # Subscribe to all agent updates
    for agent_info in agent_workers.values():
        agent = agent_info.get("agent")
        if hasattr(agent, "state_machine"):
            agent.state_machine.subscribers.append(ws)
    
    try:
        while True:
            data = await ws.receive_text()
            # Echo or process commands
            if data == "ping":
                await ws.send_text("pong")
            elif data.startswith("dispatch:"):
                # dispatch:task_type:payload_json
                parts = data.split(":", 2)
                if len(parts) == 3:
                    task_type = parts[1]
                    payload = json.loads(parts[2])
                    result = await orchestrator.dispatch_task(task_type, payload)
                    await ws.send_text(json.dumps({"type": "task_result", "data": result}))
    except WebSocketDisconnect:
        pass

# ---- Health Check ----

@app.get("/health")
async def health_check():
    agent_states = await orchestrator.get_agent_states()
    return {
        "status": "healthy",
        "agents": agent_states,
        "sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "service": "Multi-Agent Research Assistant",
        "version": "1.0.0",
        "port": 8021,
        "endpoints": {
            "sessions": "/api/sessions",
            "literature": "/api/literature/search",
            "experiment": "/api/experiment/design",
            "progress": "/api/progress/plan",
            "websocket": "/ws/{client_id}"
        }
    }

# ============================================================
# Main Entry
# ============================================================
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8021,
        reload=False,
        workers=1
    )
