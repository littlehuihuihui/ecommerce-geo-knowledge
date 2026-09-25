# -*- coding: utf-8 -*-
"""
P0 基础数据集生成器（对接 12_model_design_concept.md）

产出 5 张表（年度颗粒度；金额单位亿港元）：
  T01 分年龄性别死亡率（2020–2025实际 + 2026–2056预测）
  T02 分年龄组人口预测（2026–2056，三情景）
  T03 缴费人口与供款参数（默认新上下限；旧值对照）
  T04 投资回报假设（三情景 + eMPF 费率）
  T05 提取行为假设（按理由分类）

真实锚点优先；缺口标 [假设] 并写依据。
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CCM = ROOT / "population_ccm"
OUT = ROOT / "p0_foundation"
OUT.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2026, 2057))
SCENARIOS = ("低", "中", "高")

# ---------- 制度 / 校准锚点（用户规格） ----------
RATE_EE = 0.05  # [真实数据] 雇员强制 5%
RATE_ER = 0.05  # [真实数据] 雇主强制 5%
Y_MIN_OLD, Y_MAX_OLD = 7100, 30000  # [真实数据] 现行
Y_MIN_NEW, Y_MAX_NEW = 10500, 40000  # 拟调整；模型默认用新值（政策情景，尚未立法）
COVERAGE = 0.85  # [假设]
OFFSET_ABOLITION_DATE = "2025-05-01"  # [真实数据]

CONTRIB_FY2526 = 912.3  # [真实数据] 亿港元
KAPPA_VOL = 0.26  # [真实数据] 自愿约占总供款 26%
CONTRIB_Q2_2026 = 234.0  # [真实数据] 亿港元

R_SYSTEM_MID = 0.049  # [真实数据/公开中枢] 制度加权约 4.9%
FUND_RETURNS = {
    "股票基金": 0.051,
    "混合资产基金": 0.048,
    "DIS核心累积基金": 0.073,
    "保守基金": 0.015,  # [假设] 公开报道较少单独给点估计，取低波锚
}
ALLOC = {
    "股票基金": 0.30,
    "混合资产基金": 0.35,
    "DIS核心累积基金": 0.25,
    "保守基金": 0.10,
}  # [假设] 系统配置权重，用于情景加权校验
EMPF_FEE = 0.0029  # [真实数据] 0.29%
EMPF_FEE_OLD = 0.0037  # [真实数据] 旧值 0.37%

W_RETIRE_Q4_2025 = 56.79  # [真实数据] 亿
LUMP_SUM_SHARE = 0.947  # [真实数据] 一笔过 94.7%
W_RETIRE_2025_COUNT = 15.38  # [真实数据] 万宗
W_RETIRE_2025_AMT = 195.66  # [真实数据] 亿

AUM_2025YE = 15500.0  # [真实数据] 亿
AUM_2026MID = 16700.0  # [真实数据] 亿
ACCOUNTS_WAN = 1120.0  # [真实数据] 万个

# 入息名义增速 [假设]
INCOME_GROWTH = {"低": 0.02, "中": 0.03, "高": 0.04}
# LFPR 整体扰动 [假设]
LFPR_SHIFT = {"低": -0.02, "中": 0.0, "高": 0.02}
EMP_RATE = 0.97  # [假设] 就业/劳动人口


def _tag(kind: str, note: str) -> str:
    return f"[{kind}] {note}"


def build_t01_mortality() -> pd.DataFrame:
    """复用 population_ccm/P01（已由 C&SD 115-01023 + 改善率外推生成）。"""
    src = CCM / "P01_mortality_rates.csv"
    if not src.exists():
        raise FileNotFoundError(f"缺少 {src}，请先运行 _gen_population_ccm.py")
    df = pd.read_csv(src)
    # 统一标注字段，保留原列
    df = df.rename(columns={"来源或假设": "来源或假设_原始"})
    rows = []
    for _, r in df.iterrows():
        y = int(r["年份"])
        dtype = r["数据类型"]
        if dtype.startswith("实际"):
            tag = _tag(
                "真实数据",
                "C&SD表115-01023年龄性别死亡率；2022为疫情年，改善率估计已剔除",
            )
        else:
            tag = _tag(
                "假设",
                "以2024实际为锚，按2020-2024剔2022经验+年龄递减先验各半的年化改善率外推；改善率随年龄组上升而递减",
            )
        rows.append(
            {
                "年份": y,
                "性别": r["性别"],
                "年龄组": r["年龄组"],
                "死亡率_每千人": r["死亡率_每千人"],
                "年化改善率": r["年化改善率"],
                "数据类型": dtype,
                "真实或假设": "真实数据" if dtype.startswith("实际") else "假设",
                "来源或假设": tag,
            }
        )
    out = pd.DataFrame(rows)
    out = out.sort_values(["年份", "性别", "年龄组"]).reset_index(drop=True)
    return out


def build_t02_population() -> pd.DataFrame:
    """复用 P02；补充劳动年龄/准退休标记与真实/假设标注。"""
    src = CCM / "P02_population_by_age_sex.csv"
    if not src.exists():
        raise FileNotFoundError(f"缺少 {src}，请先运行 _gen_population_ccm.py")
    df = pd.read_csv(src)
    labour = {
        "15-19",
        "20-24",
        "25-29",
        "30-34",
        "35-39",
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
    }
    rows = []
    for _, r in df.iterrows():
        age = r["年龄组"]
        if age in labour:
            band = "劳动年龄15-64"
        elif age in {"65-69", "70-74", "75-79", "80-84", "85+"}:
            band = "退休65+"
        else:
            band = "少儿0-14"
        rows.append(
            {
                "年份": int(r["年份"]),
                "年龄组": age,
                "年龄带": band,
                "性别": r["性别"],
                "人数": r["人数"],
                "人数_万人": round(float(r["人数"]) / 10000.0, 4),
                "情景": r["情景"],
                "真实或假设": "混合",
                "来源或假设": _tag(
                    "混合",
                    "基准人口锚点=C&SD表110-01001A年中人口(不含外佣)；"
                    "2026-2056为队列成分法推算[假设路径]；"
                    "生育TFR 2023=751→2046=938对齐官方推算[真实数据路径形状]；"
                    "净迁移总量级对齐官方推算、年龄权重偏劳动年龄[假设]",
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["情景", "年份", "性别", "年龄组"]).reset_index(drop=True)


def _labour_wan_from_p03(year: int, scenario: str) -> float:
    """从 P03 取混合劳动年龄人口（万人）。"""
    src = CCM / "P03_key_age_aggregates.csv"
    df = pd.read_csv(src)
    g = df[(df["年份"] == year) & (df["情景"] == scenario) & (df["性别"] == "混合")]
    if g.empty:
        # 回退：中情景同年
        g = df[(df["年份"] == year) & (df["情景"] == "中") & (df["性别"] == "混合")]
    return float(g.iloc[0]["劳动人口15_64"]) / 10000.0


def _reach65_wan_from_p02(year: int, scenario: str) -> float:
    """新达65岁人数近似 = Pop(60-64)/5，万人。"""
    src = CCM / "P02_population_by_age_sex.csv"
    df = pd.read_csv(src)
    g = df[(df["年份"] == year) & (df["情景"] == scenario) & (df["年龄组"] == "60-64")]
    n = float(g["人数"].sum()) / 10000.0
    return n / 5.0


def build_t03_contribution() -> pd.DataFrame:
    """
    缴费人口与供款参数。
    默认有关入息上下限 = 拟调整值 10500/40000；
    另输出对照情景「旧上下限」。
    校准：2026 中情景总供款贴近 912.3 亿量级（自愿 κ=26%）。
    """
    # 反推：总供款 = 强制/(1-κ)；强制 = N×Y×12×10%/1e8
    # 设 2026 中：总≈912.3 → 强制≈912.3×0.74≈675.1
    # 取平均有关入息（新上限下）约 22000 港元/月 [假设，落在10500-40000内]
    # N(万人) = 强制×1e8 / (Y×12×0.10) / 10000
    #        = 675.1e8 / (22000×12×0.1) / 1e4
    y_avg_2026_new = 22000.0
    mand_2026 = CONTRIB_FY2526 * (1.0 - KAPPA_VOL)
    n_2026 = mand_2026 * 1e8 / (y_avg_2026_new * 12.0 * (RATE_EE + RATE_ER)) / 10000.0
    # ≈ 675.1e8 / 264000 / 10000 ≈ 255.7 万

    # 旧上下限下平均有关入息更低（截断更严）[假设]
    y_avg_2026_old = 18500.0

    rows = []
    for scenario in SCENARIOS:
        for year in YEARS:
            t = year - 2026
            labour = _labour_wan_from_p03(year, scenario)
            lfpr = 0.58 + LFPR_SHIFT[scenario]  # [假设] 整体参与率中枢
            # 随老龄化略降
            lfpr = lfpr - 0.0015 * t
            emp = EMP_RATE
            cov = COVERAGE
            n_formula = labour * lfpr * emp * cov

            # 用 2026 校准比例把公式人数缩放到锚点人数，并随劳动池漂移
            scale = n_2026 / (
                _labour_wan_from_p03(2026, "中") * (0.58) * EMP_RATE * COVERAGE
            )
            if scenario == "低":
                scale *= 0.94
            elif scenario == "高":
                scale *= 1.06
            n_contrib = n_formula * scale

            g_y = INCOME_GROWTH[scenario]
            # 名义入息增长，但受上限约束：新上限 40000，旧 30000
            y_new = min(y_avg_2026_new * ((1 + g_y) ** t), Y_MAX_NEW * 0.95)
            y_old = min(y_avg_2026_old * ((1 + g_y) ** t), Y_MAX_OLD * 0.95)

            for regime, ymin, ymax, yavg, is_default in (
                ("拟调整_默认", Y_MIN_NEW, Y_MAX_NEW, y_new, True),
                ("现行_对照", Y_MIN_OLD, Y_MAX_OLD, y_old, False),
            ):
                mand = n_contrib * 10000.0 * yavg * 12.0 * (RATE_EE + RATE_ER) / 1e8
                vol = mand * KAPPA_VOL / (1.0 - KAPPA_VOL)
                total = mand + vol
                rows.append(
                    {
                        "年份": year,
                        "情景": scenario,
                        "上下限制度": regime,
                        "是否模型默认": "是" if is_default else "否",
                        "有关入息下限_港元每月": ymin,
                        "有关入息上限_港元每月": ymax,
                        "上下限生效说明": (
                            "模型默认采用拟调整值10500/40000（积金局检讨/劳顾会咨询口径；尚未立法）"
                            if is_default
                            else "现行条例7100/30000（约2013/2014年起），作对照情景"
                        ),
                        "雇员强制费率": RATE_EE,
                        "雇主强制费率": RATE_ER,
                        "强积金覆盖率": cov,
                        "劳动年龄人口_万人": round(labour, 4),
                        "劳动参与率": round(lfpr, 4),
                        "就业率": emp,
                        "缴费人数_万人": round(n_contrib, 4),
                        "平均有关入息_港元每月": round(yavg, 1),
                        "年强制性供款_亿港元": round(mand, 2),
                        "自愿性供款占比": KAPPA_VOL,
                        "年自愿性供款_亿港元": round(vol, 2),
                        "年总供款_亿港元": round(total, 2),
                        "取消对冲生效日": OFFSET_ABOLITION_DATE,
                        "取消对冲处理": _tag(
                            "真实数据",
                            "2025-05-01起雇主强制供款不得对冲转制后服务年资遣散费/长服金；"
                            "本表以参数记录断点，量化漏损衰减见领取/资产层",
                        ),
                        "校准锚点说明": _tag(
                            "真实数据",
                            f"2025-26财年总供款{CONTRIB_FY2526}亿；自愿占比约{KAPPA_VOL:.0%}；"
                            f"2026Q2总供款{CONTRIB_Q2_2026}亿；覆盖率{COVERAGE:.0%}为[假设]",
                        ),
                        "真实或假设": "混合",
                        "来源或假设": _tag(
                            "混合",
                            "费率与现行/拟议上下限为制度/公开检讨锚点；"
                            "缴费人数=劳动人口×LFPR×就业×覆盖[假设路径]；"
                            "平均入息与人数经总供款量级校准；人口来自队列成分法",
                        ),
                    }
                )
    return pd.DataFrame(rows)


def build_t04_returns() -> pd.DataFrame:
    """投资回报三情景 + eMPF 费率影响。"""
    # 情景偏移：[假设]
    shifts = {"低": -0.019, "中": 0.0, "高": 0.021}  # 约 3.0% / 4.9% / 7.0%
    rows = []
    for year in YEARS:
        for scenario in SCENARIOS:
            shift = shifts[scenario]
            # 轻微成熟市场下行 + 弱周期 [假设]
            t = year - 2026
            drift = -0.00015 * t
            cycle = 0.003 * math.sin(2 * math.pi * t / 8.0)
            for fund, r0 in FUND_RETURNS.items():
                if fund == "保守基金":
                    r_gross = max(0.005, r0 + 0.3 * shift + 0.5 * drift)
                else:
                    r_gross = max(0.0, r0 + shift + drift + cycle)
                # 净回报：已含「制度公开净回报」叙事时，再单列 eMPF 敏感性
                # 基准列：采用公开点估计为「已近似净」；另给 eMPF 新旧费率差的调整项
                empf_drag_vs_old = EMPF_FEE - EMPF_FEE_OLD  # -0.0008
                r_net_baseline = r_gross  # 用户给的 5.1/4.8/7.3/4.9 按净中枢使用
                r_net_if_old_fee = r_net_baseline + (EMPF_FEE_OLD - EMPF_FEE)  # 旧费更高→净回报更低
                # 上面：若基准对应新费率0.29%，则旧费率下净回报 = 基准 - 0.08pp
                r_net_old_fee = r_net_baseline - (EMPF_FEE_OLD - EMPF_FEE)
                rows.append(
                    {
                        "年份": year,
                        "情景": scenario,
                        "基金类型": fund,
                        "配置权重_中枢": ALLOC[fund],
                        "年率化回报_小数": round(r_net_baseline, 6),
                        "年率化回报_百分比": round(r_net_baseline * 100, 3),
                        "eMPF行政费率_现行": EMPF_FEE,
                        "eMPF行政费率_旧值": EMPF_FEE_OLD,
                        "若仍用旧费率0.37%的净回报_百分比": round(r_net_old_fee * 100, 3),
                        "eMPF降费对净回报提升_bp": round((EMPF_FEE_OLD - EMPF_FEE) * 10000, 1),
                        "真实或假设": "混合",
                        "来源或假设": _tag(
                            "混合",
                            "股票5.1%/混合4.8%/DIS核心7.3%/制度加权约4.9%为公开回报中枢[真实数据量级]；"
                            "保守基金与配置权重、情景偏移、周期项为[假设]；"
                            f"eMPF费率{EMPF_FEE:.2%}←旧值{EMPF_FEE_OLD:.2%}[真实数据·积金局]",
                        ),
                    }
                )
            # 系统加权行
            wsum = sum(ALLOC[f] * FUND_RETURNS[f] for f in FUND_RETURNS)
            # 强制中情景中枢贴近 4.9%
            sys_r = R_SYSTEM_MID + shift + drift + 0.5 * cycle
            if scenario == "中":
                sys_r = R_SYSTEM_MID + drift + 0.5 * cycle
            rows.append(
                {
                    "年份": year,
                    "情景": scenario,
                    "基金类型": "制度加权(系统)",
                    "配置权重_中枢": 1.0,
                    "年率化回报_小数": round(sys_r, 6),
                    "年率化回报_百分比": round(sys_r * 100, 3),
                    "eMPF行政费率_现行": EMPF_FEE,
                    "eMPF行政费率_旧值": EMPF_FEE_OLD,
                    "若仍用旧费率0.37%的净回报_百分比": round(
                        (sys_r - (EMPF_FEE_OLD - EMPF_FEE)) * 100, 3
                    ),
                    "eMPF降费对净回报提升_bp": round((EMPF_FEE_OLD - EMPF_FEE) * 10000, 1),
                    "真实或假设": "混合",
                    "来源或假设": _tag(
                        "混合",
                        f"中情景中枢对齐制度加权约{R_SYSTEM_MID:.1%}[真实数据量级]；"
                        f"低/高情景约3%/7%[假设]；配置加权参考值≈{wsum:.3%}；含eMPF敏感性",
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_t05_withdrawal() -> pd.DataFrame:
    """提取行为：按理由分类；校准 2025 退休提取量级。"""
    # 其他提取约占总额 12% [假设]（落在 10–15% 经验带）
    other_share_of_total = 0.12
    # [真实数据] 2025 全年退休：15.38 万宗 / 195.66 亿 → 单笔约 12.72 万港元
    per_case_2025 = W_RETIRE_2025_AMT * 1e8 / (W_RETIRE_2025_COUNT * 10000.0)

    reason_shares_other = {
        "永久离港": 0.45,
        "提早退休": 0.20,
        "死亡": 0.15,
        "小额结余": 0.12,
        "丧失行为能力/绝密等": 0.08,
    }  # [假设] 其他提取内部结构，合计1

    rows = []
    for scenario in SCENARIOS:
        r_mult = {"低": 0.92, "中": 1.0, "高": 1.08}[scenario]
        for year in YEARS:
            t = year - 2026
            reach = _reach65_wan_from_p02(year, scenario) * r_mult
            # 单笔金额：以 2025 真实单笔为锚，随名义资产/工资增速抬升 [假设路径]
            g_bal = {"低": 0.025, "中": 0.04, "高": 0.055}[scenario]
            retire_bal = per_case_2025 * ((1 + g_bal) ** t)
            # 2026 中情景：人数用队列，金额用锚点单笔 → 总量级贴近 2025 的 195.66 亿
            retire_amt = reach * 10000.0 * retire_bal / 1e8  # 亿
            total_w = retire_amt / (1.0 - other_share_of_total)
            other_amt = total_w - retire_amt

            rows.append(
                {
                    "年份": year,
                    "情景": scenario,
                    "提取理由": "退休_一笔过",
                    "提取人数或宗数_万": round(reach * LUMP_SUM_SHARE, 4),
                    "占该类金额比例": LUMP_SUM_SHARE,
                    "人均或单笔金额_港元": round(retire_bal, 0),
                    "年提取金额_亿港元": round(retire_amt * LUMP_SUM_SHARE, 2),
                    "真实或假设": "混合",
                    "来源或假设": _tag(
                        "混合",
                        f"一笔过占比{LUMP_SUM_SHARE:.1%}对齐2025Q4[真实数据]；"
                        f"2025全年退休{W_RETIRE_2025_COUNT}万宗/{W_RETIRE_2025_AMT}亿，"
                        f"单笔≈{per_case_2025:,.0f}港元[真实数据]；"
                        "人数=Pop(60-64)/5[假设]；单笔按名义增速外推[假设]",
                    ),
                }
            )
            rows.append(
                {
                    "年份": year,
                    "情景": scenario,
                    "提取理由": "退休_分期或其他形式",
                    "提取人数或宗数_万": round(reach * (1 - LUMP_SUM_SHARE), 4),
                    "占该类金额比例": round(1 - LUMP_SUM_SHARE, 4),
                    "人均或单笔金额_港元": round(retire_bal, 0),
                    "年提取金额_亿港元": round(retire_amt * (1 - LUMP_SUM_SHARE), 2),
                    "真实或假设": "混合",
                    "来源或假设": _tag(
                        "假设",
                        f"补齐至100%；非一笔过约占{1 - LUMP_SUM_SHARE:.1%}（2025Q4结构残余）",
                    ),
                }
            )
            for reason, sh in reason_shares_other.items():
                rows.append(
                    {
                        "年份": year,
                        "情景": scenario,
                        "提取理由": reason,
                        "提取人数或宗数_万": "",
                        "占该类金额比例": sh,
                        "人均或单笔金额_港元": "",
                        "年提取金额_亿港元": round(other_amt * sh, 2),
                        "真实或假设": "假设",
                        "来源或假设": _tag(
                            "假设",
                            f"其他提取合计约占总提取{other_share_of_total:.0%}（10-15%经验带）；"
                            "内部结构为研究拆分；永久离港为香港特有漏损变量",
                        ),
                    }
                )
            rows.append(
                {
                    "年份": year,
                    "情景": scenario,
                    "提取理由": "合计_总提取",
                    "提取人数或宗数_万": round(reach, 4),
                    "占该类金额比例": 1.0,
                    "人均或单笔金额_港元": round(retire_bal, 0),
                    "年提取金额_亿港元": round(total_w, 2),
                    "真实或假设": "混合",
                    "来源或假设": _tag(
                        "混合",
                        f"资产锚点2025年底{AUM_2025YE}亿、2026年中{AUM_2026MID}亿；"
                        f"账户约{ACCOUNTS_WAN}万[真实数据]；Q4单季退休提取{W_RETIRE_Q4_2025}亿[真实数据]",
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_dictionary() -> None:
    text = """# P0 基础数据集 · 数据字典

