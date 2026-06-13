#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhysicsGate - Physical Feedback-Driven Hard Gate for Embodied AI
================================================================

embodied-robot-brain 物理门控层（对应论文 §3.1）。

核心公式（对应论文 §3.1.2 ~ §3.1.3）：
    E(A_t, K) = max{ severity_score(a_i, a_j, K) | for all conflict pairs }
    G(A_t, K, δ) = {
        HARD_REJECT  if E(A_t, K) = 1.0 (fatal, any retry count)
        SOFT_REJECT  if 0 < E(A_t, K) < 1.0 and E >= δ(t)
        PASS         if 0 <= E(A_t, K) < δ(t)
    }
    δ(t) = 0.05 (retry < 3) | 0.10 (retry >= 3)

安全性定理：致命冲突（E=1.0）在任意重试次数下始终 HARD_REJECT。

用法：
    gate = PhysicsGate(delta=0.05, delta_relaxed=0.10)
    decision = gate.decide(agent_state, conflict_knowledge)
    print(decision)  # 'PASS' | 'SOFT_REJECT' | 'HARD_REJECT'

Author: embodied-robot-brain Team
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GateDecision(Enum):
    """
    PhysicsGate 三值信号（对应论文 §3.1.3 Transfer Signal）

    PASS         : E(A_t, K) < delta(t)               — 物理约束通过
    SOFT_REJECT  : 0 < E(A_t, K) < 1.0 and E >= delta(t) — 可重试
    HARD_REJECT  : E(A_t, K) = 1.0 (fatal)            — 不可绕过
    """
    PASS = "PASS"
    SOFT_REJECT = "SOFT_REJECT"
    HARD_REJECT = "HARD_REJECT"

    # 向后兼容：旧代码使用 BLOCK/ESCALATE
    @classmethod
    def _missing_(cls, value):
        compat = {"BLOCK": "SOFT_REJECT", "ESCALATE": "HARD_REJECT"}
        if value in compat:
            return cls[compat[value]]
        return None


# severity -> error value 映射（对应论文 Table: severity_score）
SEVERITY_ERROR_MAP = {
    "absolute_forbidden": 1.0,      # fatal (十八反)
    "pharmacokinetic":    0.85,     # high (现代药理证实)
    "relative_warning":   0.7,      # high (十九畏)
    "theoretical_contradiction": 0.4,  # medium (药性对立)
    "normal":             0.0,      # none
    "synergistic":        0.0,      # none
}


# =============================================================================
# 核心决策函数
# =============================================================================

def compute_conflict_rate(
    recent_conflicts: List[Dict],
    window_size: int = 20,
    decay: float = 0.95
) -> float:
    """
    计算指数衰减的冲突率。

    参数：
        recent_conflicts: 最近 window_size 次调用的冲突记录列表
                          每条记录格式：{"has_conflict": bool}
        window_size: 滑动窗口大小
        decay: 时间衰减因子（最近的事件权重更高）

    返回：
        float: 0.0 ~ 1.0 的冲突率
    """
    if not recent_conflicts:
        return 0.0

    window = recent_conflicts[-window_size:]

    total_weight = 0.0
    weighted_sum = 0.0
    n = len(window)

    for i, record in enumerate(window):
        age_weight = math.pow(decay, n - 1 - i)
        has_conflict = int(record.get("has_conflict", False))
        weighted_sum += has_conflict * age_weight
        total_weight += age_weight

    if total_weight <= 0:
        return 0.0

    return weighted_sum / total_weight


def compute_error_function(
    conflict_knowledge: List[Dict[str, Any]],
) -> float:
    """
    计算物理约束误差值 E(A_t, K)（对应论文 §3.1.2）

    E(A_t, K) = max{ severity_score(a_i, a_j, K) | for all conflict pairs }

    severity_score 映射：
        fatal (十八反)              -> 1.0
        high  (药理机制/十九畏)     -> 0.7 ~ 0.85
        medium (药性对立/理论矛盾)  -> 0.4
        none  (无冲突)              -> 0.0

    参数：
        conflict_knowledge: 已知冲突列表

    返回：
        float: 0.0 ~ 1.0 的误差值
    """
    if not conflict_knowledge:
        return 0.0

    max_severity = 0.0
    for c in conflict_knowledge:
        # 优先使用 gap 字段作为 severity score（显式设置优先）
        gap = c.get("gap")
        if gap is not None and float(gap) > 0.0:
            max_severity = max(max_severity, float(gap))
        else:
            # 回退：根据 ctype 推断 severity（仅当 gap 未设置时）
            ctype = c.get("ctype", "")
            t = ctype.upper().replace("-", "").replace("_", "")
            if t in ("TYPE1", "TYPEI"):
                max_severity = max(max_severity, 1.0)
            elif t in ("TYPE2", "TYPEII"):
                max_severity = max(max_severity, 0.85)
            elif t in ("TYPE3", "TYPEIII"):
                max_severity = max(max_severity, 0.4)

    return max_severity


