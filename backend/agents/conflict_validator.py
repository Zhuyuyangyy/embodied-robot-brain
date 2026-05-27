#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conflict Validator Agent - 冲突检测验证Agent
==============================================

embodied-robot-brain 多主体科研验证系统
冲突类型：
- Type-I: 方法在跨数据集/设置下一致性差异（delta > 2.0%）
- Type-II: 方法在同数据集内比较时性能差距（delta > 5.0%）
- Type-III: 理论/假设互斥（检测论文间的逻辑矛盾）

用法：
    python -m backend.agents.conflict_validator \
        --input data/literature_validation_set.json \
        --output results/conflict_detection_results.json \
        --verbose

Author: embodied-robot-brain Team
"""

import argparse
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# 冲突类型定义
# =============================================================================

@dataclass
class Conflict:
    """冲突记录"""
    ctype: str           # "Type-I" | "Type-II" | "Type-III"
    description: str
    parties: List[str]  # paper_ids or method names
    dataset: Optional[str] = None
    metric: Optional[str] = None
    gap: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "type": self.ctype,
            "description": self.description,
            "parties": self.parties,
            "dataset": self.dataset,
            "metric": self.metric,
            "gap": self.gap,
        }


# =============================================================================
# 评分函数
# =============================================================================

RECENCY_HALF_LIFE = 5  # 论文衰减期（年）
WEIGHT_CITATION = 0.25
WEIGHT_RECENCY = 0.20
WEIGHT_CONSISTENCY = 0.30
WEIGHT_KG = 0.25
TYPE1_THRESHOLD = 0.02   # 2%
TYPE2_THRESHOLD = 0.05  # 5%


def compute_recency_score(year: int, current_year: int = 2026) -> float:
    """论文新颖度评分（基于论文年龄，指数衰减）"""
    age = current_year - year
    return math.pow(0.5, age / RECENCY_HALF_LIFE)


def compute_citation_score(citations: int) -> float:
    """引用影响力评分（对数归一化）"""
    if citations <= 0:
        return 0.0
    return min(1.0, math.log(1 + citations) / 10.0)


# =============================================================================
# 语义对立词对（Type-III检测）
# =============================================================================

OPPOSITE_PAIRS = [
    ("outperforms", "worse than"),
    ("significantly improves", "no significant"),
    ("effective", "ineffective"),
    ("consistent", "contrary"),
    ("supports", "refutes"),
    ("improves", "degrades"),
    ("better", "worse"),
    ("superior", "inferior"),
]


# =============================================================================
# 数据集归一化
# =============================================================================

DATASET_NORMALIZATION = {
    "cifar": "CIFAR-10",
    "cifar10": "CIFAR-10",
    "cifar-10": "CIFAR-10",
    "cifar100": "CIFAR-100",
    "cifar-100": "CIFAR-100",
    "imagenet": "ImageNet",
    "ilsvrc": "ImageNet",
    "mnist": "MNIST",
    "coco": "COCO",
    "wiki": "Wikipedia",
    "wikitext": "Wikipedia",
    "mmlu": "MMLU",
    "big bench": "BIG-bench",
    "squad": "SQuAD",
    "squad2": "SQuAD2.0",
    "pubmed": "PubMed",
}

METRIC_NORMALIZATION = {
    "acc": "Accuracy",
    "accuracy": "Accuracy",
    "prec": "Precision",
    "precision": "Precision",
    "rec": "Recall",
    "recall": "Recall",
    "f1": "F1",
    "f1score": "F1",
    "f1-score": "F1",
    "map": "mAP",
    "bleu": "BLEU",
    "rouge": "ROUGE",
    "perplexity": "Perplexity",
    "ppl": "Perplexity",
}


# =============================================================================
# 冲突检测器
# =============================================================================

class ConflictValidator:
    """
    三层冲突检测器

    - Type-I: 方法在跨数据集/设置下一致性差异（delta > 2.0%）
    - Type-II: 方法在同数据集内比较时性能差距（delta > 5.0%）
    - Type-III: 理论/假设互斥（检测论文间的逻辑矛盾）
    """

    def __init__(self, papers: List[Dict]):
        self.papers = papers
        self.paper_by_id = {p.get('paper_id', p.get('id', f'p{i}')): p for i, p in enumerate(papers)}
        self.type1_conflicts: List[Conflict] = []
        self.type2_conflicts: List[Conflict] = []
        self.type3_conflicts: List[Conflict] = []
        self.alignment: List[Dict] = []
        self.scores: Dict[str, float] = {}

    # =========================================================================
    # 主入口
    # =========================================================================

    def validate(self, top_k: int = 5) -> Dict:
        """执行完整验证流程"""
        self.alignment = self._align_evidence()
        self._detect_type1()
        self._detect_type2()
        self._detect_type3()
        self._compute_confidence()

        all_conflicts = (
            self.type1_conflicts +
            self.type2_conflicts +
            self.type3_conflicts
        )

        # 按 gap 降序
        all_conflicts.sort(key=lambda c: c.gap or 0, reverse=True)

        return {
            "total_papers": len(self.papers),
            "type1_conflicts": [c.to_dict() for c in self.type1_conflicts],
            "type2_conflicts": [c.to_dict() for c in self.type2_conflicts],
            "type3_conflicts": [c.to_dict() for c in self.type3_conflicts],
            "all_conflicts": [c.to_dict() for c in all_conflicts],
            "confidence_scores": self.scores,
            "alignment": self.alignment,
        }

    # =========================================================================
    # §3.1 证据对齐
    # =========================================================================

    def _align_evidence(self) -> List[Dict]:
        """将论文结果按 (dataset, metric) 对齐"""
        raw_results: Dict[Tuple, List[Dict]] = defaultdict(list)

        for paper in self.papers:
            pid = paper.get('paper_id', paper.get('id', 'unknown'))
            methods = paper.get('methods', [])
            datasets = paper.get('datasets', [])
            metrics_dict = paper.get('metrics', {})
            abstract = paper.get('abstract', '')
            method_primary = methods[0] if methods else 'Unknown'

            for dataset_raw in (datasets or []):
                dataset_norm = self._normalize_dataset(dataset_raw)
                for metric_raw, value in metrics_dict.items():
                    metric_norm = self._normalize_metric(metric_raw)
                    key = (dataset_norm, metric_norm)
                    row = {
                        "method": method_primary,
                        "paper_id": pid,
                        "value": value,
                        "dataset_raw": dataset_raw,
                        "metric_raw": metric_raw,
                    }
                    raw_results[key].append(row)

        alignment = []
        for (dataset, metric), rows in raw_results.items():
            alignment.append({
                "dataset": dataset,
                "metric": metric,
                "rows": rows,
            })
        alignment.sort(key=lambda x: (x["dataset"], x["metric"]))
        return alignment

    def _normalize_dataset(self, name: str) -> str:
        key = name.strip().lower()
        return DATASET_NORMALIZATION.get(key, name.strip())

    def _normalize_metric(self, name: str) -> str:
        key = name.strip().lower()
        return METRIC_NORMALIZATION.get(key, name.strip())

    # =========================================================================
    # §3.2 Type-I: 跨数据集一致性检测
    # =========================================================================

    def _detect_type1(self):
        """
        Type-I: 方法在跨数据集/设置下一致性差异（delta > 2.0%）

        如果同一方法在至少2个不同数据集上的性能差异超过阈值，
        标记为一致性冲突
        """
        # method -> {dataset -> [values]}
        method_dataset_scores: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

        for entry in self.alignment:
            for row in entry["rows"]:
                method = row["method"]
                dataset = entry["dataset"]
                value = row.get("value")
                if value is not None:
                    method_dataset_scores[method][dataset].append(float(value))

        for method, dataset_scores in method_dataset_scores.items():
            if len(dataset_scores) < 2:
                continue
            all_values = []
            for dataset, vals in dataset_scores.items():
                if vals:
                    all_values.extend(vals)

            if len(all_values) < 2:
                continue

            overall_mean = sum(all_values) / len(all_values)
            if overall_mean < 1e-6:
                continue

            max_val = max(all_values)
            min_val = min(all_values)
            max_diff = max_val - min_val

            if max_diff >= TYPE1_THRESHOLD:
                self.type1_conflicts.append(Conflict(
                    ctype="Type-I",
                    description=(
                        f"Method '{method}' shows inconsistent performance across datasets "
                        f"(range: {max_diff*100:.1f}%, threshold: {TYPE1_THRESHOLD*100:.1f}%)"
                    ),
                    parties=[method],
                    dataset="multi-dataset",
                    metric=None,
                    gap=max_diff,
                ))

    # =========================================================================
    # §3.2 Type-II: 同数据集内方法对比
    # =========================================================================

    def _detect_type2(self):
        """
        Type-II: 同数据集内方法性能对比

        如果同一数据集上至少2个方法进行比较，
        且最好和最差方法的性能差距超过阈值，标记为对比冲突
        """
        for entry in self.alignment:
            results = [r for r in entry["rows"] if r.get("value") is not None]
            if len(results) < 2:
                continue

            # 按 value 排序
            sorted_results = sorted(results, key=lambda x: float(x["value"]), reverse=True)
            best = sorted_results[0]
            worst = sorted_results[-1]
            best_val = float(best["value"])
            worst_val = float(worst["value"])
            gap = best_val - worst_val

            if gap >= TYPE2_THRESHOLD:
                self.type2_conflicts.append(Conflict(
                    ctype="Type-II",
                    description=(
                        f"Methods '{best['method']}' ({best_val*100:.1f}%) vs "
                        f"'{worst['method']}' ({worst_val*100:.1f}%) on "
                        f"{entry['dataset']} gap {gap*100:.1f}% > {TYPE2_THRESHOLD*100:.1f}%"
                    ),
                    parties=[best["paper_id"], worst["paper_id"], best["method"], worst["method"]],
                    dataset=entry["dataset"],
                    metric=entry["metric"],
                    gap=gap,
                ))

    # =========================================================================
    # §3.2 Type-III: 语义对立检测
    # =========================================================================

    def _detect_type3(self):
        """
        Type-III: 理论/假设互斥

        扫描两两论文的 conclusions 中是否存在方法论对立词
        """
        for i, pa in enumerate(self.papers):
            for j, pb in enumerate(self.papers):
                if i >= j:
                    continue

                text_a = " ".join(pa.get("conclusions", []))
                text_b = " ".join(pb.get("conclusions", []))
                if not text_a or not text_b:
                    continue

                text_a_lower = text_a.lower()
                text_b_lower = text_b.lower()

                for pos_word, neg_word in OPPOSITE_PAIRS:
                    in_a_pos = pos_word in text_a_lower
                    in_a_neg = neg_word in text_a_lower
                    in_b_pos = pos_word in text_b_lower
                    in_b_neg = neg_word in text_b_lower

                    if (in_a_pos and in_b_neg) or (in_a_neg and in_b_pos):
                        methods_a = set(m.lower() for m in pa.get("methods", []))
                        methods_b = set(m.lower() for m in pb.get("methods", []))
                        shared = methods_a & methods_b

                        if shared:
                            self.type3_conflicts.append(Conflict(
                                ctype="Type-III",
                                description=(
                                    f"Papers {pa.get('paper_id','?')} and {pb.get('paper_id','?')} "
                                    f"reach opposing conclusions on '{list(shared)[0]}' "
                                    f"({pos_word} vs {neg_word})"
                                ),
                                parties=[pa.get("paper_id", f"p{i}"), pb.get("paper_id", f"p{j}")],
                                dataset=None,
                                metric=None,
                                gap=None,
                            ))
                        break

    # =========================================================================
    # §3.3 置信度评分
    # =========================================================================

    def _compute_confidence(self):
        """计算每篇论文的置信度（Eq.3 proxy）"""
        self.scores = {}

        max_citation = max((p.get("citations", 0) for p in self.papers), default=1)
        max_year = max((p.get("year", 2026) for p in self.papers), default=2026)
        min_year = min((p.get("year", 2000) for p in self.papers), default=2000)
        year_range = max(max_year - min_year, 1)

        for paper in self.papers:
            pid = paper.get("paper_id", paper.get("id", "unknown"))
            citations = paper.get("citations", 0)
            year = paper.get("year", 2024)

            # Citation score (log-normalized)
            cite_score = math.log(1 + citations) / math.log(1 + max_citation + 1)

            # Recency score (exponential decay)
            recency_score = compute_recency_score(year, max_year)

            # Consistency score (simplified: if paper has results on multiple datasets, higher consistency)
            consistency_score = 1.0
            paper_datasets = paper.get("datasets", [])
            if len(paper_datasets) >= 2:
                consistency_score = 0.8
            elif len(paper_datasets) == 1:
                consistency_score = 0.6

            # KG score (if has kg_entities, higher)
            kg_score = 1.0 if paper.get("kg_entities") else 0.5

            # Weighted sum
            total = (
                WEIGHT_CITATION * cite_score +
                WEIGHT_RECENCY * recency_score +
                WEIGHT_CONSISTENCY * consistency_score +
                WEIGHT_KG * kg_score
            )

            self.scores[pid] = round(min(1.0, max(0.0, total)), 4)


# =============================================================================
# 评估指标计算
# =============================================================================

def compute_precision_recall(
    detected: List[Conflict],
    ground_truth: List[Dict],
    k: int = None
) -> Dict:
    """计算 Precision@K, Recall@K, F1@K"""
    if k is not None:
        detected = detected[:k]

    detected_set = set()
    for c in detected:
        key = (c.ctype, tuple(sorted(c.parties)))
        detected_set.add(key)

    gt_set = set()
    for gt in ground_truth:
        key = (gt["type"], tuple(sorted(gt["parties"])))
        gt_set.add(key)

    tp = len(detected_set & gt_set)
    fp = len(detected_set - gt_set)
    fn = len(gt_set - detected_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


# =============================================================================
# CLI 入口
# =============================================================================

def load_papers(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "papers" in data:
            return data["papers"]
        return [data]
    return []


def main():
    parser = argparse.ArgumentParser(description="Conflict Validator Agent")
    parser.add_argument("--input", required=True, help="Input JSON file with papers")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print(f"[ConflictValidator] Loading papers from {args.input}")
    papers = load_papers(args.input)
    print(f"[ConflictValidator] Loaded {len(papers)} papers")

    validator = ConflictValidator(papers)
    result = validator.validate()

    # Ground truth evaluation if available
    gt_path = Path(args.input).parent / "ground_truth_conflicts.json"
    if gt_path.exists():
        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)
        print(f"[ConflictValidator] Ground truth loaded: {len(ground_truth)} conflicts")

        all_conflicts = [
            c for c in result["all_conflicts"]
        ]

        print(f"\n[Evaluation Results]")
        for k in [5, 10, 20]:
            metrics = compute_precision_recall(
                [Conflict(**c) for c in all_conflicts],
                ground_truth,
                k=k if k <= len(all_conflicts) else None
            )
            print(f"  @{k}: Precision={metrics['precision']:.4f} "
                  f"Recall={metrics['recall']:.4f} F1={metrics['f1']:.4f}")

    # Conflict summary
    type_counts = {"Type-I": 0, "Type-II": 0, "Type-III": 0}
    for c in result["all_conflicts"]:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1

    print(f"\n[Conflict Summary]")
    print(f"  Type-I: {type_counts.get('Type-I', 0)}")
    print(f"  Type-II: {type_counts.get('Type-II', 0)}")
    print(f"  Type-III: {type_counts.get('Type-III', 0)}")

    if args.verbose:
        print(f"\n[Top Conflicts]")
        for c in result["all_conflicts"][:10]:
            print(f"  [{c['type']}] {c['description'][:80]}")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[ConflictValidator] Results saved to {args.output}")


if __name__ == "__main__":
    main()