> **对接**：`12_model_design_concept.md`  
> **目录**：`data/mpf-system-projection/p0_foundation/`  
> **时间**：2026–2056（死亡率含 2020–2025 实际）  
> **金额单位**：亿港元（入息为港元/月）  
> **原则**：真实锚点优先；`[假设]` 写明依据。

## 表清单

| 文件 | 内容 |
|------|------|
| `T01_mortality_by_age_sex.csv` | 分年龄性别死亡率 |
| `T02_population_by_age_sex.csv` | 分年龄组人口预测（三情景） |
| `T03_contribution_parameters.csv` | 缴费人口与供款参数（默认新上下限） |
| `T04_investment_return.csv` | 投资回报（三情景 + eMPF） |
| `T05_withdrawal_by_reason.csv` | 提取行为（按理由） |

## 关键真实锚点

| 项目 | 数值 | 标注 |
|------|------|------|
| 供款率 | 5%+5% | [真实数据] |
| 现行上下限 | $7,100 / $30,000 | [真实数据] |
| 拟调整上下限（模型默认） | $10,500 / $40,000 | 政策情景（检讨中，尚未立法） |
| 取消对冲 | 2025-05-01 | [真实数据] |
| 2025-26 财年总供款 | 912.3 亿 | [真实数据] |
| 自愿占比 | ~26% | [真实数据] |
| 2026Q2 总供款 | 234 亿 | [真实数据] |
| 制度加权回报中枢 | ~4.9% | [真实数据量级] |
| eMPF 行政费 | 0.29%（旧 0.37%） | [真实数据] |
| 2025Q4 退休提取 | 56.79 亿；一笔过 94.7% | [真实数据] |
| 2025 全年退休 | 15.38 万宗 / 195.66 亿 | [真实数据] |
| 总资产 | 2025 年底 15,500；2026 年中 16,700 | [真实数据] |
| 账户数 | ~1,120 万 | [真实数据] |
| 覆盖率 85% | — | [假设] |

