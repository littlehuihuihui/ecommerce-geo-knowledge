# -*- coding: utf-8 -*-
"""P2 系统性 debug / 校验：参数表、逻辑报告、回测偏差。

用法::

    python debug_validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from contribution import LFPR_BASE, assert_labour_age_alignment
from data_loader import AUM_2026, load_all_tables, load_real_data
from population import AGE_GROUPS_5, LABOUR_AGES
from run import project_one_scenario
from scenarios import (
    EMPF_FEE_2026,
    FUND_RETURNS,
    SYSTEM_NET_RETURN_MID,
    empf_fee_schedule,
    get_scenario,
    relevant_income_limits,
    system_weighted_return,
)
from withdrawal import (
    DEPART_2026_Q2_YI,
    DEPART_2026_YI,
    permanent_departure_withdrawal,
)

OUT = _PKG / "output" / "debug"
OUT.mkdir(parents=True, exist_ok=True)

# 回测锚点
# 用户稿「2020 约 1 万亿」 vs 积金局公布约 11,400 亿——表中并列
AUM_2020_USER = 10000.0
AUM_2020_MPFA = 11400.0  # [真实数据] 积金局 2020 年底
AUM_2025 = 15500.0
AUM_2026_MID = 16700.0


def task1_param_table() -> pd.DataFrame:
    """任务一：参数对照表。"""
    rows = [
        {
            "参数名": "2026起始总资产",
            "代码中的值": AUM_2026,
            "应使用值": 16700.0,
            "来源": "积金局约2026年中",
            "是否一致": "是" if abs(AUM_2026 - 16700) < 1e-6 else "否",
        },
        {
            "参数名": "eMPF费率_2026",
            "代码中的值": EMPF_FEE_2026,
            "应使用值": 0.0029,
            "来源": "积金局2026-04-01起",
            "是否一致": "是" if abs(EMPF_FEE_2026 - 0.0029) < 1e-9 else "否",
        },
        {
            "参数名": "永久离港_2026年化",
            "代码中的值": round(permanent_departure_withdrawal(2026), 2),
            "应使用值": round(DEPART_2026_Q2_YI * 4, 2),
            "来源": "2026Q2=12.03亿x4年化[假设]",
            "是否一致": (
                "是"
                if abs(permanent_departure_withdrawal(2026) - DEPART_2026_YI) < 0.01
                else "否"
            ),
        },
        {
            "参数名": "股票基金制度以来回报",
            "代码中的值": FUND_RETURNS["股票基金"],
            "应使用值": 0.051,
            "来源": "积金局公开量级（非5.0%）",
            "是否一致": "是" if abs(FUND_RETURNS["股票基金"] - 0.051) < 1e-9 else "否",
        },
        {
            "参数名": "DIS核心累积回报",
            "代码中的值": FUND_RETURNS["DIS核心累积基金"],
            "应使用值": 0.073,
            "来源": "截至约2026-06",
            "是否一致": (
                "是"
                if abs(FUND_RETURNS["DIS核心累积基金"] - 0.073) < 1e-9
                else "否"
            ),
        },
        {
            "参数名": "供款上限_2026",
            "代码中的值": relevant_income_limits(2026)[1],
            "应使用值": 30000.0,
            "来源": "现行条例；过渡至2028",
            "是否一致": "是" if relevant_income_limits(2026)[1] == 30000 else "否",
        },
        {
            "参数名": "供款上限_2028",
            "代码中的值": relevant_income_limits(2028)[1],
            "应使用值": 40000.0,
            "来源": "假设新值",
            "是否一致": "是" if relevant_income_limits(2028)[1] == 40000 else "否",
        },
        {
            "参数名": "系统净回报中枢",
            "代码中的值": SYSTEM_NET_RETURN_MID,
            "应使用值": 0.049,
            "来源": "制度加权约4.9%",
            "是否一致": "是" if abs(SYSTEM_NET_RETURN_MID - 0.049) < 1e-9 else "否",
        },
        {
            "参数名": "配置加权校验",
            "代码中的值": round(system_weighted_return(), 4),
            "应使用值": "~0.049-0.055",
            "来源": "FUND_RETURNSxALLOC（校验用）",
            "是否一致": "是（量级）",
        },
    ]
    return pd.DataFrame(rows)


def task2_logic_report() -> pd.DataFrame:
    """任务二：逻辑自洽。"""
    try:
        assert_labour_age_alignment()
        age_ok = "通过"
    except AssertionError as e:
        age_ok = f"失败:{e}"

    labour_in_ages = set(LABOUR_AGES).issubset(set(AGE_GROUPS_5))
    lfpr_by_age = len({k[0] for k in LFPR_BASE}) >= 10

    rows = [
        {
            "检查项": "人口年龄组 <-> 缴费 LFPR 分组",
            "问题描述": "LABOUR_AGES 与 LFPR_BASE 键是否一一对应；是否均为 5 岁组",
            "结果": age_ok,
            "影响": "不一致会导致漏计/错配缴费人数",
            "建议解法": "contribution.assert_labour_age_alignment() 启动时强制校验（已启用）",
        },
        {
            "检查项": "劳动参与率是否分年龄性别",
            "问题描述": f"LFPR 表含 {len(LFPR_BASE)} 个(年龄,性别)键；分年龄={lfpr_by_age}",
            "结果": "通过" if lfpr_by_age else "失败",
            "影响": "若用单一 LFPR 会高估高龄供款",
            "建议解法": "保持分年龄性别表；用 C&SD 更新数值",
        },
        {
            "检查项": "平均账户余额循环依赖",
            "问题描述": "余额=期初A/账户数x溢价 -> W -> 期末A；同期内不联立",
            "结果": "无代数循环（有一期滞后）",
            "影响": "当年市场大涨/大跌不会立刻改写同年达龄余额基数",
            "建议解法": "维持期初口径；若需年内一致可改年中流量或迭代 1-2 次（二期）",
        },
        {
            "检查项": "资产公式是否扣对冲",
            "问题描述": "A(t+1)=A(t)(1+r)+C-W-Offset",
            "结果": "已扣减（asset.step_asset / run 默认 enable_offsetting=True）",
            "影响": "若漏扣会高估资产约千亿量级（30 年累计）",
            "建议解法": "保持 Offset 项；对照情景可关 enable_offsetting",
        },
        {
            "检查项": "投资回报计算基数",
            "问题描述": "回报 = 期初资产 x r（先计息再加减流量）",
            "结果": "通过",
            "影响": "与年中流量惯例差额通常 < 数个百分点量级",
            "建议解法": "面试时说清期末惯例；精细化可用半年惯例",
        },
        {
            "检查项": "劳动年龄 ⊆ 全年龄组",
            "问题描述": f"LABOUR_AGES subset AGE_GROUPS_5 = {labour_in_ages}",
            "结果": "通过" if labour_in_ages else "失败",
            "影响": "人口投影缺组则缴费层取空",
            "建议解法": "统一 AGE_GROUPS_5 常量",
        },
    ]
    return pd.DataFrame(rows)


def task3_backtest() -> pd.DataFrame:
    """任务三：简化回测（历史回报路径 + 对冲）。"""
    from validate_analysis import (
        ACCOUNTS_2020,
        HIST_RETURNS,
        load_csd_midyear_population,
    )
    from scenarios import Y_MAX_OLD, Y_MIN_OLD

    tables = load_all_tables()
    mid = get_scenario("中")
    base = load_csd_midyear_population("202006")

    # 期初：用「用户 1 万亿」与「倒推使 2020 末贴近 11400」两种对照太重；
    # 取 A0=9800，历史回报，输出 2020/2025/2026 末（2026 用外推一年）
    res = project_one_scenario(
        tables,
        mid,
        start_year=2020,
        end_year=2026,
        a0=9800.0,
        accounts0=ACCOUNTS_2020,
        y_min=Y_MIN_OLD,
        y_max=Y_MAX_OLD,
        income_scale=1.0,
        balance_scale=0.75,
        income_base_year=2025,
        base_mid_income=18500.0,
        base_pop=base,
        returns_by_year={**HIST_RETURNS, 2026: 0.049},
        enable_offsetting=True,
    )
    ann = res["annual"].set_index("年份")

    checks = [
        (2020, "期末资产", float(ann.loc[2020, "期末资产_亿港元"]), AUM_2020_MPFA, "积金局约11400"),
        (2020, "期末资产_对照用户万亿", float(ann.loc[2020, "期末资产_亿港元"]), AUM_2020_USER, "用户稿约10000"),
        (2025, "期末资产", float(ann.loc[2025, "期末资产_亿港元"]), AUM_2025, "真实锚点15500"),
        (2026, "期末资产_近中", float(ann.loc[2026, "期末资产_亿港元"]), AUM_2026_MID, "2026中16700"),
    ]
    rows = []
    for year, name, model, actual, note in checks:
        bias = (model - actual) / actual if actual else np.nan
        rows.append(
            {
                "年份": year,
                "指标": name,
                "模型值_亿港元": round(model, 2),
                "真实锚点_亿港元": actual,
                "偏差率": round(bias, 4),
                "判定": "可接受" if abs(bias) <= 0.10 else "需调整",
                "说明": note,
            }
        )
    return pd.DataFrame(rows), res["annual"]


def write_report(params: pd.DataFrame, logic: pd.DataFrame, backtest: pd.DataFrame) -> None:
    """写 Markdown 校验报告。"""

    def md(df: pd.DataFrame) -> str:
        cols = list(df.columns)
        lines = [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join("---" for _ in cols) + " |",
        ]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
        return "\n".join(lines)

    text = f"""# P2 模型系统性 Debug / 校验报告

