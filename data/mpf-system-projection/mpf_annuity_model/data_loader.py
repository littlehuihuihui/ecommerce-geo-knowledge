# -*- coding: utf-8 -*-
"""真实年金产品定价预留接口。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from pricing import SimpleHKAnnuityPricer


class TableAnnuityPricer:
    """从费率表 CSV 查价。

    期望列：sex, age, annual_rate  或  sex, age, monthly_per_1m
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.df = pd.read_csv(self.path)

    def annual_payout(self, premium: float, sex: str, age: int = 65) -> float:
        hit = self.df[(self.df["sex"] == sex) & (self.df["age"] == age)]
        if hit.empty:
            # 回退到公开量级线性定价
            return SimpleHKAnnuityPricer().annual_payout(premium, sex, age)
        row = hit.iloc[0]
        if "annual_rate" in row and pd.notna(row["annual_rate"]):
            return float(premium) * float(row["annual_rate"])
        monthly = float(row["monthly_per_1m"])
        return float(premium) * (monthly * 12.0 / 1_000_000.0)


def load_annuity_pricer(csv_path: Optional[Union[str, Path]] = None):
    """预留接口：有费率表则用表，否则用香港年金公开量级线性定价。"""
    if csv_path is not None and Path(csv_path).exists():
        return TableAnnuityPricer(csv_path)
    return SimpleHKAnnuityPricer()
