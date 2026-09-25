# -*- coding: utf-8 -*-
"""第二层：合资格层。

合资格长者人数 = 65岁以上人口 × 申请率 × 资产审查通过率
               = 65岁以上人口 × 综合有效领取率

综合有效领取率由「年老个案 / 65+人口」反推，再拆分为申请率×通过率（拆分为假设）。
"""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from scenarios import (
    APPLY_RATE_SHARE_OF_EFFECTIVE,
    CALIB_ELDERLY_CASES,
    CALIB_YEAR,
)


def calibrate_effective_rate(
    elderly_pop: float,
    cases: float = CALIB_ELDERLY_CASES,
) -> float:
    """由个案锚点与 65+ 人口反推综合有效领取率。

    Args:
        elderly_pop: 校准年 65 岁及以上人数（人）。
        cases: 年老综援个案宗数。

    Returns:
        综合有效领取率（小数）。
    """
    if elderly_pop <= 0:
        raise ValueError("elderly_pop 必须为正")
    return float(cases) / float(elderly_pop)


def split_apply_and_pass(
    effective_rate: float,
    apply_share: float = APPLY_RATE_SHARE_OF_EFFECTIVE,
) -> Tuple[float, float]:
    """将综合率拆成申请率 × 审查通过率。

    Args:
        effective_rate: 综合有效领取率。
        apply_share: 综合率中归因于「申请意愿」的份额 [假设]。

    Returns:
        (申请率, 审查通过率)。
    """
    # effective = apply × pass；令 apply = sqrt 风格不稳定，改用份额：
    # apply = effective / pass_share_of_applicants_who_pass...
    # 简化：审查通过率固定为 apply_share 的互补解释 —
    # 设审查通过率 = apply_share（例如 0.55），申请率 = effective / 通过率
    pass_rate = float(apply_share)
    if pass_rate <= 0 or pass_rate > 1:
        raise ValueError("apply_share 应在 (0,1]")
    apply_rate = float(effective_rate) / pass_rate
    if apply_rate > 1.0:
        # 若拆分不合理，退回对称开方
        apply_rate = pass_rate = float(effective_rate) ** 0.5
    return apply_rate, pass_rate


def eligible_elderly(
    pop65: float,
    effective_rate: float,
) -> float:
    """合资格（领取）长者人数。

    Args:
        pop65: 65 岁及以上人口。
        effective_rate: 综合有效领取率 = 申请率 × 通过率。

    Returns:
        人数（人），对应「年老个案」量级。
    """
    return float(pop65) * float(effective_rate)


def build_eligibility_table(
    pop: pd.DataFrame,
    years: range,
    effective_rate: float,
    apply_rate: float,
    pass_rate: float,
) -> pd.DataFrame:
    """逐年合资格表。

    Args:
        pop: 人口投影长表（与强积金共用）。
        years: 年份范围。
        effective_rate: 综合有效领取率。
        apply_rate: 申请率（展示用）。
        pass_rate: 审查通过率（展示用）。

    Returns:
        逐年 DataFrame。
    """
    from population_bridge import elderly_total_by_year

    rows = []
    for y in years:
        p65 = elderly_total_by_year(pop, y)
        n = eligible_elderly(p65, effective_rate)
        rows.append(
            {
                "年份": y,
                "人口_65岁及以上_人": round(p65, 1),
                "人口_65岁及以上_万人": round(p65 / 1e4, 4),
                "申请率": round(apply_rate, 6),
                "资产审查通过率": round(pass_rate, 6),
                "综合有效领取率": round(effective_rate, 6),
                "合资格长者_人": round(n, 1),
                "合资格长者_万人": round(n / 1e4, 4),
                "申请率来源": "[假设] 由综合率拆分",
                "通过率来源": "[假设] 由综合率拆分",
                "综合率来源": f"[反推] {CALIB_YEAR}年老个案/{CALIB_YEAR}年65+人口",
            }
        )
    return pd.DataFrame(rows)


def rate_sources_dict(effective: float, apply: float, pass_r: float) -> Dict[str, str]:
    """参数来源说明表。"""
    return {
        "综合有效领取率": f"{effective:.4%}；[反推] 年老个案{CALIB_ELDERLY_CASES:.0f}/65+人口",
        "申请率": f"{apply:.4%}；[假设] 拆分自综合率",
        "资产审查通过率": f"{pass_r:.4%}；[假设] 拆分自综合率",
        "校准个案": f"{CALIB_ELDERLY_CASES:.0f}；[真实数据] 2025-03 个案×56.7%",
    }
