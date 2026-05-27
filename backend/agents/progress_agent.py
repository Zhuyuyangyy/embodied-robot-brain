"""
Progress Agent - 科研进度智能追踪系统
====================================

支持功能：
- 研究阶段状态机管理（LITERATURE → EXPERIMENT → EXECUTION → TRACKING）
- 多维度进度仪表盘生成
- 里程碑管理与延迟预警
- 反思式实验设计回路（基于中间结果调整计划）

Author: embodied-robot-brain Team
"""

import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TrackType(str, Enum):
    LITERATURE = "literature"
    EXPERIMENT_DESIGN = "experiment_design"
    EXPERIMENT_EXECUTION = "experiment_execution"
    PAPER_WRITING = "paper_writing"
    REVIEW = "review"


@dataclass
class Milestone:
    """里程碑"""
    milestone_id: str
    title: str
    description: str
    due_date: datetime
    status: TaskStatus = TaskStatus.PENDING
    subtasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    completed_at: Optional[datetime] = None

    def days_until_due(self) -> int:
        return (self.due_date - datetime.now()).days

    def is_overdue(self) -> bool:
        return self.days_until_due() < 0 and self.status != TaskStatus.COMPLETED

    def to_dict(self) -> Dict:
        return {
            "milestone_id": self.milestone_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat(),
            "status": self.status.value,
            "subtasks": self.subtasks,
            "dependencies": self.dependencies,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "days_until_due": self.days_until_due(),
            "is_overdue": self.is_overdue(),
        }


@dataclass
class Task:
    """研究任务"""
    task_id: str
    title: str
    description: str
    track_type: TrackType
    status: TaskStatus = TaskStatus.PENDING
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    assigned_stage: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    blocked_by: List[str] = field(default_factory=list)
    progress_pct: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "track_type": self.track_type.value,
            "status": self.status.value,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "assigned_stage": self.assigned_stage,
            "progress_pct": self.progress_pct,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "blocked_by": self.blocked_by,
        }


@dataclass
class ResearchDashboard:
    """研究会话仪表盘"""
    session_id: str
    overall_progress: float  # 0.0 - 1.0
    completed_tasks: int
    total_tasks: int
    overdue_milestones: int
    upcoming_deadlines: List[Dict]
    stage_summary: Dict[str, Dict]
    recent_activity: List[Dict]

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "overall_progress": self.overall_progress,
            "completed_tasks": self.completed_tasks,
            "total_tasks": self.total_tasks,
            "overdue_milestones": self.overdue_milestones,
            "upcoming_deadlines": self.upcoming_deadlines,
            "stage_summary": self.stage_summary,
            "recent_activity": self.recent_activity,
        }


