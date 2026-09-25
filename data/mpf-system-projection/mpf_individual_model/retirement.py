# -*- coding: utf-8 -*-
"""第三层：退休后提取与账户耗尽年龄。

提取方式：
  1) 一笔过：取出后不再投资，按目标年支出消耗
  2) 分期固定额：账户内保留，可选继续投资，每年提取定额
  3) 继续投资+比例提取（默认 4% 规则）

制度局限：强积金不提供长寿风险保障——无一笔过/分期强制转为终身年金。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from params import (
    R_RETIRE_DEFAULT,
    REPLACEMENT_TARGET,
    WITHDRAW_PCT_DEFAULT,
    e65_for_sex,
)


def years_until_deplete(
    balance: float,
    annual_withdraw: float,
    r_retire: float = 0.0,
    max_years: int = 80,
) -> float:
    """期初余额、每年提取、可选回报下，撑过的年数。

    Returns:
        年数；若 max_years 仍未耗尽返回 max_years。
    """
    if annual_withdraw <= 0:
        return float(max_years)
    if balance <= 0:
        return 0.0
    a = float(balance)
    w = float(annual_withdraw)
    r = float(r_retire)
    for t in range(1, max_years + 1):
        a = a * (1.0 + r) - w
        if a <= 0:
            # 线性插值不足一年
            prev = a + w  # 提取前（计息后）
            frac = prev / w if w > 0 else 0.0
            return float(t - 1 + max(0.0, min(1.0, frac)))
    return float(max_years)


def analyze_withdrawal_modes(
    balance: float,
    final_annual_salary: float,
    retire_age: int,
    sex: str,
    r_retire: float = R_RETIRE_DEFAULT,
    withdraw_pct: float = WITHDRAW_PCT_DEFAULT,
    replacement: float = REPLACEMENT_TARGET,
) -> pd.DataFrame:
    """比较三种提取方式的耗尽年龄。

    Args:
        balance: 退休时余额。
        final_annual_salary: 退休前年薪。
        retire_age: 退休年龄。
        sex: 性别。
        r_retire: 退休后净回报（一笔过模式为 0）。
        withdraw_pct: 比例提取。
        replacement: 目标替代率（定义年支出）。

    Returns:
        各模式对照表。
    """
    e65 = e65_for_sex(sex)
    expect_death = retire_age + e65
    need_annual = final_annual_salary * replacement
    rows = []

    # 1) 一笔过：不再投资，按目标支出消耗
    y1 = years_until_deplete(balance, need_annual, r_retire=0.0)
    rows.append(
        {
            "提取方式": "一笔过（取出后不再投资）",
            "年提取_港元": round(need_annual, 2),
            "提取说明": f"目标支出=前年薪×{replacement:.0%}",
            "退休后回报率": 0.0,
            "可支撑年数": round(y1, 2),
            "账户耗尽年龄": round(retire_age + y1, 2),
            "预期死亡年龄_余命锚点": round(expect_death, 1),
            "是否覆盖预期余命": "是" if retire_age + y1 >= expect_death - 0.5 else "否",
            "缺口年数": round(max(0.0, expect_death - (retire_age + y1)), 2),
        }
    )

    # 2) 分期固定：账户内、可继续投资，年提 = 目标支出
    y2 = years_until_deplete(balance, need_annual, r_retire=r_retire)
    rows.append(
        {
            "提取方式": f"分期定额（账户内回报{r_retire:.1%}）",
            "年提取_港元": round(need_annual, 2),
            "提取说明": f"目标支出=前年薪×{replacement:.0%}",
            "退休后回报率": r_retire,
            "可支撑年数": round(y2, 2),
            "账户耗尽年龄": round(retire_age + y2, 2),
            "预期死亡年龄_余命锚点": round(expect_death, 1),
            "是否覆盖预期余命": "是" if retire_age + y2 >= expect_death - 0.5 else "否",
            "缺口年数": round(max(0.0, expect_death - (retire_age + y2)), 2),
        }
    )

    # 3) 4% 规则：首年提取 = 余额×4%，其后名义固定，账户继续投资
    w4 = balance * withdraw_pct
    y3 = years_until_deplete(balance, w4, r_retire=r_retire)
    rows.append(
        {
            "提取方式": f"继续投资+每年提取{withdraw_pct:.0%}（首年固定）",
            "年提取_港元": round(w4, 2),
            "提取说明": "经典4%规则变体：首年比例，其后定额",
            "退休后回报率": r_retire,
            "可支撑年数": round(y3, 2),
            "账户耗尽年龄": round(retire_age + y3, 2),
            "预期死亡年龄_余命锚点": round(expect_death, 1),
            "是否覆盖预期余命": "是" if retire_age + y3 >= expect_death - 0.5 else "否",
            "缺口年数": round(max(0.0, expect_death - (retire_age + y3)), 2),
        }
    )

    # 可持续性注释行
    rows.append(
        {
            "提取方式": "【制度局限】",
            "年提取_港元": "",
            "提取说明": "强积金不提供长寿风险保障；无一笔过强制转终身年金",
            "退休后回报率": "",
            "可支撑年数": "",
            "账户耗尽年龄": "",
            "预期死亡年龄_余命锚点": "",
            "是否覆盖预期余命": "",
            "缺口年数": "",
        }
    )
    return pd.DataFrame(rows)


def withdrawal_path(
    balance: float,
    annual_withdraw: float,
    r_retire: float,
    retire_age: int,
    max_years: int = 50,
) -> pd.DataFrame:
    """逐年提取路径（作图用）。"""
    a = float(balance)
    rows = []
    for t in range(max_years + 1):
        rows.append(
            {
                "退休后年序": t,
                "年龄": retire_age + t,
                "余额_港元": round(max(a, 0.0), 2),
            }
        )
        if t == max_years or a <= 0:
            break
        a = a * (1.0 + r_retire) - annual_withdraw
    return pd.DataFrame(rows)
