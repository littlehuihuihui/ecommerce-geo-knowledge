# -*- coding: utf-8 -*-
"""
强积金缴费层模型（Contribution Layer）
基于 population_ccm 分性别×5岁组人口，计算 2026–2056 缴费人数与供款。

核心：
  缴费人数 = Σ_age,sex  Pop × LFPR × 就业率 × 覆盖率
  强制供款 ≈ 规则引擎（有关入息上下限）或 N × ȳ × 12 × 10%
  自愿供款 = 总供款 × κ  →  Total = Forced / (1-κ)

情景（参数冲击，人口默认用中情景）：
  低/悲观：LFPR−2pp，入息名义增速−1pp
  中/基准：官方参与率日程 + 入息增速 3%
  高/乐观：LFPR+2pp，入息名义增速+1pp
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
POP_DIR = ROOT / "population_ccm"
OUT = ROOT / "contribution_layer"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
LABOUR_AGES = [
    "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64",
]

# —— 有关入息上下限（可替换接口）——
Y_MIN = 7100.0          # 港元/月；条例
Y_MAX = 30000.0         # 港元/月；条例
ALPHA_EE = 0.05
ALPHA_ER = 0.05
# 低于下限人群占比与其平均工资 [假设]
PI_LOW = 0.06
Y_LOW = 5500.0

# —— 就业 / 覆盖 ——
UNEMPLOYMENT = 0.037    # ~3.7% [citation:7]
EMPLOYMENT = 1.0 - UNEMPLOYMENT  # 0.963
COVERAGE = 0.85         # [假设] 就业人口强积金覆盖约85%

# —— 入息 ——
Y_BAR_2026 = 21500.0    # 缴费人平均有关入息；略高于中位数，并与2025≈907亿锚点校准 [假设]
G_WAGE_BASE = 0.03      # 名义增速 ≈ 通胀+实际工资 [假设]

# —— 自愿占总额比例 ——
KAPPA_VOL = 0.255       # 介于25%–26% [citation:2][citation:8]

# —— 劳动参与率：合计关键值（2026）来自用户规格 / 表230-28001 量级 ——
# 分性别：用「合计 + 性别差」还原；15-19/20-24 为 [假设] 补全
LFPR_BOTH_2026 = {
    "15-19": 0.18,   # [假设] 就学为主
    "20-24": 0.62,   # [假设] 衔接官方年轻组量级
    "25-29": 0.895,
    "30-34": 0.889,
    "35-39": 0.860,
    "40-44": 0.832,
    "45-49": 0.820,
    "50-54": 0.797,
    "55-59": 0.701,
    "60-64": 0.508,
}

# 男性相对合计的溢价（百分点），使 55-59：男83.6% / 女59.3%（合计约70.1%）
# 解：w_m * m + w_f * f = both；m = both + d, f = both - d*(Nm/Nf) 近似用固定差
MALE_PREMIUM_PP = {
    "15-19": 0.02,
    "20-24": 0.03,
    "25-29": 0.04,
    "30-34": 0.05,
    "35-39": 0.06,
    "40-44": 0.07,
    "45-49": 0.09,
    "50-54": 0.11,
    "55-59": 0.135,  # 70.1+13.5=83.6；女侧约 70.1- (13.5*Nm/Nf) 用人口权重校准
    "60-64": 0.16,
}


def lfpr_by_sex(age: str, sex: str, pop_m: float, pop_f: float, both: float, premium: float) -> float:
    """由合计 LFPR 与男性溢价，按人口权重还原分性别 LFPR。"""
    # both = (Nm*m + Nf*f)/(Nm+Nf), m = f + delta → 解 f, m
    # 令 m = both + d_adj, 使加权成立
    n = pop_m + pop_f
    if n <= 0:
        return both
    # 目标：男 = min(0.98, both + premium)，女由恒等式反推
    male = min(0.98, both + premium)
    # both*n = Nm*male + Nf*female → female = (both*n - Nm*male)/Nf
    if pop_f <= 0:
        return male if sex == "男" else both
    female = (both * n - pop_m * male) / pop_f
    female = float(np.clip(female, 0.05, 0.98))
    male = float(np.clip(male, 0.05, 0.98))
    return male if sex == "男" else female


def scenario_params(code: str) -> dict:
    """低/中/高 → 参与率冲击、入息增速。"""
    if code == "低":
        return {"label": "悲观", "lfpr_shock": -0.02, "g_wage": G_WAGE_BASE - 0.01, "pop_scenario": "中"}
    if code == "高":
        return {"label": "乐观", "lfpr_shock": +0.02, "g_wage": G_WAGE_BASE + 0.01, "pop_scenario": "中"}
    return {"label": "基准", "lfpr_shock": 0.0, "g_wage": G_WAGE_BASE, "pop_scenario": "中"}


def y_bar(year: int, g: float) -> float:
    """平均有关入息（截断到法定上下限带内的建模均值）。"""
    y = Y_BAR_2026 * ((1.0 + g) ** (year - 2026))
    # 封顶效应：均值不应超过 Y_MAX；下限附近另用 π_low 处理
    return float(min(y, Y_MAX))


def mandatory_per_member_annual(y: float) -> float:
    """
    单人年强制供款（港元），体现上下限：
    - y < Y_MIN: 雇员0 + 雇主 5%*y
    - Y_MIN ≤ y ≤ Y_MAX: 10%*y
    - y > Y_MAX: 10%*Y_MAX
    对「平均人」用混合：π_low 走低薪规则，其余走 min(y,Y_MAX) 的10%。
    """
    # 低薪组
    c_low = ALPHA_ER * min(Y_LOW, Y_MAX) * 12.0
    # 常规组（已用平均有关入息，默认落在带内）
    y_rel = min(max(y, Y_MIN), Y_MAX)
    c_norm = (ALPHA_EE + ALPHA_ER) * y_rel * 12.0
    return PI_LOW * c_low + (1.0 - PI_LOW) * c_norm


def load_population() -> pd.DataFrame:
    path = POP_DIR / "P02_population_by_age_sex.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少人口层输出: {path}")
    return pd.read_csv(path)


def run_layer(pop: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """生成表1人数、表2供款、表3参数、驱动拆解。"""
    rows_n: List[dict] = []
    rows_c: List[dict] = []
    rows_drv: List[dict] = []

    # 参数表
    param_rows = []
    for code in ("低", "中", "高"):
        sp = scenario_params(code)
        param_rows.extend([
            {"参数名": "employment_rate", "数值": round(EMPLOYMENT, 4), "单位": "比例",
             "情景": code, "来源或假设": f"1−失业率{UNEMPLOYMENT:.1%}；失业率约3.7%[citation:7]"},
            {"参数名": "mpf_coverage_rate", "数值": COVERAGE, "单位": "比例",
             "情景": code, "来源或假设": "[假设] 就业人口强积金覆盖约85%（豁免职业计划/短期外籍雇员等）"},
            {"参数名": "relevant_income_min_monthly", "数值": Y_MIN, "单位": "港元/月",
             "情景": code, "来源或假设": "强积金条例有关入息下限；可替换接口"},
            {"参数名": "relevant_income_max_monthly", "数值": Y_MAX, "单位": "港元/月",
             "情景": code, "来源或假设": "强积金条例有关入息上限；可替换接口"},
            {"参数名": "avg_relevant_income_2026", "数值": Y_BAR_2026, "单位": "港元/月",
             "情景": code, "来源或假设": "缴费人平均有关入息；参考2025Q3中位数约20,500并校准至2025总供款≈907亿[假设]"},
            {"参数名": "nominal_wage_growth", "数值": sp["g_wage"], "单位": "年率",
             "情景": code, "来源或假设": f"基准约3%=通胀+实际工资[假设]；本情景冲击后={sp['g_wage']:.0%}"},
            {"参数名": "lfpr_level_shock", "数值": sp["lfpr_shock"], "单位": "百分点(小数)",
             "情景": code, "来源或假设": "乐观+2pp / 悲观−2pp / 基准0"},
            {"参数名": "voluntary_share_of_total", "数值": KAPPA_VOL, "单位": "比例",
             "情景": code, "来源或假设": "2025Q4约25%、2025-26财年约26%[citation:2][citation:8]；取25.5%"},
            {"参数名": "pi_low_income_share", "数值": PI_LOW, "单位": "比例",
             "情景": code, "来源或假设": "[假设] 月入低于下限的缴费人占比"},
        ])
        for age, v in LFPR_BOTH_2026.items():
            param_rows.append({
                "参数名": f"lfpr_both_{age}",
                "数值": v,
                "单位": "比例",
                "情景": code,
                "来源或假设": "政府统计处表230-28001量级/用户给定2026关键值；15-19·20-24为[假设]补全",
            })

    params = pd.DataFrame(param_rows)

    for code in ("低", "中", "高"):
        sp = scenario_params(code)
        pop_sc = pop[pop["情景"] == sp["pop_scenario"]].copy()
        years = sorted(pop_sc["年份"].unique())
        prev = None  # for drivers

        for year in years:
            ysub = pop_sc[pop_sc["年份"] == year]
            y_avg = y_bar(year, sp["g_wage"])
            c_person = mandatory_per_member_annual(y_avg)  # 港元/人·年

            # 分年龄性别人数
            n_by_sex = {"男": 0.0, "女": 0.0}
            n_total = 0.0
            detailed = []

            for age in LABOUR_AGES:
                pm = float(ysub[(ysub["年龄组"] == age) & (ysub["性别"] == "男")]["人数"].sum())
                pf = float(ysub[(ysub["年龄组"] == age) & (ysub["性别"] == "女")]["人数"].sum())
                both = LFPR_BOTH_2026[age]
                # 参与率随老龄化可轻微下移 [假设]：每十年 −0.5pp（仅55+）
                aging_adj = -0.005 * max(0, (year - 2026) / 10.0) if age in ("55-59", "60-64") else 0.0
                both_t = float(np.clip(both + aging_adj + sp["lfpr_shock"], 0.05, 0.98))
                prem = MALE_PREMIUM_PP[age]
                for sex, p in (("男", pm), ("女", pf)):
                    lfpr = lfpr_by_sex(age, sex, pm, pf, both_t, prem)

                    n = p * lfpr * EMPLOYMENT * COVERAGE
                    n_by_sex[sex] += n
                    n_total += n
                    detailed.append({
                        "年份": year,
                        "年龄组": age,
                        "性别": sex,
                        "人口_人": round(p, 1),
                        "劳动参与率": round(lfpr, 4),
                        "就业率": round(EMPLOYMENT, 4),
                        "覆盖率": COVERAGE,
                        "缴费人数_人": round(n, 1),
                        "情景": code,
                        "情景标签": sp["label"],
                        "来源或假设": "Pop×LFPR×就业率×覆盖率；LFPR分性别由表230-28001合计+性别差还原",
                    })

            rows_n.extend(detailed)
            # 混合行（按年龄汇总）
            for age in LABOUR_AGES:
                chunk = [d for d in detailed if d["年龄组"] == age]
                rows_n.append({
                    "年份": year,
                    "年龄组": age,
                    "性别": "混合",
                    "人口_人": round(sum(d["人口_人"] for d in chunk), 1),
                    "劳动参与率": round(
                        sum(d["劳动参与率"] * d["人口_人"] for d in chunk) / max(sum(d["人口_人"] for d in chunk), 1),
                        4,
                    ),
                    "就业率": round(EMPLOYMENT, 4),
                    "覆盖率": COVERAGE,
                    "缴费人数_人": round(sum(d["缴费人数_人"] for d in chunk), 1),
                    "情景": code,
                    "情景标签": sp["label"],
                    "来源或假设": "男+女合计",
                })

            # 供款（亿港元）
            forced_hkd = n_total * c_person
            forced_yi = forced_hkd / 1e8
            # V = κ/(1-κ) * Forced；Total = Forced/(1-κ)
            vol_yi = forced_yi * (KAPPA_VOL / (1.0 - KAPPA_VOL))
            total_yi = forced_yi + vol_yi

            # 简单10%对照
            simple_yi = n_total * y_avg * 12.0 * 0.10 / 1e8

            row_c = {
                "年份": year,
                "情景": code,
                "情景标签": sp["label"],
                "缴费人数_万人": round(n_total / 1e4, 4),
                "缴费人数_男_万人": round(n_by_sex["男"] / 1e4, 4),
                "缴费人数_女_万人": round(n_by_sex["女"] / 1e4, 4),
                "平均有关入息_港元每月": round(y_avg, 2),
                "年强制性供款_亿港元": round(forced_yi, 4),
                "年自愿性供款_亿港元": round(vol_yi, 4),
                "年总供款_亿港元": round(total_yi, 4),
                "自愿占总供款比例": KAPPA_VOL,
                "简单10%对照_亿港元": round(simple_yi, 4),
                "单人年强制供款_港元": round(c_person, 2),
                "来源或假设": "强制含低于下限雇主仍缴5%修正；自愿=强制×κ/(1-κ)；校准锚2025总供款约907亿",
            }
            rows_c.append(row_c)

            # 驱动拆解（相对上一年）
            if prev is not None:
                # C = N * c_person / 1e8 / (1-κ)  for total
                # 对数近似或加法：ΔTotal ≈ ΔN效应 + Δ入息效应 + 交叉
                n0, n1 = prev["n"], n_total
                c0, c1 = prev["c_person"], c_person
                t0, t1 = prev["total"], total_yi
                # 强制部分驱动
                f0, f1 = prev["forced"], forced_yi
                dn_effect = (n1 - n0) * c0 / 1e8
                dy_effect = n0 * (c1 - c0) / 1e8
                cross = (n1 - n0) * (c1 - c0) / 1e8
                vol_scale = 1.0 / (1.0 - KAPPA_VOL)
                rows_drv.append({
                    "年份": year,
                    "情景": code,
                    "情景标签": sp["label"],
                    "总供款_亿港元": round(t1, 4),
                    "总供款同比变动_亿港元": round(t1 - t0, 4),
                    "驱动_缴费人数_亿港元": round(dn_effect * vol_scale, 4),
                    "驱动_人均供款入息_亿港元": round(dy_effect * vol_scale, 4),
                    "驱动_交叉项_亿港元": round(cross * vol_scale, 4),
                    "缴费人数变动_万人": round((n1 - n0) / 1e4, 4),
                    "人均强制供款变动_港元": round(c1 - c0, 2),
                    "来源或假设": "加法拆解：Δ(N·c)=ΔN·c0+N0·Δc+ΔN·Δc，再按1/(1-κ)放大至含自愿的总供款",
                })

            prev = {"n": n_total, "c_person": c_person, "forced": forced_yi, "total": total_yi}

    t1 = pd.DataFrame(rows_n)
    t2 = pd.DataFrame(rows_c)
    t3 = params
    t4 = pd.DataFrame(rows_drv)
    return t1, t2, t3, t4


def write_dictionary() -> None:
    text = """# 强积金缴费层 · 数据字典

