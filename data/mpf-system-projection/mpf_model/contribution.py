# -*- coding: utf-8 -*-
"""第二层：缴费人数与供款额。"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pandas as pd

from data_loader import (
    COVERAGE,
    EMP_RATE,
    KAPPA_VOL,
    TARGET_CONTRIB_2026,
    Y_MAX_DEFAULT,
    Y_MIN_DEFAULT,
)
from population import LABOUR_AGES, labour_population
from scenarios import ScenarioConfig

# 分年龄性别劳动参与率中枢 [假设]（量级贴近香港劳动力统计形态）
# 年龄键必须与 population.LABOUR_AGES 完全一致（见 assert_labour_age_alignment）
LFPR_BASE: Dict[Tuple[str, str], float] = {
    ("15-19", "男"): 0.22,
    ("15-19", "女"): 0.20,
    ("20-24", "男"): 0.62,
    ("20-24", "女"): 0.64,
    ("25-29", "男"): 0.92,
    ("25-29", "女"): 0.88,
    ("30-34", "男"): 0.94,
    ("30-34", "女"): 0.82,
    ("35-39", "男"): 0.94,
    ("35-39", "女"): 0.78,
    ("40-44", "男"): 0.93,
    ("40-44", "女"): 0.75,
    ("45-49", "男"): 0.91,
    ("45-49", "女"): 0.72,
    ("50-54", "男"): 0.86,
    ("50-54", "女"): 0.64,
    ("55-59", "男"): 0.72,
    ("55-59", "女"): 0.48,
    ("60-64", "男"): 0.48,
    ("60-64", "女"): 0.28,
}

# 入息分布三档占比 [假设]
INCOME_BAND_SHARE = {"below": 0.12, "mid": 0.68, "above": 0.20}
# 带内代表月入：落在现行上限 30000 内；经总供款校准缩放
# 来源：[假设] 校准锚点 2025-26 财年总供款 912.3 亿
INCOME_MID_REP = 18500.0
RATE_EE = 0.05  # [真实数据] 雇员强制 5%
RATE_ER = 0.05  # [真实数据] 雇主强制 5%


def assert_labour_age_alignment() -> None:
    """校验人口层劳动年龄组与 LFPR 表键一致。"""
    expected = {(a, s) for a in LABOUR_AGES for s in ("男", "女")}
    got = set(LFPR_BASE.keys())
    if expected != got:
        missing = expected - got
        extra = got - expected
        raise AssertionError(
            f"LFPR 与 LABOUR_AGES 不一致；missing={missing} extra={extra}"
        )


assert_labour_age_alignment()


def lfpr(age: str, sex: str, shift: float = 0.0) -> float:
    """取分年龄性别劳动参与率。

    Args:
        age: 5岁组。
        sex: 男/女。
        shift: 水平平移（情景）。

    Returns:
        参与率，裁剪到 [0.01, 0.99]。
    """
    base = LFPR_BASE.get((age, sex), 0.70)
    return float(min(0.99, max(0.01, base + shift)))


def mandatory_contrib_per_person_monthly(
    monthly_income: float,
    y_min: float,
    y_max: float,
) -> Tuple[float, float]:
    """按有关入息上下限规则计算单人每月强制供款（雇员, 雇主）。

    规则：
      - 月入 < 下限：雇员 0，雇主按实际入息 × 5%
      - 下限 ≤ 月入 ≤ 上限：双方各按入息 × 5%
      - 月入 > 上限：双方各按上限 × 5%

    Args:
        monthly_income: 月入（港元）。
        y_min: 有关入息下限。
        y_max: 有关入息上限。

    Returns:
        (雇员月供, 雇主月供) 港元。
    """
    y = float(monthly_income)
    if y < y_min:
        return 0.0, y * RATE_ER
    if y > y_max:
        return y_max * RATE_EE, y_max * RATE_ER
    return y * RATE_EE, y * RATE_ER


def average_mandatory_annual(
    y_min: float,
    y_max: float,
    mid_rep: float,
) -> float:
    """按三档入息分布求人均年强制供款（港元）。

    Args:
        y_min: 下限。
        y_max: 上限。
        mid_rep: 带内代表月入。

    Returns:
        人均年强制供款（雇员+雇主）。
    """
    # below：代表取 0.7×下限
    y_below = 0.7 * y_min
    y_mid = min(max(mid_rep, y_min), y_max)
    y_above = y_max * 1.3  # 触发封顶

    total_m = 0.0
    for key, y in (("below", y_below), ("mid", y_mid), ("above", y_above)):
        ee, er = mandatory_contrib_per_person_monthly(y, y_min, y_max)
        total_m += INCOME_BAND_SHARE[key] * (ee + er)
    return total_m * 12.0


def compute_contributors(
    pop: pd.DataFrame,
    year: int,
    scenario: ScenarioConfig,
    coverage: float = COVERAGE,
    emp_rate: float = EMP_RATE,
) -> pd.DataFrame:
    """计算分年龄性别缴费人数。

    Args:
        pop: 人口投影。
        year: 年份。
        scenario: 情景配置。
        coverage: 强积金覆盖率。
        emp_rate: 就业率。

    Returns:
        含缴费人数的明细表。
    """
    lab = labour_population(pop, year)
    rows = []
    for _, r in lab.iterrows():
        age, sex = r["年龄组"], r["性别"]
        n_pop = float(r["人数"])
        p = lfpr(age, sex, scenario.lfpr_shift)
        n_c = n_pop * p * emp_rate * coverage
        rows.append(
            {
                "年份": year,
                "年龄组": age,
                "性别": sex,
                "劳动年龄人口": round(n_pop, 1),
                "劳动参与率": round(p, 4),
                "就业率": emp_rate,
                "覆盖率": coverage,
                "缴费人数": round(n_c, 1),
            }
        )
    return pd.DataFrame(rows)


def compute_contribution(
    pop: pd.DataFrame,
    year: int,
    scenario: ScenarioConfig,
    y_min: float = Y_MIN_DEFAULT,
    y_max: float = Y_MAX_DEFAULT,
    kappa_vol: float = KAPPA_VOL,
    income_scale: float = 1.0,
    headcount_scale: float = 1.0,
    base_mid_income: float = INCOME_MID_REP,
    income_base_year: int = 2026,
    coverage: float = COVERAGE,
    emp_rate: float = EMP_RATE,
) -> Dict[str, float]:
    """计算年度供款（强制 + 自愿）。

    自愿性供款 = 总供款 × κ，故 强制 = 总 × (1−κ)，总 = 强制 / (1−κ)。

    Args:
        pop: 人口投影。
        year: 年份。
        scenario: 情景。
        y_min: 有关入息下限。
        y_max: 有关入息上限。
        kappa_vol: 自愿占总供款比例。
        income_scale: 入息校准系数（使 2026 对齐 912 亿）。
        headcount_scale: 人数校准系数。
        base_mid_income: income_base_year 的带内代表月入。
        income_base_year: 入息增长锚定年。
        coverage: 强积金覆盖率。
        emp_rate: 就业率。

    Returns:
        字典：缴费人数_万人、强制/自愿/总供款_亿港元 等。
    """
    detail = compute_contributors(
        pop, year, scenario, coverage=coverage, emp_rate=emp_rate
    )
    n_people = float(detail["缴费人数"].sum()) * headcount_scale
    t = year - income_base_year
    mid_rep = base_mid_income * ((1.0 + scenario.income_growth) ** t) * income_scale
    # 名义增长但不超过上限过多
    mid_rep = min(mid_rep, y_max * 0.98)

    mand_per = average_mandatory_annual(y_min, y_max, mid_rep)
    mand_yi = n_people * mand_per / 1e8  # 亿港元
    total_yi = mand_yi / (1.0 - kappa_vol) if kappa_vol < 1 else mand_yi
    vol_yi = total_yi * kappa_vol

    return {
        "年份": year,
        "缴费人数": n_people,
        "缴费人数_万人": n_people / 10000.0,
        "带内代表月入_港元": mid_rep,
        "人均年强制供款_港元": mand_per,
        "年强制性供款_亿港元": mand_yi,
        "年自愿性供款_亿港元": vol_yi,
        "年总供款_亿港元": total_yi,
        "自愿占比": kappa_vol,
        "有关入息下限": y_min,
        "有关入息上限": y_max,
        "覆盖率": coverage,
        "detail": detail,
    }


def calibrate_income_scale(
    pop: pd.DataFrame,
    scenario: ScenarioConfig,
    target_total: float = TARGET_CONTRIB_2026,
    y_min: float = Y_MIN_DEFAULT,
    y_max: float = Y_MAX_DEFAULT,
    year: int = 2026,
    tol: float = 0.5,
    max_iter: int = 12,
) -> float:
    """二分校准入息缩放，使指定年总供款贴近锚点。

    Args:
        pop: 人口投影。
        scenario: 情景（通常用中）。
        target_total: 目标总供款（亿港元）。
        y_min: 下限。
        y_max: 上限。
        year: 校准年。
        tol: 允许绝对误差（亿港元）。
        max_iter: 最大迭代次数。

    Returns:
        income_scale 系数。
    """
    lo, hi = 0.3, 2.5
    best = 1.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        c = compute_contribution(
            pop, year, scenario, y_min=y_min, y_max=y_max, income_scale=mid
        )["年总供款_亿港元"]
        best = mid
        if abs(c - target_total) <= tol:
            return float(mid)
        if c > target_total:
            hi = mid
        else:
            lo = mid
    return float(best)
