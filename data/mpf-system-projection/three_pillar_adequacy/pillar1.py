# -*- coding: utf-8 -*-
"""第一支柱（公共福利）与互斥规则 · 参数锚点。

来源标注：
  [真实数据] 社署公开津贴额 / 限额（以注明生效日为准）
  [假设] 个体资产如何计入、情景开关
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# ---------- 长者生活津贴 OALA（公共福利金）----------
# [真实数据] 社署：由 2026-02-01 起
OALA_MONTHLY_2026 = 4345.0
OALA_INCOME_LIMIT_SINGLE = 10900.0  # 每月总入息上限（单身）
OALA_ASSET_LIMIT_SINGLE = 415000.0  # 资产总值上限（单身）
# 夫妇限额备查（本模块默认单身代表性个体）
OALA_INCOME_LIMIT_COUPLE = 16680.0
OALA_ASSET_LIMIT_COUPLE = 630000.0

# [真实数据] 2025-02-01 起曾为 4,250；模型主路径用 2026 起金额
OALA_MONTHLY_2025 = 4250.0

# ---------- 高龄津贴 OAA（生果金）----------
# [真实数据] 社署公共福利金：2025-02-01 起高龄津贴 1,640／月；70 岁+，不设经济审查
OAA_MONTHLY = 1640.0
OAA_MIN_AGE = 70

# ---------- 综援（长者部分）量级 ----------
# [真实数据量级] 任务锚点：单身长者约 8,600／月（含标准金额等合并口径的教学近似）
CSSA_ELDERLY_MONTHLY = 8600.0

# ---------- 替代率目标 ----------
# [参考] 世界银行常引区间；百科 methodology 亦写 40%–70%
REPLACEMENT_TARGET_LOW = 0.40
REPLACEMENT_TARGET_HIGH = 0.70
REPLACEMENT_TARGET_MID = 0.50  # 与对象三默认目标一致


class FirstPillarChoice(str, Enum):
    """第一支柱领取选择（互斥简化）。"""

    NONE = "无第一支柱"
    OALA = "长者生活津贴"
    OAA = "高龄津贴(生果金)"  # 需年满 70
    CSSA = "综援(长者)"


@dataclass
class PersonMeans:
    """经济状况（用于长津/综援资格示意）。

    Attributes:
        age: 年龄。
        monthly_income_ex_welfare: 不计公共福利的每月入息
            （含年金月付、职业退休金、租金净收入等；教学简化）。
        countable_assets: 计入审查的资产
            （强积金未提取余额通常计入；已付年金保费一般不计入资产——社署 FAQ）。
        on_cssa: 是否已领综援。
        on_oala: 是否已领长津。
        on_oaa: 是否已领生果金。
    """

    age: int = 65
    monthly_income_ex_welfare: float = 0.0
    countable_assets: float = 0.0
    on_cssa: bool = False
    on_oala: bool = False
    on_oaa: bool = False


def check_oala_eligibility(m: PersonMeans, single: bool = True) -> Tuple[bool, str]:
    """长者生活津贴资格示意检查。

    关键互斥（社署）：不可同时领长津与综援 / 高龄津贴 / 伤残津贴。
    """
    if m.age < 65:
        return False, "未满65岁"
    if m.on_cssa:
        return False, "已领综援（与长津互斥）"
    if m.on_oaa:
        return False, "已领高龄津贴/生果金（与长津互斥）"
    inc_lim = OALA_INCOME_LIMIT_SINGLE if single else OALA_INCOME_LIMIT_COUPLE
    as_lim = OALA_ASSET_LIMIT_SINGLE if single else OALA_ASSET_LIMIT_COUPLE
    if m.monthly_income_ex_welfare > inc_lim:
        return False, f"入息 {m.monthly_income_ex_welfare:,.0f} > 上限 {inc_lim:,.0f}"
    if m.countable_assets > as_lim:
        return False, f"资产 {m.countable_assets:,.0f} > 上限 {as_lim:,.0f}"
    return True, "符合长津入息·资产示意条件"


def check_oaa_eligibility(m: PersonMeans) -> Tuple[bool, str]:
    """高龄津贴（生果金）：70+，不设经济审查；与长津/综援互斥。"""
    if m.age < OAA_MIN_AGE:
        return False, f"未满{OAA_MIN_AGE}岁（生果金门槛）"
    if m.on_cssa:
        return False, "已领综援（互斥）"
    if m.on_oala:
        return False, "已领长津（互斥）"
    return True, "符合生果金年龄条件（无资产审查）"


def check_cssa_sketch(m: PersonMeans) -> Tuple[bool, str]:
    """综援示意：资产须显著更低；与长津/生果金互斥。

    教学简化：资产 < 长津限额的一定比例且入息很低才标「可能符合」。
    真实综援规则更复杂（家庭、租金、豁免等），不可当申请结论。
    """
    if m.on_oala or m.on_oaa:
        return False, "已领长津/生果金（与综援互斥）"
    if m.age < 65:
        return False, "本模块只示意长者综援"
    # 示意：资产远低于长津上限、入息接近零
    if m.countable_assets <= OALA_ASSET_LIMIT_SINGLE * 0.15 and m.monthly_income_ex_welfare < 3000:
        return True, "资产·入息很低，示意可能走综援通道（非正式资格）"
    return False, "资产/入息未到综援示意门槛（多数中产账户走不了综援）"


def first_pillar_monthly(
    choice: FirstPillarChoice,
    means: PersonMeans,
) -> Tuple[float, str, bool]:
    """按选择尝试发放第一支柱月金额。

    Returns:
        (月金额, 说明, 是否发放成功)
    """
    if choice == FirstPillarChoice.NONE:
        return 0.0, "不申领第一支柱", True
    if choice == FirstPillarChoice.OALA:
        ok, msg = check_oala_eligibility(means)
        return (OALA_MONTHLY_2026 if ok else 0.0), msg, ok
    if choice == FirstPillarChoice.OAA:
        ok, msg = check_oaa_eligibility(means)
        return (OAA_MONTHLY if ok else 0.0), msg, ok
    if choice == FirstPillarChoice.CSSA:
        ok, msg = check_cssa_sketch(means)
        return (CSSA_ELDERLY_MONTHLY if ok else 0.0), msg, ok
    return 0.0, "未知选择", False
