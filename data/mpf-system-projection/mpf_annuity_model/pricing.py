# -*- coding: utf-8 -*-
"""年金定价锚点与情景参数。

来源：
  [真实数据] 香港年金有限公司《保证每月年金金额示例表》（男65:5800 / 女65:5300 每百万）
  [真实数据] 保证领取 105% 保费
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol


RANDOM_SEED = 42

# ---------- 香港年金公开量级（65 岁投保）----------
# [真实数据] 香港年金有限公司《保证每月年金金额示例表》
#   整付保费 100 万：男 65 岁月付 5,800（保证期 182 个月）；
#   女 65 岁月付 5,300（保证期 199 个月）。
# 勿再用「余命 18/24」粗调女性费率——官方表已分性别定价。
ANNUITY_PREMIUM_UNIT = 1_000_000.0
ANNUITY_MONTHLY_MALE_PER_1M = 5800.0  # [真实数据]
ANNUITY_MONTHLY_FEMALE_PER_1M = 5300.0  # [真实数据]
# 年化转换率（每 1 港元保费的年给付）
ANNUITY_ANNUAL_RATE_MALE = ANNUITY_MONTHLY_MALE_PER_1M * 12.0 / ANNUITY_PREMIUM_UNIT
ANNUITY_ANNUAL_RATE_FEMALE = (
    ANNUITY_MONTHLY_FEMALE_PER_1M * 12.0 / ANNUITY_PREMIUM_UNIT
)
# 男 ≈ 0.0696；女 ≈ 0.0636

# [真实数据量级] 预期寿命 / 65 岁余命（面试叙述用；定价以官方表示例为准）
E65_MALE = 18.0
E65_FEMALE = 24.0
LE_MALE = 83.3
LE_FEMALE = 88.7

# [真实数据] 保证领取至少 105% 保费
GUARANTEE_RATIO = 1.05

# [真实数据量级] 市场热度（背景，不进公式）
HK_ANNUITY_SALES_2024_YI = 44.0
HK_ANNUITY_SALES_2025_YI = 90.0

# 年金化比例网格
ANNUITIZE_RATIOS: List[float] = [0.0, 0.25, 0.50, 0.75, 1.0]

# 剩余余额提取：与对象三对齐
REPLACEMENT_TARGET = 0.50  # 目标年支出 = 前年薪 × 50%
R_RETIRE = 0.03  # 剩余余额继续投资的偏保守回报 [假设]
RETIRE_AGE = 65

# 其他收入（综援/津贴）默认 0；可在接口中注入
OTHER_INCOME_ANNUAL_DEFAULT = 0.0


class AnnuityPricer(Protocol):
    """可替换的年金定价接口。"""

    def annual_payout(self, premium: float, sex: str, age: int = 65) -> float:
        """保费 → 年给付（港元）。"""


@dataclass
class SimpleHKAnnuityPricer:
    """线性定价：年给付 = 保费 × 分性别转换率。

    费率锚点：香港年金官方示例表（65 岁男 5800 / 女 5300 每百万）。
    可替换为真实产品费率表（按年龄/性别/保证期）。
    """

    rate_male: float = ANNUITY_ANNUAL_RATE_MALE
    rate_female: float = ANNUITY_ANNUAL_RATE_FEMALE
    guarantee_ratio: float = GUARANTEE_RATIO

    def rate_for(self, sex: str) -> float:
        return self.rate_female if sex == "女" else self.rate_male

    def monthly_per_1m(self, sex: str) -> float:
        if sex == "女":
            return ANNUITY_MONTHLY_FEMALE_PER_1M
        return ANNUITY_MONTHLY_MALE_PER_1M

    def annual_payout(self, premium: float, sex: str, age: int = 65) -> float:
        # age 预留：真实费率表可按投保年龄查表
        _ = age
        return float(premium) * self.rate_for(sex)

    def years_to_guarantee(self, sex: str) -> float:
        """领满保证金额所需年数（若持续领取）。"""
        r = self.rate_for(sex)
        return self.guarantee_ratio / r if r > 0 else float("inf")


def e65_for_sex(sex: str) -> float:
    return E65_FEMALE if sex == "女" else E65_MALE


def expected_death_age(sex: str, retire_age: int = RETIRE_AGE) -> float:
    return retire_age + e65_for_sex(sex)
