# -*- coding: utf-8 -*-
"""
香港人口队列成分法（Cohort Component）投影引擎
作为强积金模型「第一层」：输出分性别、5岁组人口 2026–2056。

数据源（优先真实）：
- 死亡率：C&SD 表 115-01023（API get.php）
- 基准人口：C&SD 表 110-01001A 年中人口（不含外佣）
- 生育：C&SD《香港人口推算 2022–2046》表5 ASFR / TFR 路径
- 迁移：对齐官方推算总量级，年龄性别结构为研究假设

方法：
1. 将5岁组按均匀假设展开为单岁，逐年存活推进，再汇总回5岁组
2. 死亡率：2020–2024（剔2022）估计年化改善率，再按「随年龄递减」的平滑日程外推
3. 生育：ASFR 形状取官方表5，缩放至目标 TFR（基准/高+10%/低-10%）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "cashflow_model" / "_raw"
OUT = ROOT / "population_ccm"
OUT.mkdir(parents=True, exist_ok=True)

AGE_GROUPS_5 = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79",
    "80-84", "85+",
]
FERTILE = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]
# 官方表5：2026 / 2046 ASFR（每千名女性），用于形状
ASFR_SHAPE_2026 = {
    "15-19": 0.9, "20-24": 13.6, "25-29": 44.6, "30-34": 71.9,
    "35-39": 47.5, "40-44": 10.3, "45-49": 0.7,
}  # TFR≈943
ASFR_SHAPE_2046 = {
    "15-19": 1.2, "20-24": 16.3, "25-29": 46.9, "30-34": 72.8,
    "35-39": 42.5, "40-44": 9.2, "45-49": 0.6,
}  # TFR=938

# 用户指定基准 TFR：2023=751 → 2046=938（每千名女性）
TFR_2023_BASE = 751.0
TFR_2046_BASE = 938.0

SEX_RATIO_BIRTH = 1.06  # 男婴/女婴 [假设] 贴近香港近年水平
RANDOM_SEED = 42


def load_mortality() -> pd.DataFrame:
    """加载 115-01023 年龄性别死亡率（每千人）。"""
    data = json.loads((RAW / "mort_api.bin").read_text(encoding="utf-8"))["dataSet"]
    rows = []
    for r in data:
        if r.get("sv") != "ASMR":
            continue
        if r.get("SEX") not in ("M", "F"):
            continue
        if not r.get("AGE"):
            continue
        rows.append(
            {
                "年份": int(r["period"]),
                "年龄码": r["AGE"],
                "年龄组": normalize_age(r["AGE"], r["AGEDesc"]),
                "性别": "男" if r["SEX"] == "M" else "女",
                "死亡率_每千人": float(r["figure"]) if r["figure"] != "" else np.nan,
            }
        )
    return pd.DataFrame(rows)


def normalize_age(code: str, desc: str) -> str:
    """统一年龄组标签。"""
    mapping = {
        "1-": "<1",
        "1-4": "1-4",
        "5-9": "5-9",
        "10-14": "10-14",
        "15-19": "15-19",
        "20-24": "20-24",
        "25-29": "25-29",
        "30-34": "30-34",
        "35-39": "35-39",
        "40-44": "40-44",
        "45-49": "45-49",
        "50-54": "50-54",
        "55-59": "55-59",
        "60-64": "60-64",
        "65-69": "65-69",
        "70-74": "70-74",
        "75-79": "75-79",
        "80-84": "80-84",
        "85_and_over": "85+",
        "0-4": "0-4",
    }
    return mapping.get(code, desc.replace(" ", "").replace("–", "-"))


def load_base_population(period: str = "202606") -> pd.DataFrame:
    """加载表110-01001A 指定年中人口（千人 → 人）。"""
    data = json.loads((RAW / "pop_api.bin").read_text(encoding="utf-8"))["dataSet"]
    rows = []
    for r in data:
        if r.get("period") != period:
            continue
        # 同一 sv 下含「人数」与「占总人口%」两套 figure，必须只取人数
        if r.get("svDesc") != "Number ('000)":
            continue
        if r.get("SEX") not in ("M", "F"):
            continue
        if not r.get("AGE"):
            continue
        age = normalize_age(r["AGE"], r["AGEDesc"])
        if age not in AGE_GROUPS_5:
            continue
        rows.append(
            {
                "年份": int(period[:4]),
                "年龄组": age,
                "性别": "男" if r["SEX"] == "M" else "女",
                "人数": float(r["figure"]) * 1000.0,  # 原单位千人
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"基准人口为空 period={period}")
    # 防御性去重
    df = df.drop_duplicates(subset=["年龄组", "性别"], keep="first")
    return df


def combine_mort_0_4(mort: pd.DataFrame) -> pd.DataFrame:
    """将 <1 与 1-4 合成 0-4（权重 1:4）。"""
    parts = []
    for (year, sex), g in mort.groupby(["年份", "性别"]):
        d = {row["年龄组"]: row["死亡率_每千人"] for _, row in g.iterrows()}
        if "<1" in d and "1-4" in d:
            m04 = (1.0 * d["<1"] + 4.0 * d["1-4"]) / 5.0
        elif "0-4" in d:
            m04 = d["0-4"]
        else:
            continue
        for age in AGE_GROUPS_5:
            if age == "0-4":
                m = m04
            else:
                m = d.get(age, np.nan)
            parts.append({"年份": year, "性别": sex, "年龄组": age, "死亡率_每千人": m})
    return pd.DataFrame(parts)


def annual_improvement(m0: float, m1: float, years: float) -> float:
    """年化改善率（正数=死亡率下降）。m_t = m_0 * (1-g)^t。"""
    if m0 <= 0 or m1 <= 0 or years <= 0:
        return 0.0
    # m1 = m0 * (1-g)^years → g = 1 - (m1/m0)^(1/years)
    ratio = m1 / m0
    g = 1.0 - ratio ** (1.0 / years)
    return float(g)


def age_mid(age: str) -> float:
    if age == "85+":
        return 90.0
    a, b = age.split("-")
    return (int(a) + int(b)) / 2.0


def build_improvement_schedule(mort5: pd.DataFrame) -> pd.DataFrame:
    """
    用 2020、2021、2023、2024 估计经验改善率（剔 2022），
    再拟合「随年龄递减」日程：目标 60-64≈1.5%、80-84≈0.5%。
    """
    use_years = [2020, 2021, 2023, 2024]
    rows = []
    for sex in ("男", "女"):
        emp = {}
        for age in AGE_GROUPS_5:
            series = []
            for y in use_years:
                v = mort5[(mort5["年份"] == y) & (mort5["性别"] == sex) & (mort5["年龄组"] == age)]
                if not v.empty and pd.notna(v.iloc[0]["死亡率_每千人"]):
                    series.append((y, float(v.iloc[0]["死亡率_每千人"])))
            if len(series) >= 2:
                # 用首末年跨度（2020→2024 = 4年）
                y0, m0 = series[0]
                y1, m1 = series[-1]
                emp[age] = annual_improvement(m0, m1, y1 - y0)
            else:
                emp[age] = np.nan

        # 线性日程：g(x) 锚定 62.5→1.5%、82.5→0.5%，再与经验各半
        schedule = {}
        for age in AGE_GROUPS_5:
            x = age_mid(age)
            g_prior = 0.015 - 0.010 * (x - 62.5) / 20.0
            g_prior = float(np.clip(g_prior, 0.002, 0.025))
            g_emp = emp.get(age, np.nan)
            if pd.notna(g_emp):
                g = 0.5 * max(g_emp, 0.0) + 0.5 * g_prior
            else:
                g = g_prior
            schedule[age] = float(np.clip(g, 0.002, 0.025))

        # 强制随年龄组单调不增（高龄改善不超过相邻较年轻组）
        for i in range(1, len(AGE_GROUPS_5)):
            a0, a1 = AGE_GROUPS_5[i - 1], AGE_GROUPS_5[i]
            if schedule[a1] > schedule[a0]:
                schedule[a1] = schedule[a0]

        for age in AGE_GROUPS_5:
            g = schedule[age]
            rows.append(
                {
                    "性别": sex,
                    "年龄组": age,
                    "经验年化改善率": None if pd.isna(emp.get(age)) else round(emp[age], 6),
                    "采用年化改善率": round(g, 6),
                    "方法说明": "2020-2024剔2022经验 + 年龄递减先验(60-64≈1.5%,80-84≈0.5%)各半；并强制随年龄单调不增",
                }
            )
    return pd.DataFrame(rows)


def project_mortality(
    mort5: pd.DataFrame,
    improv: pd.DataFrame,
    start_hist: int = 2020,
    end_proj: int = 2056,
) -> pd.DataFrame:
    """输出表1：历史实际 + 按改善率外推的预测死亡率。"""
    records = []
    hist_years = list(range(start_hist, 2026))
    for y in hist_years:
        for sex in ("男", "女"):
            for age in AGE_GROUPS_5:
                v = mort5[(mort5["年份"] == y) & (mort5["性别"] == sex) & (mort5["年龄组"] == age)]
                if v.empty:
                    continue
                m = float(v.iloc[0]["死亡率_每千人"])
                g = float(
                    improv[(improv["性别"] == sex) & (improv["年龄组"] == age)].iloc[0]["采用年化改善率"]
                )
                records.append(
                    {
                        "年份": y,
                        "性别": sex,
                        "年龄组": age,
                        "死亡率_每千人": round(m, 4),
                        "年化改善率": round(g, 6),
                        "数据类型": "实际" if y != 2022 else "实际_疫情年",
                        "来源或假设": "C&SD表115-01023" + ("；建模时改善率估计已剔除本年份" if y == 2022 else ""),
                    }
                )

    # 以 2024 为外推锚（若缺则 2025/2023）
    anchor_year = 2024
    for sex in ("男", "女"):
        for age in AGE_GROUPS_5:
            g = float(
                improv[(improv["性别"] == sex) & (improv["年龄组"] == age)].iloc[0]["采用年化改善率"]
            )
            base_rows = mort5[
                (mort5["年份"] == anchor_year) & (mort5["性别"] == sex) & (mort5["年龄组"] == age)
            ]
            if base_rows.empty:
                base_rows = mort5[
                    (mort5["年份"] == 2025) & (mort5["性别"] == sex) & (mort5["年龄组"] == age)
                ]
            if base_rows.empty:
                continue
            m_anchor = float(base_rows.iloc[0]["死亡率_每千人"])
            for y in range(2026, end_proj + 1):
                # m_y = m_2024 * (1-g)^(y-2024)
                m = m_anchor * ((1.0 - g) ** (y - anchor_year))
                records.append(
                    {
                        "年份": y,
                        "性别": sex,
                        "年龄组": age,
                        "死亡率_每千人": round(m, 4),
                        "年化改善率": round(g, 6),
                        "数据类型": "预测",
                        "来源或假设": f"以{anchor_year}实际为锚，按年龄递减年化改善率外推；非固定1%",
                    }
                )
    return pd.DataFrame(records)


def tfr_path(year: int, scenario: str) -> float:
    """基准 TFR 线性：2023=751 → 2046=938；高/低 ±10%。"""
    if year <= 2023:
        base = TFR_2023_BASE
    elif year >= 2046:
        base = TFR_2046_BASE
    else:
        base = TFR_2023_BASE + (TFR_2046_BASE - TFR_2023_BASE) * (year - 2023) / (2046 - 2023)
    # 2046后持平至2056
    if year > 2046:
        base = TFR_2046_BASE
    if scenario == "高":
        return base * 1.10
    if scenario == "低":
        return base * 0.90
    return base


def asfr_for_year(year: int, scenario: str) -> Dict[str, float]:
    """插值官方 ASFR 形状并缩放至目标 TFR。返回每名女性生育率（非每千）。"""
    t0, t1 = 2026, 2046
    w = 0.0 if year <= t0 else (1.0 if year >= t1 else (year - t0) / (t1 - t0))
    shape = {}
    for a in FERTILE:
        shape[a] = (1 - w) * ASFR_SHAPE_2026[a] + w * ASFR_SHAPE_2046[a]
    shape_tfr = 5.0 * sum(shape.values())  # 5岁组 ASFR 求和×5
    target = tfr_path(year, scenario)
    scale = target / shape_tfr if shape_tfr > 0 else 1.0
    # 返回小数：每名女性每年活产
    return {a: (shape[a] * scale) / 1000.0 for a in FERTILE}


def expand_to_single_year(pop5: Dict[Tuple[str, str], float]) -> Dict[Tuple[int, str], float]:
    """5岁组 → 单岁（组内均匀）。85+ 展到 85–99 共15岁。"""
    out = {}
    for age, sex in [(a, s) for a in AGE_GROUPS_5 for s in ("男", "女")]:
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


def aggregate_to_5(single: Dict[Tuple[int, str], float]) -> Dict[Tuple[str, str], float]:
    """单岁 → 5岁组。"""
    out = {(a, s): 0.0 for a in AGE_GROUPS_5 for s in ("男", "女")}
    for (x, sex), n in single.items():
        if x >= 85:
            out[("85+", sex)] += n
        else:
            lo = (x // 5) * 5
            key = f"{lo}-{lo+4}"
            out[(key, sex)] += n
    return out


def mort_rate(mort_idx: dict, year: int, sex: str, age5: str) -> float:
    """取死亡率（每千人）→ 概率近似 q=m/1000。"""
    m = mort_idx.get((year, sex, age5))
    if m is None:
        # 回退：同性别年龄最近年份
        cands = [k for k in mort_idx if k[1] == sex and k[2] == age5]
        if not cands:
            return 0.0
        m = mort_idx[max(cands, key=lambda k: k[0])]
    return min(float(m) / 1000.0, 0.8)


def build_mort_index(mort_tbl: pd.DataFrame) -> dict:
    """(年,性别,年龄组) → 死亡率_每千人。"""
    return {
        (int(r["年份"]), r["性别"], r["年龄组"]): float(r["死亡率_每千人"])
        for _, r in mort_tbl.iterrows()
    }


def age5_of(x: int) -> str:
    if x >= 85:
        return "85+"
    lo = (x // 5) * 5
    return f"{lo}-{lo+4}"


def net_migration_total(year: int, scenario: str) -> float:
    """
    年净迁移人数。对齐官方推算量级（约 +4.5万～+7万/年），
    高情景 +20%，低情景 -30%（迁移波动大于生育）。
    来源量级：C&SD人口推算表1增长成分；结构假设。
    """
    # 平滑路径：2026≈5.1万 → 2035峰值≈7.3万 → 2046≈4.5万 → 2056≈3.5万
    knots = {2026: 51000, 2035: 73000, 2046: 45000, 2056: 35000}
    years = sorted(knots)
    if year <= years[0]:
        base = knots[years[0]]
    elif year >= years[-1]:
        base = knots[years[-1]]
    else:
        for i in range(len(years) - 1):
            if years[i] <= year <= years[i + 1]:
                t0, t1 = years[i], years[i + 1]
                w = (year - t0) / (t1 - t0)
                base = knots[t0] * (1 - w) + knots[t1] * w
                break
    if scenario == "高":
        return base * 1.20
    if scenario == "低":
        return base * 0.70
    return base


def migration_age_sex_weights() -> Dict[Tuple[str, str], float]:
    """净迁移年龄性别权重（偏劳动年龄）[假设]。"""
    # 相对权重
    w = {}
    for age in AGE_GROUPS_5:
        mid = age_mid(age)
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


def run_ccm(
    base_pop: pd.DataFrame,
    mort_tbl: pd.DataFrame,
    scenario: str,
    start: int = 2026,
    end: int = 2056,
) -> pd.DataFrame:
    """队列成分法主循环（年步长）。"""
    pop5 = {(r["年龄组"], r["性别"]): float(r["人数"]) for _, r in base_pop.iterrows()}
    single = expand_to_single_year(pop5)
    mig_w = migration_age_sex_weights()
    mort_idx = build_mort_index(mort_tbl)
    records = []

    for year in range(start, end + 1):
        # 记录本年年中结构
        agg = aggregate_to_5(single)
        for age in AGE_GROUPS_5:
            for sex in ("男", "女"):
                records.append(
                    {
                        "年份": year,
                        "年龄组": age,
                        "性别": sex,
                        "人数": round(agg[(age, sex)], 1),
                        "情景": scenario,
                        "来源或假设": "队列成分法推算；基准人口=表110-01001A中2026年中",
                    }
                )

        if year == end:
            break

        # —— 存活到下一年 ——
        new_single: Dict[Tuple[int, str], float] = {}
        for (x, sex), n in single.items():
            q = mort_rate(mort_idx, year, sex, age5_of(x))
            survivors = n * (1.0 - q)
            x2 = x + 1
            if x2 > 99:
                new_single[(99, sex)] = new_single.get((99, sex), 0.0) + survivors
            else:
                new_single[(x2, sex)] = new_single.get((x2, sex), 0.0) + survivors

        # —— 出生 ——
        asfr = asfr_for_year(year, scenario)
        births = 0.0
        for age in FERTILE:
            women = agg[(age, "女")]
            births += women * asfr[age]
        girl = births / (1.0 + SEX_RATIO_BIRTH)
        boy = births - girl
        q0 = mort_rate(mort_idx, year, "男", "0-4") * 0.5
        q0f = mort_rate(mort_idx, year, "女", "0-4") * 0.5
        new_single[(0, "男")] = new_single.get((0, "男"), 0.0) + boy * (1 - q0)
        new_single[(0, "女")] = new_single.get((0, "女"), 0.0) + girl * (1 - q0f)

        # —— 净迁移 ——
        mig_total = net_migration_total(year, scenario)
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


def build_summary(pop: pd.DataFrame) -> pd.DataFrame:
    """表3：劳动年龄、准退休、退休汇总。"""
    rows = []
    for (year, scenario, sex), g in pop.groupby(["年份", "情景", "性别"]):
        def s(ages):
            return float(g[g["年龄组"].isin(ages)]["人数"].sum())

        labour = s([a for a in AGE_GROUPS_5 if a not in ("0-4", "5-9", "10-14") and not a.startswith("65") and a != "85+" and not a.startswith("7") and not a.startswith("8")])
        # 更清晰：
        labour_ages = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"]
        pre_retire = ["55-59"]
        retire = ["65-69", "70-74", "75-79", "80-84", "85+"]
        child = ["0-4", "5-9", "10-14"]
        rows.append(
            {
                "年份": year,
                "情景": scenario,
                "性别": sex,
                "总人口": round(float(g["人数"].sum()), 1),
                "少儿0_14": round(s(child), 1),
                "劳动人口15_64": round(s(labour_ages), 1),
                "准退休55_59": round(s(pre_retire), 1),
                "退休65及以上": round(s(retire), 1),
                "老龄化率_65plus占比": round(s(retire) / float(g["人数"].sum()), 4) if g["人数"].sum() else 0,
                "来源或假设": "由表2汇总；准退休=55-59供强积金缴费层/领取层衔接",
            }
        )
    # 混合=男+女
    both = []
    for (year, scenario), g in pop.groupby(["年份", "情景"]):
        def s(ages):
            return float(g[g["年龄组"].isin(ages)]["人数"].sum())

        labour_ages = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"]
        pre_retire = ["55-59"]
        retire = ["65-69", "70-74", "75-79", "80-84", "85+"]
        child = ["0-4", "5-9", "10-14"]
        tot = float(g["人数"].sum())
        both.append(
            {
                "年份": year,
                "情景": scenario,
                "性别": "混合",
                "总人口": round(tot, 1),
                "少儿0_14": round(s(child), 1),
                "劳动人口15_64": round(s(labour_ages), 1),
                "准退休55_59": round(s(pre_retire), 1),
                "退休65及以上": round(s(retire), 1),
                "老龄化率_65plus占比": round(s(retire) / tot, 4) if tot else 0,
                "来源或假设": "男+女合计；可供可视化男/女/混合切换",
            }
        )
    return pd.concat([pd.DataFrame(rows), pd.DataFrame(both)], ignore_index=True)


def write_data_dictionary() -> None:
    text = """# 香港人口队列成分法 · 数据字典（强积金模型第一层）

