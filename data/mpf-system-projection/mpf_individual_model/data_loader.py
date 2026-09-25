# -*- coding: utf-8 -*-
"""真实个体数据预留接口。

将 CSV / 数仓记录映射为 ``IndividualProfile`` + 期初余额即可复用全套引擎。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from params import IndividualProfile, MEDIAN_MONTHLY_INCOME_2025, R_BASE


@dataclass
class IndividualRecord:
    """真实个体一条记录。"""

    profile: IndividualProfile
    initial_balance: float = 0.0
    source: str = "placeholder"


class IndividualDataSource(ABC):
    """可替换数据源。"""

    @abstractmethod
    def load_individual(self, person_id: str) -> IndividualRecord:
        """按 ID 加载个体。"""


class CSVIndividualSource(IndividualDataSource):
    """从简易 CSV 加载。列：person_id,sex,entry_age,retire_age,start_monthly_income,..."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self._df = pd.read_csv(self.path)

    def load_individual(self, person_id: str) -> IndividualRecord:
        hit = self._df[self._df["person_id"].astype(str) == str(person_id)]
        if hit.empty:
            raise KeyError(person_id)
        r = hit.iloc[0]
        prof = IndividualProfile(
            sex=str(r.get("sex", "男")),
            entry_age=int(r.get("entry_age", 25)),
            retire_age=int(r.get("retire_age", 65)),
            start_monthly_income=float(r.get("start_monthly_income", MEDIAN_MONTHLY_INCOME_2025)),
            income_growth=float(r.get("income_growth", 0.03)),
            r=float(r.get("r", R_BASE)),
            gap_years=int(r.get("gap_years", 0)),
            voluntary_rate=float(r.get("voluntary_rate", 0.0)),
            name=str(r.get("name", person_id)),
            career_start_year=int(r["career_start_year"])
            if "career_start_year" in r and pd.notna(r["career_start_year"])
            else 2026,
        )
        bal = float(r.get("initial_balance", 0.0))
        return IndividualRecord(profile=prof, initial_balance=bal, source=str(self.path))


def load_real_individual(
    person_id: str = "demo",
    csv_path: Optional[Union[str, Path]] = None,
) -> IndividualRecord:
    """预留接口：有 CSV 则读真实/示例个体，否则返回代表性个体。"""
    if csv_path is not None and Path(csv_path).exists():
        return CSVIndividualSource(csv_path).load_individual(person_id)
    return IndividualRecord(
        profile=IndividualProfile(name="代表性个体_接口占位"),
        initial_balance=0.0,
        source="builtin_representative",
    )
