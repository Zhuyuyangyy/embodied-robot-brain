#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhysicsGate - Conflict-Aware Agent Gating Mechanism
=================================================

embodied-robot-brain 物理门控层。
基于 conflict_rate 和 δ 阈值，决定 agent 输出是 PASS / BLOCK / ESCALATE。

公式：G(A_t, K, δ) = {
    PASS     if conflict_rate(A_t, K) <= δ
    BLOCK    if δ < conflict_rate(A_t, K) < θ_HIGH
    ESCALATE if conflict_rate(A_t, K) >= θ_HIGH
}

用法：
    gate = PhysicsGate(delta=0.3, theta_high=0.7)
    decision = gate.decide(agent_state, conflict_knowledge)
    print(decision)  # 'PASS' | 'BLOCK' | 'ESCALATE'

Author: embodied-robot-brain Team
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GateDecision(Enum):
    PASS = "PASS"       # 通过：冲突率低于 δ，正常输出
    BLOCK = "BLOCK"     # 阻断：冲突率超过 δ，阻止输出
    ESCALATE = "ESCALATE"  # 升级：冲突率超过 θ_HIGH，强制人工审核


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


def G(
    agent_state: Dict[str, Any],
    conflict_knowledge: List[Dict[str, Any]],
    delta: float = 0.30,
    theta_high: float = 0.70
) -> GateDecision:
    """
    物理门控函数 G(A_t, K, δ, θ_HIGH)

    参数：
        agent_state: 当前 agent 状态，格式：
            {
                "task_type": str,
                "iteration": int,
                "confidence": float,
                "cumulative_attempts": int,   # 累计总调用数
                "cumulative_conflicts": int,  # 累计冲突数
            }
        conflict_knowledge: 已知冲突列表，格式：
            [{"ctype": "Type-I"|"Type-II"|"Type-III", "parties": [...], "gap": float}]
        delta: 阻断阈值 (0.0~1.0)，冲突率 > δ 则 BLOCK
        theta_high: 升级阈值 (0.0~1.0)，冲突率 >= θ_HIGH 则 ESCALATE

    返回：
        GateDecision: PASS | BLOCK | ESCALATE
    """
    cumulative_attempts = agent_state.get("cumulative_attempts", 1)
    cumulative_conflicts = agent_state.get("cumulative_conflicts", 0)

    conflict_rate = cumulative_conflicts / max(cumulative_attempts, 1)

    # 动态 δ 调整：早期探索宽容
    iteration = agent_state.get("iteration", 0)
    if iteration < 3:
        effective_delta = delta * 1.2
    else:
        effective_delta = delta

    if conflict_rate >= theta_high:
        return GateDecision.ESCALATE
    elif conflict_rate > effective_delta:
        return GateDecision.BLOCK
    else:
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
        delta: float = 0.30,
        theta_high: float = 0.70,
        window_size: int = 20,
        decay: float = 0.95,
    ):
        self.delta = delta
        self.theta_high = theta_high
        self.window_size = window_size
        self.decay = decay

        self._history: List[ConflictRecord] = []
        self._call_count = 0
        self._block_count = 0
        self._escalate_count = 0
        self._pass_count = 0
        self._type1_count = 0
        self._type2_count = 0
        self._type3_count = 0

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
        门控决策：给定 agent 状态和冲突知识，返回 PASS/BLOCK/ESCALATE。
        """
        self._call_count += 1
        n_conflicts = len(conflict_knowledge)

        # 统计各类冲突（统一归一化处理：Type-I/II/III, TYPE_I/II/III, Type-1/2/3 等）
        for c in conflict_knowledge:
            raw_type = c.get("ctype", "")
            # Normalize to "TYPE1"/"TYPE2"/"TYPE3" form for reliable matching
            t = raw_type.upper().replace("-", "").replace("_", "")
            if t in ("TYPE1", "TYPEI"):
                self._type1_count += 1
            elif t in ("TYPE2", "TYPEII"):
                self._type2_count += 1
            elif t in ("TYPE3", "TYPEIII"):
                self._type3_count += 1

        # 构建包含累计信息的 agent_state（覆写 cumulative 字段）
        enriched_state = dict(agent_state)
        enriched_state["cumulative_attempts"] = self._call_count
        enriched_state["cumulative_conflicts"] = (
            self._type1_count + self._type2_count + self._type3_count
        )

        decision = G(
            agent_state=enriched_state,
            conflict_knowledge=conflict_knowledge,
            delta=self.delta,
            theta_high=self.theta_high
        )

        if decision == GateDecision.BLOCK:
            self._block_count += 1
        elif decision == GateDecision.ESCALATE:
            self._escalate_count += 1
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
        返回统计摘要。
        """
        total = max(self._call_count, 1)
        total_conflicts = self._type1_count + self._type2_count + self._type3_count
        return {
            "total_calls": self._call_count,
            "pass_count": self._pass_count,
            "block_count": self._block_count,
            "escalate_count": self._escalate_count,
            "pass_rate": round(self._pass_count / total, 3),
            "block_rate": round(self._block_count / total, 3),
            "escalate_rate": round(self._escalate_count / total, 3),
            "current_conflict_rate": round(self.conflict_rate(), 3),
            "cumulative_conflict_rate": round(self.cumulative_conflict_rate(), 3),
            "type1_count": self._type1_count,
            "type2_count": self._type2_count,
            "type3_count": self._type3_count,
            "total_conflicts": total_conflicts,
            "delta": self.delta,
            "theta_high": self.theta_high,
        }

    def reset(self) -> None:
        """重置所有统计和历史记录"""
        self._history.clear()
        self._call_count = 0
        self._block_count = 0
        self._escalate_count = 0
        self._pass_count = 0
        self._type1_count = 0
        self._type2_count = 0
        self._type3_count = 0

    def __repr__(self) -> str:
        rate = self.cumulative_conflict_rate()
        return (f"PhysicsGate(delta={self.delta}, θ_HIGH={self.theta_high}, "
                f"conflict_rate={rate:.3f}, calls={self._call_count})")


