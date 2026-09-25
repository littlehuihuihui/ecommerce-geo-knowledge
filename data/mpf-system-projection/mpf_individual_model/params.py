# -*- coding: utf-8 -*-
"""个体模型参数与情景。

来源标注：[真实数据] / [真实数据量级] / [假设] / [反推]
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Optional


RANDOM_SEED = 42

# ---------- 入息与供款规则 ----------
# [真实数据量级] 2025 Q3 香港入息中位数约 20,500 港元/月
MEDIAN_MONTHLY_INCOME_2025 = 20500.0
RATE_EE = 0.05  # [真实数据] 雇员强制 5%
RATE_ER = 0.05  # [真实数据] 雇主强制 5%

# [真实数据] 现行有关入息上下限
Y_MIN_OLD = 7100.0
Y_MAX_OLD = 30000.0
# [基准情景假设] 拟议新上下限（未立法）
Y_MIN_NEW = 10500.0
Y_MAX_NEW = 40000.0
LIMIT_TRANSITION_YEAR = 2028  # [假设] 模型日历年；个体模型用「入职年后的第 N 年」或固定现行

# ---------- 回报情景 ----------
R_CONSERVATIVE = 0.03  # [假设] 偏债/保守
R_BASE = 0.049  # [真实数据量级] 制度加权约 4.9%
R_OPTIMISTIC = 0.07  # [真实数据量级] 参考 DIS 核心累积约 7.3%，情景取 7%

# ---------- 寿命锚点 ----------
# [真实数据量级] 香港预期寿命
LE_MALE = 83.3
LE_FEMALE = 88.7
# [真实数据量级] 65 岁后预期余命
E65_MALE = 18.0
E65_FEMALE = 24.0

# ---------- 退休提取默认 ----------
WITHDRAW_PCT_DEFAULT = 0.04  # [假设] 经典 4% 规则
REPLACEMENT_TARGET = 0.50  # [假设] 目标替代率：退休年支出=终薪×50%
R_RETIRE_DEFAULT = 0.03  # [假设] 退休后继续投资的偏保守净回报


@dataclass
class IndividualProfile:
    """代表性个体或可替换的真实个体画像。

    Attributes:
        sex: 男/女（影响余命）。
        entry_age: 入职年龄。
        retire_age: 退休年龄。
        start_monthly_income: 入职月薪（港元）。
        income_growth: 入息名义年增速。
        r: 累积期净回报。
        career_start_year: 入职日历年（用于上下限过渡）；None 则全程用现行上下限。
        gap_years: 供款中断年数（均匀插在职业生涯中）[假设]。
        voluntary_rate: 额外自愿供款占有关入息比例 [假设]。
        name: 标签。
    """

    sex: str = "男"
    entry_age: int = 25
    retire_age: int = 65
    start_monthly_income: float = MEDIAN_MONTHLY_INCOME_2025
    income_growth: float = 0.03
    r: float = R_BASE
    career_start_year: Optional[int] = 2026
    gap_years: int = 0
    voluntary_rate: float = 0.0
    name: str = "代表性个体"
    use_new_limits: bool = False  # True=全程假设新上下限；False=按年过渡或现行


@dataclass(frozen=True)
class ReturnScenario:
    code: str
    label: str
    r: float


RETURN_SCENARIOS: Dict[str, ReturnScenario] = {
    "低": ReturnScenario("低", "保守", R_CONSERVATIVE),
    "中": ReturnScenario("中", "基准", R_BASE),
    "高": ReturnScenario("高", "乐观", R_OPTIMISTIC),
}


def e65_for_sex(sex: str) -> float:
    """65 岁后预期余命。"""
    return E65_FEMALE if sex == "女" else E65_MALE


def life_expectancy_at_birth(sex: str) -> float:
    """出生时预期寿命锚点。"""
    return LE_FEMALE if sex == "女" else LE_MALE


def relevant_limits_for_calendar_year(
    year: Optional[int],
    use_new_limits: bool = False,
) -> tuple:
    """返回 (ymin, ymax)。

    个体模型默认：若提供日历年且 year>=2028 且未强制旧值，用假设新上限；
    否则现行。use_new_limits=True 则全程新上限。
    """
    if use_new_limits:
        return Y_MIN_NEW, Y_MAX_NEW
    if year is not None and int(year) >= LIMIT_TRANSITION_YEAR:
        return Y_MIN_NEW, Y_MAX_NEW  # [假设]
    return Y_MIN_OLD, Y_MAX_OLD


def profile_variants_grid() -> list:
    """入职年龄 × 入息水平 × 回报 的网格（表1用）。"""
    entries = [22, 25, 30]
    income_mults = [
        ("低收入×0.7", 0.7),
        ("中位数", 1.0),
        ("高收入×1.5", 1.5),
    ]
    out = []
    for ea in entries:
        for lab, m in income_mults:
            for sc in RETURN_SCENARIOS.values():
                out.append(
                    IndividualProfile(
                        entry_age=ea,
                        start_monthly_income=MEDIAN_MONTHLY_INCOME_2025 * m,
                        r=sc.r,
                        name=f"入职{ea}/{lab}/{sc.label}",
                    )
                )
    return out