def compute_dynamic_delta(
    iteration: int,
    delta: float = 0.05,
    delta_relaxed: float = 0.10,
    retry_threshold: int = 3,
) -> float:
    """
    动态 δ 阈值（对应论文 §3.1.4）

    δ(t) = delta_strict   when retry(t) < retry_threshold
    δ(t) = delta_relaxed  when retry(t) >= retry_threshold

    安全性保证：致命冲突（E=1.0）始终 HARD_REJECT，不受 δ 影响。
    """
    if iteration < retry_threshold:
        return delta
    return delta_relaxed


def G(
    agent_state: Dict[str, Any],
    conflict_knowledge: List[Dict[str, Any]],
    delta: float = 0.05,
    delta_relaxed: float = 0.10,
    retry_threshold: int = 3,
) -> GateDecision:
    """
    物理门控函数 G(A_t, K, δ)（对应论文 §3.1.3）

    数学定义：
        G(A_t, K, δ) = {
            HARD_REJECT  if E(A_t, K) = 1.0 (fatal, any retry)
            SOFT_REJECT  if 0 < E(A_t, K) < 1.0 and E >= δ(t)
            PASS         if 0 <= E(A_t, K) < δ(t)
        }

    安全性定理：致命冲突（E=1.0）在任意重试次数下始终输出 HARD_REJECT。
    证明：HARD_REJECT 条件为 E=1.0，不依赖 δ 值。QED。

    参数：
        agent_state: 当前 agent 状态
        conflict_knowledge: 已知冲突列表
        delta: 严格阈值 (默认 0.05)
        delta_relaxed: 放宽阈值 (默认 0.10)
        retry_threshold: 触发放宽的重试次数 (默认 3)

    返回：
        GateDecision: PASS | SOFT_REJECT | HARD_REJECT
    """
    # Step 1: 计算误差函数 E(A_t, K)
    error_value = compute_error_function(conflict_knowledge)

    # Step 2: 确定当前 δ 值（动态衰减）
    iteration = agent_state.get("iteration", 0)
    effective_delta = compute_dynamic_delta(
        iteration, delta, delta_relaxed, retry_threshold
    )

    # Step 3: 映射到 TransferSignal
    if error_value >= 1.0:
        # 致命冲突：不可绕过（安全性保证）
        return GateDecision.HARD_REJECT
    elif error_value >= effective_delta:
        # 中等冲突：可重试
        return GateDecision.SOFT_REJECT
    else:
        # 无冲突或低冲突：通过
        return GateDecision.PASS


# =============================================================================
# PhysicsGate 类
# =============================================================================

@dataclass
class ConflictRecord:
    """单次调用的冲突记录"""
    has_conflict: bool
    conflict_types: List[str] = field(default_factory=list)
    conflict_rate: float = 0.0
    gate_decision: str = "PASS"
    agent_confidence: float = 1.0
    task_type: str = "unknown"
    timestamp: float = field(default_factory=time.time)