# =============================================================================
# TCM 配伍冲突数据集（10 条样本）
# =============================================================================

TCM_HERB_PAIRS = [
    # 已知绝对禁忌：十八反
    {
        "herb_a": "甘草", "herb_b": "甘遂",
        "status": "conflict", "conflict_type": "Type-II",
        "severity": "absolute_forbidden",
        "description": "甘草与甘遂同用属十八反禁忌，可引起中毒反应"
    },
    {
        "herb_a": "人参", "herb_b": "藜芦",
        "status": "conflict", "conflict_type": "Type-II",
        "severity": "absolute_forbidden",
        "description": "人参与藜芦同用属十八反，人参反藜芦不可同用"
    },
    {
        "herb_a": "乌头", "herb_b": "贝母",
        "status": "conflict", "conflict_type": "Type-II",
        "severity": "absolute_forbidden",
        "description": "乌头类与贝母同用增加乌头碱毒性"
    },
    # 已知协同：无冲突
    {
        "herb_a": "人参", "herb_b": "黄芪",
        "status": "no_conflict", "conflict_type": None,
        "severity": "synergistic",
        "description": "人参与黄芪同用增强补气效果，属经典配伍"
    },
    {
        "herb_a": "麻黄", "herb_b": "桂枝",
        "status": "no_conflict", "conflict_type": None,
        "severity": "synergistic",
        "description": "麻黄与桂枝同用增强发汗解表效果"
    },
    # 疑似配伍禁忌：十九畏
    {
        "herb_a": "人参", "herb_b": "莱菔子",
        "status": "conflict", "conflict_type": "Type-I",
        "severity": "relative_warning",
        "description": "人参与莱菔子相恶，人参补气而莱菔子消气，理论上降低人参效力"
    },
    {
        "herb_a": "附子", "herb_b": "犀角",
        "status": "conflict", "conflict_type": "Type-III",
        "severity": "theoretical_contradiction",
        "description": "附子温阳与犀角清热药性相反，理论上存在寒热对抗"
    },
    # 现代药理冲突
    {
        "herb_a": "丹参", "herb_b": "藜芦",
        "status": "conflict", "conflict_type": "Type-II",
        "severity": "pharmacokinetic",
        "description": "丹参酮与藜芦生物碱同用增加心律失常风险，现代药理证实"
    },
    # 正常配伍
    {
        "herb_a": "当归", "herb_b": "川芎",
        "status": "no_conflict", "conflict_type": None,
        "severity": "normal",
        "description": "当归与川芎组成千古名方佛手散，活血养血兼施"
    },
    {
        "herb_a": "黄连", "herb_b": "吴茱萸",
        "status": "no_conflict", "conflict_type": None,
        "severity": "normal",
        "description": "黄连与吴茱萸配伍属左金丸，清肝泻火反佐工艺"
    },
]


# =============================================================================
# TCM Conflict 知识库（规则型，ground truth）
# =============================================================================

KNOWN_CONFLICTS: Dict[tuple, Dict] = {
    # 十八反（绝对禁忌）
    ("甘草", "甘遂"):   {"type": "Type-II", "severity": "absolute_forbidden"},
    ("人参", "藜芦"):   {"type": "Type-II", "severity": "absolute_forbidden"},
    ("乌头", "贝母"):   {"type": "Type-II", "severity": "absolute_forbidden"},
    ("乌头", "瓜蒌"):   {"type": "Type-II", "severity": "absolute_forbidden"},
    ("甘草", "海藻"):   {"type": "Type-II", "severity": "absolute_forbidden"},
    # 十九畏（相畏相恶）
    ("人参", "莱菔子"): {"type": "Type-I", "severity": "relative_warning"},
    ("附子", "犀角"):   {"type": "Type-III", "severity": "theoretical_contradiction"},
    # 现代药理冲突
    ("丹参", "藜芦"):   {"type": "Type-II", "severity": "pharmacokinetic"},
    ("附子", "半夏"):   {"type": "Type-II", "severity": "pharmacokinetic"},
}


