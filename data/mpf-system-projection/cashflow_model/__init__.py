# -*- coding: utf-8 -*-
"""
强积金制度总账户 · 30 年现金流预测模型

运行：
  cd data/mpf-system-projection/cashflow_model
  python run.py
"""

from scenarios import SCENARIO_MAP, list_scenarios
from model import MPFCashflowModel, ProjectionResult, compare_scenarios

__all__ = [
    "SCENARIO_MAP",
    "list_scenarios",
    "MPFCashflowModel",
    "ProjectionResult",
    "compare_scenarios",
]