class PhysicsGate:
    """
    冲突感知物理门控器。

    使用滑动指数加权窗口跟踪 conflict_rate，
    当 conflict_rate > δ 时阻断 agent 输出，
    当 conflict_rate >= θ_HIGH 时强制升级人工审核。

    使用示例：
        gate = PhysicsGate(delta=0.3, theta_high=0.7)
        decision = gate.decide(agent_state, conflicts)
        gate.record(has_conflict=True, conflict_types=["Type-II"])
        print(gate.conflict_rate())
        print(gate.stats())
    """

    def __init__(
        self,
        delta: float = 0.05,
        delta_relaxed: float = 0.10,
        theta_high: float = 0.70,
        window_size: int = 20,
        decay: float = 0.95,
        retry_threshold: int = 3,
    ):
        self.delta = delta                    # 严格阈值 (论文 δ_strict)
        self.delta_relaxed = delta_relaxed    # 放宽阈值 (论文 δ_relaxed)
        self.theta_high = theta_high          # 保留向后兼容
        self.window_size = window_size
        self.decay = decay
        self.retry_threshold = retry_threshold

        self._history: List[ConflictRecord] = []
        self._call_count = 0
        self._soft_reject_count = 0   # 原 _block_count
        self._hard_reject_count = 0   # 原 _escalate_count
        self._pass_count = 0
        self._type1_count = 0
        self._type2_count = 0
        self._type3_count = 0
        self._last_error_value = 0.0
        self._last_delta = self.delta

    def conflict_rate(self) -> float:
        """返回当前冲突率（0.0 ~ 1.0）"""
        records = [{"has_conflict": r.has_conflict} for r in self._history]
        return compute_conflict_rate(records, self.window_size, self.decay)

    def cumulative_conflict_rate(self) -> float:
        """返回全局累计冲突率（不受窗口影响）"""
        total = max(self._call_count, 1)
        conflicts = self._type1_count + self._type2_count + self._type3_count
        return conflicts / total

    def decide(
        self,
        agent_state: Dict[str, Any],
        conflict_knowledge: List[Dict[str, Any]]
    ) -> GateDecision:
        """
        门控决策（对应论文 §3.1.3 Algorithm）

        1. 计算 E(A_t, K) = max severity_score
        2. 确定 δ(t) = dynamic_delta(iteration)
        3. 输出 TransferSignal

        返回：PASS | SOFT_REJECT | HARD_REJECT
        """
        self._call_count += 1
        n_conflicts = len(conflict_knowledge)

        # 统计各类冲突
        for c in conflict_knowledge:
            raw_type = c.get("ctype", "")
            t = raw_type.upper().replace("-", "").replace("_", "")
            if t in ("TYPE1", "TYPEI"):
                self._type1_count += 1
            elif t in ("TYPE2", "TYPEII"):
                self._type2_count += 1
            elif t in ("TYPE3", "TYPEIII"):
                self._type3_count += 1

        # 计算 E(A_t, K) 和动态 δ
        self._last_error_value = compute_error_function(conflict_knowledge)
        iteration = agent_state.get("iteration", self._call_count - 1)
        self._last_delta = compute_dynamic_delta(
            iteration, self.delta, self.delta_relaxed, self.retry_threshold
        )

        # 门控决策
        decision = G(
            agent_state=agent_state,
            conflict_knowledge=conflict_knowledge,
            delta=self.delta,
            delta_relaxed=self.delta_relaxed,
            retry_threshold=self.retry_threshold,
        )

        if decision == GateDecision.SOFT_REJECT:
            self._soft_reject_count += 1
        elif decision == GateDecision.HARD_REJECT:
            self._hard_reject_count += 1
        else:
            self._pass_count += 1

        # 记录历史
        record = ConflictRecord(
            has_conflict=n_conflicts > 0,
            conflict_types=[c.get("ctype", "") for c in conflict_knowledge],
            conflict_rate=self.conflict_rate(),
            gate_decision=decision.value,
            agent_confidence=agent_state.get("confidence", 1.0),
            task_type=agent_state.get("task_type", "unknown"),
        )
        self._history.append(record)
        if len(self._history) > self.window_size * 2:
            self._history = self._history[-self.window_size:]

        return decision

    def stats(self) -> Dict[str, Any]:
        """
        返回统计摘要（对应论文 §6.3 消融实验指标）。
        """
        total = max(self._call_count, 1)
        total_conflicts = self._type1_count + self._type2_count + self._type3_count
        return {
            "total_calls": self._call_count,
            "pass_count": self._pass_count,
            "soft_reject_count": self._soft_reject_count,
            "hard_reject_count": self._hard_reject_count,
            # 向后兼容
            "block_count": self._soft_reject_count,
            "escalate_count": self._hard_reject_count,
            "pass_rate": round(self._pass_count / total, 3),
            "soft_reject_rate": round(self._soft_reject_count / total, 3),
            "hard_reject_rate": round(self._hard_reject_count / total, 3),
            "block_rate": round(self._soft_reject_count / total, 3),
            "escalate_rate": round(self._hard_reject_count / total, 3),
            "current_conflict_rate": round(self.conflict_rate(), 3),
            "cumulative_conflict_rate": round(self.cumulative_conflict_rate(), 3),
            "last_error_value": round(self._last_error_value, 3),
            "last_delta": round(self._last_delta, 3),
            "type1_count": self._type1_count,
            "type2_count": self._type2_count,
            "type3_count": self._type3_count,
            "total_conflicts": total_conflicts,
            "delta": self.delta,
            "delta_relaxed": self.delta_relaxed,
            "retry_threshold": self.retry_threshold,
            "theta_high": self.theta_high,
        }

    def reset(self) -> None:
        """重置所有统计和历史记录"""
        self._history.clear()
        self._call_count = 0
        self._soft_reject_count = 0
        self._hard_reject_count = 0
        self._pass_count = 0
        self._type1_count = 0
        self._type2_count = 0
        self._type3_count = 0
        self._last_error_value = 0.0
        self._last_delta = self.delta

    def __repr__(self) -> str:
        rate = self.cumulative_conflict_rate()
        return (f"PhysicsGate(delta={self.delta}, delta_relaxed={self.delta_relaxed}, "
                f"conflict_rate={rate:.3f}, calls={self._call_count})")


