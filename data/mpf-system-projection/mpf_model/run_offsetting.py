# -*- coding: utf-8 -*-
"""对冲流出模块：规则自检 + 2020–2056 系统投影输出。

用法::

    python run_offsetting.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from contribution import calibrate_income_scale
from data_loader import (
    ACCOUNTS_WAN,
    AUM_2026,
    TARGET_CONTRIB_2026,
    Y_MAX_DEFAULT,
    Y_MIN_DEFAULT,
    load_all_tables,
)
from offsetting import (
    TRANSITION_DATE,
    calc_offsetting_flow,
    calc_pre_transition_portion,
    system_offsetting_outflow,
)
from population import extract_base_population, project_population
from run import calibrate_balance_scale, project_one_scenario
from scenarios import get_scenario

OUT = _PKG / "output" / "offsetting"
OUT.mkdir(parents=True, exist_ok=True)


def self_check_rules() -> pd.DataFrame:
    """规则单元自检（金额单位任意，取相对关系）。"""
    cases = []

    # 1) 转制后入职：强制 80 不可对冲，自愿 20 可对冲；遣散 50 → 对冲 20
    o1 = calc_offsetting_flow(
        2030,
        "post_transition",
        employer_mandatory_balance=80,
        employer_voluntary_balance=20,
        severance_payment=50,
        hire_year=2026,
        leave_year=2030,
    )
    cases.append(
        {
            "案例": "转制后入职_仅自愿可对冲",
            "结果": o1,
            "期望": 20.0,
            "通过": abs(o1 - 20.0) < 1e-9,
        }
    )

    # 2) 转制前离职：强制+自愿均可；遣散 100，余额 60+15 → 75
    o2 = calc_offsetting_flow(
        2024,
        "pre_transition",
        employer_mandatory_balance=60,
        employer_voluntary_balance=15,
        severance_payment=100,
        hire_year=2015,
        leave_year=2024,
        leave_month=6,
    )
    cases.append(
        {
            "案例": "转制前离职_强制自愿均可",
            "结果": o2,
            "期望": 75.0,
            "通过": abs(o2 - 75.0) < 1e-9,
        }
    )

    # 3) hybrid：入职 2015，离职 2030-6；转制前占比 = (2025.333-2015)/(2030.417-2015)
    portion = calc_pre_transition_portion(2015.0, 2030.0, 6.0)
    o3 = calc_offsetting_flow(
        2030,
        "hybrid",
        employer_mandatory_balance=100,
        employer_voluntary_balance=20,
        severance_payment=200,
        hire_year=2015,
        leave_year=2030,
        leave_month=6,
    )
    expect3 = min(100 * portion + 20, 200)
    cases.append(
        {
            "案例": f"混合队列_转制前占比{portion:.3f}",
            "结果": round(o3, 6),
            "期望": round(expect3, 6),
            "通过": abs(o3 - expect3) < 1e-6,
        }
    )

    # 4) 转制后入职遣散小于自愿
    o4 = calc_offsetting_flow(
        2028,
        "post_transition",
        100,
        40,
        25,
        hire_year=2026,
        leave_year=2028,
    )
    cases.append(
        {
            "案例": "转制后_遣散小于自愿",
            "结果": o4,
            "期望": 25.0,
            "通过": abs(o4 - 25.0) < 1e-9,
        }
    )

    return pd.DataFrame(cases)


def main() -> None:
    """生成对冲流出与修正资产路径。"""
    checks = self_check_rules()
    checks.to_csv(OUT / "O00_rule_self_check.csv", index=False, encoding="utf-8-sig")
    if not checks["通过"].all():
        raise RuntimeError("对冲规则自检失败：\n" + checks.to_string(index=False))

    tables = load_all_tables()
    mid = get_scenario("中")
    base = extract_base_population(tables["population"], 2026, "中")
    pop0 = project_population(tables["mortality"], base, "中", 2026, 2026)
    income_scale = calibrate_income_scale(
        pop0, mid, TARGET_CONTRIB_2026, Y_MIN_DEFAULT, Y_MAX_DEFAULT
    )
    probe = project_one_scenario(
        tables, mid, income_scale=income_scale, balance_scale=1.0, enable_offsetting=True
    )
    c0 = float(probe["annual"].iloc[0]["年总供款_亿港元"])
    if c0 > 0:
        income_scale *= TARGET_CONTRIB_2026 / c0
    balance_scale = calibrate_balance_scale(tables, mid)

    # 有对冲 vs 无对冲（2020–2056，基准情景）
    # 2020 起点用回测同口径近似
    from validate_analysis import (
        AUM_2020_START,
        ACCOUNTS_2020,
        HIST_RETURNS,
        load_csd_midyear_population,
    )
    from data_loader import Y_MAX_OLD, Y_MIN_OLD

    base2020 = load_csd_midyear_population("202006")

    # 历史段用旧上下限 + 历史回报；2026 起切到新默认上下限与恒定 4.9%
    # 为简洁：整段 2020–2056 用中情景，回报=历史∪4.9%，上下限 2025 前旧值、其后新值
    # 分两段跑再拼接
    returns = dict(HIST_RETURNS)
    for y in range(2026, 2057):
        returns[y] = mid.r

    # —— 有对冲 ——
    res_hist = project_one_scenario(
        tables,
        mid,
        start_year=2020,
        end_year=2025,
        a0=AUM_2020_START,
        accounts0=ACCOUNTS_2020,
        y_min=Y_MIN_OLD,
        y_max=Y_MAX_OLD,
        income_scale=income_scale,
        balance_scale=balance_scale,
        income_base_year=2026,
        base_mid_income=22000.0,
        base_pop=base2020,
        returns_by_year=returns,
        enable_offsetting=True,
    )
    a_2026 = float(res_hist["annual"].iloc[-1]["期末资产_亿港元"])
    acc_2026 = float(res_hist["annual"].iloc[-1]["账户数_万个"]) * 1.005
    res_fut = project_one_scenario(
        tables,
        mid,
        start_year=2026,
        end_year=2056,
        a0=a_2026,
        accounts0=acc_2026,
        y_min=Y_MIN_DEFAULT,
        y_max=Y_MAX_DEFAULT,
        income_scale=income_scale,
        balance_scale=balance_scale,
        returns_by_year=returns,
        enable_offsetting=True,
    )
    annual_on = pd.concat(
        [res_hist["annual"], res_fut["annual"]], ignore_index=True
    )

    # —— 无对冲对照 ——
    res_hist_off = project_one_scenario(
        tables,
        mid,
        start_year=2020,
        end_year=2025,
        a0=AUM_2020_START,
        accounts0=ACCOUNTS_2020,
        y_min=Y_MIN_OLD,
        y_max=Y_MAX_OLD,
        income_scale=income_scale,
        balance_scale=balance_scale,
        income_base_year=2026,
        base_mid_income=22000.0,
        base_pop=base2020,
        returns_by_year=returns,
        enable_offsetting=False,
    )
    a_2026b = float(res_hist_off["annual"].iloc[-1]["期末资产_亿港元"])
    acc_2026b = float(res_hist_off["annual"].iloc[-1]["账户数_万个"]) * 1.005
    res_fut_off = project_one_scenario(
        tables,
        mid,
        start_year=2026,
        end_year=2056,
        a0=a_2026b,
        accounts0=acc_2026b,
        y_min=Y_MIN_DEFAULT,
        y_max=Y_MAX_DEFAULT,
        income_scale=income_scale,
        balance_scale=balance_scale,
        returns_by_year=returns,
        enable_offsetting=False,
    )
    annual_off = pd.concat(
        [res_hist_off["annual"], res_fut_off["annual"]], ignore_index=True
    )

    # 对冲明细
    offset_cols = [
        "年份",
        "对冲流出_亿港元",
        "对冲流出_pre_亿港元",
        "对冲流出_hybrid_亿港元",
        "对冲流出_post_亿港元",
        "对冲占比_pre",
        "对冲占比_hybrid",
        "对冲占比_post",
        "期初资产_亿港元",
        "期末资产_亿港元",
    ]
    offset_df = annual_on[offset_cols].copy()
    offset_df.to_csv(OUT / "O01_offsetting_flow_by_year.csv", index=False, encoding="utf-8-sig")

    share = annual_on[
        [
            "年份",
            "对冲占比_pre",
            "对冲占比_hybrid",
            "对冲占比_post",
            "对冲流出_亿港元",
        ]
    ].copy()
    share.to_csv(OUT / "O02_offsetting_share_by_cohort.csv", index=False, encoding="utf-8-sig")

    # 资产对比曲线
    cmp = pd.DataFrame(
        {
            "年份": annual_on["年份"],
            "期末资产_含对冲_亿港元": annual_on["期末资产_亿港元"],
            "期末资产_无对冲_亿港元": annual_off["期末资产_亿港元"],
            "差额_无对冲减含对冲_亿港元": annual_off["期末资产_亿港元"].astype(float)
            - annual_on["期末资产_亿港元"].astype(float),
            "对冲流出_亿港元": annual_on["对冲流出_亿港元"],
            "年总供款_亿港元": annual_on["年总供款_亿港元"],
            "年总提取_亿港元": annual_on["年总提取_亿港元"],
        }
    )
    cmp.to_csv(OUT / "O03_asset_path_with_vs_without_offset.csv", index=False, encoding="utf-8-sig")

    annual_on.to_csv(OUT / "O04_annual_with_offsetting.csv", index=False, encoding="utf-8-sig")

    # 关键年摘要
    key_years = [2020, 2024, 2025, 2026, 2030, 2035, 2045, 2056]
    snap = offset_df[offset_df["年份"].isin(key_years)].copy()
    snap.to_csv(OUT / "O05_key_years_snapshot.csv", index=False, encoding="utf-8-sig")

    # 2024 校准检查
    y2024 = system_offsetting_outflow(2024, 12900.0)
    md = f"""# 对冲流出模块说明

