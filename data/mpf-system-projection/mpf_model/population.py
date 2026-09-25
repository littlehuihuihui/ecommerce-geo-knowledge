# -*- coding: utf-8 -*-
"""第一层：队列成分法人口预测。

数据来源：
- 死亡率 / 基准人口：C&SD 表（经 P1 T01/T02 输入）
- 生育：官方推算 TFR 751→938 [真实数据路径]
- 迁移：总量级对齐官方、年龄权重 [假设]
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

AGE_GROUPS_5: List[str] = [
    "0-4",
    "5-9",
    "10-14",
    "15-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85+",
]
LABOUR_AGES = [
    "15-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
]
FERTILE = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]

# C&SD《人口推算》ASFR 形状（每千名女性）→ 缩放至目标 TFR
ASFR_SHAPE_2026 = {
    "15-19": 0.9,
    "20-24": 13.6,
    "25-29": 44.6,
    "30-34": 71.9,
    "35-39": 47.5,
    "40-44": 10.3,
    "45-49": 0.7,
}
ASFR_SHAPE_2046 = {
    "15-19": 1.2,
    "20-24": 16.3,
    "25-29": 46.9,
    "30-34": 72.8,
    "35-39": 42.5,
    "40-44": 9.2,
    "45-49": 0.6,
}
TFR_2023 = 751.0  # [真实数据] 每千名女性
TFR_2046 = 938.0  # [真实数据] 官方推算路径
SEX_RATIO_BIRTH = 1.06  # [假设] 男/女


def _age_mid(age: str) -> float:
    """年龄组中点。"""
    if age == "85+":
        return 90.0
    a, b = age.split("-")
    return (int(a) + int(b)) / 2.0


def _tfr(year: int, scenario: str) -> float:
    """目标总和生育率（每千名女性）。"""
    if year <= 2023:
        base = TFR_2023
    elif year >= 2046:
        base = TFR_2046
    else:
        base = TFR_2023 + (TFR_2046 - TFR_2023) * (year - 2023) / (2046 - 2023)
    if scenario == "高":
        return base * 1.10
    if scenario == "低":
        return base * 0.90
    return base


def _asfr(year: int, scenario: str) -> Dict[str, float]:
    """分年龄生育率（每名女性每年活产）。"""
    w = 0.0 if year <= 2026 else (1.0 if year >= 2046 else (year - 2026) / (2046 - 2026))
    shape = {
        a: (1 - w) * ASFR_SHAPE_2026[a] + w * ASFR_SHAPE_2046[a] for a in FERTILE
    }
    shape_tfr = 5.0 * sum(shape.values())
    scale = _tfr(year, scenario) / shape_tfr if shape_tfr else 1.0
    return {a: (shape[a] * scale) / 1000.0 for a in FERTILE}


def _net_migration(year: int, scenario: str) -> float:
    """年净迁移人数。[假设] 总量级对齐官方推算。"""
    knots = {2026: 51000, 2035: 73000, 2046: 45000, 2056: 35000}
    ys = sorted(knots)
    if year <= ys[0]:
        base = knots[ys[0]]
    elif year >= ys[-1]:
        base = knots[ys[-1]]
    else:
        base = knots[ys[0]]
        for i in range(len(ys) - 1):
            if ys[i] <= year <= ys[i + 1]:
                t0, t1 = ys[i], ys[i + 1]
                w = (year - t0) / (t1 - t0)
                base = knots[t0] * (1 - w) + knots[t1] * w
                break
    if scenario == "高":
        return base * 1.20
    if scenario == "低":
        return base * 0.70
    return base


def _mig_weights() -> Dict[Tuple[str, str], float]:
    """净迁移年龄性别权重（偏劳动年龄）[假设]。"""
    w: Dict[Tuple[str, str], float] = {}
    for age in AGE_GROUPS_5:
        mid = _age_mid(age)
        if mid < 15:
            base = 0.4
        elif mid < 45:
            base = 1.6
        elif mid < 65:
            base = 1.0
        else:
            base = 0.3
        w[(age, "男")] = base * 0.48
        w[(age, "女")] = base * 0.52
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


def _expand(pop5: Dict[Tuple[str, str], float]) -> Dict[Tuple[int, str], float]:
    """5岁组 → 单岁（组内均匀）；85+ 展到 85–99。"""
    out: Dict[Tuple[int, str], float] = {}
    for age in AGE_GROUPS_5:
        for sex in ("男", "女"):
            n = pop5.get((age, sex), 0.0)
            if age == "85+":
                ages = list(range(85, 100))
            else:
                lo, hi = map(int, age.split("-"))
                ages = list(range(lo, hi + 1))
            share = n / len(ages) if ages else 0.0
            for x in ages:
                out[(x, sex)] = share
    return out


def _aggregate(single: Dict[Tuple[int, str], float]) -> Dict[Tuple[str, str], float]:
    """单岁 → 5岁组。"""
    out = {(a, s): 0.0 for a in AGE_GROUPS_5 for s in ("男", "女")}
    for (x, sex), n in single.items():
        if x >= 85:
            out[("85+", sex)] += n
        else:
            lo = (x // 5) * 5
            out[(f"{lo}-{lo + 4}", sex)] += n
    return out


def _age5_of(x: int) -> str:
    """单岁 → 5岁组标签。"""
    if x >= 85:
        return "85+"
    lo = (x // 5) * 5
    return f"{lo}-{lo + 4}"


def build_mortality_index(mortality: pd.DataFrame) -> Dict[Tuple[int, str, str], float]:
    """构建 (年,性别,年龄组) → 死亡率(每千人) 索引。

    Args:
        mortality: P1 表1。

    Returns:
        字典索引。
    """
    idx: Dict[Tuple[int, str, str], float] = {}
    for _, r in mortality.iterrows():
        idx[(int(r["年份"]), r["性别"], r["年龄组"])] = float(r["死亡率_每千人"])
    return idx


def _q(
    mort_idx: Dict[Tuple[int, str, str], float],
    year: int,
    sex: str,
    age5: str,
) -> float:
    """死亡率每千人 → 粗死亡概率，封顶 0.8。"""
    m = mort_idx.get((year, sex, age5))
    if m is None:
        cands = [k for k in mort_idx if k[1] == sex and k[2] == age5]
        if not cands:
            return 0.0
        m = mort_idx[max(cands, key=lambda k: k[0])]
    return min(float(m) / 1000.0, 0.8)


def extract_base_population(
    population: pd.DataFrame,
    year: int = 2026,
    scenario: str = "中",
) -> pd.DataFrame:
    """从 P1 表2 抽取基准年分年龄性别人口。

    Args:
        population: P1 表2。
        year: 基准年。
        scenario: 人口情景。

    Returns:
        列：年龄组、性别、人数。
    """
    g = population[(population["年份"] == year) & (population["情景"] == scenario)]
    if g.empty:
        raise ValueError(f"基准人口为空 year={year} scenario={scenario}")
    return g[["年龄组", "性别", "人数"]].drop_duplicates(subset=["年龄组", "性别"])


def project_population(
    mortality: pd.DataFrame,
    base_pop: pd.DataFrame,
    scenario: str = "中",
    start_year: int = 2026,
    end_year: int = 2056,
) -> pd.DataFrame:
    """队列成分法主循环：存活 → 生育 → 迁移。

    Args:
        mortality: P1 表1（含预测段死亡率）。
        base_pop: 基准年分年龄性别人数（人）。
        scenario: 低/中/高（生育与迁移强弱）。
        start_year: 起始年（含）。
        end_year: 终止年（含）。

    Returns:
        长表：年份×年龄组×性别×人数。
    """
    pop5 = {(r["年龄组"], r["性别"]): float(r["人数"]) for _, r in base_pop.iterrows()}
    single = _expand(pop5)
    mig_w = _mig_weights()
    mort_idx = build_mortality_index(mortality)
    records = []

    for year in range(start_year, end_year + 1):
        agg = _aggregate(single)
        for age in AGE_GROUPS_5:
            for sex in ("男", "女"):
                records.append(
                    {
                        "年份": year,
                        "年龄组": age,
                        "性别": sex,
                        "人数": round(agg[(age, sex)], 1),
                        "情景": scenario,
                    }
                )
        if year == end_year:
            break

        new_single: Dict[Tuple[int, str], float] = {}
        for (x, sex), n in single.items():
            survivors = n * (1.0 - _q(mort_idx, year, sex, _age5_of(x)))
            x2 = min(x + 1, 99)
            new_single[(x2, sex)] = new_single.get((x2, sex), 0.0) + survivors

        asfr = _asfr(year, scenario)
        births = sum(agg[(a, "女")] * asfr[a] for a in FERTILE)
        girl = births / (1.0 + SEX_RATIO_BIRTH)
        boy = births - girl
        new_single[(0, "男")] = new_single.get((0, "男"), 0.0) + boy * (
            1 - 0.5 * _q(mort_idx, year, "男", "0-4")
        )
        new_single[(0, "女")] = new_single.get((0, "女"), 0.0) + girl * (
            1 - 0.5 * _q(mort_idx, year, "女", "0-4")
        )

        mig_total = _net_migration(year, scenario)
        for (age, sex), w in mig_w.items():
            add = mig_total * w
            if age == "85+":
                ages = list(range(85, 100))
            else:
                lo, hi = map(int, age.split("-"))
                ages = list(range(lo, hi + 1))
            share = add / len(ages)
            for x in ages:
                new_single[(x, sex)] = new_single.get((x, sex), 0.0) + share

        single = new_single

    return pd.DataFrame(records)


def labour_population(pop: pd.DataFrame, year: int) -> pd.DataFrame:
    """提取某年 15–64 岁分年龄性别劳动年龄人口。

    Args:
        pop: ``project_population`` 输出。
        year: 年份。

    Returns:
        仅含 LABOUR_AGES 的子集。
    """
    return pop[(pop["年份"] == year) & (pop["年龄组"].isin(LABOUR_AGES))].copy()


# 长者年龄组（综援长者部分 / 退休相关共用）
ELDERLY_AGES = ["65-69", "70-74", "75-79", "80-84", "85+"]


def elderly_population(pop: pd.DataFrame, year: int) -> pd.DataFrame:
    """提取某年 65 岁及以上分年龄性别人口。

    Args:
        pop: ``project_population`` 输出。
        year: 年份。

    Returns:
        仅含 ELDERLY_AGES 的子集。
    """
    return pop[(pop["年份"] == year) & (pop["年龄组"].isin(ELDERLY_AGES))].copy()


def elderly_population_total(pop: pd.DataFrame, year: int) -> float:
    """某年 65 岁及以上总人数（人）。"""
    return float(elderly_population(pop, year)["人数"].sum())


def new_age_65(pop: pd.DataFrame, year: int) -> float:
    """当年新达 65 岁人数近似 = Pop(60–64)/5。

    Args:
        pop: 人口投影表。
        year: 年份。

    Returns:
        人数（人）。
    """
    g = pop[(pop["年份"] == year) & (pop["年龄组"] == "60-64")]
    return float(g["人数"].sum()) / 5.0