> **版本**：v1.0  
> **投影期**：2026–2056（年中口径）  
> **方法**：Cohort Component Method（单岁展开 + 年步长存活/生育/迁移，再汇总5岁组）  
> **目录**：`data/mpf-system-projection/population_ccm/`  
> **衔接**：为准退休队列（55–59）、劳动年龄（15–64）、退休（65+）向 MPF 缴费/领取层提供输入。

---

## 1. 表清单

| 文件 | 内容 | 主键 |
|------|------|------|
| `P01_mortality_rates.csv` | 分年龄性别死亡率（2020–2025实际 + 2026–2056预测）及年化改善率 | 年份×性别×年龄组 |
| `P02_population_by_age_sex.csv` | 分年龄组、分性别人口（三情景） | 年份×年龄组×性别×情景 |
| `P03_key_age_aggregates.csv` | 劳动/准退休/退休等关键汇总（含混合） | 年份×情景×性别 |
| `P00_improvement_schedule.csv` | 改善率估计明细（经验 + 采用值） | 性别×年龄组 |
| `P00_data_dictionary.md` | 本字典 | — |

情景码：**低 / 中 / 高** ↔ 较低生育·迁移 / 基准 / 较高生育·迁移。

---

## 2. 字段定义

### 表1 `P01_mortality_rates.csv`

