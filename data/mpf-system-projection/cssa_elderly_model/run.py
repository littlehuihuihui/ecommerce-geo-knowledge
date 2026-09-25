# -*- coding: utf-8 -*-
"""综援长者财政支出模型 · 主入口。

三层：人口（共用 MPF CCM）→ 合资格 → 支出。
输出 2026–2056 三情景逐年表与摘要。

用法::

    python run.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from eligibility import (
    build_eligibility_table,
    calibrate_effective_rate,
    rate_sources_dict,
    split_apply_and_pass,
)
from expenditure import build_expenditure_table
from population_bridge import elderly_total_by_year, load_shared_population
from scenarios import (
    CALIB_ELDERLY_CASES,
    CALIB_YEAR,
    CSSA_BUDGET_2025_26_YI,
    CSSA_ELDERLY_CASES_2025_03,
    CSSA_ELDERLY_SHARE_2025_03,
    CSSA_TOTAL_SPEND_2024_25_YI,
    MONTHLY_ALLOWANCE_2025,
    SCENARIOS,
    get_scenario,
)

OUT = _PKG / "output"
OUT.mkdir(parents=True, exist_ok=True)

START, END = 2026, 2056


def project_one(code: str, base_effective: float, apply: float, pass_r: float) -> Dict:
    """单情景投影。"""
    sc = get_scenario(code)
    pop = load_shared_population(sc.pop_scenario, START, END)
    eff = base_effective * sc.effective_rate_mult
    # 情景乘数作用在综合率上；拆分同比缩放申请率，通过率保持解释稳定
    apply_s = apply * sc.effective_rate_mult
    if apply_s > 0.99:
        apply_s = 0.99
        pass_use = eff / apply_s
    else:
        pass_use = pass_r

    elig = build_eligibility_table(
        pop, range(START, END + 1), eff, apply_s, pass_use
    )
    annual = build_expenditure_table(elig, sc.inflation, sc.code, sc.label)

    y0 = annual[annual["年份"] == START].iloc[0]
    y1 = annual[annual["年份"] == END].iloc[0]
    summary = {
        "情景": sc.code,
        "情景标签": sc.label,
        "人口情景": sc.pop_scenario,
        "说明": sc.note,
        "综合有效领取率": round(eff, 6),
        "申请率": round(apply_s, 6),
        "资产审查通过率": round(pass_use, 6),
        "津贴通胀率": sc.inflation,
        f"{START}_65岁及以上_万人": round(float(y0["人口_65岁及以上_万人"]), 4),
        f"{START}_合资格_万人": round(float(y0["合资格长者_万人"]), 4),
        f"{START}_年支出_亿港元": round(float(y0["年支出_亿港元"]), 4),
        f"{END}_65岁及以上_万人": round(float(y1["人口_65岁及以上_万人"]), 4),
        f"{END}_合资格_万人": round(float(y1["合资格长者_万人"]), 4),
        f"{END}_年支出_亿港元": round(float(y1["年支出_亿港元"]), 4),
        "累计支出_亿港元": round(float(annual["年支出_亿港元"].sum()), 2),
        "支出峰值年": int(annual.loc[annual["年支出_亿港元"].idxmax(), "年份"]),
        "支出峰值_亿港元": round(float(annual["年支出_亿港元"].max()), 4),
    }
    return {"annual": annual, "eligibility": elig, "summary": summary, "pop": pop}


def run_all() -> Dict:
    """校准 + 三情景。"""
    # 用中方案人口校准综合领取率（与强积金基准人口一致）
    pop_mid = load_shared_population("中", START, END)
    p65_cal = elderly_total_by_year(pop_mid, CALIB_YEAR)
    base_eff = calibrate_effective_rate(p65_cal, CALIB_ELDERLY_CASES)
    apply, pass_r = split_apply_and_pass(base_eff)

    results = {}
    annuals: List[pd.DataFrame] = []
    summaries = []
    for code in ("低", "中", "高"):
        res = project_one(code, base_eff, apply, pass_r)
        results[code] = res
        annuals.append(res["annual"])
        summaries.append(res["summary"])
        label = get_scenario(code).label
        res["annual"].to_csv(
            OUT / f"annual_{label}.csv", index=False, encoding="utf-8-sig"
        )

    all_df = pd.concat(annuals, ignore_index=True)
    all_df.to_csv(OUT / "annual_all_scenarios.csv", index=False, encoding="utf-8-sig")
    sum_df = pd.DataFrame(summaries)
    sum_df.to_csv(OUT / "summary_comparison.csv", index=False, encoding="utf-8-sig")

    # 人口 65+ 路径（中方案）供核对与强积金一致
    eld_rows = []
    for y in range(START, END + 1):
        eld_rows.append(
            {
                "年份": y,
                "情景": "中",
                "人口_65岁及以上_人": round(elderly_total_by_year(pop_mid, y), 1),
                "人口_65岁及以上_万人": round(elderly_total_by_year(pop_mid, y) / 1e4, 4),
                "来源": "mpf_model.population.project_population 共用",
            }
        )
    pd.DataFrame(eld_rows).to_csv(
        OUT / "population_65plus_中.csv", index=False, encoding="utf-8-sig"
    )

    # 参数来源表
    sources = pd.DataFrame(
        [
            {
                "参数": "2025-03综援个案总数",
                "数值": 195581,
                "来源": "[真实数据] 社署公开量级",
            },
            {
                "参数": "年老个案占比",
                "数值": CSSA_ELDERLY_SHARE_2025_03,
                "来源": "[真实数据] 56.7%",
            },
            {
                "参数": "年老个案宗数",
                "数值": CSSA_ELDERLY_CASES_2025_03,
                "来源": "[真实数据] 约110,846宗（占比×总数之约数）",
            },
            {
                "参数": f"{CALIB_YEAR}年65岁及以上人口_人",
                "数值": round(p65_cal, 1),
                "来源": "[模型] 与强积金共用队列成分法·中方案",
            },
            {
                "参数": "综合有效领取率_基准",
                "数值": round(base_eff, 6),
                "来源": "[反推] 年老个案/65+人口",
            },
            {
                "参数": "申请率_基准",
                "数值": round(apply, 6),
                "来源": "[假设] 综合率拆分",
            },
            {
                "参数": "资产审查通过率_基准",
                "数值": round(pass_r, 6),
                "来源": "[假设] 综合率拆分",
            },
            {
                "参数": "单身长者月津贴_2025",
                "数值": MONTHLY_ALLOWANCE_2025,
                "来源": "[真实数据量级] 约8,600港元",
            },
            {
                "参数": "2024-25综援总开支_亿",
                "数值": CSSA_TOTAL_SPEND_2024_25_YI,
                "来源": "[真实数据] 对照用（含非长者）",
            },
            {
                "参数": "2025-26综援预算_亿",
                "数值": CSSA_BUDGET_2025_26_YI,
                "来源": "[真实数据] 对照用（含非长者）",
            },
            {
                "参数": "公式",
                "数值": "支出=合资格人数×月津贴×12",
                "来源": "财政支出定义（非个人账户）",
            },
        ]
    )
    sources.to_csv(OUT / "S00_parameter_sources.csv", index=False, encoding="utf-8-sig")

    # 校准核对：隐含长者开支 vs 总开支
    spend0 = float(
        results["中"]["annual"].loc[
            results["中"]["annual"]["年份"] == START, "年支出_亿港元"
        ].iloc[0]
    )
    check = {
        "校准年": CALIB_YEAR,
        "65岁及以上_万人": round(p65_cal / 1e4, 4),
        "年老个案锚点": CSSA_ELDERLY_CASES_2025_03,
        "综合有效领取率": round(base_eff, 6),
        "申请率": round(apply, 6),
        "审查通过率": round(pass_r, 6),
        f"{START}_长者综援支出_亿": round(spend0, 4),
        "占2024-25总开支比重": round(spend0 / CSSA_TOTAL_SPEND_2024_25_YI, 4),
        "说明": "长者部分模型；总开支含失业/单亲等，比重仅作量级对照",
    }
    pd.DataFrame([check]).to_csv(
        OUT / "S01_calibration_check.csv", index=False, encoding="utf-8-sig"
    )

    results["_meta"] = {
        "base_effective": base_eff,
        "apply": apply,
        "pass": pass_r,
        "p65_cal": p65_cal,
        "sources": rate_sources_dict(base_eff, apply, pass_r),
        "summary": sum_df,
        "check": check,
    }
    return results


def write_readme_snippet(meta: dict) -> None:
    """更新数据字典中的校准数字。"""
    path = _PKG / "00_data_dictionary.md"
    check = meta["check"]
    text = f"""# 综援计划（长者部分）财政支出模型 · 数据字典