> **输入**：`population_ccm/P02_population_by_age_sex.csv`（15–64 岁组）  
> **输出目录**：`contribution_layer/`  
> **年份**：2026–2056  

## 表清单

| 文件 | 内容 |
|------|------|
| `C01_contributors_by_age_sex.csv` | 分年龄性别（含混合）缴费人数 |
| `C02_contribution_breakdown.csv` | 强制/自愿/总供款（年度×情景） |
| `C03_assumptions.csv` | 关键假设参数 |
| `C04_growth_drivers.csv` | 供款同比增长驱动拆解 |
| `C00_data_dictionary.md` | 本字典 |

## 核心公式

```
缴费人数_age,sex = Pop_age,sex × LFPR_age,sex × 就业率 × 覆盖率
强制供款 = Σ 人数 × 单人年强制供款(有关入息规则)
自愿供款 = 强制 × κ/(1−κ)    （κ=自愿占总供款比例）
总供款 = 强制 + 自愿 = 强制/(1−κ)
```

## 情景

| 码 | 标签 | LFPR | 入息名义增速 |
|----|------|------|--------------|
| 低 | 悲观 | −2pp | 2%/年 |
| 中 | 基准 | 0 | 3%/年 |
| 高 | 乐观 | +2pp | 4%/年 |