| 字段 | 类型 | 说明 | 来源/假设 |
|------|------|------|-----------|
| 年份 | int | 日历年 | — |
| 性别 | string | 男 / 女 | — |
| 年龄组 | string | 0-4 … 80-84, 85+ | 0-4 由 `<1` 与 `1-4` 按 1:4 合成 |
| 死亡率_每千人 | float | 年龄性别死亡率 | **实际**：C&SD 表 **115-01023**；**预测**：见改善率 |
| 年化改善率 | float | 正数表示死亡率年降幅 | 2020–2024（**剔除2022**）经验 + 年龄递减先验各半 |
| 数据类型 | string | 实际 / 实际_疫情年 / 预测 | 2022 保留但标注疫情年 |
| 来源或假设 | string | 可追溯说明 | — |

**改善率先验**：随年龄递减，约 60–64 ≈ **1.5%/年**，80–84 ≈ **0.5%/年**（用户规格）；封顶 2.5%，地板 0.2%。  
**外推**：\\(m_y = m_{2024}\\cdot(1-g)^{y-2024}\\)，**非**固定 1%。

### 表2 `P02_population_by_age_sex.csv`

| 字段 | 类型 | 说明 | 来源/假设 |
|------|------|------|-----------|
| 年份 | int | 2026–2056 | — |
| 年龄组 | string | 5岁组 | — |
| 性别 | string | 男 / 女 | 可视化可再聚合为「混合」 |
| 人数 | float | 人 | 年中概念 |
| 情景 | string | 低/中/高 | — |
| 来源或假设 | string | — | 基准人口：**110-01001A** 2026年中（不含外佣） |

