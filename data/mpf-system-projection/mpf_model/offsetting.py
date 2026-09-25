# -*- coding: utf-8 -*-
"""取消对冲安排 · 对冲流出模块。

转制日：2025-05-01（劳工处 / 积金局公开规则）。

规则摘要：
1. 转制日前离职：雇主强制 + 自愿均可对冲。
2. 转制日后入职：雇主强制不可对冲；雇主自愿（及按年资酬金）仍可对冲。
3. 转制日前已受雇、转制日后离职：强制只可对冲「转制前部分」；
   自愿可对冲转制前及/或转制后部分。

系统层用队列权重加总个人规则，输出年度对冲流出（亿港元）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

TRANSITION_DATE = "2025-05-01"
TRANSITION_YEAR = 2025
TRANSITION_MONTH = 5

# 历史对冲规模校准锚点 [假设]
# 公开统计少有单独「对冲流出」序列；取「其他提取」量级的一部分作制度漏损
# 约 30–45 亿/年，落在总提取的数个百分点
OFFSET_BASE_2024_YI = 38.0  # 亿港元 [假设·量级校准]
# 雇主自愿累算权益约占雇主侧可对冲池的比例 [假设]
VOL_SHARE_OF_ER_POOL = 0.18
# 遣散费/长服金相对「潜在可对冲余额」的兑现率（非人人离职都触发）[假设]
SEVERANCE_REALIZATION = 0.55


@dataclass(frozen=True)
class OffsetCase:
    """单笔对冲案例（用于单元规则测试）。"""

    cohort_type: str
    employer_mandatory_balance: float
    employer_voluntary_balance: float
    severance_payment: float
    hire_year: Optional[float] = None
    leave_year: Optional[float] = None
    leave_month: Optional[float] = None


def calc_pre_transition_portion(
    hire_year: float,
    leave_year: float,
    leave_month: float = 6.0,
    transition_year: int = TRANSITION_YEAR,
    transition_month: int = TRANSITION_MONTH,
) -> float:
    """计算遣散费/长服金中「转制前部分」占比。

    以服务月数近似：转制前服务 / 总服务。
    若整段雇佣均在转制前结束，返回 1.0；
    若整段均在转制后开始，返回 0.0。

    Args:
        hire_year: 入职公历年（可用小数表示年中，如 2018.5）。
        leave_year: 离职公历年。
        leave_month: 离职月份 1–12。
        transition_year: 转制年。
        transition_month: 转制月。

    Returns:
        转制前部分占比，落在 [0, 1]。
    """
    hire = float(hire_year)
    leave = float(leave_year) + (float(leave_month) - 1.0) / 12.0
    trans = float(transition_year) + (float(transition_month) - 1.0) / 12.0

    if leave <= hire:
        return 1.0
    total = leave - hire
    if total <= 0:
        return 1.0

    # 整段在转制前结束
    if leave <= trans:
        return 1.0
    # 整段在转制后开始
    if hire >= trans:
        return 0.0

    pre = max(0.0, trans - hire)
    return float(np.clip(pre / total, 0.0, 1.0))


def calc_offsetting_flow(
    year: int,
    cohort_type: str,
    employer_mandatory_balance: float,
    employer_voluntary_balance: float,
    severance_payment: float,
    hire_year: Optional[float] = None,
    leave_year: Optional[float] = None,
    leave_month: float = 6.0,
) -> float:
    """计算某年因对冲产生的资金流出（从强积金账户流出）。

    Args:
        year: 离职/对冲发生年（用于校验，不改变规则分支）。
        cohort_type: ``pre_transition``（转制日前入职）或
                     ``post_transition``（转制日后入职）。
                     亦可传 ``hybrid``，等价于 pre_transition + 按年资拆分。
        employer_mandatory_balance: 雇主强制性供款累算权益。
        employer_voluntary_balance: 雇主自愿性供款累算权益。
        severance_payment: 应支付的遣散费/长服金。
        hire_year: 入职年（pre/hybrid 算转制前占比时需要）。
        leave_year: 离职年；缺省用 ``year``。
        leave_month: 离职月。

    Returns:
        实际被对冲的金额（与余额同单位）。
    """
    _ = year  # 规则由队列类型与转制日决定；年份供审计
    er_m = max(0.0, float(employer_mandatory_balance))
    er_v = max(0.0, float(employer_voluntary_balance))
    sev = max(0.0, float(severance_payment))
    leave_y = float(leave_year) if leave_year is not None else float(year)

    ctype = cohort_type.strip().lower()
    if ctype in ("post_transition", "post", "转制后入职"):
        # 强制不可对冲；自愿可对冲（酬金不在强积金账户内，此处不计入账户流出）
        return float(min(er_v, sev))

    if ctype in ("pre_transition", "pre", "hybrid", "转制前入职", "混合"):
        # 转制日前已离职：占比=1，强制+自愿均可对冲
        # 转制日前入职、转制日后离职：强制只可对冲转制前部分；自愿可对冲全部
        if hire_year is None:
            # 无入职年时：若 leave 在转制前 → 全额可对冲；否则用默认占比衰减
            if leave_y < TRANSITION_YEAR or (
                leave_y == TRANSITION_YEAR and leave_month < TRANSITION_MONTH
            ):
                portion = 1.0
            else:
                # [假设] 缺入职年时用系统层平均转制前占比
                portion = default_pre_portion_for_year(int(leave_y))
        else:
            portion = calc_pre_transition_portion(
                float(hire_year), leave_y, leave_month
            )

        # 强制：仅转制前部分可对冲；自愿：可对冲转制前及/或转制后（即可对冲全部自愿）
        allowable = er_m * portion + er_v
        return float(min(allowable, sev))

    raise ValueError(
        f"未知 cohort_type={cohort_type!r}；"
        "请用 pre_transition / post_transition / hybrid"
    )


def default_pre_portion_for_year(leave_year: int) -> float:
    """系统层：转制日后离职的「旧雇员」平均转制前服务占比 [假设]。

    随日历推移，剩余旧雇员的转制前占比上升（因其入职更早、转制后年资变长
    会使占比下降——此处用缓降刻画「平均旧雇员」）。
    """
    if leave_year < TRANSITION_YEAR:
        return 1.0
    # 2025: ~0.85 → 2035: ~0.35 → 2045: ~0.15
    t = leave_year - TRANSITION_YEAR
    return float(np.clip(0.85 - 0.05 * t, 0.10, 0.95))


def cohort_weights(year: int) -> Dict[str, float]:
    """当年触发对冲的离职案中，各队列权重（合计 1）。

    - 2025 年前：几乎全是 pre（转制前规则）
    - 2025–2035：pre/hybrid 下降，post 上升
    - 2035 年后：pre/hybrid 趋近 0

    Returns:
        ``pre_transition`` / ``hybrid`` / ``post_transition`` 权重。
    """
    if year < TRANSITION_YEAR:
        return {"pre_transition": 1.0, "hybrid": 0.0, "post_transition": 0.0}

    t = year - TRANSITION_YEAR  # 0 at 2025
    # pre：转制前入职且转制前已离职 —— 2025 起迅速归零
    pre = 0.0 if year >= TRANSITION_YEAR else 1.0
    # hybrid：转制前入职、转制后离职 —— 主力衰减队列
    # 2025≈0.90 → 2035≈0.15 → 2045≈0.02
    hybrid = float(np.clip(0.90 * np.exp(-0.18 * t), 0.0, 0.95))
    # 2025 年转制日前进离职仍有一小段按旧例：用年中权重近似
    if year == TRANSITION_YEAR:
        pre = 0.33  # 约 1–4 月 [假设]
        hybrid = 0.55
    post = float(np.clip(1.0 - pre - hybrid, 0.0, 1.0))
    s = pre + hybrid + post
    return {
        "pre_transition": pre / s,
        "hybrid": hybrid / s,
        "post_transition": post / s,
    }


def offset_scale_factor(year: int) -> float:
    """对冲「案量」相对 2024 基准的缩放。

    2025 前：≈1；其后随旧雇员退出下降，但 post 队列仍有自愿对冲残差。
    """
    if year <= 2024:
        # 轻微历史波动 [假设]
        return float(1.0 + 0.02 * (year - 2024))
    t = year - TRANSITION_YEAR
    # 总对冲案量：旧规则驱动部分衰减 + 自愿对冲残差地板
    legacy = np.exp(-0.16 * max(t, 0))
    residual = 0.12  # post 队列自愿对冲长期地板（相对 2024 案量）
    if year == TRANSITION_YEAR:
        # 年内过渡：旧例 4 个月 + 新例 8 个月
        return float(0.40 * 1.0 + 0.60 * (0.75 * legacy + residual))
    return float(np.clip(0.88 * legacy + residual, 0.08, 1.2))


def system_offsetting_outflow(
    year: int,
    aum_yi: float,
    employer_contrib_yi: Optional[float] = None,
) -> Dict[str, float]:
    """系统层年度对冲流出（亿港元）。

    构造「代表性案」余额后，按队列权重加权 ``calc_offsetting_flow``。

    Args:
        year: 日历年。
        aum_yi: 期初总资产（亿），用于缩放雇主累算池。
        employer_contrib_yi: 可选当年雇主强制供款流量，辅助定余额量级。

    Returns:
        总流出及分队列金额、权重、占比。
    """
    # 潜在对冲池：与资产规模联动（亿）
    # 2024 校准：使总流出 ≈ OFFSET_BASE_2024_YI
    aum_ref = 12900.0  # 2024 年底量级 [真实数据量级]
    pool = OFFSET_BASE_2024_YI / SEVERANCE_REALIZATION
    pool *= (aum_yi / aum_ref) if aum_yi > 0 else 1.0
    pool *= offset_scale_factor(year)

    er_m = pool * (1.0 - VOL_SHARE_OF_ER_POOL)
    er_v = pool * VOL_SHARE_OF_ER_POOL
    sev = pool * SEVERANCE_REALIZATION
    if employer_contrib_yi is not None and employer_contrib_yi > 0:
        # 轻量挂钩雇主供款流量，避免与缴费层脱节
        er_m = 0.85 * er_m + 0.15 * float(employer_contrib_yi) * 0.08

    weights = cohort_weights(year)
    # 代表性入职年：hybrid 用「转制前若干年」；pre 用更早；post 用转制后
    hire_pre = year - 12.0
    hire_hybrid = min(year - 8.0, TRANSITION_YEAR - 0.5)
    hire_post = max(TRANSITION_YEAR + 0.2, year - 3.0)

    parts = {}
    total = 0.0
    for ctype, w in weights.items():
        if w <= 0:
            parts[ctype] = 0.0
            continue
        hire = {
            "pre_transition": hire_pre,
            "hybrid": hire_hybrid,
            "post_transition": hire_post,
        }[ctype]
        # pre_transition 在转制后年权重应为 0；若残留则按转制前离职处理（portion=1）
        leave_month = 3.0 if ctype == "pre_transition" else 6.0
        flow = calc_offsetting_flow(
            year=year,
            cohort_type=ctype,
            employer_mandatory_balance=er_m,
            employer_voluntary_balance=er_v,
            severance_payment=sev,
            hire_year=hire,
            leave_year=float(year),
            leave_month=leave_month,
        )
        amt = w * flow
        parts[ctype] = amt
        total += amt

    # 2024 再精确校准一次缩放（仅作水平锚定，不改相对结构）
    if year == 2024 and total > 0:
        # 上面构造已使期望接近 BASE；此处记录即可
        pass

    out = {
        "年份": year,
        "对冲流出_合计_亿港元": total,
        "对冲流出_pre_transition_亿港元": parts.get("pre_transition", 0.0),
        "对冲流出_hybrid_亿港元": parts.get("hybrid", 0.0),
        "对冲流出_post_transition_亿港元": parts.get("post_transition", 0.0),
        "权重_pre": weights["pre_transition"],
        "权重_hybrid": weights["hybrid"],
        "权重_post": weights["post_transition"],
        "转制日": TRANSITION_DATE,
    }
    if total > 0:
        out["占比_pre"] = parts.get("pre_transition", 0.0) / total
        out["占比_hybrid"] = parts.get("hybrid", 0.0) / total
        out["占比_post"] = parts.get("post_transition", 0.0) / total
    else:
        out["占比_pre"] = out["占比_hybrid"] = out["占比_post"] = 0.0
    return out


def project_offsetting_series(
    years,
    aum_by_year: Optional[Dict[int, float]] = None,
    aum_default: float = 16700.0,
) -> pd.DataFrame:
    """生成多年对冲流出表。

    Args:
        years: 年份可迭代。
        aum_by_year: 可选各年期初资产；缺省用常数。
        aum_default: 缺省资产（亿港元）。

    Returns:
        DataFrame。
    """
    rows = []
    for y in years:
        aum = float(aum_by_year.get(int(y), aum_default)) if aum_by_year else aum_default
        rows.append(system_offsetting_outflow(int(y), aum))
    return pd.DataFrame(rows)


# ---------- 与全自由行等并列的制度局限说明（不进入资产方程） ----------
MODEL_SCOPE_NOTES = [
    "对冲：按转制日 2025-05-01 入职/离职队列分层；不具追溯力，流出渐进归零。",
    "全自由行：2025-09 完成修例，首阶段预计 2026 Q4 实际实施、次阶段 2027 上半年立法；"
    "不改变制度总资产，仅影响账户分布与市场竞争——本模块不建模受托人迁移流量。",
    "有关入息上下限：现行 7100/30000；2028 起 10500/40000 为基准情景假设（非法定值，"
    "最终幅度与时间表待政府公布；敏感性保留维持现行对照）。",
]


def model_limitation_notes() -> list:
    """返回对冲模块相关的模型局限条文（供报告/P3 面板引用）。"""
    return list(MODEL_SCOPE_NOTES)
