# -*- coding: utf-8 -*-
"""第一层：从对象三读入 65 岁账户余额分布。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_IND = Path(__file__).resolve().parent.parent / "mpf_individual_model"
_IND_OUT = _IND / "output"
T01 = _IND_OUT / "T01_retirement_balance_by_sex_return.csv"


def load_age65_balances(path: Optional[Path] = None) -> pd.DataFrame:
    """加载对象三退休余额表；若缺失则现场重算。

    Returns:
        含 性别、回报情景、退休时账户余额_港元、退休前年薪_港元 等列。
    """
    p = Path(path) if path else T01
    if p.exists():
        df = pd.read_csv(p)
        return df

    # 回退：调用对象三引擎
    if str(_IND) not in sys.path:
        sys.path.insert(0, str(_IND))
    from career import retirement_summary, simulate_career
    from params import IndividualProfile, MEDIAN_MONTHLY_INCOME_2025, RETURN_SCENARIOS

    rows = []
    for sex in ("男", "女"):
        for sc in RETURN_SCENARIOS.values():
            prof = IndividualProfile(
                sex=sex,
                start_monthly_income=MEDIAN_MONTHLY_INCOME_2025,
                r=sc.r,
                name=f"{sex}/{sc.label}",
            )
            career = simulate_career(prof)
            sm = retirement_summary(career, prof)
            sm["回报情景"] = sc.label
            rows.append(sm)
    return pd.DataFrame(rows)


def balance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """透视：行=性别，列=回报情景。"""
    return df.pivot_table(
        index="性别",
        columns="回报情景",
        values="退休时账户余额_港元",
        aggfunc="first",
    )