**生育**：ASFR 形状取 C&SD《人口推算2022–2046》表5；TFR 基准由 **2023=751** 线性升至 **2046=938**（用户指定，对齐官方「回升至938」叙事）；高/低 = 基准 ±10%。  
**出生性别比**：1.06（男/女）**[假设]**。  
**迁移**：总量级对齐官方推算净移入（约数万/年）；年龄性别权重偏 15–44 岁 **[假设]**；高 +20% / 低 −30%。

### 表3 `P03_key_age_aggregates.csv`

| 字段 | 类型 | 说明 |
|------|------|------|
| 年份 | int | — |
| 情景 | string | 低/中/高 |
| 性别 | string | 男 / 女 / **混合** |
| 总人口 | float | 人 |
| 少儿0_14 | float | 0–14 |
| 劳动人口15_64 | float | 15–64（缴费层主力池） |
| 准退休55_59 | float | **准退休队列**（领取层前置） |
| 退休65及以上 | float | 65+ |
| 老龄化率_65plus占比 | float | 65+/总人口 |
| 来源或假设 | string | — |

---

## 3. 核心算法（口述版）

1. **存量存活**：单岁人数 × (1 − q_{年龄组,性别,年}) → 下一岁。  
2. **新增出生**：Σ 育龄女性 × ASFR；按性别比拆分后计入 0 岁。  
3. **迁移**：年净迁移总量按权重加到各年龄性别。  
4. 每年末将单岁**汇总回 5 岁组**输出。