def check_tcm_conflict(herb_a: str, herb_b: str) -> Optional[Dict]:
    """
    查询两味中药是否存在配伍禁忌（规则知识库查询）。

    参数：
        herb_a, herb_b: 中药名称

    返回：
        Dict 包含 ctype, severity 或 None（无禁忌）
        注意：返回字典使用 'ctype' 键（与 PhysicsGate.decide 接口一致）
    """
    for p in [(herb_a, herb_b), (herb_b, herb_a)]:
        if p in KNOWN_CONFLICTS:
            info = KNOWN_CONFLICTS[p]
            return {"ctype": info["type"], "severity": info["severity"]}
    return None


# =============================================================================
# 核心验证逻辑（最小闭环）
# =============================================================================

def run_tcm_validation(n_samples: int = None) -> Dict[str, Any]:
    """
    在 TCM_HERB_PAIRS 上跑最小闭环验证。

    闭环链路：
        conflict_validator.check() → conflict_knowledge
        → PhysicsGate.decide(agent_state, conflict_knowledge)
        → gate_decision (PASS/BLOCK/ESCALATE)

    参数：
        n_samples: 最多跑几条样本，默认全部 10 条

    返回：
        {
            "samples_tested": int,
            "tp": int, "fp": int, "tn": int, "fn": int,
            "precision": float, "recall": float, "f1": float,
            "results": List[Dict],   # 每条样本的详细结果
            "gate_stats": Dict,
        }
    """
    samples = TCM_HERB_PAIRS[:n_samples]
    gate = PhysicsGate(delta=0.3, theta_high=0.7)

    tp = fp = tn = fn = 0
    results = []

    for i, sample in enumerate(samples):
        herb_a = sample["herb_a"]
        herb_b = sample["herb_b"]
        expected_conflict = sample["status"] == "conflict"

        # Step 1: conflict_validator 检测（知识库查询）
        detected = check_tcm_conflict(herb_a, herb_b)
        has_conflict = detected is not None

        # Step 2: 构造 conflict_knowledge（冲突知识列表）
        conflict_knowledge = []
        if detected:
            conflict_knowledge = [{
                "ctype": detected["ctype"],
                "parties": [herb_a, herb_b],
                "gap": 0.05,
            }]

        # Step 3: agent_state（累计上下文）
        agent_state = {
            "task_type": "tcm_herb_conflict",
            "iteration": i,
            "confidence": 0.9,
        }

        # Step 4: PhysicsGate 决策
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
            "gate_decision": decision.value,
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
    print("=" * 62)
    print("PhysicsGate × conflict_validator  最小闭环验证")
    print("=" * 62)

    results = run_tcm_validation()

    print(f"\n[样本统计]")
    print(f"  测试样本:    {results['samples_tested']}")
    print(f"  TP={results['tp']}  FP={results['fp']}  TN={results['tn']}  FN={results['fn']}")

    print(f"\n[检测指标]")
    print(f"  Precision:  {results['precision']}")
    print(f"  Recall:     {results['recall']}")
    print(f"  F1:         {results['f1']}")

    print(f"\n[逐样本门控决策]")
    print(f"  {'药对':<16} {'预期':<12} {'检测':<8} {'类型':<10} {'决策':<10} {'累计冲突率'}")
    print(f"  {'-'*16} {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
    for r in results["results"]:
        ctype = r["ctype"] or "-"
        print(f"  {r['herb_a']}-{r['herb_b']:<8} {r['expected']:<12} "
              f"{str(r['detected']):<8} {ctype:<10} {r['gate_decision']:<10} "
              f"{r['conflict_rate']:.3f}")

    print(f"\n[PhysicsGate 统计]")
    s = results["gate_stats"]
    print(f"  δ={s['delta']}  θ_HIGH={s['theta_high']}  总调用={s['total_calls']}")
    print(f"  通过率={s['pass_rate']}  阻断率={s['block_rate']}  升级率={s['escalate_rate']}")
    print(f"  累计冲突率={s['cumulative_conflict_rate']}  滑动冲突率={s['current_conflict_rate']}")
    print(f"  Type-I={s['type1_count']}  Type-II={s['type2_count']}  Type-III={s['type3_count']}")

    print(f"\n{repr(PhysicsGate(delta=0.3, theta_high=0.7))}")
    print()


if __name__ == "__main__":
    main()