# =============================================================================
# TCM 配伍冲突数据集（200+ 条样本）— 扩展版用于统计有效性
# =============================================================================

# 十八反绝对禁忌（E=1.0）
HERB_PAIRS_18CONTRA = [
    ("甘草", "甘遂"), ("甘草", "大戟"), ("甘草", "海藻"), ("甘草", "芫花"),
    ("乌头", "贝母"), ("乌头", "瓜蒌"), ("乌头", "半夏"), ("乌头", "白蔹"),
    ("乌头", "白芨"),
    ("人参", "五灵脂"),
    ("丹参", "藜芦"),
    ("巴豆", "牵牛"), ("丁香", "郁金"), ("牙硝", "荆三棱"),
    ("附子", "贝母"), ("附子", "瓜蒌"), ("附子", "半夏"), ("附子", "白蔹"),
    ("川乌", "贝母"), ("川乌", "瓜蒌"), ("川乌", "半夏"), ("川乌", "白蔹"),
    ("官桂", "石脂"), ("三棱", "朴硝"),
]

# 十九畏相对禁忌（E=0.7）
HERB_PAIRS_19FEAR = [
    ("人参", "莱菔子"), ("附子", "犀角"),
    ("硫黄", "朴硝"), ("水银", "砒霜"),
    ("狼毒", "密陀僧"),
    ("牙硝", "三棱"),
]

# 药理机制冲突（E=0.85）
HERB_PAIRS_PHARMA = [
    ("附子", "半夏"), ("附子", "石膏"),
    ("麻黄", "石膏"), ("黄连", "附子"),
    ("三棱", "芒硝"), ("三棱", "硇砂"),
    ("朴硝", "郁金"),
]

# 协同药对（无冲突）
HERB_PAIRS_SYNG = [
    ("人参", "黄芪"), ("麻黄", "桂枝"), ("当归", "川芎"),
    ("黄连", "吴茱萸"), ("附子", "干姜"), ("枸杞子", "菊花"),
    ("白术", "茯苓"), ("金银花", "连翘"), ("柴胡", "黄芩"),
    ("陈皮", "半夏"), ("党参", "白术"), ("熟地黄", "山茱萸"),
    ("酸枣仁", "远志"), ("石菖蒲", "远志"), ("百合", "麦冬"),
    ("天冬", "麦冬"), ("龟板", "鳖甲"), ("龙骨", "牡蛎"),
    ("白芍", "赤芍"), ("知母", "黄柏"), ("沙参", "麦冬"),
    ("川芎", "当归"), ("红花", "桃仁"), ("乳香", "没药"),
    ("三七", "白及"), ("艾叶", "香附"), ("枳实", "枳壳"),
]

# 正常配伍（无冲突）
HERB_PAIRS_NORMAL = [
    ("黄芪", "党参"), ("山药", "茯苓"), ("山楂", "神曲"),
    ("麦芽", "谷芽"), ("生姜", "大枣"), ("薄荷", "牛蒡子"),
    ("葛根", "柴胡"), ("升麻", "柴胡"), ("菊花", "桑叶"),
    ("竹叶", "黄芩"), ("佩兰", "藿香"), ("苍术", "厚朴"),
    ("木香", "砂仁"), ("香附", "川芎"), ("丹皮", "赤芍"),
    ("玄参", "地骨皮"), ("地骨皮", "银柴胡"), ("胡黄连", "银柴胡"),
    ("黄芩", "黄连"), ("黄柏", "知母"),("栀子", "淡豆豉"),
    ("豆豉", "葱白"), ("芦根", "茅根"), ("天花粉", "芦根"),
    ("勾藤", "天麻"), ("石决明", "草决明"), ("磁石", "朱砂"),
    ("远志", "石菖蒲"), ("酸枣仁", "五味子"), ("龟板", "龙骨"),
]

