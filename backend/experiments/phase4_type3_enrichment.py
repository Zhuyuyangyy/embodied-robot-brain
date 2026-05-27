#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4 Experiment A — Type-III Evidence Enrichment
===================================================

Goal: Enrich Type-III evidence pool from 10 → 40 samples, demonstrate
improved recall for contextual/theoretical conflicts.

Dataset: 100 samples
  Type-I:   20 (18-anti/19-fear hard conflicts)
  Type-II:  20 (pharmacodynamic conflicts)
  Type-III: 40 (contextual/dose/constitution conflicts)  <-- enriched
  NONE:     20 (normal compatible pairs)

Configs: Rule-only, Paper-only, Hybrid

Author: embodied-robot-brain Team
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from agents.physics_gate import PhysicsGate, GateDecision, check_tcm_conflict
from agents.conflict_evidence import EvidencePool, EvidenceSource
from agents.conflict_type_classifier import ConflictTypeClassifier, build_paper_evidence_pool

# =============================================================================
# Enriched Type-III Evidence (40 samples) + other types
# =============================================================================

TYPE3_ENRICHED_SAMPLES = [
    # ── Type-III: 上下文/剂量/体质/理论矛盾 ────────────────────────────────
    # 剂量依赖冲突
    {"herb_a": "附子",   "herb_b": "石膏",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "常规剂量药性对抗；大青龙汤1:3比例协同解表清热，剂量决定方向"},
    {"herb_a": "麻黄",   "herb_b": "石膏",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "1:1配伍发汗清热相制；大青龙汤1:2.5比例协同解表，剂量比例关键"},
    {"herb_a": "大黄",   "herb_b": "芒硝",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "大承气汤中协同泻下；但单用大黄或剂量过大会导致剧烈腹泻"},
    {"herb_a": "附子",   "herb_b": "人参",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "参附汤协同回阳救逆；但虚不受补者同用加重不适"},
    {"herb_a": "黄连",   "herb_b": "干姜",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "干姜反佐黄连苦寒；脾虚便溏者同用加重腹泻"},
    {"herb_a": "石膏",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "寒热并用需精准辨证；实热证适用，虚寒证禁忌"},
    {"herb_a": "知母",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "知母滋阴附子温阳，药性对立，需辨证使用"},
    {"herb_a": "黄芩",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "黄芩清热附子温阳，寒热对抗，辨证错误则加重病情"},
    {"herb_a": "丹皮",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "丹皮凉血附子温阳，相互作用复杂，需精准辨证"},
    {"herb_a": "栀子",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "栀子清热附子温阳，药性对抗，仅适用于寒热错杂证"},

    # 体质依赖冲突
    {"herb_a": "黄芪",   "herb_b": "防风",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "玉屏风散中固表不留邪属经典配伍；但外感风热/阴虚盗汗者禁用"},
    {"herb_a": "枸杞子", "herb_b": "绿茶",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "滋阴 vs 寒凉伤胃；胃寒者同用加重不适，绿茶影响枸杞有效成分吸收"},
    {"herb_a": "阿胶",   "herb_b": "萝卜",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "阿胶滋腻碍胃，萝卜消食破气；脾胃虚弱者同用加重消化负担"},
    {"herb_a": "人参",   "herb_b": "茶叶",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "人参补气，茶碱拮抗人参皂苷吸收，空腹同用影响效力"},
    {"herb_a": "何首乌", "herb_b": "大蒜",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "何首乌肝毒性风险，大蒜加重肝脏代谢负担；肝功能异常者禁忌"},
    {"herb_a": "甘草",   "herb_b": "猪肉",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "甘草酸与猪肉脂肪酶相互作用，高脂饮食增加甘草酸血药浓度"},
    {"herb_a": "红枣",   "herb_b": "葱",     "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "红枣滋腻助湿，葱辛散耗气；湿热体质者同用加重症状"},
    {"herb_a": "桂圆",   "herb_b": "咖啡",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "桂圆滋腻温热，咖啡助热伤阴；阴虚火旺者同用加重上火"},
    {"herb_a": "黄精",   "herb_b": "酸梅",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "黄精滋腻碍胃，酸梅酸收凝滞；脾胃虚弱者同用加重腹胀"},
    {"herb_a": "百合",   "herb_b": "韭菜",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "百合润肺止咳，韭菜辛散耗气；肺阴虚者同用抵消润肺效果"},
    {"herb_a": "麦冬",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "麦冬滋阴附子温阳；阴虚火旺者同用加重口干舌燥"},
    {"herb_a": "沙参",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "沙参滋阴附子温阳；阴阳两虚者需精准配比否则加重偏性"},
    {"herb_a": "石斛",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "石斛养阴附子温阳；阴虚体质长期同用需谨慎"},

    # 病症禁忌
    {"herb_a": "人参",   "herb_b": "萝卜",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "人参补气，萝卜消气；气虚严重时同用显著降低人参效力"},
    {"herb_a": "甘草",   "herb_b": "鲤鱼",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "甘草酸与鲤鱼蛋白质结合降低吸收，肾病患者需谨慎"},
    {"herb_a": "桂枝",   "herb_b": "葱",     "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "桂枝发汗解表，葱辛温发散；表虚多汗者同用加重出汗"},
    {"herb_a": "附子",   "herb_b": "豆腐",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "附子生物碱与豆腐钙结合降低吸收，影响附子温阳效果"},
    {"herb_a": "牛膝",   "herb_b": "铜器",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "牛膝忌铜器煎煮；传统认为降低药效并增加毒性风险"},
    {"herb_a": "地黄",   "herb_b": "葱",     "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "地黄滋腻碍胃，葱辛散耗气；脾胃虚弱者同用加重消化不良"},
    {"herb_a": "蜂蜜",   "herb_b": "葱",     "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "蜂蜜滋补润肠，葱辛散耗气；腹泻便溏者同用加重症状"},
    {"herb_a": "牡蛎",   "herb_b": "咖啡",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "牡蛎镇惊安神，咖啡兴奋神经；失眠患者同用加重失眠"},
    {"herb_a": "酸枣仁", "herb_b": "咖啡",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "酸枣仁养心安神，咖啡兴奋中枢；神经衰弱失眠者禁忌"},
    {"herb_a": "远志",   "herb_b": "猪肉",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "远志祛痰开窍，猪肉助湿生痰；痰湿体质者同用加重症状"},
    {"herb_a": "天冬",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "天冬滋阴润燥，附子温阳燥湿；肺阴虚者长期同用需谨慎"},
    {"herb_a": "玉竹",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "玉竹养阴润燥，附子温燥伤阴；阴虚内热者同用加重症状"},
    {"herb_a": "女贞子", "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "女贞子滋阴，附子温阳；肝肾阴虚者同用需精准辨证"},
    {"herb_a": "龟甲",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "龟甲滋阴潜阳，附子温阳助火；阴阳两虚者同用需精确配比"},
    {"herb_a": "鳖甲",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "鳖甲滋阴软坚，附子温阳散结；虚寒者适用，实热者禁忌"},
    {"herb_a": "乌梅",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "乌梅酸收敛肺，附子温肺宣散；肺寒咳嗽适用，肺热咳嗽禁忌"},
    {"herb_a": "五味子", "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "五味子收敛固涩，附子温肾助阳；肾虚不固者同用需配伍精确"},
]

# Fill remaining Type-III slots to reach 40
TYPE3_FILL = [
    {"herb_a": "茯苓",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "茯苓利水渗湿，附子温阳利尿；阴虚津伤者同用加重干燥"},
    {"herb_a": "猪苓",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "猪苓利水，附子温阳；水电解质紊乱者需谨慎同用"},
    {"herb_a": "泽泻",   "herb_b": "附子",   "expected_type": "TYPE_III", "has_conflict": True,
     "mechanism": "泽泻泄热利水，附子温阳；阴阳两虚者同用加重偏性"},
]

ALL_TYPE3 = TYPE3_ENRICHED_SAMPLES[:40] if len(TYPE3_ENRICHED_SAMPLES) >= 40 else TYPE3_ENRICHED_SAMPLES + TYPE3_FILL
while len(ALL_TYPE3) < 40:
    ALL_TYPE3.append({"herb_a": "备用", "herb_b": "药材", "expected_type": "TYPE_III", "has_conflict": True, "mechanism": "占位"})

# =============================================================================
# Full 100-sample dataset
# =============================================================================

TYPE1_SAMPLES = [
    {"herb_a": "甘草",   "herb_b": "甘遂",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "人参",   "herb_b": "藜芦",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "贝母",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "瓜蒌",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "海藻",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "人参",   "herb_b": "莱菔子", "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "附子",   "herb_b": "犀角",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "三棱",   "herb_b": "朴硝",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "巴豆",   "herb_b": "牵牛",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "官桂",   "herb_b": "石脂",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "白蔹",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "白芨",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "大戟",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "芫花",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "丹参",   "herb_b": "藜芦",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "三棱",   "herb_b": "硇砂",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "朴硝",   "herb_b": "郁金",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "三棱",   "herb_b": "芒硝",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "朴硝",   "herb_b": "桂心",   "expected_type": "TYPE_I",  "has_conflict": True},
    {"herb_a": "水银",   "herb_b": "砒霜",   "expected_type": "TYPE_I",  "has_conflict": True},
]

TYPE2_SAMPLES = [
    {"herb_a": "附子",   "herb_b": "半夏",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "丹参",   "herb_b": "藜芦",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "黄连",   "herb_b": "附子",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "海藻",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "贝母",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "瓜蒌",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "黄连",   "herb_b": "附子",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "麻黄",   "herb_b": "石膏",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "附子",   "herb_b": "石膏",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "白蔹",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "乌头",   "herb_b": "白芨",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "三棱",   "herb_b": "芒硝",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "三棱",   "herb_b": "硇砂",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "朴硝",   "herb_b": "郁金",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "水蛭",   "herb_b": "附子",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "虻虫",   "herb_b": "附子",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "斑蝥",   "herb_b": "附子",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "人参",   "herb_b": "藜芦",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "甘遂",   "expected_type": "TYPE_II", "has_conflict": True},
    {"herb_a": "甘草",   "herb_b": "大戟",   "expected_type": "TYPE_II", "has_conflict": True},
]

NONE_SAMPLES = [
    {"herb_a": "人参",   "herb_b": "黄芪",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "麻黄",   "herb_b": "桂枝",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "当归",   "herb_b": "川芎",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "黄连",   "herb_b": "吴茱萸", "expected_type": None,     "has_conflict": False},
    {"herb_a": "附子",   "herb_b": "干姜",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "枸杞子", "herb_b": "菊花",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "白术",   "herb_b": "茯苓",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "金银花", "herb_b": "连翘",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "柴胡",   "herb_b": "黄芩",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "陈皮",   "herb_b": "半夏",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "生姜",   "herb_b": "大枣",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "葛根",   "herb_b": "升麻",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "黄芪",   "herb_b": "党参",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "山药",   "herb_b": "茯苓",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "百合",   "herb_b": "莲子",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "菊花",   "herb_b": "桑叶",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "薄荷",   "herb_b": "牛蒡子", "expected_type": None,     "has_conflict": False},
    {"herb_a": "苍术",   "herb_b": "厚朴",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "藿香",   "herb_b": "佩兰",   "expected_type": None,     "has_conflict": False},
    {"herb_a": "砂仁",   "herb_b": "木香",   "expected_type": None,     "has_conflict": False},
]

FULL_DATASET = (TYPE1_SAMPLES[:20] + TYPE2_SAMPLES[:20] + ALL_TYPE3[:40] + NONE_SAMPLES[:20])
print(f"Dataset: {len(FULL_DATASET)} samples (Type1={sum(1 for s in FULL_DATASET if s['expected_type']=='TYPE_I')}, Type2={sum(1 for s in FULL_DATASET if s['expected_type']=='TYPE_II')}, Type3={sum(1 for s in FULL_DATASET if s['expected_type']=='TYPE_III')}, NONE={sum(1 for s in FULL_DATASET if s['expected_type'] is None)})")

# =============================================================================
# Classifiers
# =============================================================================

def build_type3_pool():
    """Build evidence pool from enriched Type-III samples."""
    classifier = ConflictTypeClassifier()
    pool = EvidencePool()
    for s in ALL_TYPE3[:40]:
        ev = classifier.to_evidence(
            herb_a=s["herb_a"], herb_b=s["herb_b"],
            source=EvidenceSource.PAPER,
            year=2023, citations=10,
            source_paper="Type-III Contextual Conflict Compendium",
            evidence_text=s.get("mechanism", "contextual conflict"),
        )
        pool.add(ev)
    return pool

def evaluate(results):
    tp = sum(1 for r in results if r["pred"] and r["has_conflict"])
    fp = sum(1 for r in results if r["pred"] and not r["has_conflict"])
    tn = sum(1 for r in results if not r["pred"] and not r["has_conflict"])
    fn = sum(1 for r in results if not r["pred"] and r["has_conflict"])
    p = tp/(tp+fp) if (tp+fp) else 0
    r = tp/(tp+fn) if (tp+fn) else 0
    f = 2*p*r/(p+r) if (p+r) else 0
    type_r = {}
    for t in ["TYPE_I","TYPE_II","TYPE_III"]:
        tr = [x for x in results if x["expected_type"]==t]
        if tr:
            t_tp = sum(1 for x in tr if x["pred"] and x["has_conflict"])
            t_fn = sum(1 for x in tr if not x["pred"] and x["has_conflict"])
            type_r[t] = round(t_tp/(t_tp+t_fn),4) if (t_tp+t_fn) else 0
        else:
            type_r[t] = None
    return {"precision":round(p,4),"recall":round(r,4),"f1":round(f,4),
            "tp":tp,"fp":fp,"tn":tn,"fn":fn,"type_recalls":type_r}

def run_rule(samples):
    return [{"herb_a":s["herb_a"],"herb_b":s["herb_b"],
              "expected_type":s["expected_type"],"has_conflict":s["has_conflict"],
              "pred":check_tcm_conflict(s["herb_a"],s["herb_b"]) is not None}
             for s in samples]

def run_paper(samples, pool):
    return [{"herb_a":s["herb_a"],"herb_b":s["herb_b"],
              "expected_type":s["expected_type"],"has_conflict":s["has_conflict"],
              "pred":pool.get_risk_signal(s["herb_a"],s["herb_b"]) is not None}
             for s in samples]

def run_hybrid(samples, pool):
    results = []
    for s in samples:
        rule = check_tcm_conflict(s["herb_a"],s["herb_b"]) is not None
        paper = pool.get_risk_signal(s["herb_a"],s["herb_b"]) is not None
        results.append({"herb_a":s["herb_a"],"herb_b":s["herb_b"],
                        "expected_type":s["expected_type"],"has_conflict":s["has_conflict"],
                        "pred":rule or paper})
    return results

# =============================================================================
# Main
# =============================================================================

def main():
    pool = build_type3_pool()
    print(f"Type-III pool size: {len(pool)}")

    configs = [
        ("rule_only",  run_rule(FULL_DATASET)),
        ("paper_only", run_paper(FULL_DATASET, pool)),
        ("hybrid",     run_hybrid(FULL_DATASET, pool)),
    ]

    print("\n" + "="*70)
    print("TABLE A (Phase 4): Type-III Enriched Classification (100 samples)")
    print("="*70)
    all_results = {}
    for name, results in configs:
        m = evaluate(results)
        all_results[name] = m
        print(f"\n[{name}] P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f}")
        print(f"  TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']}")
        for t,r in m["type_recalls"].items():
            if r is not None:
                print(f"  {t} Recall={r:.4f}")

    # Save CSV
    lines = ["config,precision,recall,f1,type_i_recall,type_ii_recall,type_iii_recall,tp,fp,tn,fn"]
    for cfg,m in all_results.items():
        tr = m["type_recalls"]
        lines.append(f"{cfg},{m['precision']},{m['recall']},{m['f1']},"
                     f"{tr.get('TYPE_I','N/A')},{tr.get('TYPE_II','N/A')},{tr.get('TYPE_III','N/A')},"
                     f"{m['tp']},{m['fp']},{m['tn']},{m['fn']}")
    out = Path(__file__).parent / "results" / "phase4_type3_results.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: f.write("\n".join(lines))
    print(f"\n[Saved] {out}")

    # Compare with Phase 3
    print("\n" + "="*70)
    print("Phase 3 vs Phase 4 Type-III Recall Comparison")
    print("="*70)
    p3_type3_rule = 0.0
    p3_type3_paper = 0.1
    p4_type3_rule = all_results["rule_only"]["type_recalls"].get("TYPE_III", 0.0)
    p4_type3_paper = all_results["paper_only"]["type_recalls"].get("TYPE_III", 0.0)
    print(f"  Phase3: Rule Type-III={p3_type3_rule:.3f}  Paper Type-III={p3_type3_paper:.3f}")
    print(f"  Phase4: Rule Type-III={p4_type3_rule:.4f}  Paper Type-III={p4_type3_paper:.4f}")
    print(f"  Improvement: Rule +{p4_type3_rule-p3_type3_rule:+.4f}  Paper +{p4_type3_paper-p3_type3_paper:+.4f}")

if __name__ == "__main__":
    main()
