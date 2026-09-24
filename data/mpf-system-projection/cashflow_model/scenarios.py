# -*- coding: utf-8 -*-
"""三情景参数配置（对接 Prompt 1-2 §8）。

CSV 情景码：低 / 中 / 高  ↔  悲观 / 基准 / 乐观。
表 1–5 的路径变量由 CSV 提供；本模块存放扩展控制参数。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


RANDOM_SEED: int = 42

SCENARIO_MAP: Dict[str, str] = {
    "低": "悲观",
    "中": "基准",
    "高": "乐观",
}

SCENARIO_CSV_CODES: List[str] = ["低", "中", "高"]


@dataclass(frozen=True)
class ScenarioParams:
    """单个情景的模型控制参数。

    Attributes:
        csv_code: Prompt 1-1 CSV 情景列取值。
        label: 对外名称（悲观/基准/乐观）。
        kappa: 自愿供款占强制供款比例。
        phi: 行政费用率（占期初资产）。
        se_share: 自雇占缴费人数比例。
        se_income_factor: 自雇入息相对雇员均值折算。
        pi_low: 月入低于下限的受雇比例。
        y_low: 低薪组平均月工资（港元）。
        lambda_dep: 永久离港提前取款强度。
        lambda_incap: 完全丧失行为能力强度。
        lambda_other: 其他核准提前取款强度。
        early_balance_factor: 提前取款人均余额相对退休队列折算。
        cons_weight_drift: 保守基金配置每年上调幅度。
        use_income_band_engine: 是否启用有关入息分段+自雇规则引擎。
        aum0_scale: 初值资产情景缩放（推荐均为 1.0）。
    """

    csv_code: str
    label: str
    kappa: float
    phi: float
    se_share: float
    se_income_factor: float
    pi_low: float
    y_low: float
    lambda_dep: float
    lambda_incap: float
    lambda_other: float
    early_balance_factor: float
    cons_weight_drift: float
    use_income_band_engine: bool = True
    aum0_scale: float = 1.0

    def to_dict(self) -> dict:
        """导出为普通字典。"""
        return asdict(self)


PESSIMISTIC = ScenarioParams(
    csv_code="低",
    label="悲观",
    kappa=0.04,
    phi=0.0025,
    se_share=0.12,
    se_income_factor=0.90,
    pi_low=0.07,
    y_low=5500.0,
    lambda_dep=0.004,
    lambda_incap=0.0005,
    lambda_other=0.0004,
    early_balance_factor=0.60,
    cons_weight_drift=0.006,
    aum0_scale=1.0,
)

BASE = ScenarioParams(
    csv_code="中",
    label="基准",
    kappa=0.08,
    phi=0.0020,
    se_share=0.12,
    se_income_factor=0.90,
    pi_low=0.06,
    y_low=5500.0,
    lambda_dep=0.003,
    lambda_incap=0.0004,
    lambda_other=0.0003,
    early_balance_factor=0.60,
    cons_weight_drift=0.004,
    aum0_scale=1.0,
)

OPTIMISTIC = ScenarioParams(
    csv_code="高",
    label="乐观",
    kappa=0.12,
    phi=0.0015,
    se_share=0.12,
    se_income_factor=0.90,
    pi_low=0.05,
    y_low=5500.0,
    lambda_dep=0.002,
    lambda_incap=0.0003,
    lambda_other=0.0002,
    early_balance_factor=0.60,
    cons_weight_drift=0.002,
    aum0_scale=1.0,
)


SCENARIOS: Dict[str, ScenarioParams] = {
    "低": PESSIMISTIC,
    "中": BASE,
    "高": OPTIMISTIC,
    "悲观": PESSIMISTIC,
    "基准": BASE,
    "乐观": OPTIMISTIC,
}


def get_scenario(name: str) -> ScenarioParams:
    """按 CSV 码或中文标签取情景参数。

    Args:
        name: 「低/中/高」或「悲观/基准/乐观」。

    Returns:
        ScenarioParams 实例。

    Raises:
        KeyError: 未知情景名。
    """
    if name not in SCENARIOS:
        raise KeyError(f"未知情景: {name!r}，可选: {list_scenarios()}")
    return SCENARIOS[name]


def list_scenarios() -> List[str]:
    """返回标准 CSV 情景码列表。"""
    return list(SCENARIO_CSV_CODES)