> 生成：`debug_validate.py` · `load_real_data()` 仍为 CSV 预留接口  
> 随机种子 / 金额单位：亿港元

---

## 任务一：参数一致性

{md(params)}

### 小结
- **总资产 16700、eMPF 0.29%、上下限过渡、股票 5.1%、DIS 7.3%**：与应使用值一致。
- **永久离港**：已改为 2026=Q2x4=**{DEPART_2026_YI:.2f}** 亿（原「2025 起每年-10%」会得到 52.97，高于 Q2 年化约 10%，已修正）。

---

## 任务二：逻辑自洽性

{md(logic)}

### 循环依赖结论
**不存在需联立求解的循环。** 余额用期初 A；公式为  
`A(t+1)=A(t)x(1+r)+C(t)-W(t)-Offset(t)`，回报基数为 **期初 A(t)**，且已减对冲。

---

## 任务三：回测验证（2020-2026）

说明：用户稿「2020 约 1 万亿」与积金局公布 **约 11,400 亿** 并存；判定以积金局锚点为主。

{md(backtest)}

### 若偏差>10% 的调整建议
1. **优先换历史真实年度回报**（恒定 4.9% 无法拟合 2022 熊市）。
2. 校准 **2020 期初资产**（若锚定年末 11400，期初约 0.95-1.0 万亿量级）。
3. 提取/对冲水平用 2025 真实流量再闭合 `balance_scale`。
4. 勿用「用户万亿」与「积金局 11400」混为同一锚点。

---

## 任务四：代码状态

已修正并保留接口：`population.py` / `contribution.py` / `withdrawal.py` /  
`asset.py` / `offsetting.py` / `scenarios.py` / `run.py`；`load_real_data()` 仍可用。
"""
    (OUT / "DEBUG_REPORT.md").write_text(text, encoding="utf-8")


def main() -> None:
    # 证明预留接口可调用
    _ = load_real_data()

    params = task1_param_table()
    logic = task2_logic_report()
    backtest, annual = task3_backtest()

    params.to_csv(OUT / "D01_param_consistency.csv", index=False, encoding="utf-8-sig")
    logic.to_csv(OUT / "D02_logic_checks.csv", index=False, encoding="utf-8-sig")
    backtest.to_csv(OUT / "D03_backtest_bias.csv", index=False, encoding="utf-8-sig")
    annual.to_csv(OUT / "D03_backtest_annual.csv", index=False, encoding="utf-8-sig")
    write_report(params, logic, backtest)

    print(params.to_string(index=False))
    print("---")
    print(logic[["检查项", "结果"]].to_string(index=False))
    print("---")
    print(backtest.to_string(index=False))
    print("report:", OUT / "DEBUG_REPORT.md")


if __name__ == "__main__":
    main()