## 上下限情景说明

- **拟调整_默认**：模型主路径使用 $10,500 / $40,000。  
- **现行_对照**：同一套人口与人数，改回 $7,100 / $30,000，用于差额对比。

## 与 population_ccm 关系

T01/T02 由 `population_ccm`（C&SD 115-01023、110-01001A + 队列成分法）导出；本目录为 P0「五表」交付面。
"""
    (OUT / "00_data_dictionary.md").write_text(text, encoding="utf-8")


def main() -> None:
    t01 = build_t01_mortality()
    t02 = build_t02_population()
    t03 = build_t03_contribution()
    t04 = build_t04_returns()
    t05 = build_t05_withdrawal()

    t01.to_csv(OUT / "T01_mortality_by_age_sex.csv", index=False, encoding="utf-8-sig")
    t02.to_csv(OUT / "T02_population_by_age_sex.csv", index=False, encoding="utf-8-sig")
    t03.to_csv(OUT / "T03_contribution_parameters.csv", index=False, encoding="utf-8-sig")
    t04.to_csv(OUT / "T04_investment_return.csv", index=False, encoding="utf-8-sig")
    t05.to_csv(OUT / "T05_withdrawal_by_reason.csv", index=False, encoding="utf-8-sig")
    write_dictionary()

    # 摘要
    mid_2026 = t03[(t03["年份"] == 2026) & (t03["情景"] == "中") & (t03["是否模型默认"] == "是")].iloc[0]
    mid_2026_old = t03[(t03["年份"] == 2026) & (t03["情景"] == "中") & (t03["是否模型默认"] == "否")].iloc[0]
    summary = OUT / "_build_summary.txt"
    lines = [
        f"T01 rows={len(t01)} years={t01['年份'].min()}-{t01['年份'].max()}",
        f"T02 rows={len(t02)} scenarios={sorted(t02['情景'].unique())}",
        f"T03 rows={len(t03)}",
        f"  2026中·默认(新上下限) 缴费人数={mid_2026['缴费人数_万人']}万 总供款={mid_2026['年总供款_亿港元']}亿",
        f"  2026中·对照(旧上下限) 总供款={mid_2026_old['年总供款_亿港元']}亿",
        f"T04 rows={len(t04)}",
        f"T05 rows={len(t05)}",
        f"OUT={OUT}",
    ]
    summary.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