> 与强积金模型**共用** `mpf_model.population` 队列成分法人口层。  
> 金额单位：亿港元；津贴：港元/月；人口：人 / 万人。

---

## 与强积金模型的区别

| 维度 | 强积金 | 综援长者 |
|------|--------|----------|
| 性质 | 个人账户累积 | **政府财政支出** |
| 核心公式 | A(t+1)=A(t)(1+r)+C−W−Offset | **支出 = 合资格人数 × 月津贴 × 12** |
| 人口层 | 队列成分法 | **同一套**（本模型只取 65+） |
| 资产/回报 | 需要 | **不需要** |

---

## 三层框架

1. **人口层**：`population_bridge.load_shared_population` → 65 岁及以上分年龄组  
2. **合资格层**：综合有效领取率 = 申请率 × 资产审查通过率（产品由个案反推）  
3. **支出层**：月津贴自 2025 年约 8,600 港元按情景通胀递推  

---

## 真实数据锚点

| 参数 | 数值 | 来源 |
|------|------|------|
| 2025-03 综援个案 | 195,581 宗 | [真实数据] |
| 年老占比 | 56.7% → **{CSSA_ELDERLY_CASES_2025_03:,}** 宗 | [真实数据] |
| 2025-03 受助人数 | 262,266 | [真实数据] |
| 2025-12 受助人数 | 约 256,518 | [真实数据] |
| 2024-25 总开支 | 223.53 亿 | [真实数据]（含非长者） |
| 2025-26 预算 | 约 231 亿 | [真实数据]（含非长者） |
| 单身长者月津贴 | 约 8,600 港元 | [真实数据量级] |

