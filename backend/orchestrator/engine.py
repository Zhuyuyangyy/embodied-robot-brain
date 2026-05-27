"""
Agent Orchestrator - Multi-Agent Coordination Engine
Event-driven message passing between agents
"""
import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from collections import defaultdict

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"
    HEARTBEAT = "heartbeat"

class AgentMessage:
    """Agent间传递的消息"""
    def __init__(
        self,
        msg_type: MessageType,
        sender: str,
        receiver: Optional[str],
        content: Dict[str, Any],
        reply_to: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.sender = sender
        self.receiver = receiver  # None means broadcast
        self.content = content
        self.reply_to = reply_to
        self.timestamp = datetime.now()
        self.priority = TaskPriority.NORMAL
        
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value
        }

class Orchestrator:
    """
    Agent调度引擎 - 事件驱动的多Agent协作
    
    核心功能:
    1. Agent注册与生命周期管理
    2. 任务分发与状态跟踪
    3. Agent间消息路由
    4. 事件总线广播
    5. 错误处理与重试
    """
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.agent_meta: Dict[str, Dict] = {}  # Agent元信息
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.message_bus: asyncio.Queue = asyncio.Queue()
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.task_registry: Dict[str, Dict] = {}
        self.event_history: List[Dict] = []
        self._max_history = 1000  # 防止内存无限增长
        self.subscribers: Dict[str, List[Any]] = defaultdict(list)
        
        # 统计
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "messages_sent": 0
        }
        
        # 启动消息处理循环
        self._running = False
        
    async def start(self):
        """启动调度引擎"""
        self._running = True
        asyncio.create_task(self._process_tasks())
        asyncio.create_task(self._process_messages())
        asyncio.create_task(self._heartbeat_monitor())
        
    async def stop(self):
        """停止调度引擎"""
        self._running = False
        
    # ---- Agent Management ----
    
    async def register_agent(
        self,
        agent_id: str,
        agent: Any,
        agent_type: str,
        capabilities: List[str] = None
    ):
        """注册Agent"""
        self.agents[agent_id] = agent
        self.agent_meta[agent_id] = {
            "type": agent_type,
            "capabilities": capabilities or [],
            "status": "idle",
            "registered_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        await self._emit_event("agent_registered", {
            "agent_id": agent_id,
            "type": agent_type,
            "capabilities": capabilities
        })
        
    async def deregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            await self._emit_event("agent_deregistered", {"agent_id": agent_id})
            
    async def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """获取Agent状态"""
        if agent_id not in self.agents:
            return None
            
        agent = self.agents[agent_id]
        meta = self.agent_meta[agent_id]
        
        status = {
            "agent_id": agent_id,
            "type": meta["type"],
            "status": meta["status"],
            "capabilities": meta["capabilities"],
            "last_active": meta["last_active"]
        }
        
        # 获取Agent特有状态
        if hasattr(agent, "state"):
            status["state"] = agent.state
        if hasattr(agent, "state_machine"):
            status["state"] = agent.state_machine.state
            
        return status
        
    async def list_agents(self) -> List[Dict]:
        """列出所有Agent"""
        return [await self.get_agent_status(aid) for aid in self.agents.keys()]
        
    # ---- Task Dispatch ----
    
    async def dispatch_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        target_agent: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        retry_count: int = 3
    ) -> str:
        """
        分发任务到指定Agent或自动路由
        """
        task_id = str(uuid.uuid4())
        
        # 自动路由到合适Agent
        if target_agent is None:
            target_agent = await self._route_task(task_type)
            
        if target_agent not in self.agents:
            raise ValueError(f"No agent available for task type: {task_type}")
            
        task = {
            "task_id": task_id,
            "type": task_type,
            "payload": payload,
            "target_agent": target_agent,
            "priority": priority,
            "retry_count": retry_count,
            "status": TaskStatus.QUEUED,
            "created_at": datetime.now().isoformat()
        }
        
        self.task_registry[task_id] = task
        self.stats["total_tasks"] += 1
        
        # 加入优先级队列：PriorityQueue按最小值排序，所以0=CRITICAL最早出队
        # 用(priority_val, time.time(), task)三元组，time.time()解决priority相等时的字典比较崩溃问题
        import time as time_module
        priority_val = 0 if priority == TaskPriority.CRITICAL else 1 if priority == TaskPriority.HIGH else 2
        await self.task_queue.put((priority_val, time_module.time(), task))
        
        await self._emit_event("task_dispatched", {
            "task_id": task_id,
            "type": task_type,
            "target": target_agent
        })
        
        return task_id
        
    async def _route_task(self, task_type: str) -> Optional[str]:
        """根据任务类型路由到合适Agent"""
        # 简单路由规则
        routing = {
            "literature_search":    "literature_agent",
            "literature_validate":  "validator_agent",
            "literature_review":    "literature_agent",   # literature → validate 联合
            "experiment_design":    "experiment_agent",
            "progress_update":      "progress_agent",
            "kg_query":            "literature_agent"
        }
        
        agent_id = routing.get(task_type)
        
        if agent_id and agent_id in self.agents:
            return agent_id
            
        # 尝试找有相关能力的Agent
        for aid, meta in self.agent_meta.items():
            if task_type.replace("_", " ") in " ".join(meta.get("capabilities", [])).lower():
                return aid
                
        return None
        
    async def _process_tasks(self):
        """任务处理循环"""
        while self._running:
            try:
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await self._emit_event("orchestrator_error", {"error": str(e)})
                
    async def _execute_task(self, task: Dict):
        """执行单个任务"""
        task_id = task["task_id"]
        task["status"] = TaskStatus.RUNNING
        task["started_at"] = datetime.now().isoformat()
        
        # 更新Agent状态
        agent_id = task["target_agent"]
        if agent_id in self.agent_meta:
            self.agent_meta[agent_id]["status"] = "busy"
            self.agent_meta[agent_id]["last_active"] = datetime.now().isoformat()
            
        try:
            agent = self.agents[agent_id]
            
            # 根据任务类型调用Agent方法
            if task["type"] == "literature_search":
                result = await agent.search_literature(**task["payload"])
            elif task["type"] == "literature_validate":
                result = await agent.validate(**task["payload"])
            elif task["type"] == "literature_review":
                # literature_review = 检索 + 验证 联合流程
                # Step 1: 检索
                search_result = await agent.search_literature(**task["payload"])
                papers = search_result.get("papers", [])
                # Step 2: 调度验证
                validator = self.agents.get("validator_agent")
                if validator and papers:
                    validate_result = await validator.validate(
                        papers,
                        user_query=task["payload"].get("query", ""),
                        top_k=task["payload"].get("top_k", 5)
                    )
                    result = {
                        "search": search_result,
                        "validation": validate_result
                    }
                else:
                    result = search_result
            elif task["type"] == "experiment_design":
                result = await agent.design_experiment(**task["payload"])
            elif task["type"] == "progress_update":
                result = await agent.update_progress(**task["payload"])
            else:
                raise ValueError(f"Unknown task type: {task['type']}")
                
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
            task["completed_at"] = datetime.now().isoformat()
            self.stats["completed_tasks"] += 1
            
            await self._emit_event("task_completed", {
                "task_id": task_id,
                "result_summary": str(result)[:100]
            })
            
        except Exception as e:
            task["status"] = TaskStatus.FAILED
            task["error"] = str(e)
            task["failed_at"] = datetime.now().isoformat()
            self.stats["failed_tasks"] += 1
            
            # 重试逻辑：递减retry_count后再入队，不是放回原任务（会重复执行）
            if task["retry_count"] > 0:
                task_copy = dict(task)  # 深拷贝，避免修改原任务注册表
                task_copy["retry_count"] -= 1
                task_copy["status"] = TaskStatus.QUEUED
                task_copy["last_retry_at"] = datetime.now().isoformat()
                # 重试任务排在同优先级末尾（用时间戳确保在dispatch时刻之后）
                import time as time_module
                priority_val = 0 if task_copy["priority"] == TaskPriority.CRITICAL else 1 if task_copy["priority"] == TaskPriority.HIGH else 2
                await self.task_queue.put((priority_val, time_module.time() + 999999, task_copy))
            else:
                await self._emit_event("task_failed", {
                    "task_id": task_id,
                    "error": str(e)
                })
        finally:
            if agent_id in self.agent_meta:
                self.agent_meta[agent_id]["status"] = "idle"
                
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.task_registry.get(task_id)
        
    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict]:
        """列出任务"""
        tasks = list(self.task_registry.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks
        
    # ---- Message Passing ----
    
    async def send_message(
        self,
        sender: str,
        receiver: str,
        content: Dict[str, Any],
        msg_type: MessageType = MessageType.MESSAGE
    ) -> str:
        """发送消息"""
        msg = AgentMessage(
            msg_type=msg_type,
            sender=sender,
            receiver=receiver,
            content=content
        )
        
        await self.message_bus.put(msg)
        self.stats["messages_sent"] += 1
        
        # 如果是点对点消息，直接投递
        if receiver in self.agents:
            asyncio.create_task(self._deliver_message(msg, receiver))
            
        return msg.id
        
    async def broadcast(
        self,
        sender: str,
        content: Dict[str, Any],
        msg_type: MessageType = MessageType.EVENT
    ):
        """广播消息"""
        for agent_id in self.agents:
            if agent_id != sender:
                await self.send_message(sender, agent_id, content, msg_type)
                
    async def _process_messages(self):
        """消息处理循环"""
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.message_bus.get(),
                    timeout=0.5
                )
                
                if msg.receiver:
                    await self._deliver_message(msg, msg.receiver)
                else:
                    await self._broadcast_message(msg)
                    
            except asyncio.TimeoutError:
                continue
                
    async def _deliver_message(self, msg: AgentMessage, receiver: str):
        """投递消息到Agent"""
        if receiver in self.agents:
            agent = self.agents[receiver]
            
            # 调用Agent的消息处理方法
            if hasattr(agent, "handle_message"):
                await agent.handle_message(msg)
                
            await self._emit_event("message_delivered", {
                "msg_id": msg.id,
                "from": msg.sender,
                "to": receiver
            })
            
    async def _broadcast_message(self, msg: AgentMessage):
        """广播消息"""
        for agent_id in self.agents:
            if agent_id != msg.sender:
                await self._deliver_message(msg, agent_id)
                
    # ---- Event System ----
    
    def on_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event_type].append(handler)
        
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发送事件"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.event_history.append(event)
        # 防止内存无限增长：保留最近N条
        if len(self.event_history) > self._max_history:
            self.event_history = self.event_history[-self._max_history:]
        
        # 调用处理器
        for handler in self.event_handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass
                
        # 通知订阅者
        for subscriber in self.subscribers.get(event_type, []):
            try:
                await subscriber.send(json.dumps(event))
            except:
                pass
                
    async def subscribe(self, client: Any, events: List[str]):
        """订阅事件"""
        for event in events:
            self.subscribers[event].append(client)
            
    # ---- Heartbeat ----
    
    async def _heartbeat_monitor(self):
        """心跳监控"""
        while self._running:
            await asyncio.sleep(10)
            
            for agent_id, meta in self.agent_meta.items():
                last_active = datetime.fromisoformat(meta["last_active"])
                # 用.total_seconds()获取真实时间差秒数，不要用timedelta的seconds属性（它只取分量<86400）
                elapsed = (datetime.now() - last_active).total_seconds()
                if elapsed > 60:
                    # Agent可能失联
                    await self._emit_event("agent_stale", {
                        "agent_id": agent_id,
                        "last_active": meta["last_active"]
                    })
                    
    # ---- Stats ----
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "registered_agents": len(self.agents),
            "queued_tasks": self.task_queue.qsize(),
            "event_history_size": len(self.event_history)
        }