class ProgressAgent:
    """
    进度管理Agent

    核心职责：
    1. 创建和管理研究计划（create_plan）
    2. 追踪任务状态并更新进度（update_task）
    3. 生成多维度仪表盘（get_dashboard）
    4. 检测阻塞和延迟并触发预警（check_blockers）
    5. 基于中间结果反思并调整计划（reflect_and_adjust）
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._milestones: Dict[str, Milestone] = {}
        self._sessions: Dict[str, Dict] = {}
        self._activity_log: List[Dict] = []

    async def create_plan(
        self,
        session_id: str,
        research_topic: str,
        goals: List[str],
    ) -> Dict:
        """
        根据研究主题创建完整计划

        Args:
            session_id: 会话ID
            research_topic: 研究主题
            goals: 研究目标列表

        Returns:
            包含里程碑和任务的完整计划
        """
        self._sessions[session_id] = {
            "topic": research_topic,
            "goals": goals,
            "created_at": datetime.now().isoformat(),
        }

        tasks = []
        milestones = []

        # Stage 1: 文献调研里程碑
        lit_milestone = Milestone(
            milestone_id=f"{session_id}_lit_1",
            title="文献调研完成",
            description=f"完成 {research_topic} 相关文献的系统性调研",
            due_date=datetime.now() + timedelta(days=7),
            subtasks=[
                "关键词检索与筛选",
                "全文阅读与证据提取",
                "冲突检测与分类",
                "文献综述撰写",
            ],
        )
        milestones.append(lit_milestone)
        self._milestones[lit_milestone.milestone_id] = lit_milestone

        # 文献调研任务
        lit_tasks = [
            Task(
                task_id=f"{session_id}_lit_search",
                title="文献检索",
                description="使用关键词和知识图谱检索相关论文",
                track_type=TrackType.LITERATURE,
                estimated_hours=4.0,
                assigned_stage="literature",
            ),
            Task(
                task_id=f"{session_id}_lit_extract",
                title="证据提取与对齐",
                description="从论文中提取方法、指标、数据集信息并对齐",
                track_type=TrackType.LITERATURE,
                estimated_hours=6.0,
                assigned_stage="literature",
            ),
            Task(
                task_id=f"{session_id}_lit_conflict",
                title="冲突检测",
                description="执行三层冲突检测，识别Type-I/II/III冲突",
                track_type=TrackType.LITERATURE,
                estimated_hours=3.0,
                assigned_stage="literature",
            ),
        ]
        for t in lit_tasks:
            self._tasks[t.task_id] = t
            tasks.append(t.to_dict())

        # Stage 2: 实验设计里程碑
        exp_milestone = Milestone(
            milestone_id=f"{session_id}_exp_1",
            title="实验方案设计完成",
            description="生成可复现的实验方案（含基线、对比方法、评测指标）",
            due_date=datetime.now() + timedelta(days=14),
            dependencies=[lit_milestone.milestone_id],
            subtasks=[
                "确定实验设置与超参数",
                "设计对比基线",
                "定义评测指标与数据集",
                "规划计算资源",
            ],
        )
        milestones.append(exp_milestone)
        self._milestones[exp_milestone.milestone_id] = exp_milestone

        exp_tasks = [
            Task(
                task_id=f"{session_id}_exp_design",
                title="实验方案设计",
                description="设计包含基线、对比方法、消融实验的完整方案",
                track_type=TrackType.EXPERIMENT_DESIGN,
                estimated_hours=5.0,
                assigned_stage="experiment",
            ),
            Task(
                task_id=f"{session_id}_exp_resource",
                title="资源规划",
                description="确定数据集、计算资源、评测流程",
                track_type=TrackType.EXPERIMENT_DESIGN,
                estimated_hours=2.0,
                assigned_stage="experiment",
            ),
        ]
        for t in exp_tasks:
            self._tasks[t.task_id] = t
            tasks.append(t.to_dict())

        # Stage 3: 实验执行里程碑
        exec_milestone = Milestone(
            milestone_id=f"{session_id}_exec_1",
            title="实验执行完成",
            description="运行全部实验并收集结果",
            due_date=datetime.now() + timedelta(days=30),
            dependencies=[exp_milestone.milestone_id],
            subtasks=[
                "基线方法复现",
                "提出的方法训练与评测",
                "消融实验",
                "统计显著性检验",
            ],
        )
        milestones.append(exec_milestone)
        self._milestones[exec_milestone.milestone_id] = exec_milestone

        exec_tasks = [
            Task(
                task_id=f"{session_id}_exec_baseline",
                title="基线复现",
                description="复现论文中报告的基线方法结果",
                track_type=TrackType.EXPERIMENT_EXECUTION,
                estimated_hours=8.0,
                assigned_stage="execution",
            ),
            Task(
                task_id=f"{session_id}_exec_main",
                title="主实验运行",
                description="运行提出的方法并收集完整指标",
                track_type=TrackType.EXPERIMENT_EXECUTION,
                estimated_hours=12.0,
                assigned_stage="execution",
            ),
            Task(
                task_id=f"{session_id}_exec_ablation",
                title="消融实验",
                description="运行组件级消融分析",
                track_type=TrackType.EXPERIMENT_EXECUTION,
                estimated_hours=6.0,
                assigned_stage="execution",
            ),
        ]
        for t in exec_tasks:
            self._tasks[t.task_id] = t
            tasks.append(t.to_dict())

        # Stage 4: 论文撰写
        paper_milestone = Milestone(
            milestone_id=f"{session_id}_paper_1",
            title="论文初稿完成",
            description="完成论文初稿，包含Related Work、Method、Experiment、Discussion",
            due_date=datetime.now() + timedelta(days=45),
            dependencies=[exec_milestone.milestone_id],
            subtasks=[
                "Introduction撰写",
                "Related Work整理",
                "Methodology描述",
                "实验结果分析",
                "Discussion与Conclusion",
            ],
        )
        milestones.append(paper_milestone)
        self._milestones[paper_milestone.milestone_id] = paper_milestone

        paper_tasks = [
            Task(
                task_id=f"{session_id}_paper_draft",
                title="论文初稿",
                description="撰写完整初稿并确保逻辑连贯",
                track_type=TrackType.PAPER_WRITING,
                estimated_hours=20.0,
                assigned_stage="writing",
            ),
        ]
        for t in paper_tasks:
            self._tasks[t.task_id] = t
            tasks.append(t.to_dict())

        self._log_activity(session_id, "plan_created", {"task_count": len(tasks), "milestone_count": len(milestones)})

        return {
            "session_id": session_id,
            "research_topic": research_topic,
            "goals": goals,
            "tasks": tasks,
            "milestones": [m.to_dict() for m in milestones],
            "estimated_total_hours": sum(t.estimated_hours for t in self._tasks.values()
                                        if session_id in t.task_id),
        }

    async def get_dashboard(self, session_id: str) -> ResearchDashboard:
        """
        生成当前研究会话的多维度仪表盘

        Returns:
            ResearchDashboard，包含整体进度、阻塞检测、即将到期里程碑
        """
        session_tasks = [t for tid, t in self._tasks.items() if session_id in tid]
        session_milestones = [m for mid, m in self._milestones.items() if session_id in mid]

        completed = [t for t in session_tasks if t.status == TaskStatus.COMPLETED]
        overall_progress = len(completed) / len(session_tasks) if session_tasks else 0.0

        overdue = [m for m in session_milestones if m.is_overdue()]
        upcoming = sorted(
            [m for m in session_milestones if not m.is_overdue() and m.status != TaskStatus.COMPLETED],
            key=lambda m: m.due_date
        )[:5]

        # 按阶段分组
        stage_summary = {}
        for track in TrackType:
            track_tasks = [t for t in session_tasks if t.track_type == track]
            if track_tasks:
                completed_in_track = [t for t in track_tasks if t.status == TaskStatus.COMPLETED]
                stage_summary[track.value] = {
                    "total": len(track_tasks),
                    "completed": len(completed_in_track),
                    "progress": len(completed_in_track) / len(track_tasks) if track_tasks else 0.0,
                }

        return ResearchDashboard(
            session_id=session_id,
            overall_progress=overall_progress,
            completed_tasks=len(completed),
            total_tasks=len(session_tasks),
            overdue_milestones=len(overdue),
            upcoming_deadlines=[m.to_dict() for m in upcoming],
            stage_summary=stage_summary,
            recent_activity=self._activity_log[-10:] if self._activity_log else [],
        )

    async def update_task(
        self,
        session_id: str,
        task_id: str,
        status: TaskStatus,
        progress_pct: Optional[float] = None,
        notes: str = "",
    ) -> Dict:
        """更新任务状态"""
        if task_id not in self._tasks:
            return {"error": f"Task {task_id} not found"}

        task = self._tasks[task_id]
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        if progress_pct is not None:
            task.progress_pct = progress_pct
        if status == TaskStatus.COMPLETED:
            task.progress_pct = 100.0
            task.completed_at = datetime.now()

        self._log_activity(session_id, "task_updated", {
            "task_id": task_id,
            "old_status": old_status.value,
            "new_status": status.value,
            "notes": notes,
        })

        # 检查里程碑是否完成
        await self._check_milestone_completion(session_id)

        return task.to_dict()

    async def check_blockers(self, session_id: str) -> List[Dict]:
        """检测阻塞任务和延迟预警"""
        blockers = []
        session_tasks = [t for tid, t in self._tasks.items() if session_id in tid]

        for task in session_tasks:
            if task.status == TaskStatus.BLOCKED:
                blockers.append({
                    "task_id": task.task_id,
                    "title": task.title,
                    "blocked_by": task.blocked_by,
                    "severity": "high",
                })
            elif task.status == TaskStatus.IN_PROGRESS:
                # 检查实际/预估时间比
                if task.actual_hours > task.estimated_hours * 1.5:
                    blockers.append({
                        "task_id": task.task_id,
                        "title": task.title,
                        "actual_hours": task.actual_hours,
                        "estimated_hours": task.estimated_hours,
                        "overrun_pct": (task.actual_hours / task.estimated_hours - 1) * 100,
                        "severity": "medium",
                    })

        return blockers

    async def reflect_and_adjust(
        self,
        session_id: str,
        intermediate_result: Dict,
    ) -> Dict:
        """
        基于中间结果的反思式调整

        Args:
            session_id: 会话ID
            intermediate_result: 实验中间结果，包含accuracy/指标值/观察

        Returns:
            调整后的计划变更说明
        """
        adjustments = []
        warnings = []

        # 检查实验结果是否低于预期
        accuracy = intermediate_result.get("accuracy")
        if accuracy is not None:
            if accuracy < 0.70:
                warnings.append(f"准确率偏低 ({accuracy:.1%})，建议检查数据质量或增加训练轮次")
                adjustments.append("增加数据增强策略")
            elif accuracy > 0.90:
                warnings.append(f"准确率偏高 ({accuracy:.1%})，需验证是否存在数据泄露")

        # 检查是否需要补充实验
        baseline_gap = intermediate_result.get("baseline_gap")
        if baseline_gap is not None:
            if baseline_gap < 0.01:
                warnings.append("与基线差距过小，改进空间有限，需重新审视方法设计")
                adjustments.append("考虑引入新组件或调整架构")

        self._log_activity(session_id, "reflection", {
            "intermediate_result": intermediate_result,
            "adjustments": adjustments,
            "warnings": warnings,
        })

        return {
            "session_id": session_id,
            "warnings": warnings,
            "suggested_adjustments": adjustments,
            "continue_as_planned": len(warnings) == 0,
        }

    async def _check_milestone_completion(self, session_id: str):
        """检查里程碑完成状态"""
        session_milestones = [m for mid, m in self._milestones.items() if session_id in mid]
        for milestone in session_milestones:
            if milestone.status == TaskStatus.COMPLETED:
                continue
            deps_completed = all(
                self._tasks.get(dep_id, Milestone(dep_id, "", "", datetime.now())).status == TaskStatus.COMPLETED
                for dep_id in milestone.dependencies
                if dep_id in self._tasks
            )
            if deps_completed:
                # 检查所有subtask是否完成
                related_tasks = [
                    t for tid, t in self._tasks.items()
                    if session_id in tid and
                    any(st.lower() in t.title.lower() or t.title.lower() in st.lower()
                        for st in milestone.subtasks)
                ]
                if related_tasks and all(t.status == TaskStatus.COMPLETED for t in related_tasks):
                    milestone.status = TaskStatus.COMPLETED
                    milestone.completed_at = datetime.now()

    def _log_activity(self, session_id: str, event: str, data: Dict):
        """记录活动日志"""
        self._activity_log.append({
            "session_id": session_id,
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