---

## 4. 与强积金模型衔接

| 本层输出 | MPF 层用途 |
|----------|------------|
| 劳动人口15–64 | 缴费人数上限 / 覆盖率分母 |
| 准退休55–59 | 「未来5年进入可提取」队列预警 |
| 退休65+ | 领取层规模；校准提取人数 R_t |
| 分性别 | 可视化男/女/混合；精算差异扩展 |

---

## 5. 局限

- 5岁组均匀展单岁为近似；真实队列分布非均匀。  
- 115-01023 的 `<1`/`1-4` 合成 0–4 用固定 1:4 权重。  
- 迁移年龄结构非官方微观公布，属研究假设。  
- 官方推算止于 2046；本层延至 2056 时 TFR 与迁移为外推持平/缓降。  
- 不含外籍家庭佣工（与生育率分母口径一致）。

---

## 6. 原始下载

```
https://www.censtatd.gov.hk/api/get.php?id=115-01023&lang=en&full_series=1
https://www.censtatd.gov.hk/api/get.php?id=110-01001A&lang=en&full_series=1
```
"""
    (OUT / "P00_data_dictionary.md").write_text(text, encoding="utf-8")


def main() -> None:
    np.random.seed(RANDOM_SEED)
    print("Loading mortality 115-01023 ...")
    mort_raw = load_mortality()
    mort5 = combine_mort_0_4(mort_raw)
    print("Building improvement schedule ...")
    improv = build_improvement_schedule(mort5)
    improv.to_csv(OUT / "P00_improvement_schedule.csv", index=False, encoding="utf-8-sig")
    print("Projecting mortality table ...")
    mort_out = project_mortality(mort5, improv)
    mort_out.to_csv(OUT / "P01_mortality_rates.csv", index=False, encoding="utf-8-sig")

    print("Loading base population 202606 ...")
    base = load_base_population("202606")
    print("Base total", base["人数"].sum() / 1e4, "万人")

    all_pop = []
    for sc in ("低", "中", "高"):
        print("CCM scenario", sc)
        pop = run_ccm(base, mort_out, sc)
        all_pop.append(pop)
    pop_all = pd.concat(all_pop, ignore_index=True)
    pop_all.to_csv(OUT / "P02_population_by_age_sex.csv", index=False, encoding="utf-8-sig")

    summary = build_summary(pop_all)
    summary.to_csv(OUT / "P03_key_age_aggregates.csv", index=False, encoding="utf-8-sig")

    write_data_dictionary()

    # 控制台示例
    print("\n=== 表1 示例 ===")
    print(mort_out[(mort_out["年份"].isin([2021, 2024, 2036])) & (mort_out["年龄组"] == "60-64") & (mort_out["性别"] == "男")].to_string(index=False))
    print("\n=== 表2 示例 ===")
    print(pop_all[(pop_all["年份"] == 2026) & (pop_all["情景"] == "中") & (pop_all["年龄组"].isin(["55-59", "60-64", "65-69"]))].to_string(index=False))
    print("\n=== 表3 示例 ===")
    print(summary[(summary["年份"].isin([2026, 2036, 2056])) & (summary["情景"] == "中") & (summary["性别"] == "混合")].to_string(index=False))
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
