# -*- coding: utf-8 -*-
"""第一层：个体职业生涯与账户积累。

A(t+1) = A(t)×(1+r) + 雇员供款(t) + 雇主供款(t) [+自愿]
追踪累计供款与累计投资收益，避免与制度总账户混淆。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from params import (
    RATE_EE,
    RATE_ER,
    IndividualProfile,
    relevant_limits_for_calendar_year,
)


def mandatory_monthly(y: float, y_min: float, y_max: float) -> Tuple[float, float]:
    """有关入息规则下的月强制供款（雇员, 雇主）。

    与制度模型 ``contribution.mandatory_contrib_per_person_monthly`` 一致。
    """
    if y < y_min:
        return 0.0, RATE_ER * y
    y_rel = min(y, y_max)
    return RATE_EE * y_rel, RATE_ER * y_rel


def simulate_career(
    profile: IndividualProfile,
    initial_balance: float = 0.0,
) -> pd.DataFrame:
    """模拟入职至退休前一年的账户路径。

    Args:
        profile: 个体画像。
        initial_balance: 期初余额（港元）；真实个体可接入既有结余。

    Returns:
        逐年明细表（年龄、入息、供款、余额、累计供款/收益）。
    """
    years_work = profile.retire_age - profile.entry_age
    if years_work <= 0:
        raise ValueError("retire_age 必须大于 entry_age")

    # 供款中断：均匀分布在职业生涯中的若干整年
    gap_set = set()
    if profile.gap_years > 0:
        step = max(1, years_work // (profile.gap_years + 1))
        for i in range(profile.gap_years):
            gap_set.add(min(years_work - 1, (i + 1) * step))

    a = float(initial_balance)
    cum_contrib = 0.0
    cum_ee = 0.0
    cum_er = 0.0
    cum_vol = 0.0
    rows: List[Dict[str, Any]] = []
    income = float(profile.start_monthly_income)

    for k in range(years_work):
        age = profile.entry_age + k
        cal_year = (
            None
            if profile.career_start_year is None
            else int(profile.career_start_year) + k
        )
        y_min, y_max = relevant_limits_for_calendar_year(
            cal_year, profile.use_new_limits
        )

        interrupted = k in gap_set
        if interrupted:
            ee_m = er_m = vol_m = 0.0
        else:
            ee_m, er_m = mandatory_monthly(income, y_min, y_max)
            y_rel = 0.0 if income < y_min else min(income, y_max)
            vol_m = profile.voluntary_rate * y_rel

        ee_y = ee_m * 12.0
        er_y = er_m * 12.0
        vol_y = vol_m * 12.0
        c_y = ee_y + er_y + vol_y

        a_begin = a
        inv_gain = a_begin * profile.r
        a_end = a_begin * (1.0 + profile.r) + c_y

        cum_contrib += c_y
        cum_ee += ee_y
        cum_er += er_y
        cum_vol += vol_y
        # 投资收益累计 = 期末余额 − 累计供款 − 期初（相对初始）
        cum_inv = a_end - initial_balance - cum_contrib

        rows.append(
            {
                "工作年序": k + 1,
                "年龄": age,
                "日历年": cal_year if cal_year is not None else "",
                "月入_港元": round(income, 2),
                "年入_港元": round(income * 12, 2),
                "有关入息下限": y_min,
                "有关入息上限": y_max,
                "供款中断": int(interrupted),
                "雇员供款_港元": round(ee_y, 2),
                "雇主供款_港元": round(er_y, 2),
                "自愿供款_港元": round(vol_y, 2),
                "年总供款_港元": round(c_y, 2),
                "期初余额_港元": round(a_begin, 2),
                "投资收益_港元": round(inv_gain, 2),
                "期末余额_港元": round(a_end, 2),
                "累计供款_港元": round(cum_contrib, 2),
                "累计雇员_港元": round(cum_ee, 2),
                "累计雇主_港元": round(cum_er, 2),
                "累计自愿_港元": round(cum_vol, 2),
                "累计投资收益_港元": round(cum_inv, 2),
                "回报率": profile.r,
                "性别": profile.sex,
                "标签": profile.name,
            }
        )
        a = a_end
        income *= 1.0 + profile.income_growth

    return pd.DataFrame(rows)


def retirement_summary(career: pd.DataFrame, profile: IndividualProfile) -> Dict[str, Any]:
    """第二层：退休时账户摘要。"""
    last = career.iloc[-1]
    bal = float(last["期末余额_港元"])
    cum_c = float(last["累计供款_港元"])
    cum_inv = float(last["累计投资收益_港元"])
    final_annual = float(last["年入_港元"]) * (1.0 + profile.income_growth)
    # 退休当年「前年薪」≈ 最后工作年入息再增长一年
    multiple = bal / final_annual if final_annual > 0 else float("nan")
    return {
        "标签": profile.name,
        "性别": profile.sex,
        "入职年龄": profile.entry_age,
        "退休年龄": profile.retire_age,
        "工作年数": profile.retire_age - profile.entry_age,
        "起薪_月_港元": profile.start_monthly_income,
        "入息增速": profile.income_growth,
        "累积期回报率": profile.r,
        "退休时账户余额_港元": round(bal, 2),
        "累计供款_港元": round(cum_c, 2),
        "累计投资收益_港元": round(cum_inv, 2),
        "供款占余额_pct": round(100.0 * cum_c / bal, 2) if bal else 0.0,
        "投资收益占余额_pct": round(100.0 * cum_inv / bal, 2) if bal else 0.0,
        "退休前年薪_港元": round(final_annual, 2),
        "余额相对前年薪倍数": round(multiple, 2),
        "备注": "倍数≈账户余额/退休前年薪，非年金替代率",
    }
