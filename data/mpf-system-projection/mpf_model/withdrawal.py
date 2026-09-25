# -*- coding: utf-8 -*-
"""第三层：领取（退休 + 永久离港 + 其他提取）。

循环依赖处理（重要）：
  人均余额用**期初**总资产 A_t / 账户数 推算，再算当年提取 W_t，
  最后才更新 A_{t+1}。同一年内不联立求解，故无代数循环依赖；
  存在一期滞后（今年提取不立刻改写用于计算自身的余额基数）。
"""

from __future__ import annotations

from typing import Dict, Optional

from population import new_age_65
from scenarios import ScenarioConfig

# ---------- 永久离港 ----------
# [真实数据] 2025 全年：2.42 万宗 / 58.86 亿
# [真实数据] 2026 Q2：5,200 宗 / 12.03 亿 → 年化约 48.12 亿（×4，假设）
# 若仍用「2025 起每年 -10%」，2026 得 52.97，高于 Q2 年化约 10% → 已改为锚定 2026 年化后再递减
DEPART_2025_YI = 58.86  # [真实数据]
DEPART_2025_CASES_WAN = 2.42  # [真实数据]
DEPART_2026_Q2_YI = 12.03  # [真实数据]
DEPART_2026_Q2_CASES = 5200  # [真实数据] 宗
DEPART_2026_YI = DEPART_2026_Q2_YI * 4.0  # [假设] 由季频年化
DEPART_ANNUAL_DECLINE = 0.10  # [假设] 2027 起相对上一年递减
DEPART_FLOOR_YEAR = 2035


def permanent_departure_withdrawal(
    year: int,
    base_2025_yi: float = DEPART_2025_YI,
    base_2026_yi: float = DEPART_2026_YI,
    decline_rate: float = DEPART_ANNUAL_DECLINE,
    floor_year: int = DEPART_FLOOR_YEAR,
) -> float:
    """独立计算永久离港提取（亿港元）。

    路径：2025 用全年真实锚点；2026 用 Q2×4 年化锚点；
    2027–floor_year 每年递减 decline_rate；其后持平。

    Args:
        year: 日历年。
        base_2025_yi: 2025 全年锚点。
        base_2026_yi: 2026 年化锚点（默认 Q2×4）。
        decline_rate: 2027 起年递减率。
        floor_year: 趋稳年。

    Returns:
        亿港元。
    """
    y = int(year)
    if y == 2025:
        return float(base_2025_yi)
    if y == 2026:
        return float(base_2026_yi)
    if y < 2025:
        # 回测：由 2025 按递减率反向
        return float(base_2025_yi / ((1.0 - decline_rate) ** (2025 - y)))
    # 2027+：自 2026 锚点递减
    t_cap = min(y, floor_year) - 2026
    return float(base_2026_yi * ((1.0 - decline_rate) ** t_cap))


def average_account_balance(
    aum_yi: float,
    accounts_wan: float,
    retire_premium: float = 1.6,
) -> float:
    """从**期初**制度总资产反推达龄人均余额（港元）。

    来源：aum / accounts × 溢价；溢价 1.6 为 [假设]。
    刻意使用期初 A，避免与当年 W 形成同期内生联立。
    """
    if accounts_wan <= 0:
        return 0.0
    avg = (aum_yi / accounts_wan) * 10000.0
    return avg * retire_premium


def compute_withdrawal(
    pop,
    year: int,
    aum_yi: float,
    accounts_wan: float,
    scenario: ScenarioConfig,
    extract_ratio: float = 1.0,
    other_share: Optional[float] = None,
    retire_premium: float = 1.6,
    balance_scale: float = 1.0,
) -> Dict[str, float]:
    """计算年度提取 = 退休 + 永久离港 + 其他（非离港）。

    退休：新达 65 岁 × 提取比例 × 期初推算余额。
    永久离港：独立外生路径（不依赖 A）。
    其他：不含离港，按退休块残余份额。
    """
    s = scenario.other_withdrawal_share if other_share is None else other_share
    s = min(max(float(s), 0.0), 0.40)

    n_retire = new_age_65(pop, year)
    bal = average_account_balance(aum_yi, accounts_wan, retire_premium) * balance_scale
    w_retire = n_retire * extract_ratio * bal / 1e8

    w_depart = permanent_departure_withdrawal(year)
    w_other = w_retire * s / (1.0 - s) if s < 1 else 0.0
    w_total = w_retire + w_depart + w_other

    return {
        "年份": year,
        "新达65岁人数": n_retire,
        "新达65岁_万人": n_retire / 10000.0,
        "提取比例": extract_ratio,
        "人均账户余额_港元": bal,
        "年退休提取_亿港元": w_retire,
        "年永久离港提取_亿港元": w_depart,
        "年其他提取_亿港元": w_other,
        "年总提取_亿港元": w_total,
        "其他提取占比_相对退休块": s,
        "余额计算口径": "期初资产/账户数×溢价（无期内循环）",
    }
