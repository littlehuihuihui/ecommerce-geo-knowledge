# -*- coding: utf-8 -*-
"""第三层：支出层。

年度支出（亿港元）= 合资格人数 × 平均每月津贴 × 12 / 1e8
平均每月津贴按情景通胀率自 2025 基准 8,600 港元递推。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from scenarios import MONTHLY_ALLOWANCE_2025


def monthly_allowance(
    year: int,
    inflation: float,
    base_year: int = 2025,
    base_amount: float = MONTHLY_ALLOWANCE_2025,
) -> float:
    """名义平均每月津贴。

    Args:
        year: 日历年。
        inflation: 年调整率。
        base_year: 锚点年。
        base_amount: 锚点月津贴（港元）。

    Returns:
        港元/月。
    """
    t = max(0, int(year) - int(base_year))
    return float(base_amount) * ((1.0 + float(inflation)) ** t)


def annual_spend_yi(
    eligible_persons: float,
    month_allowance: float,
) -> float:
    """年度财政支出（亿港元）。"""
    return float(eligible_persons) * float(month_allowance) * 12.0 / 1e8


def build_expenditure_table(
    eligibility: pd.DataFrame,
    inflation: float,
    scenario_code: str,
    scenario_label: str,
) -> pd.DataFrame:
    """合并合资格表，生成支出路径。

    Args:
        eligibility: ``build_eligibility_table`` 输出。
        inflation: 津贴年调整率。
        scenario_code: 情景码。
        scenario_label: 情景标签。

    Returns:
        逐年支出 DataFrame。
    """
    rows = []
    for _, r in eligibility.iterrows():
        y = int(r["年份"])
        m = monthly_allowance(y, inflation)
        n = float(r["合资格长者_人"])
        spend = annual_spend_yi(n, m)
        rows.append(
            {
                "年份": y,
                "情景": scenario_code,
                "情景标签": scenario_label,
                "人口_65岁及以上_万人": r["人口_65岁及以上_万人"],
                "综合有效领取率": r["综合有效领取率"],
                "申请率": r["申请率"],
                "资产审查通过率": r["资产审查通过率"],
                "合资格长者_万人": r["合资格长者_万人"],
                "平均每月津贴_港元": round(m, 2),
                "年支出_亿港元": round(spend, 4),
                "津贴通胀率": inflation,
                "津贴来源": "[真实数据量级] 2025单身长者约8600；其后按情景通胀[假设]",
                "公式": "合资格人数×月津贴×12",
            }
        )
    return pd.DataFrame(rows)
