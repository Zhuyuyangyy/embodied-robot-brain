#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConflictEvidence Schema — 统一冲突证据结构
==========================================

embodied-robot-brain 的所有冲突来源（规则库 / 知识图谱 / 论文 / LLM 抽取）
统一用 ConflictEvidence 表示。

格式统一后，conflict_type_classifier 和 PhysicsGate 可以无差别消费任意来源的证据。

Author: embodied-robot-brain Team
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConflictSeverity(Enum):
    """冲突严重程度（0.0~1.0）"""
    NONE = 0.0      # 无冲突
    LOW = 0.25      # 弱冲突/上下文依赖
    MEDIUM = 0.50   # 中等冲突/机制不明
    HIGH = 0.75     # 强冲突/有药理证据
    ABSOLUTE = 1.0  # 绝对禁忌/十八反/十九畏


class EvidenceSource(Enum):
    """证据来源"""
    RULE = "rule"                     # 规则知识库（十八反/十九畏）
    KG = "kg"                         # 知识图谱抽取
    PAPER = "paper"                   # 论文表格/实验数据
    LLM = "llm"                       # LLM 抽取
    PHARMACOKINETIC = "pharmacokinetic"  # 现代药理
    CLINICAL = "clinical"             # 临床报告


@dataclass
class ConflictEvidence:
    """
    统一冲突证据结构。

    属性：
        herb_a / herb_b: 药对名称
        conflict_type: "TYPE_I" | "TYPE_II" | "TYPE_III"
            - TYPE_I:   明确禁忌（十八反/十九畏/硬冲突）
            - TYPE_II:  药理机制冲突（功效方向相反、代谢干扰）
            - TYPE_III: 剂量/体质/病症上下文冲突（语义对立/理论矛盾）
        severity: 0.0~1.0，冲突严重程度
        confidence: 0.0~1.0，证据可信度（来源可靠性 × 推断置信度）
        source: EvidenceSource enum，证据来源
        mechanism: 冲突机制描述（药理/功效/剂量等）
        evidence_text: 原始证据文本（用于可解释性）
        source_paper: 来源文献（如有）
        year: 来源年份
        citations: 来源引用数（如有）
        compatible_alternatives: 替代无冲突药对建议（如有）
    """
    herb_a: str
    herb_b: str
    conflict_type: str               # "TYPE_I" | "TYPE_II" | "TYPE_III"
    severity: float                 # 0.0 ~ 1.0
    confidence: float               # 0.0 ~ 1.0
    source: EvidenceSource

    # 可选字段
    mechanism: Optional[str] = None
    evidence_text: Optional[str] = None
    source_paper: Optional[str] = None
    year: Optional[int] = None
    citations: Optional[int] = None
    compatible_alternatives: Optional[List[str]] = None

    # 内部使用
    _id: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        # 校验
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError(f"severity must be in [0.0, 1.0], got {self.severity}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

    @property
    def pair_key(self) -> tuple:
        """药对标准化 key（用于去重和查询）"""
        return tuple(sorted([self.herb_a, self.herb_b]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "herb_a": self.herb_a,
            "herb_b": self.herb_b,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "source": self.source.value if isinstance(self.source, EvidenceSource) else self.source,
            "mechanism": self.mechanism,
            "evidence_text": self.evidence_text,
            "source_paper": self.source_paper,
            "year": self.year,
            "citations": self.citations,
            "compatible_alternatives": self.compatible_alternatives,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConflictEvidence":
        """从字典构造（兼容旧格式）"""
        source_val = d.get("source", "rule")
        if isinstance(source_val, str):
            try:
                source = EvidenceSource(source_val)
            except ValueError:
                source = EvidenceSource.RULE
        else:
            source = source_val

        return cls(
            herb_a=d["herb_a"],
            herb_b=d["herb_b"],
            conflict_type=d["conflict_type"],
            severity=float(d["severity"]),
            confidence=float(d["confidence"]),
            source=source,
            mechanism=d.get("mechanism"),
            evidence_text=d.get("evidence_text"),
            source_paper=d.get("source_paper"),
            year=d.get("year"),
            citations=d.get("citations"),
            compatible_alternatives=d.get("compatible_alternatives"),
        )


# =============================================================================
# Evidence Pool — 证据集合管理
# =============================================================================

class EvidencePool:
    """
    冲突证据集合，支持多来源融合和去重。

    用法：
        pool = EvidencePool()
        pool.add(evidence1)
        pool.add(evidence2)
        results = pool.query("甘草", "甘遂")
        print(results[0].conflict_type)  # "TYPE_II"
        print(results[0].severity)        # 1.0
    """

    def __init__(self):
        # pair_key -> list of ConflictEvidence（可能多条证据同一药对）
        self._evidence: Dict[tuple, List[ConflictEvidence]] = {}
        # 全局统计
        self._type_counts = {"TYPE_I": 0, "TYPE_II": 0, "TYPE_III": 0}
        self._source_counts: Dict[str, int] = {}

    def add(self, evidence: ConflictEvidence) -> None:
        key = evidence.pair_key
        if key not in self._evidence:
            self._evidence[key] = []
        self._evidence[key].append(evidence)
        self._type_counts[evidence.conflict_type] = (
            self._type_counts.get(evidence.conflict_type, 0) + 1
        )
        src = evidence.source.value if isinstance(evidence.source, EvidenceSource) else str(evidence.source)
        self._source_counts[src] = self._source_counts.get(src, 0) + 1

    def add_batch(self, evidences: List[ConflictEvidence]) -> None:
        for e in evidences:
            self.add(e)

    def query(self, herb_a: str, herb_b: str) -> List[ConflictEvidence]:
        """查询药对所有冲突证据"""
        key = tuple(sorted([herb_a, herb_b]))
        return self._evidence.get(key, [])

    def has_conflict(self, herb_a: str, herb_b: str) -> bool:
        """药对是否存在任意冲突证据"""
        return len(self.query(herb_a, herb_b)) > 0

    def get_highest_severity(
        self, herb_a: str, herb_b: str
    ) -> Optional[ConflictEvidence]:
        """返回严重程度最高的冲突证据"""
        evidences = self.query(herb_a, herb_b)
        if not evidences:
            return None
        return max(evidences, key=lambda e: e.severity)

    def get_by_type(
        self, herb_a: str, herb_b: str, conflict_type: str
    ) -> List[ConflictEvidence]:
        """返回特定类型的冲突证据"""
        evidences = self.query(herb_a, herb_b)
        return [e for e in evidences if e.conflict_type == conflict_type]

    def get_risk_signal(
        self, herb_a: str, herb_b: str
    ) -> Optional[Dict[str, Any]]:
        """
        返回 PhysicsGate 消费的风险信号。

        融合多条证据，返回：
        {
            "conflict": bool,
            "conflict_type": str,   # 最严重类型
            "severity": float,      # 最高严重度
            "confidence": float,    # 加权置信度
            "num_evidences": int,   # 证据条数
        }
        """
        evidences = self.query(herb_a, herb_b)
        if not evidences:
            return None

        # 严重度加权置信度
        best = max(evidences, key=lambda e: e.severity * e.confidence)
        avg_confidence = sum(e.confidence for e in evidences) / len(evidences)
        weighted_confidence = (best.confidence + avg_confidence) / 2.0

        return {
            "conflict": True,
            "conflict_type": best.conflict_type,
            "severity": best.severity,
            "confidence": weighted_confidence,
            "num_evidences": len(evidences),
            "mechanism": best.mechanism,
        }

    def stats(self) -> Dict[str, Any]:
        """返回证据池统计"""
        return {
            "total_pairs": len(self._evidence),
            "total_evidences": sum(len(v) for v in self._evidence.values()),
            "type_counts": self._type_counts,
            "source_counts": self._source_counts,
        }

    def __len__(self) -> int:
        return sum(len(v) for v in self._evidence.values())