人口路径默认取人口层**中**情景，以便隔离缴费参数敏感性。

## 可替换接口（条例参数）

代码顶部常量：`Y_MIN` / `Y_MAX` / `ALPHA_EE` / `ALPHA_ER` / `COVERAGE` / `KAPPA_VOL`。

## 校准锚点

- 2025 年总供款约 **907 亿**；2025–26 财年约 **912.3 亿**
- 模型 2026 基准总供款应落在同一量级（约 8.5–10.5 百亿）
"""
    (OUT / "C00_data_dictionary.md").write_text(text, encoding="utf-8")


def main() -> None:
    np.random.seed(RANDOM_SEED)
    pop = load_population()
    t1, t2, t3, t4 = run_layer(pop)
    t1.to_csv(OUT / "C01_contributors_by_age_sex.csv", index=False, encoding="utf-8-sig")
    t2.to_csv(OUT / "C02_contribution_breakdown.csv", index=False, encoding="utf-8-sig")
    t3.to_csv(OUT / "C03_assumptions.csv", index=False, encoding="utf-8-sig")
    t4.to_csv(OUT / "C04_growth_drivers.csv", index=False, encoding="utf-8-sig")
    write_dictionary()

    base = t2[(t2["情景"] == "中") & (t2["年份"] == 2026)].iloc[0]
    print("=== 2026 基准校准 ===")
    print(f"缴费人数 {base['缴费人数_万人']:.1f} 万人")
    print(f"强制 {base['年强制性供款_亿港元']:.1f} 亿 | 自愿 {base['年自愿性供款_亿港元']:.1f} 亿 | 总计 {base['年总供款_亿港元']:.1f} 亿")
    print(f"简单10%对照 {base['简单10%对照_亿港元']:.1f} 亿")
    print("锚点参考：2025年约907亿 / 2025-26财年912.3亿")
    print("\n三情景 2026 / 2056 总供款：")
    for sc in ("低", "中", "高"):
        a = t2[(t2["情景"] == sc) & (t2["年份"] == 2026)].iloc[0]
        b = t2[(t2["情景"] == sc) & (t2["年份"] == 2056)].iloc[0]
        print(f"  {sc}({a['情景标签']}): {a['年总供款_亿港元']:.1f} → {b['年总供款_亿港元']:.1f} 亿")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
