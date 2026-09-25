# -*- coding: utf-8 -*-
"""第四层：长寿风险与账户耗尽年龄分布（蒙特卡洛）。

对每条路径：
  - 抽取 65 岁后余命（围绕官方余命锚点）
  - 抽取退休后逐年回报（均值 r_retire，波动 σ）
  - 按选定提取规则推演耗尽年龄
  - 比较耗尽年龄 vs 死亡年龄 → 长寿缺口

强积金不提供长寿风险保障：存活超过耗尽年龄时无自动年金续付。
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from params import RANDOM_SEED, R_RETIRE_DEFAULT, WITHDRAW_PCT_DEFAULT, e65_for_sex
from retirement import years_until_deplete


def sample_remaining_life(
    e65: float,
    n: int,
    rng: np.random.Generator,
    cv: float = 0.25,
) -> np.ndarray:
    """抽样余命（年）。均值≈e65，变异系数 cv [假设]。

    使用对数正态并截断到 [5, 45]，避免负值与极端。
    """
    sigma = np.sqrt(np.log(1 + cv**2))
    mu = np.log(e65) - 0.5 * sigma**2
    x = rng.lognormal(mu, sigma, size=n)
    return np.clip(x, 5.0, 45.0)


def monte_carlo_depletion(
    balance: float,
    final_annual_salary: float,
    retire_age: int,
    sex: str,
    mode: str = "pct4",
    replacement: float = 0.50,
    withdraw_pct: float = WITHDRAW_PCT_DEFAULT,
    r_retire_mean: float = R_RETIRE_DEFAULT,
    r_sigma: float = 0.08,
    n_sim: int = 2000,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """蒙特卡洛：耗尽年龄与长寿缺口分布。

    Args:
        balance: 退休余额。
        final_annual_salary: 前年薪。
        retire_age: 退休年龄。
        sex: 性别。
        mode: ``pct4`` | ``replacement`` | ``lump_replacement``。
        replacement: 目标替代率。
        withdraw_pct: 比例提取。
        r_retire_mean: 退休后回报均值。
        r_sigma: 单年回报标准差 [假设]。
        n_sim: 模拟次数。
        seed: 随机种子。

    Returns:
        (明细表, 分位数字典)。
    """
    rng = np.random.default_rng(seed)
    e65 = e65_for_sex(sex)
    lives = sample_remaining_life(e65, n_sim, rng)

    if mode == "pct4":
        base_w = balance * withdraw_pct
        r0 = r_retire_mean
    elif mode == "replacement":
        base_w = final_annual_salary * replacement
        r0 = r_retire_mean
    else:  # lump_replacement
        base_w = final_annual_salary * replacement
        r0 = 0.0

    deplete_ages = np.empty(n_sim)
    death_ages = retire_age + lives
    shortfall = np.empty(n_sim)

    for i in range(n_sim):
        # 简化：用路径平均回报近似（避免逐年嵌套过慢）
        # 抽一条「等效常数回报」= clip(正态)
        r_i = float(np.clip(rng.normal(r0, r_sigma / 2.5), -0.15, 0.20))
        if mode == "lump_replacement":
            r_i = 0.0
        y = years_until_deplete(balance, base_w, r_retire=r_i, max_years=80)
        d_age = retire_age + y
        deplete_ages[i] = d_age
        shortfall[i] = max(0.0, death_ages[i] - d_age)

    detail = pd.DataFrame(
        {
            "sim_id": np.arange(n_sim),
            "性别": sex,
            "提取模式": mode,
            "余命_年": np.round(lives, 2),
            "死亡年龄": np.round(death_ages, 2),
            "账户耗尽年龄": np.round(deplete_ages, 2),
            "长寿缺口_年": np.round(shortfall, 2),
            "是否长寿缺口": (shortfall > 0.5).astype(int),
        }
    )

    def q(a: np.ndarray, p: float) -> float:
        return float(np.percentile(a, p))

    summary = {
        "性别": sex,
        "提取模式": mode,
        "N": n_sim,
        "e65_锚点": e65,
        "耗尽年龄_P10": round(q(deplete_ages, 10), 2),
        "耗尽年龄_P50": round(q(deplete_ages, 50), 2),
        "耗尽年龄_P90": round(q(deplete_ages, 90), 2),
        "死亡年龄_P50": round(q(death_ages, 50), 2),
        "长寿缺口发生率": round(float((shortfall > 0.5).mean()), 4),
        "缺口年数_P50_条件": round(
            float(np.median(shortfall[shortfall > 0.5])) if (shortfall > 0.5).any() else 0.0,
            2,
        ),
        "制度局限": "强积金不提供长寿风险保障",
    }
    return detail, summary


def run_longevity_by_sex(
    balance_male: float,
    balance_female: float,
    salary_male: float,
    salary_female: float,
    retire_age: int = 65,
    n_sim: int = 2000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """男女各跑三模式，汇总分位数。"""
    summaries = []
    details = []
    for sex, bal, sal in (
        ("男", balance_male, salary_male),
        ("女", balance_female, salary_female),
    ):
        for mode in ("pct4", "replacement", "lump_replacement"):
            d, s = monte_carlo_depletion(
                bal, sal, retire_age, sex, mode=mode, n_sim=n_sim
            )
            summaries.append(s)
            details.append(d)
    return pd.DataFrame(summaries), pd.concat(details, ignore_index=True)
