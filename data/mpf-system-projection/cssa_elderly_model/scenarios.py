# -*- coding: utf-8 -*-
"""综援长者情景与真实锚点。

参数来源标注约定：
  [真实数据] 社署 / 财政预算公开数字
  [反推]     由真实锚点与人口层相除得到
  [假设]     情景或缺乏官方分拆时的建模假设
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ---------- 真实数据锚点（社署 / 财政公开量级）----------
# [真实数据] 2025-03 综援个案总数
CSSA_CASES_TOTAL_2025_03 = 195581
# [真实数据] 年老个案占比 56.7%；用户稿约 110,846 宗（195581×56.7%≈110,894，取公开约数 110,846）
CSSA_ELDERLY_SHARE_2025_03 = 0.567
CSSA_ELDERLY_CASES_2025_03 = 110846
# [真实数据] 2025-03 受助人数
CSSA_RECIPIENTS_2025_03 = 262266
# [真实数据] 2025-12 受助人数约 256,518
CSSA_RECIPIENTS_2025_12 = 256518
# [真实数据] 2024-25 年度综援总开支（亿港元）
CSSA_TOTAL_SPEND_2024_25_YI = 223.53
# [真实数据] 2025-26 年度预算约（亿港元）
CSSA_BUDGET_2025_26_YI = 231.0
# [真实数据量级] 单身长者平均每月领取约 8,600 港元
MONTHLY_ALLOWANCE_2025 = 8600.0

# 校准锚点年：用 2026 人口层起步年对齐「约 11 万宗年老个案」
CALIB_YEAR = 2026
CALIB_ELDERLY_CASES = float(CSSA_ELDERLY_CASES_2025_03)  # [真实数据] 以 2025-03 结构作量级锚点

# ---------- 审查通过率拆分（产品校准，拆分为假设）----------
# 综合有效领取率 = 申请率 × 资产审查通过率
# 基准情景下产品由校准锁定；拆分比例为 [假设]，便于面试解释
APPLY_RATE_SHARE_OF_EFFECTIVE = 0.55  # [假设] 综合率中「愿意/会申请」部分
# → 若综合率 6.05%，则申请率≈11.0%，审查通过率≈55%（见 run 打印）


@dataclass(frozen=True)
class CssaScenario:
    """综援长者情景。

    Attributes:
        code: 情景码。
        label: 中文标签。
        pop_scenario: 共用人口层低/中/高。
        effective_rate_mult: 相对校准综合领取率的乘数。
        inflation: 津贴名义年通胀/调整率。
        note: 情景含义（财政压力方向）。
    """

    code: str
    label: str
    pop_scenario: str
    effective_rate_mult: float
    inflation: float
    note: str


# 财政分析口径：
#   保守 = 支出压力较低；基准 = 校准路径；高支出压力 = 领取率与津贴增速更高
SCENARIOS: Dict[str, CssaScenario] = {
    "低": CssaScenario(
        code="低",
        label="保守（支出偏低）",
        pop_scenario="低",
        effective_rate_mult=0.90,  # [假设] 领取率略降（就业/资产改善）
        inflation=0.015,  # [假设] 津贴调整偏慢
        note="领取率×0.9、通胀1.5%、人口低方案",
    ),
    "中": CssaScenario(
        code="中",
        label="基准",
        pop_scenario="中",
        effective_rate_mult=1.00,  # 锚定 2025-03 年老个案 / 2026 年 65+ 人口
        inflation=0.025,  # [假设] 接近近年综合社会保障援助调整量级
        note="综合领取率校准值、通胀2.5%、人口中方案",
    ),
    "高": CssaScenario(
        code="高",
        label="高支出压力",
        pop_scenario="高",
        effective_rate_mult=1.15,  # [假设] 申请更积极或审查边际放宽
        inflation=0.035,  # [假设] 津贴加快上调
        note="领取率×1.15、通胀3.5%、人口高方案",
    ),
}


def get_scenario(code: str) -> CssaScenario:
    """按别名取情景。"""
    alias = {
        "保守": "低",
        "基准": "中",
        "乐观": "高",  # 对财政=更高支出
        "高压力": "高",
        "low": "低",
        "mid": "中",
        "high": "高",
    }
    key = alias.get(code, code)
    if key not in SCENARIOS:
        raise KeyError(f"未知情景 {code}；可选 {list(SCENARIOS)}")
    return SCENARIOS[key]
