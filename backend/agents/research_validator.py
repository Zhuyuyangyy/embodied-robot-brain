"""
Research Validator Agent
========================
科研验证Agent：证据对齐 → 冲突检测 → 可信度评估 → 综合结论

核心设计原则：
- 论文意识：每个算法模块注释对应的论文公式编号
- 可独立调用：Aligner/Conflict/Scorer/Synthesis 均暴露为 public API
- 可验证性闭环：每一步输出均可追溯证据来源

论文对应：
  - Evidence Aligner    → Section 3.1 (Evidence Extraction & Alignment)
  - Conflict Detector   → Section 3.2 (Conflict Detection Taxonomy)
  - Confidence Scorer   → Section 3.3 (Eq.1 - Eq.4)
  - Synthesis           → Section 3.4 (Evidence-Weighted Conclusion Generation)
"""

import asyncio
import math
import re
import hashlib
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

# =============================================================================
# 内部数据类型
# =============================================================================

class Conflict:
    """冲突记录"""
    def __init__(
        self,
        ctype: str,          # "Type-I" | "Type-II" | "Type-III"
        description: str,
        parties: List[str],  # paper_ids
        dataset: Optional[str] = None,
        metric: Optional[str] = None,
        gap: Optional[float] = None,
    ):
        self.type = ctype
        self.description = description
        self.parties = parties
        self.dataset = dataset
        self.metric = metric
        self.gap = gap

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "description": self.description,
            "parties": self.parties,
            "dataset": self.dataset,
            "metric": self.metric,
            "gap": self.gap,
        }


# =============================================================================
# Research Validator Agent
# =============================================================================

