# -*- coding: utf-8 -*-
"""三层收入合并与替代率。

退休后月收入 ≈
  第一支柱（综援/长津/生果金，互斥）
+ 第二支柱（强积金剩余提取，可耗尽）
+ 第三支柱（年金终身地板 + 其他自愿储蓄，本模块年金来自对象四）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pillar1 import (
    REPLACEMENT_TARGET_HIGH,
    REPLACEMENT_TARGET_LOW,
    REPLACEMENT_TARGET_MID,
    FirstPillarChoice,
    PersonMeans,
    first_pillar_monthly,
)


@dataclass
class PillarIncomes:
    """三层月收入拆解。"""

    pillar1_monthly: float
    pillar1_label: str
    pillar1_ok: bool
    pillar1_note: str
    mpf_draw_monthly: float  # 第二支柱：剩余账户提取（可耗尽）
    annuity_monthly: float  # 第三支柱：终身年金
    other_monthly: float = 0.0

    @property
    def total_monthly(self) -> float:
        return (
            self.pillar1_monthly
            + self.mpf_draw_monthly
            + self.annuity_monthly
            + self.other_monthly
        )

    @property
    def floor_monthly(self) -> float:
        """耗尽 MPF 剩余提取后仍在的收入（长寿地板）。"""
        return self.pillar1_monthly + self.annuity_monthly + self.other_monthly


def combine_replacement(
    pre_retire_annual_salary: float,
    pillar1_choice: FirstPillarChoice,
    means: PersonMeans,
    mpf_draw_annual: float,
    annuity_annual: float,
    other_annual: float = 0.0,
) -> Dict[str, Any]:
    """合并三层并计算替代率。

    Args:
        pre_retire_annual_salary: 退休前年薪。
        pillar1_choice: 第一支柱选择。
        means: 入息·资产状况（年金月付应已计入 means.monthly_income_ex_welfare）。
        mpf_draw_annual: 强积金剩余年提取。
        annuity_annual: 年金年收入。
        other_annual: 其他（如 QDAP，默认 0）。
    """
    p1_m, note, ok = first_pillar_monthly(pillar1_choice, means)
    incomes = PillarIncomes(
        pillar1_monthly=p1_m,
        pillar1_label=pillar1_choice.value,
        pillar1_ok=ok,
        pillar1_note=note,
        mpf_draw_monthly=mpf_draw_annual / 12.0,
        annuity_monthly=annuity_annual / 12.0,
        other_monthly=other_annual / 12.0,
    )
    pre_m = pre_retire_annual_salary / 12.0
    rr_early = incomes.total_monthly / pre_m if pre_m > 0 else float("nan")
    rr_floor = incomes.floor_monthly / pre_m if pre_m > 0 else float("nan")

    def band(rr: float) -> str:
        if rr != rr:
            return "—"
        if rr < REPLACEMENT_TARGET_LOW:
            return "低于40%（可能不足）"
        if rr <= REPLACEMENT_TARGET_HIGH:
            return "落在40%–70%建议带"
        return "高于70%（较充足/或目标设定偏低）"

    gap_to_50 = max(0.0, REPLACEMENT_TARGET_MID * pre_m - incomes.total_monthly)

    return {
        "第一支柱": incomes.pillar1_label,
        "第一支柱_获批": ok,
        "第一支柱_说明": note,
        "第一支柱_月_港元": round(p1_m, 2),
        "第二支柱_MPF提取_月_港元": round(incomes.mpf_draw_monthly, 2),
        "第三支柱_年金_月_港元": round(incomes.annuity_monthly, 2),
        "其他_月_港元": round(incomes.other_monthly, 2),
        "退休初期_总月收入_港元": round(incomes.total_monthly, 2),
        "长寿地板_月收入_港元": round(incomes.floor_monthly, 2),
        "退休前年薪_月_港元": round(pre_m, 2),
        "替代率_初期": round(rr_early, 4),
        "替代率_地板": round(rr_floor, 4),
        "替代率_初期_pct": round(100 * rr_early, 2),
        "替代率_地板_pct": round(100 * rr_floor, 2),
        "对照世界银行带_初期": band(rr_early),
        "对照世界银行带_地板": band(rr_floor),
        "相对50%目标_月缺口_港元": round(gap_to_50, 2),
        "概念提示": "长津≠综援≠生果金≠年金；长津与综援/生果金互斥",
    }