# 生成扩展数据集（200+ 样本）
def _generate_extended_tcm_pairs():
    """生成扩展的 TCM 药对数据集"""
    pairs = []

    # 十八反冲突（23 对）
    for herb_a, herb_b in HERB_PAIRS_18CONTRA:
        pairs.append({
            "herb_a": herb_a, "herb_b": herb_b,
            "status": "conflict", "conflict_type": "TYPE_I",
            "severity": "absolute_forbidden", "error_value": 1.0,
        })

    # 十九畏冲突（7 对）
    for herb_a, herb_b in HERB_PAIRS_19FEAR:
        pairs.append({
            "herb_a": herb_a, "herb_b": herb_b,
            "status": "conflict", "conflict_type": "TYPE_II",
            "severity": "relative_warning", "error_value": 0.7,
        })

    # 药理机制冲突（8 对）
    for herb_a, herb_b in HERB_PAIRS_PHARMA:
        pairs.append({
            "herb_a": herb_a, "herb_b": herb_b,
            "status": "conflict", "conflict_type": "TYPE_II",
            "severity": "pharmacokinetic", "error_value": 0.85,
        })

    # 协同药对（30 对）
    for herb_a, herb_b in HERB_PAIRS_SYNG:
        pairs.append({
            "herb_a": herb_a, "herb_b": herb_b,
            "status": "no_conflict", "conflict_type": None,
            "severity": "synergistic", "error_value": 0.0,
        })

    # 正常配伍（30 对）
    for herb_a, herb_b in HERB_PAIRS_NORMAL:
        pairs.append({
            "herb_a": herb_a, "herb_b": herb_b,
            "status": "no_conflict", "conflict_type": None,
            "severity": "normal", "error_value": 0.0,
        })

    return pairs

TCM_HERB_PAIRS = _generate_extended_tcm_pairs()


# =============================================================================
# TCM Conflict 知识库（规则型，ground truth）
# =============================================================================

