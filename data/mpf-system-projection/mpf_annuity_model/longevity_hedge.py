# -*- coding: utf-8 -*-
"""第四层：长寿风险对冲效果。

无年金化：收入完全依赖账户 → 耗尽后归零（除其他收入）
有年金化：终身地板 > 0 → 长寿缺口幅度下降

提升幅度定义：
  保障提升 = 地板覆盖率(有年金) − 地板覆盖率(0%年金)
  缺口发生率下降 = 以预期余命为终点，耗尽早于死亡的情形减少
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from engine import analyze_one
from pricing import (
    ANNUITIZE_RATIOS,
    RANDOM_SEED,
    R_RETIRE,
    REPLACEMENT_TARGET,
    RETIRE_AGE,
    SimpleHKAnnuityPricer,
    e65_for_sex,
)


def _sample_lives(e65: float, n: int, rng: np.random.Generator) -> np.ndarray:
    cv = 0.25
    sigma = np.sqrt(np.log(1 + cv**2))
    mu = np.log(e65) - 0.5 * sigma**2
    return np.clip(rng.lognormal(mu, sigma, size=n), 5.0, 45.0)


def longevity_hedge_metrics(
    balance: float,
    final_annual_salary: float,
    sex: str,
    return_label: str,
    ratios: Optional[List[float]] = None,
    n_sim: int = 2000,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """对每个年金化比例，用 MC 余命评估「收入归零前」是否覆盖死亡。

    判定：
      - 若存在终身年金地板 > 0：视为**永不因账户耗尽而收入归零**（长寿保障）
      - 若年金化=0：耗尽年龄 < 死亡年龄 → 长寿缺口
    """
    ratios = ratios or ANNUITIZE_RATIOS
    pricer = SimpleHKAnnuityPricer()
    rng = np.random.default_rng(seed + (0 if sex == "男" else 17))
    lives = _sample_lives(e65_for_sex(sex), n_sim, rng)
    death_ages = RETIRE_AGE + lives

    base0 = analyze_one(
        balance, final_annual_salary, sex, return_label, 0.0, pricer=pricer
    )
    floor0 = float(base0["耗尽后年收入_港元_终身地板"])

    rows = []
    for ratio in ratios:
        row = analyze_one(
            balance, final_annual_salary, sex, return_label, ratio, pricer=pricer
        )
        floor = float(row["耗尽后年收入_港元_终身地板"])
        dep = row["账户耗尽年龄"]
        # MC：缺口 = 死亡时总收入能力不足（此处：无地板且耗尽早于死亡）
        if floor > 1.0:
            # 有终身年金：定义「收入归零缺口」发生率为 0
            gap_rate = 0.0
            # 但仍可能地板 < 目标支出 → 「充足性缺口」
            target = final_annual_salary * REPLACEMENT_TARGET
            adequacy_gap = float(np.mean(death_ages > 0)) * (
                1.0 if floor < target - 1 else 0.0
            )
            # 上面 adequacy 对所有人相同；改为：存活期内地板低于目标的比例
            adequacy_gap_rate = 1.0 if floor < target - 1 else 0.0
        else:
            # 无年金：用对象三剩余耗尽
            if dep is None or (isinstance(dep, float) and np.isinf(dep)):
                gap_rate = 0.0
            else:
                gap_rate = float(np.mean(death_ages > float(dep)))
            adequacy_gap_rate = gap_rate

        floor_cov = float(row["终身地板覆盖目标支出_pct"] or 0.0)
        floor0_cov = float(base0["终身地板覆盖目标支出_pct"] or 0.0)

        rows.append(
            {
                "性别": sex,
                "回报情景": return_label,
                "年金化比例": ratio,
                "终身地板_年收入_港元": round(floor, 2),
                "地板覆盖目标_pct": floor_cov,
                "相对0%年金_地板覆盖提升_pp": round(floor_cov - floor0_cov, 2),
                "账户耗尽年龄": dep if dep is not None else "∞（或不适用）",
                "MC长寿缺口发生率_收入归零": round(gap_rate, 4),
                "相对0%_缺口发生率下降_pp": round(
                    (float(base0.get("_gap0", gap_rate) if ratio > 0 else gap_rate) - gap_rate)
                    * 100
                    if ratio == 0
                    else 0,
                    2,
                ),
                "目标支出充足性缺口_地板不足": round(adequacy_gap_rate, 4),
                "权衡": "年金化解决长寿风险，但降低流动性",
            }
        )

    # 第二遍修正：0% 的 gap 作为基准
    out = pd.DataFrame(rows)
    gap0 = float(out.loc[out["年金化比例"] == 0.0, "MC长寿缺口发生率_收入归零"].iloc[0])
    out["相对0%_缺口发生率下降_pp"] = (
        (gap0 - out["MC长寿缺口发生率_收入归零"]) * 100.0
    ).round(2)
    out["相对0%_终身保障提升说明"] = out.apply(
        lambda r: (
            f"地板覆盖 +{r['相对0%年金_地板覆盖提升_pp']}pp；"
            f"收入归零风险 −{r['相对0%_缺口发生率下降_pp']}pp"
        ),
        axis=1,
    )
    return out


def hedge_table_all(balances: pd.DataFrame, n_sim: int = 2000) -> pd.DataFrame:
    """全性别×情景的对冲效果表。"""
    parts = []
    for _, r in balances.iterrows():
        parts.append(
            longevity_hedge_metrics(
                float(r["退休时账户余额_港元"]),
                float(r["退休前年薪_港元"]),
                str(r["性别"]),
                str(r["回报情景"]),
                n_sim=n_sim,
            )
        )
    return pd.concat(parts, ignore_index=True)


def depletion_age_distribution_points(
    balances: pd.DataFrame,
    sex: str = "男",
    scenario: str = "基准",
) -> pd.DataFrame:
    """图用：各年金化比例对应的「账户耗尽年龄」（剩余部分）。"""
    hit = balances[(balances["性别"] == sex) & (balances["回报情景"] == scenario)]
    if hit.empty:
        return pd.DataFrame()
    r = hit.iloc[0]
    rows = []
    for ratio in ANNUITIZE_RATIOS:
        a = analyze_one(
            float(r["退休时账户余额_港元"]),
            float(r["退休前年薪_港元"]),
            sex,
            scenario,
            ratio,
        )
        dep = a["账户耗尽年龄"]
        rows.append(
            {
                "性别": sex,
                "回报情景": scenario,
                "年金化比例": ratio,
                "账户耗尽年龄": 120.0 if dep is None else float(dep),
                "耗尽年龄_显示": "∞/不耗尽" if dep is None else str(dep),
                "终身地板_港元": a["耗尽后年收入_港元_终身地板"],
            }
        )
    return pd.DataFrame(rows)