class ResearchValidatorAgent:
    """
    科研验证Agent主类

    工作流：
        validate() → align_evidence() → detect_conflicts()
                   → compute_confidence() → synthesize()

    集成方式（Orchestrator）：
        dispatch_task("literature_validate", {"papers": papers})
    """

    # ---------- 全局超参数（可配置） ----------
    CONSISTENCY_THRESHOLD = 2.0   # 方法一致性判断阈值（%）
    CONFLICT_GAP_THRESHOLD = 5.0  # Type-II 冲突判断阈值（%）
    RECENCY_DECAY_HALF_LIFE = 5    # 论文半衰期（年）

    # 评分权重（对应论文 Eq.3）
    WEIGHT_CITATION  = 0.25
    WEIGHT_RECENCY   = 0.20
    WEIGHT_CONSIST   = 0.30
    WEIGHT_KG        = 0.25

    def __init__(self, agent_id: str, kg: Optional[Any] = None):
        self.agent_id = agent_id
        self.kg = kg
        self.state = "idle"
        self.history: List[Dict] = []

    # =========================================================================
    # 主入口
    # =========================================================================

    async def validate(
        self,
        papers: List[Dict],
        user_query: str = "",
        top_k: int = 5
    ) -> Dict:
        """
        主验证流程（对应论文 Algorithm 1）

        Step 1: Evidence Alignment
        Step 2: Conflict Detection
        Step 3: Confidence Scoring
        Step 4: Synthesis

        Args:
            papers: Literature Agent返回的论文列表
            user_query: 用户原始查询（用于识别知识空白）
            top_k: 最终返回top K可信论文

        Returns:
            Dict含: summary / stable_conclusions / conflicts /
                   knowledge_gaps / top_papers / scores / alignment
        """
        self.state = "running"

        # Step 1: 证据对齐
        alignment = await self.align_evidence(papers)

        # Step 2: 冲突检测
        conflicts = await self.detect_conflicts(papers, alignment)

        # Step 3: 可信度评分
        scores = await self.compute_confidence(papers, alignment)

        # Step 4: 综合结论
        synthesis = await self.synthesize(
            papers, alignment, conflicts, scores, user_query
        )

        result = {
            **synthesis,
            "scores": scores,
            "alignment": [a for a in alignment if a["rows"]],  # 只保留有数据的行
        }

        self.state = "ready"
        await self._record("validate", result)
        return result

    # =========================================================================
    # §3.1 Evidence Aligner（证据对齐）
    # =========================================================================

    # 数据集名称归一化映射表（部分示例，完整表可扩展）
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

    # 指标归一化
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
        "map@": "mAP",
        "bleu": "BLEU",
        "rouge": "ROUGE",
        "perplexity": "Perplexity",
        "ppl": "Perplexity",
    }

    async def align_evidence(self, papers: List[Dict]) -> List[Dict]:
        """
        证据对齐（对应论文 Section 3.1）

        处理流程：
          1. 从每篇论文抽取 method / dataset / metric / result 字段
          2. 归一化 dataset 和 metric 名称
          3. 按 (dataset, metric) 分组建对齐矩阵

        Returns:
            List[Dict]: 对齐表，每个元素对应一个 (dataset, metric) 组合
                       含所有测过该组合的论文方法及结果
        """
        # Step 1: 抽取字段
        extracted = [self._extract_fields(p) for p in papers]

        # Step 2: 构建原始结果表
        raw_results: Dict[tuple, List[Dict]] = defaultdict(list)
        for paper, ex in zip(papers, extracted):
            for dataset_raw in ex["datasets"]:
                dataset_norm = self._normalize_dataset(dataset_raw)
                for metric_raw in ex["metrics"]:
                    metric_norm = self._normalize_metric(metric_raw)
                    key = (dataset_norm, metric_norm)
                    row = {
                        "method":  ex["method_primary"],
                        "paper_id": paper["paper_id"],
                        "value":    ex["results"].get(metric_raw) or
                                    ex["results"].get(metric_norm),
                        "note":     f"{dataset_raw} → {dataset_norm}, "
                                    f"{metric_raw} → {metric_norm}",
                    }
                    raw_results[key].append(row)

        # Step 3: 打包为对齐表
        alignment = []
        for (dataset, metric), rows in raw_results.items():
            alignment.append({
                "dataset": dataset,
                "metric":  metric,
                "rows":    rows,
            })

        # 按数据集+指标字母序排列
        alignment.sort(key=lambda x: (x["dataset"], x["metric"]))
        return alignment

    def _extract_fields(self, paper: Dict) -> Dict:
        """
        从论文字典中抽取结构化字段（对应论文 Eq.2）

        用规则+正则抽取 method / dataset / metric / result。
        生产环境应替换为LLM调用或PDF解析器。
        """
        # 优先取预标注字段，否则从abstract推断
        abstract = paper.get("abstract", "")

        methods  = paper.get("methods", [])  or self._extract_methods(abstract)
        datasets = paper.get("datasets", [])  or self._extract_datasets(abstract)
        metrics  = paper.get("metrics", [])  or self._extract_metrics(abstract)
        results  = paper.get("results", {})   or {}

        return {
            "method_primary": methods[0] if methods else "Unknown",
            "methods":  methods,
            "datasets": datasets,
            "metrics":  metrics,
            "results":  results,
        }

    def _extract_methods(self, text: str) -> List[str]:
        """抽取方法名（正则 + 启发式规则）"""
        patterns = [
            r"(?:method|approach|model|framework)\s+[:.]?\s*([A-Z][\w\-]+)",
            r"\b(ResNet|ViT|BERT|GPT|CLIP|CoT|Chain-of-Thought|"
            r"T5|LSTM|CNN|RNN|GNN|Transformer|LLM)\b",
        ]
        found = []
        for pat in patterns:
            found.extend(re.findall(pat, text, re.IGNORECASE))
        # 去重保留顺序
        seen = set()
        unique = []
        for m in found:
            m_clean = m.strip()
            if m_clean.lower() not in seen:
                seen.add(m_clean.lower())
                unique.append(m_clean)
        return unique[:5]  # 最多取5个

    def _extract_datasets(self, text: str) -> List[str]:
        """抽取数据集名"""
        patterns = [
            r"\b(CIFAR-?10|CIFAR-?100|ImageNet|ILSVRC|MNIST|COCO|"
            r"WikiText|Wikipedia|SQuAD|MMLU|BIG-?bench|PubMed|"
            r"GLUE|SuperGLUE| Alpaca|Wilds|OGB)\b",
        ]
        found = []
        for pat in patterns:
            found.extend(re.findall(pat, text, re.IGNORECASE))
        return list(dict.fromkeys(found))[:5]

    def _extract_metrics(self, text: str) -> List[str]:
        """抽取评估指标"""
        patterns = [
            r"\b(Accuracy|Precision|Recall|F1[ -]?Score?|mAP|BLEU|"
            r"ROUGE|Perplexity|BERTScore|EM)\b",
        ]
        found = []
        for pat in patterns:
            found.extend(re.findall(pat, text, re.IGNORECASE))
        return list(dict.fromkeys(found))[:5]

    def _normalize_dataset(self, name: str) -> str:
        """数据集名称归一化"""
        key = name.strip().lower()
        return self.DATASET_NORMALIZATION.get(key, name.strip())

    def _normalize_metric(self, name: str) -> str:
        """指标名称归一化"""
        key = name.strip().lower()
        return self.METRIC_NORMALIZATION.get(key, name.strip())

    # =========================================================================
    # §3.2 Conflict Detector（冲突检测）
    # =========================================================================

    # 语义对立词对（用于Type-III检测）
    OPPOSITE_PAIRS = [
        ("outperforms",   "worse than"),
        ("significantly improves", "no significant"),
        ("effective",     "ineffective"),
        ("consistent",    "contrary"),
        ("supports",      "refutes"),
        ("improves",      "degrades"),
        ("better",         "worse"),
        ("superior",      "inferior"),
    ]

    async def detect_conflicts(
        self, papers: List[Dict], alignment: List[Dict]
    ) -> List[Dict]:
        """
        冲突检测（对应论文 Section 3.2）

        三类冲突：
          Type-I  : 方法级直接矛盾（同一方法+同一数据集+同一指标，结论相反）
          Type-II : 数据集依赖型不一致（同一方法在不同数据集结论不同）
          Type-III: 语义对立（conclusions中存在方法论对立词）

        Returns:
            List[Conflict]: 按严重程度排序的冲突列表
        """
        conflicts: List[Conflict] = []

        # Type-I & Type-II: 结构化冲突检测
        for entry in alignment:
            results = [r for r in entry["rows"] if r["value"] is not None]
            if len(results) < 2:
                continue

            # 按方法分组
            by_method: Dict[str, List[Dict]] = defaultdict(list)
            for r in results:
                by_method[r["method"]].append(r)

            methods = list(by_method.keys())

            # Type-II: 同一方法在不同数据集表现不一致
            if len(results) >= 2:
                sorted_results = sorted(results, key=lambda x: x["value"], reverse=True)
                best  = sorted_results[0]
                worst = sorted_results[-1]
                gap   = best["value"] - worst["value"]

                if gap >= self.CONFLICT_GAP_THRESHOLD:
                    # 判断是Type-I还是Type-II
                    if best["method"] == worst["method"]:
                        ctype = "Type-I"
                        desc  = (f"方法 {best['method']} 在 {entry['dataset']} 上 "
                                 f"最优 {best['value']}% vs 最差 {worst['value']}%，"
                                 f"差距 {gap:.1f}%")
                    else:
                        ctype = "Type-II"
                        desc  = (f"方法 {best['method']}({best['value']}%) vs "
                                 f"{worst['method']}({worst['value']}%) 在 "
                                 f"{entry['dataset']} 上差距 {gap:.1f}%")

                    conflicts.append(Conflict(
                        ctype=ctype,
                        description=desc,
                        parties=[best["paper_id"], worst["paper_id"]],
                        dataset=entry["dataset"],
                        metric=entry["metric"],
                        gap=gap,
                    ))

            # Type-II扩展：同一方法跨数据集对比
            for method, method_results in by_method.items():
                if len(method_results) < 2:
                    continue
                vals = [r["value"] for r in method_results]
                if max(vals) - min(vals) >= self.CONFLICT_GAP_THRESHOLD:
                    paper_ids = [r["paper_id"] for r in method_results]
                    datasets  = [entry["dataset"]] * len(method_results)
                    conflicts.append(Conflict(
                        ctype="Type-II",
                        description=(f"方法 {method} 在多个数据集上表现差异显著 "
                                     f"(range: {min(vals):.1f}% ~ {max(vals):.1f}%)"),
                        parties=paper_ids,
                        dataset=entry["dataset"],
                        metric=entry["metric"],
                        gap=max(vals) - min(vals),
                    ))

        # Type-III: 语义对立检测
        semantic_conflicts = self._detect_semantic_conflicts(papers)
        conflicts.extend(semantic_conflicts)

        # 按 gap 降序排列（gap越大冲突越严重）
        conflicts.sort(key=lambda c: c.gap or 0, reverse=True)

        return [c.to_dict() for c in conflicts]

    def _detect_semantic_conflicts(self, papers: List[Dict]) -> List[Conflict]:
        """Type-III: 扫描conclusions中的方法论对立词"""
        conflicts = []
        for i, pa in enumerate(papers):
            for j, pb in enumerate(papers):
                if i >= j:
                    continue
                text_a = " ".join(pa.get("conclusions", []))
                text_b = " ".join(pb.get("conclusions", []))
                text_a_lower = text_a.lower()
                text_b_lower = text_b.lower()

                for pos_word, neg_word in self.OPPOSITE_PAIRS:
                    in_a_pos = pos_word in text_a_lower
                    in_a_neg = neg_word in text_a_lower
                    in_b_pos = pos_word in text_b_lower
                    in_b_neg = neg_word in text_b_lower

                    # 如果两篇论文conclusions中出现了对立判断
                    if (in_a_pos and in_b_neg) or (in_a_neg and in_b_pos):
                        # 进一步判断是否涉及同一方法
                        methods_a = set(m.lower() for m in pa.get("methods", []))
                        methods_b = set(m.lower() for m in pb.get("methods", []))
                        shared    = methods_a & methods_b

                        if shared:
                            conflicts.append(Conflict(
                                ctype="Type-III",
                                description=(f"论文 {pa['paper_id']} 与 "
                                             f"{pb['paper_id']} 对方法 "
                                             f"{list(shared)[0]} 得出语义对立结论 "
                                             f"({pos_word} vs {neg_word})"),
                                parties=[pa["paper_id"], pb["paper_id"]],
                            ))
                        break  # 一对论文只报一次Type-III
        return conflicts

    # =========================================================================
    # §3.3 Confidence Scorer（可信度评分）
    # =========================================================================

    async def compute_confidence(
        self, papers: List[Dict], alignment: List[Dict]
    ) -> Dict[str, float]:
        """
        可信度评分（对应论文 Eq.1 - Eq.4）

        公式（论文 Eq.1）：
            Score(p) = Σ_{i} w_i · f_i(x_i)

        其中：
            f_citation(x)  = log(1 + x)                      （论文 Eq.2）
            f_recency(x)   = exp(-Δyear / λ)                （论文 Eq.2）
            f_consist(x)   = consistency(p, alignment)       （论文 Eq.2）
            f_kg(x)        = log(1 + KG_support(p))          （论文 Eq.2）

        权重（论文 Eq.3）：
            w_citation=0.25, w_recency=0.20, w_consist=0.30, w_kg=0.25

        Returns:
            Dict[str, float]: paper_id → score [0, 1]
        """
        scores: Dict[str, float] = {}
        paper_by_id = {p["paper_id"]: p for p in papers}

        # 全局最大值（用于min-max归一化）
        max_citation = max((p.get("citations", 0) for p in papers), default=1)
        max_year     = max((p.get("year", 2024) for p in papers), default=2024)
        min_year     = min((p.get("year", 2000) for p in papers), default=2000)
        year_range   = max(max_year - min_year, 1)

        # 预计算每篇论文的consistency分数（论文 Eq.2 第3项）
        consist_scores = {
            p["paper_id"]: self._compute_consistency(p, papers, alignment)
            for p in papers
        }
        max_consist = max(consist_scores.values()) or 1.0

        # 预计算KG Support（论文 Eq.2 第4项）
        kg_scores = {
            p["paper_id"]: await self._compute_kg_support(p)
            for p in papers
        }
        max_kg = max(kg_scores.values()) or 1.0

        for paper in papers:
            pid     = paper["paper_id"]
            cite    = paper.get("citations", 0)
            year    = paper.get("year", 2024)

            # f_citation: 对数归一化（论文 Eq.2）
            f_cite = math.log(1 + cite) / math.log(1 + max_citation)

            # f_recency: 指数衰减，half-life=5年（论文 Eq.2）
            # Δyear = 0 → f=1; Δyear=5 → f=0.5
            delta_year = max_year - year
            f_recency  = math.exp(-delta_year / (self.RECENCY_DECAY_HALF_LIFE
                               * math.log(2)))  # 使 half-life 生效

            # f_consistency: 归一化一致性分数（论文 Eq.2）
            f_consist = consist_scores.get(pid, 0.5) / max_consist

            # f_kg: 归一化KG支持度（论文 Eq.2）
            f_kg = kg_scores.get(pid, 0) / max_kg if max_kg > 0 else 0.0

            # 加权求和（论文 Eq.1）
            raw = (
                self.WEIGHT_CITATION  * f_cite
              + self.WEIGHT_RECENCY   * f_recency
              + self.WEIGHT_CONSIST   * f_consist
              + self.WEIGHT_KG         * f_kg
            )

            # clamp to [0, 1]
            scores[pid] = max(0.0, min(1.0, raw))

        return scores

    def _compute_consistency(
        self, paper: Dict, all_papers: List[Dict], alignment: List[Dict]
    ) -> float:
        """
        计算论文一致性分数（论文 Eq.2 第3项的定义）

        一致性 = 该论文结论与peer论文结论方向一致的比例。
        一致：差距 < CONSISTENCY_THRESHOLD
        """
        pid = paper["paper_id"]
        paper_methods = set(paper.get("methods", []))

        if not paper_methods:
            return 0.5

        # 找使用过相同方法的peer论文
        peers = [
            p for p in all_papers
            if p["paper_id"] != pid
            and set(p.get("methods", [])) & paper_methods
        ]
        if not peers:
            return 0.5

        # 在对齐表中比较结果方向
        consistent_count = 0
        total_comparisons = 0

        for entry in alignment:
            p_result = next(
                (r for r in entry["rows"] if r["paper_id"] == pid and r["value"] is not None),
                None
            )
            if not p_result:
                continue

            for peer in peers:
                peer_result = next(
                    (r for r in entry["rows"]
                     if r["paper_id"] == peer["paper_id"] and r["value"] is not None),
                    None
                )
                if not peer_result:
                    continue

                diff = abs(p_result["value"] - peer_result["value"])
                total_comparisons += 1
                if diff < self.CONSISTENCY_THRESHOLD:
                    consistent_count += 1

        if total_comparisons == 0:
            return 0.5
        return consistent_count / total_comparisons

    async def _compute_kg_support(self, paper: Dict) -> float:
        """
        计算论文在知识图谱中的支持度（论文 Eq.2 第4项）

        KG Support = 该论文方法节点被其他论文节点引用的总次数
        """
        if self.kg is None:
            return 0.0

        pid = paper["paper_id"]
        methods = paper.get("methods", [])
        if not methods:
            return 0.0

        total = 0
        for method in methods:
            # 查询KG中该方法相关论文（取前5作为近似引用计数）
            hits = await self.kg.query_by_keyword(method, limit=5)
            for hit in hits:
                if hit.get("id") != pid:
                    total += hit.get("citations", 0)

        return math.log(1 + total)

    # =========================================================================
    # §3.4 Synthesis（综合结论生成）
    # =========================================================================

    async def synthesize(
        self,
        papers: List[Dict],
        alignment: List[Dict],
        conflicts: List[Dict],
        scores: Dict[str, float],
        user_query: str = "",
    ) -> Dict:
        """
        综合结论生成（对应论文 Section 3.4）

        输出三类结论：
          stable_conclusions : 跨论文一致性结论（带置信传播分数）
          conflicts          : 有冲突的结论（带冲突解释）
          knowledge_gaps     : 当前论文集合未覆盖的知识空白

        置信传播（对应论文 Eq.4）：
            Conclusion_Confidence = Σ (paper_score_i × support_flag_i) / N
        """
        stable = []
        paper_by_id = {p["paper_id"]: p for p in papers}

        for entry in alignment:
            results = [r for r in entry["rows"] if r["value"] is not None]
            if len(results) < 1:
                continue

            # 检查是否存在相关冲突
            entry_conflicts = [
                c for c in conflicts
                if c.get("dataset") == entry["dataset"]
                and c.get("metric") == entry["metric"]
                and c.get("type") in ("Type-I", "Type-II")
            ]

            if entry_conflicts:
                continue  # 有冲突的留在 conflicts 中，不进 stable

            # 无冲突 → 提取稳定结论
            results_sorted = sorted(results, key=lambda x: x["value"], reverse=True)
            best = results_sorted[0]
            avg  = sum(r["value"] for r in results) / len(results)

            # 置信传播分数（论文 Eq.4）
            supporting_scores = [scores.get(r["paper_id"], 0) for r in results]
            conclusion_confidence = sum(supporting_scores) / len(supporting_scores)

            stable.append({
                "statement": (
                    f"方法 {best['method']} 在 {entry['dataset']} 数据集上 "
                    f"平均达到 {avg:.1f}%，最优 {best['value']}%"
                ),
                "supporting_papers": [r["paper_id"] for r in results],
                "supporting_titles": [
                    paper_by_id[r["paper_id"]].get("title", "")
                    for r in results if r["paper_id"] in paper_by_id
                ],
                "dataset": entry["dataset"],
                "metric":  entry["metric"],
                "conclusion_confidence": conclusion_confidence,  # 论文 Eq.4
            })

        # 整理冲突输出
        conflict_summaries = []
        for c in conflicts:
            conflict_summaries.append({
                "statement":     c["description"],
                "parties":       c["parties"],
                "conflict_type": c["type"],
                "note":          self._explain_conflict(c),
                "gap":           c.get("gap"),
            })

        # 识别知识空白
        gaps = self._identify_gaps(papers, alignment, user_query)

        # 生成一句话摘要
        summary = self._generate_summary(stable, conflict_summaries)

        # Top-K 论文
        sorted_papers = sorted(
            [
                {
                    "paper_id": p["paper_id"],
                    "title":    p.get("title", ""),
                    "year":     p.get("year", 0),
                    "score":    scores.get(p["paper_id"], 0),
                    "methods":  p.get("methods", []),
                }
                for p in papers
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        return {
            "summary":              summary,
            "stable_conclusions":  stable,
            "conflicts":           conflict_summaries,
            "knowledge_gaps":       gaps,
            "top_papers":          sorted_papers[:5],
        }

    def _explain_conflict(self, conflict: Dict) -> str:
        """为冲突生成人类可读的解释"""
        ctype = conflict.get("type", "")
        if ctype == "Type-I":
            return (
                "直接矛盾：相同方法在相同数据集上得出相反结论，"
                "可能源于实验设置差异（随机种子、评估协议、超参）"
            )
        elif ctype == "Type-II":
            return (
                "条件依赖：方法性能随数据集变化显著，"
                "表明该方法的泛化能力存在局限，需结合具体应用场景评估"
            )
        elif ctype == "Type-III":
            return (
                "语义对立：论文结论在方法论层面存在对立判断，"
                "需进一步核查实验条件是否可比"
            )
        return "未知类型冲突"

    def _identify_gaps(
        self, papers: List[Dict], alignment: List[Dict], user_query: str
    ) -> List[Dict]:
        """识别当前论文集合未覆盖的知识空白"""
        gaps = []
        all_datasets = set()
        all_methods  = set()

        for entry in alignment:
            all_datasets.add(entry["dataset"])
            for row in entry["rows"]:
                all_methods.add(row["method"])

        # 启发式：某方法只在1个数据集上测过 → 泛化性空白
        method_datasets: Dict[str, set] = defaultdict(set)
        for entry in alignment:
            for row in entry["rows"]:
                method_datasets[row["method"]].add(entry["dataset"])

        for method, dset in method_datasets.items():
            if len(dset) == 1:
                gaps.append({
                    "gap":               f"方法 {method} 仅在 {list(dset)[0]} 上验证",
                    "suggested_approach": f"建议在 {'/'.join(all_datasets - dset)} 等数据集上补充实验",
                })

        # 如果用户query中的实体未被任何论文覆盖
        if user_query:
            query_tokens = set(re.findall(r"[a-zA-Z0-9]{3,}", user_query.lower()))
            covered = set()
            for p in papers:
                p_tokens = set(re.findall(
                    r"[a-zA-Z0-9]{3,}",
                    (p.get("title", "") + " " + p.get("abstract", "")).lower()
                ))
                covered |= (p_tokens & query_tokens)
            uncovered = query_tokens - covered
            if uncovered:
                gaps.append({
                    "gap":               f"查询关键词 {uncovered} 在当前文献集中未被充分覆盖",
                    "suggested_approach": "建议扩大检索范围或进行专项文献补充检索",
                })

        return gaps[:5]

    def _generate_summary(
        self, stable: List[Dict], conflicts: List[Dict]
    ) -> str:
        """生成一句话摘要"""
        n_stable  = len(stable)
        n_conflict = len(conflicts)
        if n_stable > 0 and n_conflict == 0:
            return (f"共找到 {n_stable} 条跨文献一致结论，未发现显著冲突。"
                    f"结论可信度高。")
        elif n_stable > 0 and n_conflict > 0:
            return (f"共找到 {n_stable} 条一致结论，但存在 {n_conflict} 条冲突需要关注。"
                    f"请查阅冲突详情。")
        elif n_conflict > 0:
            return (f"当前文献集中存在 {n_conflict} 条冲突，"
                    f"建议进一步核查实验条件和数据集差异。")
        else:
            return "文献证据不足，无法形成稳定结论。"

    # =========================================================================
    # 工具方法
    # =========================================================================

    async def _record(self, action: str, data: Any):
        """记录历史"""
        self.history.append({
            "action":    action,
            "timestamp": datetime.now().isoformat(),
            "summary":    str(data)[:200],
        })
        if len(self.history) > 100:
            self.history = self.history[-100:]

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "agent_id": self.agent_id,
            "state":    self.state,
            "history":  len(self.history),
        }