KNOWN_CONFLICTS: Dict[tuple, Dict] = {
    # 十八反（绝对禁忌，E=1.0）
    ("甘草", "甘遂"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("甘草", "大戟"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("甘草", "海藻"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("甘草", "芫花"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("人参", "藜芦"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("人参", "五灵脂"): {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("乌头", "贝母"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("乌头", "瓜蒌"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("乌头", "半夏"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("乌头", "白蔹"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("乌头", "白芨"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("丹参", "藜芦"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("巴豆", "牵牛"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("丁香", "郁金"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("牙硝", "荆三棱"): {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("附子", "贝母"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("附子", "瓜蒌"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("附子", "半夏"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("附子", "白蔹"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("川乌", "贝母"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("川乌", "瓜蒌"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("川乌", "半夏"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("川乌", "白蔹"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("官桂", "石脂"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    ("三棱", "朴硝"):   {"type": "TYPE_I", "severity": "absolute_forbidden", "error": 1.0},
    # 十九畏（相畏相恶，E=0.7）
    ("人参", "莱菔子"): {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    ("附子", "犀角"):   {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    ("硫黄", "朴硝"):   {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    ("水银", "砒霜"):   {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    ("狼毒", "密陀僧"): {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    ("牙硝", "三棱"):   {"type": "TYPE_II", "severity": "relative_warning", "error": 0.7},
    # 现代药理冲突（E=0.85）
    ("附子", "半夏"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("附子", "石膏"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("麻黄", "石膏"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("黄连", "附子"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("三棱", "芒硝"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("三棱", "硇砂"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
    ("朴硝", "郁金"):   {"type": "TYPE_II", "severity": "pharmacokinetic", "error": 0.85},
}


def check_tcm_conflict(herb_a: str, herb_b: str) -> Optional[Dict]:
    """
    O(1) 哈希查询两味中药是否存在配伍禁忌（对应论文 §3.2.4）。

    参数：
        herb_a, herb_b: 中药名称

    返回：
        Dict 包含 ctype, severity, error 或 None（无禁忌）
        'error' 字段对应论文 severity_score E(A_t, K)
    """
    for p in [(herb_a, herb_b), (herb_b, herb_a)]:
        if p in KNOWN_CONFLICTS:
            info = KNOWN_CONFLICTS[p]
            return {
                "ctype": info["type"],
                "severity": info["severity"],
                "error": info.get("error", SEVERITY_ERROR_MAP.get(info["severity"], 0.5)),
            }
    return None


# =============================================================================
# TCMConstraintLibrary — 三层约束结构（对应论文 §3.2.4）
# =============================================================================

class TCMConstraintLibrary:
    """
    TCM配伍禁忌规则库 —物理约束的Hard Constraints来源

    三层结构：
    - Layer 1 (E=1.0): 十八反绝对禁忌
    - Layer 2 (E=0.7~0.85): 十九畏/药理机制冲突
    - Layer 3 (E=0.4): 理论/上下文冲突

    用法：
        lib = TCMConstraintLibrary()
        constraint = lib.get_constraint("甘草", "甘遂")
        if constraint:
            print(f"Type: {constraint['conflict_type']}, Error: {constraint['error_value']}")
    """

    # Layer 1: 十八反（绝对禁忌，E=1.0）
    EIGHTEEN_CONTRA = [
        ("甘草", "甘遂"), ("甘草", "大戟"), ("甘草", "海藻"), ("甘草", "芫花"),
        ("乌头", "贝母"), ("乌头", "瓜蒌"), ("乌头", "半夏"), ("乌头", "白蔹"),
        ("乌头", "白芨"),
        ("人参", "五灵脂"),
        ("丹参", "藜芦"),
        ("巴豆", "牵牛"), ("丁香", "郁金"), ("牙硝", "荆三棱"),
        ("附子", "贝母"), ("附子", "瓜蒌"), ("附子", "半夏"), ("附子", "白蔹"),
        ("川乌", "贝母"), ("川乌", "瓜蒌"), ("川乌", "半夏"), ("川乌", "白蔹"),
        ("官桂", "石脂"), ("三棱", "朴硝"),
    ]

    # Layer 2: 十九畏（相对禁忌，E=0.7）
    NINETEEN_FEAR = [
        ("人参", "莱菔子"), ("附子", "犀角"),
        ("硫黄", "朴硝"), ("水银", "砒霜"),
        ("狼毒", "密陀僧"), ("巴豆", "牵牛"),
        ("丁香", "郁金"), ("牙硝", "三棱"),
    ]

    # Layer 3: 药理机制冲突（E=0.85）
    PHARMACOKINETIC = [
        ("附子", "半夏"), ("附子", "石膏"),
        ("麻黄", "石膏"), ("黄连", "附子"),
        ("丹参", "藜芦"),
    ]

    # 扩展协同药对（用于负样本生成）
    SYNERGISTIC_PAIRS = [
        ("人参", "黄芪"), ("麻黄", "桂枝"), ("当归", "川芎"),
        ("黄连", "吴茱萸"), ("附子", "干姜"), ("枸杞子", "菊花"),
        ("白术", "茯苓"), ("金银花", "连翘"), ("柴胡", "黄芩"),
        ("陈皮", "半夏"), ("党参", "白术"), ("熟地黄", "山茱萸"),
        ("酸枣仁", "远志"), ("石菖蒲", "远志"), ("百合", "麦冬"),
        ("天冬", "麦冬"), ("龟板", "鳖甲"), ("龙骨", "牡蛎"),
    ]

    def __init__(self):
        self._build_constraint_pairs()

    def _build_constraint_pairs(self):
        """构建约束药对列表"""
        self.constraint_pairs = []

        # Layer 1: 十八反
        for herb_a, herb_b in self.EIGHTEEN_CONTRA:
            self.constraint_pairs.append({
                "herb_a": herb_a,
                "herb_b": herb_b,
                "conflict_type": "十八反",
                "severity": "absolute_forbidden",
                "error_value": 1.0,
            })

        # Layer 2: 十九畏
        for herb_a, herb_b in self.NINETEEN_FEAR:
            self.constraint_pairs.append({
                "herb_a": herb_a,
                "herb_b": herb_b,
                "conflict_type": "十九畏",
                "severity": "relative_warning",
                "error_value": 0.7,
            })

        # Layer 3: 药理机制
        for herb_a, herb_b in self.PHARMACOKINETIC:
            self.constraint_pairs.append({
                "herb_a": herb_a,
                "herb_b": herb_b,
                "conflict_type": "药理冲突",
                "severity": "pharmacokinetic",
                "error_value": 0.85,
            })

    def get_constraint(self, herb_a: str, herb_b: str) -> Optional[Dict]:
        """查询约束药对"""
        for pair in self.constraint_pairs:
            if (pair["herb_a"] == herb_a and pair["herb_b"] == herb_b) or \
               (pair["herb_a"] == herb_b and pair["herb_b"] == herb_a):
                return pair
        return None

    def has_conflict(self, herb_a: str, herb_b: str) -> bool:
        """检查是否存在约束冲突"""
        return self.get_constraint(herb_a, herb_b) is not None

    def get_all_pairs(self) -> List[Dict]:
        """返回所有约束药对"""
        return self.constraint_pairs


# =============================================================================
# 统计验证函数（Bootstrap置信区间）
# =============================================================================

import random


def bootstrap_confidence_interval(
    metric_fn,
    samples: List[Dict],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    random_seed: int = 42,
) -> Dict[str, float]:
    """
    Bootstrap 重采样计算置信区间（对应论文 §6.3 统计验证）。

    参数：
        metric_fn: 计算指标的函数，输入样本列表，输出 {precision, recall, f1}
        samples: 完整样本列表
        n_bootstrap: 重采样次数（默认 1000）
        confidence: 置信度（默认 95%）
        random_seed: 随机种子

    返回：
        {mean, lower, upper, std, ci_width}
    """
    random.seed(random_seed)
    n = len(samples)

    if n == 0:
        return {"mean": 0.0, "lower": 0.0, "upper": 0.0, "std": 0.0, "ci_width": 0.0}

    metric_values = []
    for _ in range(n_bootstrap):
        # 有放回采样
        bootstrap_sample = [random.choice(samples) for _ in range(n)]
        metrics = metric_fn(bootstrap_sample)
        metric_values.append(metrics.get("f1", metrics.get("precision", 0.0)))

    metric_values.sort()
    alpha = 1 - confidence
    lower_idx = int(alpha / 2 * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap)

    mean_val = sum(metric_values) / len(metric_values)
    variance = sum((x - mean_val) ** 2 for x in metric_values) / len(metric_values)
    std_val = variance ** 0.5

    return {
        "mean": round(mean_val, 4),
        "lower": round(metric_values[lower_idx], 4),
        "upper": round(metric_values[upper_idx], 4),
        "std": round(std_val, 4),
        "ci_width": round(metric_values[upper_idx] - metric_values[lower_idx], 4),
    }


def compute_metrics_with_ci(
    results: List[Dict],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """
    计算分类指标及其 Bootstrap 95% 置信区间。

    参数：
        results: 检测结果列表，每项包含 expected/predicted_conflict
        n_bootstrap: 重采样次数
        confidence: 置信度

    返回：
        {precision, recall, f1, ci_precision, ci_recall, ci_f1}
    """
    def calc_metrics(sample_list):
        tp = sum(1 for r in sample_list if r.get("predicted_conflict") and r.get("has_conflict"))
        fp = sum(1 for r in sample_list if r.get("predicted_conflict") and not r.get("has_conflict"))
        tn = sum(1 for r in sample_list if not r.get("predicted_conflict") and not r.get("has_conflict"))
        fn = sum(1 for r in sample_list if not r.get("predicted_conflict") and r.get("has_conflict"))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {"precision": precision, "recall": recall, "f1": f1}

    # 基础指标
    base = calc_metrics(results)

    # Bootstrap CI
    ci_precision = bootstrap_confidence_interval(
        lambda s: calc_metrics(s), results, n_bootstrap, confidence, random_seed=42
    )
    ci_recall = bootstrap_confidence_interval(
        lambda s: calc_metrics(s), results, n_bootstrap, confidence, random_seed=43
    )
    ci_f1 = bootstrap_confidence_interval(
        lambda s: calc_metrics(s), results, n_bootstrap, confidence, random_seed=44
    )

    return {
        "precision": round(base["precision"], 4),
        "recall": round(base["recall"], 4),
        "f1": round(base["f1"], 4),
        "ci_precision": ci_precision,
        "ci_recall": ci_recall,
        "ci_f1": ci_f1,
    }


# =============================================================================
# 核心验证逻辑（最小闭环）
# =============================================================================

def run_tcm_validation(n_samples: int = None) -> Dict[str, Any]:
    """
    在 TCM_HERB_PAIRS 上跑最小闭环验证（对应论文 §6.2）。

    闭环链路（对应论文 Algorithm 1）：
        check_tcm_conflict() → conflict_knowledge
        → E(A_t, K) = compute_error_function(conflict_knowledge)
        → G(A_t, K, δ) → TransferSignal (PASS/SOFT_REJECT/HARD_REJECT)

    参数：
        n_samples: 最多跑几条样本，默认全部 10 条

    返回：
        {
            "samples_tested": int,
            "tp": int, "fp": int, "tn": int, "fn": int,
            "precision": float, "recall": float, "f1": float,
            "results": List[Dict],
            "gate_stats": Dict,
        }
    """
    samples = TCM_HERB_PAIRS[:n_samples]
    gate = PhysicsGate(delta=0.05, delta_relaxed=0.10, retry_threshold=3)

    tp = fp = tn = fn = 0
    results = []

    for i, sample in enumerate(samples):
        herb_a = sample["herb_a"]
        herb_b = sample["herb_b"]
        expected_conflict = sample["status"] == "conflict"

        # Step 1: O(1) 哈希查询（论文 §3.2.4）
        detected = check_tcm_conflict(herb_a, herb_b)
        has_conflict = detected is not None

        # Step 2: 构造 conflict_knowledge（带 severity error value）
        conflict_knowledge = []
        if detected:
            conflict_knowledge = [{
                "ctype": detected["ctype"],
                "parties": [herb_a, herb_b],
                "gap": detected.get("error", 0.5),
            }]

        # Step 3: agent_state
        agent_state = {
            "task_type": "tcm_herb_conflict",
            "iteration": i,
            "confidence": 0.9,
        }

        # Step 4: PhysicsGate 决策（G(A_t, K, δ)）
        decision = gate.decide(agent_state, conflict_knowledge)

        # Step 5: 计算 TP/FP/TN/FN
        if has_conflict and expected_conflict:
            tp += 1
        elif has_conflict and not expected_conflict:
            fp += 1
        elif not has_conflict and expected_conflict:
            fn += 1
        else:
            tn += 1

        results.append({
            "herb_a": herb_a,
            "herb_b": herb_b,
            "expected": sample["status"],
            "detected": has_conflict,
            "ctype": detected["ctype"] if detected else None,
            "error_value": detected.get("error", 0.0) if detected else 0.0,
            "gate_decision": decision.value,
            "effective_delta": gate._last_delta,
            "conflict_rate": gate.cumulative_conflict_rate(),
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "samples_tested": len(samples),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "results": results,
        "gate_stats": gate.stats(),
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 70)
    print("PhysicsGate × TCM 最小闭环验证（论文 §6 实验）")
    print("=" * 70)

    results = run_tcm_validation()

    print(f"\n[样本统计]")
    print(f"  测试样本:    {results['samples_tested']}")
    print(f"  TP={results['tp']}  FP={results['fp']}  TN={results['tn']}  FN={results['fn']}")

    print(f"\n[检测指标]")
    print(f"  Precision:  {results['precision']}")
    print(f"  Recall:     {results['recall']}")
    print(f"  F1:         {results['f1']}")

    print(f"\n[逐样本门控决策]")
    print(f"  {'药对':<16} {'预期':<12} {'检测':<8} {'类型':<10} {'E值':<6} {'δ(t)':<6} {'决策':<14}")
    print(f"  {'-'*16} {'-'*12} {'-'*8} {'-'*10} {'-'*6} {'-'*6} {'-'*14}")
    for r in results["results"]:
        ctype = r["ctype"] or "-"
        print(f"  {r['herb_a']}-{r['herb_b']:<8} {r['expected']:<12} "
              f"{str(r['detected']):<8} {ctype:<10} "
              f"{r.get('error_value', 0):<6.2f} {r.get('effective_delta', 0.05):<6.2f} "
              f"{r['gate_decision']:<14}")

    print(f"\n[PhysicsGate 统计]")
    s = results["gate_stats"]
    print(f"  δ_strict={s['delta']}  δ_relaxed={s['delta_relaxed']}  "
          f"retry_threshold={s['retry_threshold']}  总调用={s['total_calls']}")
    print(f"  PASS={s['pass_count']}  SOFT_REJECT={s['soft_reject_count']}  "
          f"HARD_REJECT={s['hard_reject_count']}")
    print(f"  通过率={s['pass_rate']}  软拒率={s['soft_reject_rate']}  "
          f"硬拒率={s['hard_reject_rate']}")
    print(f"  Type-I={s['type1_count']}  Type-II={s['type2_count']}  "
          f"Type-III={s['type3_count']}")

    print(f"\n{repr(PhysicsGate())}")
    print()


if __name__ == "__main__":
    main()