---

## 校准结果（每次 `run.py` 刷新）

| 项 | 数值 |
|----|------|
| 校准年 65+ 人口 | **{check['65岁及以上_万人']}** 万人 |
| 综合有效领取率 | **{check['综合有效领取率']:.4%}** [反推] |
| 申请率 | **{check['申请率']:.4%}** [假设·拆分] |
| 资产审查通过率 | **{check['审查通过率']:.4%}** [假设·拆分] |
| {START} 年长者综援支出 | **{check[f'{START}_长者综援支出_亿']}** 亿 |
| 相对 2024-25 总开支 | 约 **{check['占2024-25总开支比重']:.1%}**（量级对照） |

---

## 情景（财政口径）

| 码 | 标签 | 领取率 | 通胀 | 人口 |
|----|------|--------|------|------|
| 低 | 保守（支出偏低） | ×0.90 | 1.5% | 低 |
| 中 | 基准 | ×1.00（校准） | 2.5% | 中 |
| 高 | 高支出压力 | ×1.15 | 3.5% | 高 |

---

## 输出文件

| 文件 | 内容 |
|------|------|
| `annual_all_scenarios.csv` | 三情景逐年支出 |
| `annual_*.csv` | 分情景 |
| `summary_comparison.csv` | 摘要对比 |
| `population_65plus_中.csv` | 中方案 65+ 人口路径 |
| `S00_parameter_sources.csv` | 参数来源 |
| `S01_calibration_check.csv` | 校准核对 |

---

## 局限

1. 「年老」社署口径可能含部分 60–64 岁；本模型按用户要求用 **65+**，综合率可能略偏。  
2. 申请率 / 审查通过率拆分为假设，**产品**才是反推锚点。  
3. 未建模资产分布、长者生活津贴替代、残疾增补等细分。  
4. 总开支 223.53 亿含非长者，不可与本模型长者支出直接等同。
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    """CLI。"""
    res = run_all()
    meta = res["_meta"]
    write_readme_snippet(meta)
    check = meta["check"]
    print("=== 综援长者 · 校准 ===")
    for k, v in check.items():
        print(f"  {k}: {v}")
    print("=== 三情景摘要 ===")
    print(meta["summary"].to_string(index=False))
    print(f"输出目录: {OUT}")


if __name__ == "__main__":
    main()
