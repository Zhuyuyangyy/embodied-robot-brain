"""
PhysicsGate单元测试（更新版）
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from agents.physics_gate import (
    PhysicsGate, GateDecision, TCMConstraintLibrary,
    check_tcm_conflict, compute_error_function, G,
    TCM_HERB_PAIRS, KNOWN_CONFLICTS,
    compute_metrics_with_ci,
)


class TestTCMConstraintLibrary:
    """TCM约束库测试"""

    def test_init(self):
        """测试初始化"""
        lib = TCMConstraintLibrary()
        assert lib is not None
        assert hasattr(lib, 'constraint_pairs')

    def test_load_constraints(self):
        """测试加载约束"""
        lib = TCMConstraintLibrary()
        # 验证约束已加载
        assert len(lib.constraint_pairs) > 0

    def test_get_constraint_18contra(self):
        """测试获取十八反约束"""
        lib = TCMConstraintLibrary()
        # 测试获取存在的约束
        constraint = lib.get_constraint("甘草", "甘遂")
        assert constraint is not None
        assert constraint['conflict_type'] == '十八反'
        assert constraint['error_value'] == 1.0

    def test_get_constraint_19fear(self):
        """测试获取十九畏约束"""
        lib = TCMConstraintLibrary()
        constraint = lib.get_constraint("人参", "莱菔子")
        assert constraint is not None
        assert constraint['conflict_type'] == '十九畏'
        assert constraint['error_value'] == 0.7

    def test_get_nonexistent_constraint(self):
        """测试获取不存在的约束"""
        lib = TCMConstraintLibrary()
        constraint = lib.get_constraint("人参", "枸杞")
        assert constraint is None

    def test_constraint_error_values(self):
        """测试约束错误值"""
        lib = TCMConstraintLibrary()
        # 测试十八反
        constraint_18 = lib.get_constraint("甘草", "甘遂")
        assert constraint_18['error_value'] == 1.0

        # 测试十九畏
        constraint_19 = lib.get_constraint("硫黄", "朴硝")
        assert constraint_19['error_value'] == 0.7

    def test_constraint_types(self):
        """测试约束类型"""
        lib = TCMConstraintLibrary()
        # 验证不同的约束类型
        types = set()
        for pair in lib.constraint_pairs:
            types.add(pair['conflict_type'])

        assert '十八反' in types
        assert '十九畏' in types
        assert '药理冲突' in types


class TestPhysicsGateCore:
    """PhysicsGate核心函数测试"""

    def test_compute_error_function(self):
        """测试误差函数计算"""
        # 无冲突
        assert compute_error_function([]) == 0.0
        assert compute_error_function(None) == 0.0

        # 致命冲突 E=1.0
        error = compute_error_function([{"ctype": "TYPE_I", "gap": 1.0}])
        assert error == 1.0

        # 药理冲突 E=0.85
        error = compute_error_function([{"ctype": "TYPE_II", "gap": 0.85}])
        assert error == 0.85

        # 取最大值
        error = compute_error_function([
            {"ctype": "TYPE_III", "gap": 0.4},
            {"ctype": "TYPE_I", "gap": 1.0},
        ])
        assert error == 1.0

    def test_G_function_fatal(self):
        """测试G函数致命冲突（HARD_REJECT）"""
        agent_state = {"iteration": 0}
        conflict_knowledge = [{"ctype": "TYPE_I", "gap": 1.0}]

        # 任何delta下都应HARD_REJECT
        assert G(agent_state, conflict_knowledge, delta=0.05) == GateDecision.HARD_REJECT
        assert G(agent_state, conflict_knowledge, delta=0.50) == GateDecision.HARD_REJECT
        assert G(agent_state, conflict_knowledge, delta=0.99) == GateDecision.HARD_REJECT

    def test_G_function_soft_reject(self):
        """测试G函数软拒绝"""
        agent_state = {"iteration": 0}
        conflict_knowledge = [{"ctype": "TYPE_II", "gap": 0.85}]

        # E=0.85 >= delta=0.05 应SOFT_REJECT
        assert G(agent_state, conflict_knowledge, delta=0.05) == GateDecision.SOFT_REJECT

    def test_G_function_pass(self):
        """测试G函数通过"""
        agent_state = {"iteration": 0}
        # 无冲突
        assert G(agent_state, [], delta=0.05) == GateDecision.PASS

        # 低误差 (E=0.03 < delta=0.05)
        conflict_knowledge = [{"ctype": "TYPE_III", "gap": 0.03}]
        assert G(agent_state, conflict_knowledge, delta=0.05) == GateDecision.PASS

    def test_G_dynamic_delta(self):
        """测试G函数动态delta"""
        # retry < 3: delta_strict
        for i in range(3):
            agent_state = {"iteration": i}
            # E=0.08 >= delta_strict=0.05, should SOFT_REJECT
            conflict_knowledge = [{"ctype": "TYPE_II", "gap": 0.08}]
            result = G(agent_state, conflict_knowledge, delta=0.05, delta_relaxed=0.10)
            assert result == GateDecision.SOFT_REJECT  # 0.08 >= 0.05 (strict)

        # retry >= 3: delta_relaxed
        agent_state = {"iteration": 3}
        # E=0.08 < delta_relaxed=0.10, should PASS
        result = G(agent_state, conflict_knowledge, delta=0.05, delta_relaxed=0.10)
        assert result == GateDecision.PASS  # 0.08 < 0.10 (relaxed)


class TestPhysicsGate:
    """PhysicsGate类测试"""

    def test_init(self):
        """测试初始化"""
        gate = PhysicsGate()
        assert gate is not None
        assert gate.delta == 0.05
        assert gate.delta_relaxed == 0.10
        assert gate.retry_threshold == 3

    def test_custom_config(self):
        """测试自定义配置"""
        gate = PhysicsGate(delta=0.03, delta_relaxed=0.08, retry_threshold=5)
        assert gate.delta == 0.03
        assert gate.delta_relaxed == 0.08
        assert gate.retry_threshold == 5

    def test_decide_pass(self):
        """测试门控决策-通过"""
        gate = PhysicsGate()
        agent_state = {"iteration": 0, "confidence": 0.9}
        decision = gate.decide(agent_state, [])
        assert decision == GateDecision.PASS

    def test_decide_hard_reject(self):
        """测试门控决策-硬拒绝"""
        gate = PhysicsGate()
        agent_state = {"iteration": 0}
        conflict_knowledge = [{"ctype": "TYPE_I", "gap": 1.0}]
        decision = gate.decide(agent_state, conflict_knowledge)
        assert decision == GateDecision.HARD_REJECT

    def test_decide_soft_reject(self):
        """测试门控决策-软拒绝"""
        gate = PhysicsGate()
        agent_state = {"iteration": 0}
        conflict_knowledge = [{"ctype": "TYPE_II", "gap": 0.85}]
        decision = gate.decide(agent_state, conflict_knowledge)
        assert decision == GateDecision.SOFT_REJECT

    def test_safety_guarantee(self):
        """测试安全保证：致命冲突总是HARD_REJECT"""
        gate = PhysicsGate()
        # 测试不同delta配置
        for delta in [0.01, 0.05, 0.10, 0.20, 0.50]:
            gate.reset()
            agent_state = {"iteration": 0}
            conflict_knowledge = [{"ctype": "TYPE_I", "gap": 1.0}]
            decision = gate.decide(agent_state, conflict_knowledge)
            assert decision == GateDecision.HARD_REJECT, f"Failed at delta={delta}"

    def test_stats(self):
        """测试统计信息"""
        gate = PhysicsGate()
        stats = gate.stats()
        assert "total_calls" in stats
        assert "pass_count" in stats
        assert "soft_reject_count" in stats
        assert "hard_reject_count" in stats

    def test_latency(self):
        """测试延迟"""
        gate = PhysicsGate()
        import time
        start = time.time()
        for _ in range(1000):
            gate.decide({"iteration": 0}, [{"ctype": "TYPE_I", "gap": 1.0}])
        end = time.time()
        # 1000次检查应该在1秒内完成
        assert end - start < 1.0

    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        gate = PhysicsGate()
        results = []

        def check_herb_pair():
            decision = gate.decide({"iteration": 0}, [{"ctype": "TYPE_I", "gap": 1.0}])
            results.append(decision)

        # 创建多个线程
        threads = [threading.Thread(target=check_herb_pair) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证所有结果一致
        assert len(results) == 10
        for result in results:
            assert result == GateDecision.HARD_REJECT


class TestDataset:
    """数据集测试"""

    def test_extended_dataset_size(self):
        """测试扩展数据集大小（90+样本）"""
        assert len(TCM_HERB_PAIRS) >= 90, f"Expected 90+ samples, got {len(TCM_HERB_PAIRS)}"

    def test_dataset_balance(self):
        """测试数据集类别平衡"""
        conflicts = [p for p in TCM_HERB_PAIRS if p["status"] == "conflict"]
        no_conflicts = [p for p in TCM_HERB_PAIRS if p["status"] == "no_conflict"]

        # 冲突和非冲突样本都应该有足够数量
        assert len(conflicts) >= 30, f"Expected 30+ conflicts, got {len(conflicts)}"
        assert len(no_conflicts) >= 30, f"Expected 30+ no_conflicts, got {len(no_conflicts)}"

    def test_known_conflicts_completeness(self):
        """测试KNOWN_CONFLICTS完整性"""
        # 检查核心冲突对存在
        core_pairs = [
            ("甘草", "甘遂"),
            ("人参", "藜芦"),
            ("乌头", "贝母"),
            ("附子", "半夏"),
            ("丹参", "藜芦"),
        ]
        for herb_a, herb_b in core_pairs:
            result = check_tcm_conflict(herb_a, herb_b)
            assert result is not None, f"Conflict pair ({herb_a}, {herb_b}) not detected"


class TestCheckTCMConflict:
    """check_tcm_conflict函数测试"""

    def test_18contra(self):
        """测试十八反检测"""
        result = check_tcm_conflict("甘草", "甘遂")
        assert result is not None
        assert result["error"] == 1.0
        assert result["ctype"] == "TYPE_I"

    def test_19fear(self):
        """测试十九畏检测"""
        result = check_tcm_conflict("人参", "莱菔子")
        assert result is not None
        assert result["error"] == 0.7

    def test_no_conflict(self):
        """测试无冲突药对"""
        result = check_tcm_conflict("人参", "黄芪")
        assert result is None

    def test_bidirectional(self):
        """测试双向查询"""
        r1 = check_tcm_conflict("甘草", "甘遂")
        r2 = check_tcm_conflict("甘遂", "甘草")
        assert r1 is not None
        assert r2 is not None
        assert r1["error"] == r2["error"]


class TestStatisticalValidity:
    """统计有效性测试"""

    def test_bootstrap_ci(self):
        """测试Bootstrap置信区间计算"""
        # 使用更大的数据集避免边界问题
        results = [
            {"has_conflict": True, "predicted_conflict": True},
            {"has_conflict": True, "predicted_conflict": True},
            {"has_conflict": False, "predicted_conflict": False},
            {"has_conflict": True, "predicted_conflict": True},
            {"has_conflict": False, "predicted_conflict": False},
            {"has_conflict": True, "predicted_conflict": False},
            {"has_conflict": False, "predicted_conflict": True},
            {"has_conflict": True, "predicted_conflict": True},
            {"has_conflict": False, "predicted_conflict": False},
            {"has_conflict": True, "predicted_conflict": True},
        ]

        metrics_with_ci = compute_metrics_with_ci(results, n_bootstrap=100)

        assert "ci_precision" in metrics_with_ci
        assert "ci_recall" in metrics_with_ci
        assert "ci_f1" in metrics_with_ci

        # 检查CI格式
        for key in ["ci_precision", "ci_recall", "ci_f1"]:
            ci = metrics_with_ci[key]
            assert "mean" in ci
            assert "lower" in ci
            assert "upper" in ci
            assert "std" in ci
            # CI范围应该合理
            assert ci["lower"] <= 1.0
            assert ci["upper"] >= 0.0
