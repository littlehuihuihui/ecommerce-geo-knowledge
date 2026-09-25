# -*- coding: utf-8 -*-
"""主入口：串联四层架构，输出逐年明细与摘要。

用法::

    python run.py
    python run.py --data-dir ../p0_foundation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# 保证包内相对导入在直接 python run.py 时可工作
_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from asset import find_inflection_points, step_asset
from contribution import (
    INCOME_MID_REP,
    calibrate_income_scale,
    compute_contribution,
)
from data_loader import (
    ACCOUNTS_WAN,
    AUM_2026,
    COVERAGE,
    TARGET_CONTRIB_2026,
    Y_MAX_DEFAULT,
    Y_MIN_DEFAULT,
    load_all_tables,
    load_real_data,
)
from offsetting import system_offsetting_outflow
from population import extract_base_population, project_population
from scenarios import (
    RANDOM_SEED,
    SCENARIOS,
    ScenarioConfig,
    Y_MAX_OLD,
    Y_MIN_OLD,
    apply_empf_to_net_return,
    empf_fee_schedule,
    get_scenario,
    relevant_income_limits,
)
from withdrawal import compute_withdrawal

OUT_DIR = _PKG / "output"


def project_one_scenario(
    tables: Dict[str, pd.DataFrame],
    scenario: ScenarioConfig,
    start_year: int = 2026,
    end_year: int = 2056,
    a0: float = AUM_2026,
    accounts0: float = ACCOUNTS_WAN,
    y_min: float = Y_MIN_DEFAULT,
    y_max: float = Y_MAX_DEFAULT,
    income_scale: float = 1.0,
    balance_scale: float = 1.0,
    extract_ratio: float = 1.0,
    coverage: float = COVERAGE,
    income_base_year: int = 2026,
    base_mid_income: float = INCOME_MID_REP,
    returns_by_year: Optional[Dict[int, float]] = None,
    base_pop: Optional[pd.DataFrame] = None,
    pop_df: Optional[pd.DataFrame] = None,
    enable_offsetting: bool = True,
) -> Dict[str, object]:
    """对单一情景跑完整四层投影。

    Args:
        tables: P1 全表。
        scenario: 情景配置。
        start_year: 起始年。
        end_year: 终止年。
        a0: 起始总资产（亿港元）。
        accounts0: 起始账户数（万个）。
        y_min: 有关入息下限。
        y_max: 有关入息上限。
        income_scale: 入息校准系数。
        balance_scale: 提取余额校准系数。
        extract_ratio: 达龄提取比例。
        coverage: 强积金覆盖率。
        income_base_year: 入息增长锚定年。
        base_mid_income: 锚定年代表月入。
        returns_by_year: 可选逐年回报；缺省用 scenario.r。
        base_pop: 可选外部基准人口；缺省从 tables 抽取。
        pop_df: 可选已算好的人口路径；若提供则跳过 CCM。
        enable_offsetting: 是否扣减对冲流出（默认开启）。

    Returns:
        含 ``annual`` DataFrame 与 ``summary`` 的字典。
    """
    # —— 第一层：人口 ——
    if pop_df is not None:
        pop = pop_df
    else:
        base = base_pop if base_pop is not None else extract_base_population(
            tables["population"], year=start_year, scenario=scenario.pop_scenario
        )
        # 若 start_year 不在 P1 表2，需外部传入 base_pop
        if base_pop is None and start_year != 2026:
            # 尝试用表中最接近年
            years_avail = sorted(tables["population"]["年份"].unique())
            y0 = min(years_avail, key=lambda y: abs(int(y) - start_year))
            base = extract_base_population(
                tables["population"], year=int(y0), scenario=scenario.pop_scenario
            )
        pop = project_population(
            tables["mortality"],
            base,
            scenario=scenario.pop_scenario,
            start_year=start_year,
            end_year=end_year,
        )

    years = list(range(start_year, end_year + 1))
    rows: List[dict] = []
    a = float(a0)
    accounts = float(accounts0)

    for y in years:
        # 有关入息上下限：2026–2027 旧值，2028+ 假设新值（或全程旧值对照）
        y_min_y, y_max_y = relevant_income_limits(
            y,
            keep_old_limits=scenario.keep_old_limits,
            transition_year=scenario.upper_limit_transition_year,
        )

        r_base = (
            float(returns_by_year[y])
            if returns_by_year and y in returns_by_year
            else scenario.r
        )
        # eMPF 费率动态：相对 0.29% 口径上调净回报
        r = apply_empf_to_net_return(r_base, y)
        empf = empf_fee_schedule(y)

        c = compute_contribution(
            pop,
            y,
            scenario,
            y_min=y_min_y,
            y_max=y_max_y,
            income_scale=income_scale,
            coverage=coverage,
            income_base_year=income_base_year,
            base_mid_income=base_mid_income,
        )
        w = compute_withdrawal(
            pop,
            y,
            aum_yi=a,
            accounts_wan=accounts,
            scenario=scenario,
            extract_ratio=extract_ratio,
            balance_scale=balance_scale,
        )
        # 雇主强制供款约占总强制的一半
        er_mand = float(c["年强制性供款_亿港元"]) * 0.5
        if enable_offsetting:
            off = system_offsetting_outflow(y, a, employer_contrib_yi=er_mand)
            offset_yi = float(off["对冲流出_合计_亿港元"])
        else:
            off = {
                "对冲流出_合计_亿港元": 0.0,
                "对冲流出_pre_transition_亿港元": 0.0,
                "对冲流出_hybrid_亿港元": 0.0,
                "对冲流出_post_transition_亿港元": 0.0,
                "占比_pre": 0.0,
                "占比_hybrid": 0.0,
                "占比_post": 0.0,
                "权重_pre": 0.0,
                "权重_hybrid": 0.0,
                "权重_post": 0.0,
            }
            offset_yi = 0.0

        a_end = step_asset(
            a, r, c["年总供款_亿港元"], w["年总提取_亿港元"], offset_yi
        )

        rows.append(
            {
                "年份": y,
                "情景": scenario.code,
                "情景标签": scenario.label,
                "期初资产_亿港元": round(a, 4),
                "回报率": r,
                "回报率_未调eMPF": r_base,
                "eMPF费率": empf,
                "投资收益_亿港元": round(a * r, 4),
                "有关入息下限": y_min_y,
                "有关入息上限": y_max_y,
                "缴费人数_万人": round(c["缴费人数_万人"], 4),
                "带内代表月入_港元": round(c["带内代表月入_港元"], 1),
                "年强制性供款_亿港元": round(c["年强制性供款_亿港元"], 4),
                "年自愿性供款_亿港元": round(c["年自愿性供款_亿港元"], 4),
                "年总供款_亿港元": round(c["年总供款_亿港元"], 4),
                "新达65岁_万人": round(w["新达65岁_万人"], 4),
                "人均账户余额_港元": round(w["人均账户余额_港元"], 0),
                "年退休提取_亿港元": round(w["年退休提取_亿港元"], 4),
                "年永久离港提取_亿港元": round(w["年永久离港提取_亿港元"], 4),
                "年其他提取_亿港元": round(w["年其他提取_亿港元"], 4),
                "年总提取_亿港元": round(w["年总提取_亿港元"], 4),
                "对冲流出_亿港元": round(offset_yi, 4),
                "对冲流出_pre_亿港元": round(off["对冲流出_pre_transition_亿港元"], 4),
                "对冲流出_hybrid_亿港元": round(off["对冲流出_hybrid_亿港元"], 4),
                "对冲流出_post_亿港元": round(
                    off["对冲流出_post_transition_亿港元"], 4
                ),
                "对冲占比_pre": round(float(off["占比_pre"]), 4),
                "对冲占比_hybrid": round(float(off["占比_hybrid"]), 4),
                "对冲占比_post": round(float(off["占比_post"]), 4),
                "净现金流_亿港元": round(
                    c["年总供款_亿港元"] - w["年总提取_亿港元"] - offset_yi, 4
                ),
                "期末资产_亿港元": round(a_end, 4),
                "账户数_万个": round(accounts, 4),
            }
        )
        a = a_end
        accounts *= 1.005

    annual = pd.DataFrame(rows)
    summary = find_inflection_points(annual, a0=a0)
    summary["情景"] = scenario.code
    summary["情景标签"] = scenario.label
    summary["回报率"] = scenario.r
    summary["上下限过渡年"] = scenario.upper_limit_transition_year
    summary["维持旧上限"] = scenario.keep_old_limits
    summary["有关入息下限"] = y_min
    summary["有关入息上限"] = y_max
    summary["累计对冲流出_亿港元"] = round(float(annual["对冲流出_亿港元"].sum()), 2)
    summary["累计永久离港_亿港元"] = round(
        float(annual["年永久离港提取_亿港元"].sum()), 2
    )
    summary["首年总供款_亿港元"] = float(annual.iloc[0]["年总供款_亿港元"])
    summary["首年总提取_亿港元"] = float(annual.iloc[0]["年总提取_亿港元"])
    # 兼容旧字段名
    summary["2026总供款_亿港元"] = float(
        annual.loc[annual["年份"] == 2026, "年总供款_亿港元"].iloc[0]
    ) if (annual["年份"] == 2026).any() else summary["首年总供款_亿港元"]
    summary["2026总提取_亿港元"] = float(
        annual.loc[annual["年份"] == 2026, "年总提取_亿港元"].iloc[0]
    ) if (annual["年份"] == 2026).any() else summary["首年总提取_亿港元"]

    return {"annual": annual, "summary": summary, "population": pop}


def calibrate_balance_scale(
    tables: Dict[str, pd.DataFrame],
    scenario: ScenarioConfig,
    target_retire_yi: float = 195.66,
    a0: float = AUM_2026,
    accounts0: float = ACCOUNTS_WAN,
) -> float:
    """校准达龄余额系数，使 2026 退休提取贴近 2025 全年锚点量级。

    Args:
        tables: P1 表。
        scenario: 基准情景。
        target_retire_yi: 目标退休提取（亿港元）。
        a0: 起始资产。
        accounts0: 账户数。

    Returns:
        balance_scale。
    """
    base = extract_base_population(tables["population"], 2026, scenario.pop_scenario)
    pop = project_population(
        tables["mortality"], base, scenario.pop_scenario, 2026, 2026
    )
    w0 = compute_withdrawal(
        pop, 2026, a0, accounts0, scenario, balance_scale=1.0
    )
    r0 = w0["年退休提取_亿港元"]
    if r0 <= 0:
        return 1.0
    return float(target_retire_yi / r0)


def run_all(
    data_dir: Optional[str] = None,
    use_real_loader: bool = False,
    out_dir: Optional[Path] = None,
) -> Dict[str, object]:
    """跑三情景并落盘。

    Args:
        data_dir: P1 CSV 目录。
        use_real_loader: True 时走 ``load_real_data()`` 预留接口。
        out_dir: 输出目录。

    Returns:
        结果字典。
    """
    np.random.seed(RANDOM_SEED)

    if use_real_loader:
        source = load_real_data()
        tables = load_all_tables(source=source)
    else:
        tables = load_all_tables(data_dir=data_dir)

    out = Path(out_dir) if out_dir else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    # 以中情景校准入息与余额
    mid = get_scenario("中")
    base = extract_base_population(tables["population"], 2026, mid.pop_scenario)
    pop_mid = project_population(
        tables["mortality"], base, mid.pop_scenario, 2026, 2026
    )
    income_scale = calibrate_income_scale(
        pop_mid, mid, target_total=TARGET_CONTRIB_2026,
        y_min=Y_MIN_OLD, y_max=Y_MAX_OLD,
    )
    balance_scale = calibrate_balance_scale(tables, mid)

    # 二次闭合：用完整投影首年供款再微调（消除 CCM 单年/多年路径细差）
    probe = project_one_scenario(
        tables, mid, income_scale=income_scale, balance_scale=balance_scale
    )
    c_probe = float(probe["annual"].iloc[0]["年总供款_亿港元"])
    if c_probe > 0:
        income_scale *= TARGET_CONTRIB_2026 / c_probe

    all_annual = []
    summaries = []
    for code in ("低", "中", "高"):
        sc = get_scenario(code)
        result = project_one_scenario(
            tables,
            sc,
            income_scale=income_scale,
            balance_scale=balance_scale,
        )
        annual = result["annual"]
        annual.to_csv(
            out / f"annual_{sc.label}.csv", index=False, encoding="utf-8-sig"
        )
        all_annual.append(annual)
        summaries.append(result["summary"])

        # 人口亦可选落盘（仅中情景，避免过大）
        if code == "中":
            result["population"].to_csv(
                out / "population_ccm_中.csv", index=False, encoding="utf-8-sig"
            )

    annual_all = pd.concat(all_annual, ignore_index=True)
    annual_all.to_csv(out / "annual_all_scenarios.csv", index=False, encoding="utf-8-sig")

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(out / "summary_comparison.csv", index=False, encoding="utf-8-sig")

    # 拐点专用表
    infl_rows = []
    for s in summaries:
        infl_rows.append(
            {
                "情景": s["情景"],
                "情景标签": s["情景标签"],
                "回报率": s["回报率"],
                "2026期初资产_亿港元": s["期初资产_亿港元"],
                "2026总供款_亿港元": s["2026总供款_亿港元"],
                "2026总提取_亿港元": s["2026总提取_亿港元"],
                "净流出年份": s["净流出年份"],
                "资产峰值年份": s["资产峰值年份"],
                "资产峰值_亿港元": s["资产峰值_亿港元"],
                "资产下降拐点年份": s["资产下降拐点年份"],
                "投影期内是否见顶回落": s["投影期内是否见顶回落"],
                "2056期末资产_亿港元": s["期末资产_亿港元"],
                "累计供款_亿港元": s["累计供款_亿港元"],
                "累计提取_亿港元": s["累计提取_亿港元"],
            }
        )
    infl_df = pd.DataFrame(infl_rows)
    infl_df.to_csv(out / "inflection_points.csv", index=False, encoding="utf-8-sig")

    # 校验说明
    mid_sum = next(s for s in summaries if s["情景"] == "中")
    check_lines = [
        f"income_scale={income_scale:.6f}",
        f"balance_scale={balance_scale:.6f}",
        f"A0={mid_sum['期初资产_亿港元']} (目标≈{AUM_2026})",
        f"C2026={mid_sum['2026总供款_亿港元']} (目标≈{TARGET_CONTRIB_2026})",
        f"W2026={mid_sum['2026总提取_亿港元']}",
        f"净流出年份={mid_sum['净流出年份']}",
        f"资产峰值年份={mid_sum['资产峰值年份']} 见顶回落={mid_sum['投影期内是否见顶回落']}",
        f"期末资产={mid_sum['期末资产_亿港元']}",
        f"输出目录={out}",
    ]
    (out / "run_check.txt").write_text("\n".join(check_lines), encoding="utf-8")

    # 宽表资产路径
    wide = annual_all.pivot_table(
        index="年份", columns="情景标签", values="期末资产_亿港元"
    ).reset_index()
    wide.to_csv(out / "asset_path_wide.csv", index=False, encoding="utf-8-sig")

    return {
        "annual_all": annual_all,
        "summary": summary_df,
        "income_scale": income_scale,
        "balance_scale": balance_scale,
        "check": check_lines,
    }


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="强积金制度总账户 30年现金流预测")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="P1 数据目录（默认 ../p0_foundation）",
    )
    parser.add_argument(
        "--real-data",
        action="store_true",
        help="走 load_real_data() 预留接口",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="输出目录（默认 ./output）",
    )
    args = parser.parse_args()
    result = run_all(
        data_dir=args.data_dir,
        use_real_loader=args.real_data,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    print("\n".join(result["check"]))


if __name__ == "__main__":
    main()
