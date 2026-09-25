# -*- coding: utf-8 -*-
"""第二–三层：年金转换 + 退休收入结构 + 剩余余额耗尽。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

_IND = Path(__file__).resolve().parent.parent / "mpf_individual_model"
if str(_IND) not in sys.path:
    sys.path.insert(0, str(_IND))

from retirement import years_until_deplete  # noqa: E402

from pricing import (
    ANNUITIZE_RATIOS,
    OTHER_INCOME_ANNUAL_DEFAULT,
    R_RETIRE,
    REPLACEMENT_TARGET,
    RETIRE_AGE,
    AnnuityPricer,
    SimpleHKAnnuityPricer,
    e65_for_sex,
    expected_death_age,
)


def split_annuity_and_residual(
    balance: float,
    annuitize_ratio: float,
    sex: str,
    pricer: Optional[AnnuityPricer] = None,
    age: int = RETIRE_AGE,
) -> Dict[str, float]:
    """按比例拆分余额 → 年金保费 / 剩余可提取余额 / 年年金收入。"""
    pricer = pricer or SimpleHKAnnuityPricer()
    ratio = float(max(0.0, min(1.0, annuitize_ratio)))
    premium = balance * ratio
    residual = balance * (1.0 - ratio)
    annuity_annual = pricer.annual_payout(premium, sex, age=age)
    return {
        "年金化比例": ratio,
        "年金保费_港元": premium,
        "剩余余额_港元": residual,
        "年金年收入_港元": annuity_annual,
        "年金月收入_港元": annuity_annual / 12.0,
    }


def analyze_one(
    balance: float,
    final_annual_salary: float,
    sex: str,
    return_label: str,
    annuitize_ratio: float,
    pricer: Optional[AnnuityPricer] = None,
    replacement: float = REPLACEMENT_TARGET,
    r_retire: float = R_RETIRE,
    other_income: float = OTHER_INCOME_ANNUAL_DEFAULT,
) -> Dict[str, Any]:
    """单一（性别×情景×年金化比例）收入与耗尽分析。

    剩余余额提取规则（与对象三衔接）：
      目标总支出 = 前年薪 × replacement
      若年金+其他已覆盖目标，剩余余额可按更低提取或仅作流动性缓冲；
      本模型：剩余年提取 = max(0, 目标支出 − 年金 − 其他)，
      若剩余余额为 0，则年收入 = 年金 + 其他（终身地板）。
    """
    pricer = pricer or SimpleHKAnnuityPricer()
    parts = split_annuity_and_residual(balance, annuitize_ratio, sex, pricer)
    target = final_annual_salary * replacement
    annuity = parts["年金年收入_港元"]
    residual = parts["剩余余额_港元"]

    # 剩余提取：补足至目标；无剩余余额则无法提取
    if residual <= 1e-6:
        draw = 0.0
        years = float("inf") if annuity + other_income > 0 else 0.0
        deplete_age = float("inf")
    else:
        draw = max(0.0, target - annuity - other_income)
        if draw <= 1e-6:
            years = float("inf")  # 无需动用剩余即可达目标
            deplete_age = float("inf")
        else:
            years = years_until_deplete(residual, draw, r_retire=r_retire)
            deplete_age = RETIRE_AGE + years

    # 终身收入地板 = 年金 + 其他（不依赖账户）
    floor_annual = annuity + other_income
    income_while_residual = floor_annual + draw

    e_death = expected_death_age(sex)
    covers = deplete_age >= e_death - 0.5 if deplete_age != float("inf") else True
    # 耗尽后收入（仅地板）
    income_after_deplete = floor_annual

    # 终身收入保障指数：地板 / 目标支出
    floor_coverage = floor_annual / target if target > 0 else float("nan")

    return {
        "性别": sex,
        "回报情景": return_label,
        "退休余额_港元": round(balance, 2),
        "退休前年薪_港元": round(final_annual_salary, 2),
        "年金化比例": parts["年金化比例"],
        "年金保费_港元": round(parts["年金保费_港元"], 2),
        "剩余余额_港元": round(residual, 2),
        "年金年收入_港元": round(annuity, 2),
        "年金月收入_港元": round(parts["年金月收入_港元"], 2),
        "其他收入_港元": round(other_income, 2),
        "目标支出_港元": round(target, 2),
        "剩余年提取_港元": round(draw, 2),
        "退休初期年收入_港元": round(income_while_residual, 2),
        "耗尽后年收入_港元_终身地板": round(income_after_deplete, 2),
        "替代率_初期_vs前年薪": round(income_while_residual / final_annual_salary, 4)
        if final_annual_salary
        else None,
        "替代率_地板_vs前年薪": round(floor_annual / final_annual_salary, 4)
        if final_annual_salary
        else None,
        "剩余可支撑年数": None if years == float("inf") else round(years, 2),
        "账户耗尽年龄": None if deplete_age == float("inf") else round(deplete_age, 2),
        "预期死亡年龄": round(e_death, 1),
        "剩余账户是否覆盖余命": "不适用(无穷)"
        if deplete_age == float("inf")
        else ("是" if covers else "否"),
        "终身地板覆盖目标支出_pct": round(100.0 * floor_coverage, 2)
        if floor_coverage == floor_coverage
        else None,
        "权衡": "年金化对冲长寿风险，但降低流动性与遗产弹性",
    }


def run_income_grid(
    balances: pd.DataFrame,
    ratios: Optional[List[float]] = None,
    pricer: Optional[AnnuityPricer] = None,
    other_income: float = OTHER_INCOME_ANNUAL_DEFAULT,
) -> pd.DataFrame:
    """全网格：性别 × 回报情景 × 年金化比例。"""
    ratios = ratios or ANNUITIZE_RATIOS
    pricer = pricer or SimpleHKAnnuityPricer()
    rows = []
    for _, r in balances.iterrows():
        for ratio in ratios:
            rows.append(
                analyze_one(
                    float(r["退休时账户余额_港元"]),
                    float(r["退休前年薪_港元"]),
                    str(r["性别"]),
                    str(r["回报情景"]),
                    ratio,
                    pricer=pricer,
                    other_income=other_income,
                )
            )
    return pd.DataFrame(rows)


def income_structure_for_chart(
    grid: pd.DataFrame,
    sex: str = "男",
    scenario: str = "基准",
) -> pd.DataFrame:
    """图：不同年金化比例下 年金 vs 剩余提取 结构。"""
    sub = grid[(grid["性别"] == sex) & (grid["回报情景"] == scenario)].copy()
    sub = sub.sort_values("年金化比例")
    return sub[
        [
            "年金化比例",
            "年金年收入_港元",
            "剩余年提取_港元",
            "其他收入_港元",
            "退休初期年收入_港元",
            "耗尽后年收入_港元_终身地板",
        ]
    ]
