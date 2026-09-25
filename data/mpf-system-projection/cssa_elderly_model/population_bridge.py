# -*- coding: utf-8 -*-
"""人口桥接：复用 ``mpf_model`` 队列成分法，保证与强积金人口层一致。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_MPF = Path(__file__).resolve().parent.parent / "mpf_model"
if str(_MPF) not in sys.path:
    sys.path.insert(0, str(_MPF))

from data_loader import load_all_tables  # noqa: E402
from population import (  # noqa: E402
    ELDERLY_AGES,
    elderly_population,
    elderly_population_total,
    extract_base_population,
    project_population,
)


def load_shared_population(
    scenario: str = "中",
    start_year: int = 2026,
    end_year: int = 2056,
    base_year: int = 2026,
) -> pd.DataFrame:
    """加载与强积金相同的人口投影路径。

    Args:
        scenario: 低/中/高。
        start_year: 起始年。
        end_year: 终止年。
        base_year: 从 P1 表抽取基准人口的年份。

    Returns:
        ``project_population`` 长表。
    """
    tables = load_all_tables()
    base = extract_base_population(
        tables["population"], year=base_year, scenario=scenario
    )
    return project_population(
        tables["mortality"],
        base,
        scenario=scenario,
        start_year=start_year,
        end_year=end_year,
    )


def elderly_total_by_year(pop: pd.DataFrame, year: int) -> float:
    """某年 65+ 总人数。"""
    return elderly_population_total(pop, year)


def elderly_by_age_sex(pop: pd.DataFrame, year: int) -> pd.DataFrame:
    """某年 65+ 分年龄性别。"""
    return elderly_population(pop, year)


__all__ = [
    "ELDERLY_AGES",
    "load_shared_population",
    "elderly_total_by_year",
    "elderly_by_age_sex",
    "load_all_tables",
]
