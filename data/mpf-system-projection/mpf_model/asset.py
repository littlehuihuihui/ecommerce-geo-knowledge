# -*- coding: utf-8 -*-
"""第四层：资产演化与拐点识别。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd


def step_asset(
    a_t: float,
    r: float,
    contrib_yi: float,
    withdraw_yi: float,
    offset_yi: float = 0.0,
) -> float:
    """单年资产递推：A(t+1) = A(t)×(1+r) + C(t) − W(t) − Offset(t)。

    计息惯例与基数：
      - 投资回报基数 = **期初**存量 A(t)（先计息，再加减当年流量）
      - Offset 为对冲账户流出（见 offsetting.py）；默认 0 可关闭

    来源：P0 设计恒等式 + 取消对冲规则修正。

    Args:
        a_t: 期初总资产（亿港元）。
        r: 年率化净回报（已含 eMPF 调整时由 run 传入）。
        contrib_yi: 当年总供款。
        withdraw_yi: 当年总提取（含退休/离港/其他）。
        offset_yi: 当年对冲流出。

    Returns:
        期末总资产 A(t+1)。
    """
    return a_t * (1.0 + r) + contrib_yi - withdraw_yi - float(offset_yi)


def find_inflection_points(
    annual: pd.DataFrame,
    a0: Optional[float] = None,
) -> Dict[str, object]:
    """识别资产峰值、净流出与耗尽类拐点。

    净流出定义（任务三）：年度提取 > 年度供款 + 投资收益。
    另保留「流量净流出」：提取 > 供款（不含投资收益）。

    Args:
        annual: 含列 年份、期初资产_亿港元、期末资产_亿港元、
                年总供款_亿港元、年总提取_亿港元；宜含 投资收益_亿港元。
        a0: 投影期初资产；用于「降至初始 50%」判定。缺省取首年期初。

    Returns:
        摘要字典。
    """
    df = annual.sort_values("年份").reset_index(drop=True)
    if "投资收益_亿港元" not in df.columns:
        df["投资收益_亿港元"] = df["期初资产_亿港元"].astype(float) * df["回报率"].astype(
            float
        )

    # 经济净流出：W + Offset > C + 投资收益（若无对冲列则 Offset=0）
    has_off = "对冲流出_亿港元" in df.columns
    econ_out_year: Optional[int] = None
    for _, r in df.iterrows():
        off = float(r["对冲流出_亿港元"]) if has_off else 0.0
        if float(r["年总提取_亿港元"]) + off > float(r["年总供款_亿港元"]) + float(
            r["投资收益_亿港元"]
        ):
            econ_out_year = int(r["年份"])
            break

    # 流量净流出：W + Offset > C
    flow_out_year: Optional[int] = None
    for _, r in df.iterrows():
        off = float(r["对冲流出_亿港元"]) if has_off else 0.0
        if float(r["年总提取_亿港元"]) + off > float(r["年总供款_亿港元"]):
            flow_out_year = int(r["年份"])
            break

    end_assets = df["期末资产_亿港元"].astype(float)
    peak_idx = int(end_assets.idxmax())
    peak_year = int(df.loc[peak_idx, "年份"])
    peak_val = float(end_assets.loc[peak_idx])

    drop_year: Optional[int] = None
    for i in range(1, len(df)):
        if float(df.loc[i, "期末资产_亿港元"]) < float(df.loc[i - 1, "期末资产_亿港元"]):
            drop_year = int(df.loc[i, "年份"])
            break

    last_end = float(df.iloc[-1]["期末资产_亿港元"])
    peak_in_horizon = peak_val > last_end + 1e-6

    a_init = float(a0) if a0 is not None else float(df.iloc[0]["期初资产_亿港元"])
    half_year: Optional[int] = None
    for _, r in df.iterrows():
        if float(r["期末资产_亿港元"]) < 0.5 * a_init:
            half_year = int(r["年份"])
            break

    return {
        "净流出年份": econ_out_year if econ_out_year is not None else "30年内未出现",
        "流量净流出年份_W大于C": flow_out_year
        if flow_out_year is not None
        else "30年内未出现",
        "资产峰值年份": peak_year if peak_in_horizon else "30年内持续增长",
        "资产峰值年份_路径最高点": peak_year,
        "资产峰值_亿港元": round(peak_val, 2),
        "资产下降拐点年份": drop_year if drop_year is not None else "30年内未出现",
        "投影期内是否见顶回落": "是" if peak_in_horizon else "否",
        "资产降至初值50_年份": half_year if half_year is not None else "30年内未出现",
        "期末资产_亿港元": round(last_end, 2),
        "期初资产_亿港元": round(a_init, 2),
        "累计供款_亿港元": round(float(df["年总供款_亿港元"].sum()), 2),
        "累计提取_亿港元": round(float(df["年总提取_亿港元"].sum()), 2),
    }


def run_asset_path(
    years: List[int],
    a0: float,
    r: float,
    contributions: Dict[int, float],
    withdrawals: Dict[int, float],
    offsets: Optional[Dict[int, float]] = None,
) -> pd.DataFrame:
    """给定流量路径，滚动资产（可选对冲流出）。

    Args:
        years: 流量年份列表。
        a0: 首年期初资产。
        r: 恒定回报（情景）。
        contributions: 年 → 供款。
        withdrawals: 年 → 提取。
        offsets: 年 → 对冲流出；缺省 0。

    Returns:
        逐年明细 DataFrame。
    """
    rows = []
    a = float(a0)
    off_map = offsets or {}
    for y in years:
        c = float(contributions.get(y, 0.0))
        w = float(withdrawals.get(y, 0.0))
        o = float(off_map.get(y, 0.0))
        a_end = step_asset(a, r, c, w, o)
        rows.append(
            {
                "年份": y,
                "期初资产_亿港元": round(a, 4),
                "回报率": r,
                "投资收益_亿港元": round(a * r, 4),
                "年总供款_亿港元": round(c, 4),
                "年总提取_亿港元": round(w, 4),
                "对冲流出_亿港元": round(o, 4),
                "净现金流_亿港元": round(c - w - o, 4),
                "期末资产_亿港元": round(a_end, 4),
            }
        )
        a = a_end
    return pd.DataFrame(rows)
