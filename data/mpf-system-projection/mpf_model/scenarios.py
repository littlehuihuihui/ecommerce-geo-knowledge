# -*- coding: utf-8 -*-
"""情景配置：保守 / 基准 / 乐观 + 制度过渡参数。

参数来源标注：
- 总资产 / eMPF / 基金回报：积金局公开披露量级
- 上下限过渡：2026–2027 现行法定；2028+ 新值为【基准情景假设】（未立法）
- 全自由行：2025-09 修例、预计 2026 Q4 实施；不进入资产方程，仅作局限说明
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


RANDOM_SEED = 42  # 预留蒙特卡洛

# ---------- 有关入息上下限过渡 ----------
# 入息上下限调整：2026-2027 沿用旧值 $7,100 / $30,000
# 2028 年起上调至 $10,500 / $40,000 为【基准情景假设】，
# 非已确定的法定值。最终调整幅度及生效时间待政府公布。
# 背景（截至约 2026-09）：积金局仍在进行 2022-2026 周期检讨，
# 目标于 2026 年中向政府提交报告及建议；幅度与时间表尚未公布。
# [真实数据] 现行条例：7100/30000（约 12–13 年未调）
# [基准情景假设] 拟议量级 10500/40000；模型默认 transition_year=2028
Y_MIN_OLD = 7100.0
Y_MAX_OLD = 30000.0
Y_MIN_NEW = 10500.0
Y_MAX_NEW = 40000.0
upper_limit_transition_year = 2028  # [假设] 生效年，非法定时间表

# ---------- eMPF 费率日程 ----------
# [真实数据] 2026-04-01：0.37% → 0.29%
# [假设] 2027–2030 线性降至 0.22%，其后持平
EMPF_FEE_2026 = 0.0029
EMPF_FEE_2030 = 0.0022
EMPF_FEE_OLD = 0.0037

# ---------- 基金类别回报中枢（制度以来量级）----------
# [真实数据量级] 股票 5.1%；混合 4.8%；DIS 核心累积 7.3%（截至约 2026-06）
# 系统加权中枢约 4.9%（与情景 r 对齐）
FUND_RETURNS = {
    "股票基金": 0.051,  # [真实数据] 制度以来约 5.1%（非旧值 5.0%）
    "混合资产基金": 0.048,  # [真实数据量级]
    "DIS核心累积基金": 0.073,  # [真实数据] 截至约 2026-06 约 7.3%
    "保守基金": 0.015,  # [假设]
}
FUND_ALLOC = {
    "股票基金": 0.30,
    "混合资产基金": 0.35,
    "DIS核心累积基金": 0.25,
    "保守基金": 0.10,
}  # [假设] 系统配置权重
SYSTEM_NET_RETURN_MID = 0.049  # [真实数据量级] 制度加权约 4.9%


def empf_fee_schedule(year: int) -> float:
    """返回某年 eMPF 行政费率（小数）。

    来源：积金局 2026-03 公布自 2026-04-01 起 0.29%；其后为情景假设。
    """
    y = int(year)
    if y < 2026:
        return EMPF_FEE_OLD
    if y == 2026:
        return EMPF_FEE_2026
    if y >= 2030:
        return EMPF_FEE_2030
    w = (y - 2026) / (2030 - 2026)
    return EMPF_FEE_2026 + w * (EMPF_FEE_2030 - EMPF_FEE_2026)


def empf_fee_path(start: int = 2020, end: int = 2056) -> Dict[int, float]:
    """生成 eMPF 费率路径字典。"""
    return {y: empf_fee_schedule(y) for y in range(start, end + 1)}


def apply_empf_to_net_return(r_base_net_at_029: float, year: int) -> float:
    """将「按 0.29% 费率口径的净回报」调整到当年费率。

    费率每降 1bp，净回报约升 1bp。
    """
    return float(r_base_net_at_029 + (EMPF_FEE_2026 - empf_fee_schedule(year)))


def system_weighted_return() -> float:
    """按 FUND_ALLOC 加权的基金中枢（校验用）。"""
    return float(sum(FUND_ALLOC[k] * FUND_RETURNS[k] for k in FUND_RETURNS))


def relevant_income_limits(
    year: int,
    keep_old_limits: bool = False,
    transition_year: int = upper_limit_transition_year,
) -> Tuple[float, float]:
    """按年返回有关入息（下限, 上限）。

    2026–2027（及 transition_year 之前）：旧值 7100/30000（现行法定）；
    transition_year 起：基准情景假设新值 10500/40000（**非已确定法定值**）。
    keep_old_limits=True 时全程维持现行上下限（敏感性对照）。
    """
    if keep_old_limits or int(year) < int(transition_year):
        return Y_MIN_OLD, Y_MAX_OLD
    return Y_MIN_NEW, Y_MAX_NEW


FULL_PORTABILITY_NOTES: List[str] = [
    # 时间线：2025-09 立法会完成修例；首阶段预计 2026 Q4 实际实施（待系统优化）
    "全自由行首阶段：2025年9月完成修例，预计2026年Q4实际实施；"
    "允许2025年5月1日或之后入职的雇员，将雇主强制性供款转移至自选计划。",
    "次阶段：2027年上半年提交修订条例草案，覆盖其余雇员。",
    "对模型的影响：不改变制度总资产，但影响账户分布和市场竞争；"
    "本次建模未纳入受托人层面，仅在模型局限中说明。",
]


@dataclass(frozen=True)
class ScenarioConfig:
    """单情景参数包。"""

    code: str
    label: str
    r: float  # 净回报，按 eMPF=0.29% 口径；运行时再按年调整
    income_growth: float
    lfpr_shift: float
    other_withdrawal_share: float  # 其他提取（不含永久离港）
    pop_scenario: str
    keep_old_limits: bool = False
    upper_limit_transition_year: int = upper_limit_transition_year


SCENARIOS: Dict[str, ScenarioConfig] = {
    "低": ScenarioConfig(
        code="低",
        label="保守",
        r=0.03,
        income_growth=0.02,
        lfpr_shift=-0.02,
        other_withdrawal_share=0.08,
        pop_scenario="低",
    ),
    "中": ScenarioConfig(
        code="中",
        label="基准",
        r=SYSTEM_NET_RETURN_MID,  # 4.9%
        income_growth=0.03,
        lfpr_shift=0.0,
        other_withdrawal_share=0.06,
        pop_scenario="中",
    ),
    "高": ScenarioConfig(
        code="高",
        label="乐观",
        r=0.07,
        income_growth=0.04,
        lfpr_shift=0.02,
        other_withdrawal_share=0.05,
        pop_scenario="高",
    ),
    "旧上限对照": ScenarioConfig(
        code="旧上限对照",
        label="维持旧上限",
        r=SYSTEM_NET_RETURN_MID,
        income_growth=0.03,
        lfpr_shift=0.0,
        other_withdrawal_share=0.06,
        pop_scenario="中",
        keep_old_limits=True,
    ),
}


def get_scenario(code: str) -> ScenarioConfig:
    """按情景码取配置。"""
    alias = {
        "保守": "低",
        "基准": "中",
        "乐观": "高",
        "low": "低",
        "mid": "中",
        "high": "高",
        "old_limits": "旧上限对照",
        "维持旧上限": "旧上限对照",
    }
    key = alias.get(code, code)
    if key not in SCENARIOS:
        raise KeyError(f"未知情景: {code}；可选 {list(SCENARIOS)}")
    return SCENARIOS[key]
