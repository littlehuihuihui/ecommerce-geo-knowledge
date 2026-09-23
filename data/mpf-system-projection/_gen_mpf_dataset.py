# -*- coding: utf-8 -*-
"""Generate HK MPF system total-account baseline dataset (2026-2056)."""
from pathlib import Path
import csv
import math

OUT = Path(r"d:/cursor/行业百科/data/mpf-system-projection")
OUT.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2026, 2057))  # inclusive 2056
AGE_GROUPS = [
    ("15-24", 15, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55-64", 55, 64),
    ("65+", 65, 100),
]

# ---- Anchors (2026) ----
AUM_2026_YI = 16700.0          # 亿港元 = 1.67 万亿
ACCOUNTS_2026 = 1100.0         # 万个
RELEVANT_MIN = 7100            # HKD / month
RELEVANT_MAX = 30000
EMPLOYER_RATE = 0.05
EMPLOYEE_RATE = 0.05
TOTAL_RATE = 0.10
LEXP_M = 83.3
LEXP_F = 88.7

# Mid labour / income anchors [假设 calibrated to HK order-of-magnitude]
LABOUR_2026_WAN = 400.0        # 万劳动人口 [假设] ~4.0m
LFPR_2026 = 0.58               # [假设] 整体劳动参与率
EMP_RATE_2026 = 0.97           # [假设] 就业率
MEDIAN_INCOME_2026 = 20000     # HKD/月 [假设] 接近全职入息中位数量级
CONTRIB_POP_2026_WAN = 280.0   # 万缴费人 [假设] < 劳动人口且与账户规模可对照

# Population base by age group (万人) — [假设] 量级贴近香港人口结构
POP_2026 = {
    "15-24": 65.0,
    "25-34": 95.0,
    "35-44": 110.0,
    "45-54": 105.0,
    "55-64": 100.0,
    "65+": 150.0,
}

# Age-group drift rates per year (mid) — aging society
POP_DRIFT = {
    "15-24": -0.004,
    "25-34": -0.002,
    "35-44": -0.001,
    "45-54": 0.000,
    "55-64": 0.004,
    "65+": 0.018,
}

# Fund types + historical-ish mid net annualized returns (%), low/high bands
# Anchored loosely to MPFA long-horizon public ranges; labeled mixed real/[假设]
FUNDS = {
    "股票基金": {"mid": 0.065, "low": 0.035, "high": 0.095, "src": "参考MPFA股票基金长期年率化净回报量级[假设情景中枢]"},
    "混合资产基金": {"mid": 0.045, "low": 0.025, "high": 0.065, "src": "参考MPFA混合资产基金长期年率化净回报量级[假设情景中枢]"},
    "DIS核心累积基金": {"mid": 0.050, "low": 0.028, "high": 0.072, "src": "参考DIS Core Accumulation长期净回报量级[假设情景中枢]"},
    "保守基金": {"mid": 0.015, "low": 0.005, "high": 0.025, "src": "参考MPFA保守基金/低波资产长期净回报量级[假设情景中枢]"},
}

# Allocation weights for system-level blend (mid) [假设]
ALLOC = {
    "股票基金": 0.28,
    "混合资产基金": 0.35,
    "DIS核心累积基金": 0.25,
    "保守基金": 0.12,
}


def scenario_mult(year, scenario):
    """Mild path differences for population/income growth."""
    t = year - 2026
    if scenario == "low":
        return {"pop": 0.85, "income": 0.012, "contrib_pen": -0.003, "ret_shift": -0.015, "withdraw": 0.92}
    if scenario == "high":
        return {"pop": 1.15, "income": 0.035, "contrib_pen": 0.004, "ret_shift": 0.015, "withdraw": 1.08}
    return {"pop": 1.00, "income": 0.025, "contrib_pen": 0.001, "ret_shift": 0.0, "withdraw": 1.00}


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ========== 表1 核心参数 ==========
core_rows = []
core_defs = [
    ("mpf_aum_total", 16700, "亿港元", "公开锚点：强积金总资产约1.67万亿港元", 2026, "中", "真实锚点"),
    ("mpf_account_count", 1100, "万个", "公开锚点：账户总数约1100万", 2026, "中", "真实锚点"),
    ("employer_contrib_rate", 5, "%", "强积金条例：雇主强制性供款比例", 2026, "中", "真实"),
    ("employee_contrib_rate", 5, "%", "强积金条例：雇员强制性供款比例", 2026, "中", "真实"),
    ("relevant_income_min_monthly", 7100, "港元/月", "有关入息下限", 2026, "中", "真实"),
    ("relevant_income_max_monthly", 30000, "港元/月", "有关入息上限", 2026, "中", "真实"),
    ("life_expectancy_male", 83.3, "岁", "香港男性预期寿命", 2026, "中", "真实锚点"),
    ("life_expectancy_female", 88.7, "岁", "香港女性预期寿命", 2026, "中", "真实锚点"),
    ("labour_force", 400, "万人", "[假设] 约400万劳动人口，量级贴近香港劳动人口统计", 2026, "中", "[假设]"),
    ("labour_force_participation_rate", 58, "%", "[假设] 整体劳动参与率；分年龄参与率见建模扩展", 2026, "中", "[假设]"),
    ("employment_rate", 97, "%", "[假设] 就业人数/劳动人口，对应低失业率情景", 2026, "中", "[假设]"),
    ("median_monthly_income", 20000, "港元/月", "[假设] 全职入息中位数量级，落在7100-30000有关入息带内", 2026, "中", "[假设]"),
    ("contributing_members", 280, "万人", "[假设] 当年有强制性供款的成员；须 < 劳动人口(400万)，且与账户数(含多账户/闲置)自洽", 2026, "中", "[假设]"),
    ("accounts_per_active_member", 1.8, "个/人", "[假设] 由1100万账户 / ~600万曾参与成员量级推得；活跃缴费人账户集中度更高", 2026, "中", "[假设]"),
    ("avg_relevant_income_active", 18500, "港元/月", "[假设] 缴费人平均有关入息（截断于上下限后），略低于全职中位数因兼职/低薪结构", 2026, "中", "[假设]"),
    ("annual_mandatory_inflow_2026", 621.6, "亿港元", "[假设]≈280万×1.85万×12×10%/1e8；供后续闭合校验", 2026, "中", "[假设]推算"),
    ("system_net_return_mid", 4.6, "%", "[假设] 按资产配置加权的系统年率化净回报中枢", 2026, "中", "[假设]"),
    ("retire_age_norm", 65, "岁", "[假设] 提取行为建模的常态退休年龄（法定提取条件更广，此处简化）", 2026, "中", "[假设]"),
    ("avg_withdrawal_ratio_at_retire", 0.35, "比例", "[假设] 退休当年平均提取占个人账户余额比例（其余延期/分期）", 2026, "中", "[假设]"),
]

# Add L/H companions for assumed params
extra = []
for name, val, unit, src, year, scen, tag in list(core_defs):
    if tag.startswith("[假设]") or "推算" in tag:
        if isinstance(val, (int, float)) and name not in ("employer_contrib_rate", "employee_contrib_rate"):
            if "rate" in name or "return" in name or "ratio" in name or name.endswith("_rate"):
                lo, hi = round(val * 0.85, 4) if val < 5 else round(val - 1, 2), round(val * 1.15, 4) if val < 5 else round(val + 1, 2)
            elif name == "avg_withdrawal_ratio_at_retire":
                lo, hi = 0.25, 0.50
            elif name == "system_net_return_mid":
                lo, hi = 3.1, 6.1
            elif name == "median_monthly_income":
                lo, hi = 17000, 23000
            elif name == "avg_relevant_income_active":
                lo, hi = 16000, 21000
            elif name == "contributing_members":
                lo, hi = 250, 310
            elif name == "labour_force":
                lo, hi = 380, 420
            elif name == "annual_mandatory_inflow_2026":
                lo, hi = round(val * 0.85, 1), round(val * 1.15, 1)
            else:
                lo, hi = round(val * 0.9, 2) if isinstance(val, float) else int(val * 0.9), round(val * 1.1, 2) if isinstance(val, float) else int(val * 1.1)
            extra.append((name, lo, unit, src + " | 低档", year, "低", tag))
            extra.append((name, hi, unit, src + " | 高档", year, "高", tag))

for name, val, unit, src, year, scen, tag in core_defs + extra:
    core_rows.append({
        "参数名": name,
        "数值": val,
        "单位": unit,
        "来源或假设": src,
        "年份": year,
        "情景": scen,
        "真实或假设": tag,
    })

write_csv(OUT / "01_core_parameters.csv",
          ["参数名", "数值", "单位", "来源或假设", "年份", "情景", "真实或假设"],
          core_rows)


# ========== 表2 人口预测 ==========
pop_rows = []
for scenario in ("低", "中", "高"):
    key = {"低": "low", "中": "mid", "高": "high"}[scenario]
    sm = scenario_mult(2026, key)
    for year in YEARS:
        t = year - 2026
        for ag, _, _ in AGE_GROUPS:
            base = POP_2026[ag]
            # geometric drift with scenario scaling on aging intensity for 65+
            drift = POP_DRIFT[ag]
            if ag == "65+":
                drift = drift * (1.2 if key == "high" else 0.8 if key == "low" else 1.0)
            elif ag in ("15-24", "25-34"):
                drift = drift * (1.2 if key == "low" else 0.8 if key == "high" else 1.0)
            pop = base * ((1 + drift) ** t)
            # overall scale
            pop *= 0.98 if key == "low" else 1.02 if key == "high" else 1.0
            pop_rows.append({
                "年份": year,
                "年龄组": ag,
                "人数_万人": round(pop, 2),
                "情景": scenario,
                "备注": "结构漂移[假设]；总量级贴近香港老龄化路径",
            })

write_csv(OUT / "02_population_projection.csv",
          ["年份", "年龄组", "人数_万人", "情景", "备注"],
          pop_rows)


# ========== 表3 缴费人口 ==========
contrib_rows = []
for scenario in ("低", "中", "高"):
    key = {"低": "low", "中": "mid", "高": "high"}[scenario]
    for year in YEARS:
        t = year - 2026
        sm = scenario_mult(year, key)
        # labour force path
        labour = LABOUR_2026_WAN * ((1 + (0.001 if key == "mid" else -0.002 if key == "low" else 0.004)) ** t)
        # contributing members grow then plateau with aging
        g = sm["contrib_pen"]
        contrib = CONTRIB_POP_2026_WAN * ((1 + g) ** t)
        # self-consistency: contributing < labour * emp_rate
        cap = labour * EMP_RATE_2026 * 0.85
        contrib = min(contrib, cap)
        income0 = {"low": 16000, "mid": 18500, "high": 21000}[key]
        income = income0 * ((1 + sm["income"]) ** t)
        # clip conceptually to relevant income band (monthly)
        income_clipped = max(RELEVANT_MIN, min(RELEVANT_MAX, income))
        annual_inflow_yi = contrib * 10000 * income_clipped * 12 * TOTAL_RATE / 1e8
        contrib_rows.append({
            "年份": year,
            "缴费人数_万人": round(contrib, 2),
            "劳动人口_万人": round(labour, 2),
            "就业率": EMP_RATE_2026,
            "平均有关入息_港元每月": round(income_clipped, 0),
            "年强制性供款流入_亿港元": round(annual_inflow_yi, 2),
            "情景": scenario,
            "自洽校验": "缴费人数≤劳动人口×就业率×0.85",
            "备注": "[假设] 入息增长与老龄化拖累参与率；金额单位亿港元",
        })

write_csv(OUT / "03_contributing_population.csv",
          ["年份", "缴费人数_万人", "劳动人口_万人", "就业率", "平均有关入息_港元每月",
           "年强制性供款流入_亿港元", "情景", "自洽校验", "备注"],
          contrib_rows)


# ========== 表4 投资回报 ==========
ret_rows = []
for scenario in ("低", "中", "高"):
    key = {"低": "low", "中": "mid", "高": "high"}[scenario]
    for year in YEARS:
        t = year - 2026
        # mean-reverting mild cycle
        cycle = 0.01 * math.sin(2 * math.pi * t / 8.0)
        for fund, cfg in FUNDS.items():
            base = cfg[key]
            # conservatism: returns gently decline 3bp/year mid (longevity / valuation) [假设]
            trend = -0.0003 * t if key == "mid" else (-0.0005 * t if key == "low" else -0.0001 * t)
            r = base + cycle + trend
            ret_rows.append({
                "年份": year,
                "基金类型": fund,
                "年率化净回报率": round(r, 4),
                "年率化净回报率_百分比": round(r * 100, 2),
                "情景": scenario,
                "配置权重_中枢": ALLOC[fund],
                "来源或假设": cfg["src"],
            })

write_csv(OUT / "04_investment_return_assumptions.csv",
          ["年份", "基金类型", "年率化净回报率", "年率化净回报率_百分比", "情景", "配置权重_中枢", "来源或假设"],
          ret_rows)


# ========== 表5 提取行为 ==========
# New retirees roughly from 65+ growth + cohort flow [假设]
withdraw_rows = []
for scenario in ("低", "中", "高"):
    key = {"低": "low", "中": "mid", "高": "high"}[scenario]
    sm0 = scenario_mult(2026, key)
    for year in YEARS:
        t = year - 2026
        # baseline new retirees (万人)
        retirees = 7.5 * ((1 + 0.015) ** t)
        retirees *= 0.9 if key == "low" else 1.1 if key == "high" else 1.0
        ratio = 0.35 * sm0["withdraw"]
        # slight rise in drawdown under low-return stress
        if key == "low":
            ratio = min(0.55, ratio + 0.002 * t)
        elif key == "high":
            ratio = max(0.22, ratio - 0.001 * t)
        # 人均账户余额（万港元）
        avg_bal_wan_hkd = 45 * ((1 + (0.02 if key == "low" else 0.035 if key == "mid" else 0.045)) ** t)
        # 万人 × 万港元 = 亿港元（再乘提取比例）
        outflow_yi = retirees * avg_bal_wan_hkd * ratio
        withdraw_rows.append({
            "年份": year,
            "退休人数_万人": round(retirees, 2),
            "平均提取比例": round(ratio, 4),
            "人均账户余额_万港元": round(avg_bal_wan_hkd, 2),
            "系统提取流出_亿港元": round(outflow_yi, 2),
            "情景": scenario,
            "备注": "[假设] 退休年龄简化为65；提取含整笔/分期/保留，比例为当年流量口径",
        })

write_csv(OUT / "05_withdrawal_behavior.csv",
          ["年份", "退休人数_万人", "平均提取比例", "人均账户余额_万港元",
           "系统提取流出_亿港元", "情景", "备注"],
          withdraw_rows)


# ========== Data dictionary markdown ==========
dd = '''# 强积金制度总账户 · 30年预测基础数据字典（2026–2056）

> 用途：为「强积金制度总账户」系统动力学 / 精算投影提供**年度颗粒度**输入。  
> 金额口径：除入息为「港元/月」或「万港元」外，**系统级流量与存量统一为亿港元**。  
> 情景：低 / 中 / 高（悲观 / 基准 / 乐观）。

## 0. 设计原则

1. **真实锚点优先**：总资产、账户数、供款率、有关入息上下限、预期寿命等采用公开制度/统计锚点。  
2. **缺失则标注 [假设]**：给出依据，并与其他表自洽（缴费人口 < 劳动人口；入息落在有关入息带内等）。  
3. **不替代官方精算**：本数据集用于研究与教学建模，非 MPFA / 政府官方预测。

## 1. 表清单

| 文件 | 表名 | 主键 | 行量级 |
|---|---|---|---|
| `01_core_parameters.csv` | 核心参数表 | 参数名 + 情景 | 含中枢及假设参数的低/高档 |
| `02_population_projection.csv` | 人口预测表 | 年份×年龄组×情景 | 31年×6年龄组×3情景 |
| `03_contributing_population.csv` | 缴费人口表 | 年份×情景 | 31×3 |
| `04_investment_return_assumptions.csv` | 投资回报假设表 | 年份×基金类型×情景 | 31×4×3 |
| `05_withdrawal_behavior.csv` | 提取行为表 | 年份×情景 | 31×3 |

## 2. 字段字典

### 表1 `01_core_parameters.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| 参数名 | string | 英文蛇形命名，便于建模引用 |
| 数值 | number | 见单位 |
| 单位 | string | 亿港元 / 万个 / % / 港元/月 / 岁 等 |
| 来源或假设 | string | 真实锚点说明，或 `[假设]` + 依据 |
| 年份 | int | 参数锚定年份（多为2026） |
| 情景 | string | 低 / 中 / 高 |
| 真实或假设 | string | `真实` / `真实锚点` / `[假设]` / `[假设]推算` |

**关键参数**

| 参数名 | 中枢值 | 单位 | 说明 |
|---|---:|---|---|
| mpf_aum_total | 16700 | 亿港元 | 2026总资产约1.67万亿港元 |
| mpf_account_count | 1100 | 万个 | 账户约1100万 |
| employer_contrib_rate / employee_contrib_rate | 5 / 5 | % | 强制性供款 |
| relevant_income_min_monthly / max | 7100 / 30000 | 港元/月 | 有关入息上下限 |
| life_expectancy_male / female | 83.3 / 88.7 | 岁 | 预期寿命锚点 |
| labour_force | 400 | 万人 | `[假设]` |
| contributing_members | 280 | 万人 | `[假设]`，且 < 劳动人口 |
| avg_relevant_income_active | 18500 | 港元/月 | `[假设]`，落在上下限内 |
| system_net_return_mid | 4.6 | % | `[假设]` 系统配置加权净回报中枢 |

### 表2 `02_population_projection.csv`

| 字段 | 说明 |
|---|---|
| 年份 | 2026–2056 |
| 年龄组 | 15-24 / 25-34 / 35-44 / 45-54 / 55-64 / 65+ |
| 人数_万人 | 该年龄组人口 |
| 情景 | 低/中/高（老龄化速度不同） |
| 备注 | 结构漂移假设说明 |

### 表3 `03_contributing_population.csv`

| 字段 | 说明 |
|---|---|
| 年份 | 2026–2056 |
| 缴费人数_万人 | 当年有强制性供款的人数 |
| 劳动人口_万人 | 同情景劳动人口路径 |
| 就业率 | 就业/劳动人口 |
| 平均有关入息_港元每月 | 截断至 [7100, 30000] |
| 年强制性供款流入_亿港元 | 缴费人数×入息×12×10% |
| 情景 | 低/中/高 |
| 自洽校验 | 缴费人数≤劳动人口×就业率×0.85 |
| 备注 | 假设说明 |

### 表4 `04_investment_return_assumptions.csv`

| 字段 | 说明 |
|---|---|
| 年份 | 2026–2056 |
| 基金类型 | 股票基金 / 混合资产基金 / DIS核心累积基金 / 保守基金 |
| 年率化净回报率 | 小数（如 0.065） |
| 年率化净回报率_百分比 | 百分数便于阅读 |
| 情景 | 低/中/高对应历史带的悲观/中枢/乐观 |
| 配置权重_中枢 | `[假设]` 系统资产配置，用于加权 |
| 来源或假设 | 回报中枢依据 |

含轻微周期项 `sin(2πt/8)` 与缓慢下行趋势（估值/成熟市场）`[假设]`。

### 表5 `05_withdrawal_behavior.csv`

| 字段 | 说明 |
|---|---|
| 年份 | 2026–2056 |
| 退休人数_万人 | `[假设]` 简化为常态65岁队列流量 |
| 平均提取比例 | 退休当年提取占个人余额比例 |
| 人均账户余额_万港元 | `[假设]` 退休时点人均余额 |
| 系统提取流出_亿港元 | 人数×人均余额×提取比例 |
| 情景 | 低/中/高 |
| 备注 | 法定提取条件更广，此处流量口径简化 |

## 3. 情景定义（低 / 中 / 高）

| 维度 | 低 | 中 | 高 |
|---|---|---|---|
| 缴费人数增长 | 缓降/停滞 | 微增后平台 | 温和扩张 |
| 入息增长 | ~1.2%/年 | ~2.5%/年 | ~3.5%/年 |
| 投资净回报 | 历史带下限 | 中枢 | 历史上限 |
| 老龄化 | 65+增长偏慢 | 基准 | 偏快 |
| 提取比例 | 偏高（资金更早流出） | 0.35 起 | 偏低（更多保留） |

## 4. 建议闭合恒等式（建模时）

```text
期末总资产 ≈ 期初总资产 × (1 + 系统净回报)
            + 年强制性供款流入
            + 自愿供款/其他流入[本数据集未单列，可扩]
            − 系统提取流出
            − 费用与其他[可扩]
```

2026 中枢示意：流入约 622 亿港元（见核心参数推算）。

## 5. 文件位置

`data/mpf-system-projection/`
'''

(OUT / "00_data_dictionary.md").write_text(dd, encoding="utf-8")
print("wrote to", OUT)
for p in sorted(OUT.glob("*.csv")):
    with p.open(encoding="utf-8-sig") as f:
        n = sum(1 for _ in f) - 1
    print(p.name, "rows", n)