> 转制日：**{TRANSITION_DATE}**  
> 恒等式：`A(t+1)=A(t)×(1+r)+C(t)−W(t)−Offset(t)`

## 规则自检

全部通过：{'是' if checks['通过'].all() else '否'}

## 时间趋势（系统层假设）

| 阶段 | 行为 |
|------|------|
| 2025 年前 | 几乎全为 pre_transition，强制+自愿可对冲；2024 校准约 {y2024['对冲流出_合计_亿港元']:.1f} 亿 |
| 2025–2035 | hybrid（转制前入职、转制后离职）主导并衰减；post 上升但仅自愿可对冲 |
| 2035 年后 | pre/hybrid 趋近 0；残留主要为 post 自愿对冲 |

## 关键年快照

| 年份 | 对冲合计(亿) | pre占比 | hybrid占比 | post占比 | 期末资产含对冲(亿) |
|------|-------------|---------|------------|----------|-------------------|
"""
    for _, r in snap.iterrows():
        md += (
            f"| {int(r['年份'])} | {r['对冲流出_亿港元']:.2f} | "
            f"{r['对冲占比_pre']:.1%} | {r['对冲占比_hybrid']:.1%} | "
            f"{r['对冲占比_post']:.1%} | {r['期末资产_亿港元']:.1f} |\n"
        )

    end_on = float(annual_on.iloc[-1]["期末资产_亿港元"])
    end_off = float(annual_off.iloc[-1]["期末资产_亿港元"])
    md += f"""
## 资产影响

- 2056 期末（含对冲）：**{end_on:,.1f}** 亿  
- 2056 期末（无对冲）：**{end_off:,.1f}** 亿  
- 差额（取消对冲额外留存）：**{end_off - end_on:,.1f}** 亿  

> 注：2024 对冲规模 `{y2024['对冲流出_合计_亿港元']:.1f} 亿` 为研究校准假设，非积金局单独公布序列。
"""
    (OUT / "O00_offsetting_readme.md").write_text(md, encoding="utf-8")

    print(checks.to_string(index=False))
    print("---")
    print(snap.to_string(index=False))
    print(f"2056 含对冲={end_on:.1f} 无对冲={end_off:.1f} 差额={end_off-end_on:.1f}")
    print(f"输出目录: {OUT}")


if __name__ == "__main__":
    main()
