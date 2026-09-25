# -*- coding: utf-8 -*-
"""
强积金领取层 + 制度总资产演化（Withdrawal & Asset Layer）

输入：
  - population_ccm/P02：60–64 岁组 → 年达 65 岁人数近似（/5）
  - contribution_layer/C02：年度总供款

恒等式：
  A_{t+1} = A_t·(1+r) + C_t − W_t

校准锚点：
  - 2025-12 总资产约 15,500 亿；2026-06 约 16,700 亿
  - 2025 年退休提取约 15.38 万宗、195.66 亿
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
POP = ROOT / "population_ccm" / "P02_population_by_age_sex.csv"
CONTRIB = ROOT / "contribution_layer" / "C02_contribution_breakdown.csv"
OUT = ROOT / "withdrawal_asset_layer"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

# —— 资产初值与账户 ——
A0_2026 = 16700.0          # 亿港元；2026年中锚点 [citation:5]
ACCOUNTS_2026 = 1100.0     # 万个 [citation:5]
ACCOUNTS_GROWTH = 0.005    # 账户数年增速 [假设]

# —— 提取行为 ——
WITHDRAW_RATIO_AT_65 = 1.0  # [假设] 达龄且有余额者几乎全部提取；一笔过>94%
OTHER_SHARE_OF_TOTAL_W = 0.12  # 其他提取占总提取 10%–15%，取 12% [假设]
# 其他提取内部分解比例（占其他提取）
OTHER_BREAKDOWN = {
    "提早退休": 0.35,
    "永久离港": 0.25,
    "丧失行为能力_末期_死亡": 0.15,
    "抵销遣散费_长期服务金": 0.25,
}

# —— 退休人均余额相对「系统户均」的溢价 ——
# 系统户均 = A / 账户数；退休队列通常略高或接近（多账户稀释）
RETIREE_BALANCE_FACTOR = 1.05  # [假设]；校准使 2026 退休提取量级贴近 ~196 亿

# —— 回报三情景 ——
R_SCENARIOS = {
    "低": {"label": "保守", "r": 0.030, "contrib_sc": "低",
           "来源": "保守/债券基金量级约3%"},
    "中": {"label": "基准", "r": 0.049, "contrib_sc": "中",
           "来源": "制度加权约4.9%（股票5.1%×47%+混合4.8%×34%等）[citation:5]"},
    "高": {"label": "乐观", "r": 0.070, "contrib_sc": "高",
           "来源": "参考DIS核心累积历史约7.3%[citation:5]，情景取7.0%"},
}


def load_inputs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    pop = pd.read_csv(POP)
    contrib = pd.read_csv(CONTRIB)
    return pop, contrib


def new_age65(pop: pd.DataFrame, year: int, pop_scenario: str = "中") -> Dict[str, float]:
    """
    当年新达 65 岁人数（人）。
    近似：60–64 岁组人口 / 5（组内均匀）。
    """
    sub = pop[(pop["年份"] == year) & (pop["情景"] == pop_scenario) & (pop["年龄组"] == "60-64")]
    out = {"男": 0.0, "女": 0.0}
    for sex in ("男", "女"):
        n = float(sub[sub["性别"] == sex]["人数"].sum())
        out[sex] = n / 5.0
    out["混合"] = out["男"] + out["女"]
    return out


def accounts_wan(year: int) -> float:
    return ACCOUNTS_2026 * ((1.0 + ACCOUNTS_GROWTH) ** (year - 2026))


def avg_retiree_balance_wan(assets_yi: float, year: int) -> float:
    """
    人均账户余额（万港元）。
    系统户均（万港元）= A(亿) / 账户(万) ；再乘退休溢价。
    """
    acc = accounts_wan(year)
    sys_avg = assets_yi / acc if acc > 0 else 0.0  # 万港元/账户
    return sys_avg * RETIREE_BALANCE_FACTOR


def run_scenario(
    code: str,
    pop: pd.DataFrame,
    contrib: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    cfg = R_SCENARIOS[code]
    r = cfg["r"]
    c_sc = cfg["contrib_sc"]
    cpath = contrib[contrib["情景"] == c_sc].set_index("年份")

    years = list(range(2026, 2057))
    a = A0_2026
    rows_ret: List[dict] = []
    rows_other: List[dict] = []
    rows_asset: List[dict] = []

    for year in years:
        n65 = new_age65(pop, year, "中")
        # 供款：2056 仍有流量年；资产递推用到 2055→2056 期末
        if year in cpath.index:
            c_yi = float(cpath.loc[year, "年总供款_亿港元"])
        else:
            c_yi = float(cpath.iloc[-1]["年总供款_亿港元"])

        b_wan = avg_retiree_balance_wan(a, year)  # 万港元
        # 退休提取：人数(人)×余额(万港元)/100 = 亿？  人×万港元 = 万人×万港元×1e-4?
        # 正确：N人 × (B万港元 × 1e4港元) / 1e8 = N × B / 1e4 亿
        # 或：N_万人 × B_万港元 = 亿港元
        n_mix_wan = n65["混合"] / 1e4
        w_ret = n_mix_wan * b_wan * WITHDRAW_RATIO_AT_65  # 亿港元

        # 总提取：退休占 (1 - other_share)
        w_total = w_ret / (1.0 - OTHER_SHARE_OF_TOTAL_W)
        w_other = w_total - w_ret

        inv = a * r
        # 期末资产（本年计息后加减流量）
        a_next = a * (1.0 + r) + c_yi - w_total
        if a_next < 0:
            a_next = 0.0

        net_cf = c_yi - w_total  # 供款−提取（不含回报）
        econ_net = c_yi - w_total + inv  # 供款+回报−提取

        for sex in ("男", "女", "混合"):
            n = n65[sex]
            # 金额按人数占比分摊
            share = (n / n65["混合"]) if n65["混合"] > 0 else 0.0
            rows_ret.append({
                "年份": year,
                "性别": sex,
                "新达65岁人数_人": round(n, 1),
                "实际提取比例": WITHDRAW_RATIO_AT_65,
                "人均账户余额_万港元": round(b_wan, 4),
                "退休提取人数_人": round(n * WITHDRAW_RATIO_AT_65, 1),
                "退休提取金额_亿港元": round(w_ret * share, 4),
                "情景": code,
                "情景标签": cfg["label"],
                "来源或假设": "达龄人数≈(60-64)/5；提取比100%[假设]因一笔过>94%；余额=A/账户数×1.05",
            })

        # 其他提取分项
        for reason, wgt in OTHER_BREAKDOWN.items():
            rows_other.append({
                "年份": year,
                "提取理由": reason,
                "金额_亿港元": round(w_other * wgt, 4),
                "占其他提取比例": wgt,
                "占全部提取比例": round(OTHER_SHARE_OF_TOTAL_W * wgt, 4),
                "情景": code,
                "情景标签": cfg["label"],
                "来源或假设": "其他提取=总提取×12%[假设]；内部分解比例按近期季度量级粗分",
            })
        rows_other.append({
            "年份": year,
            "提取理由": "其他合计",
            "金额_亿港元": round(w_other, 4),
            "占其他提取比例": 1.0,
            "占全部提取比例": OTHER_SHARE_OF_TOTAL_W,
            "情景": code,
            "情景标签": cfg["label"],
            "来源或假设": "总提取的10%–15%取12%",
        })

        rows_asset.append({
            "年份": year,
            "情景": code,
            "情景标签": cfg["label"],
            "总资产_期初_亿港元": round(a, 4),
            "加权净回报率": r,
            "投资损益_亿港元": round(inv, 4),
            "总供款_亿港元": round(c_yi, 4),
            "退休提取_亿港元": round(w_ret, 4),
            "其他提取_亿港元": round(w_other, 4),
            "总提取_亿港元": round(w_total, 4),
            "净现金流_供款减提取_亿港元": round(net_cf, 4),
            "经济净流入_含回报_亿港元": round(econ_net, 4),
            "总资产_期末_亿港元": round(a_next, 4),
            "账户数_万个": round(accounts_wan(year), 2),
            "系统户均余额_万港元": round(a / accounts_wan(year), 4),
            "回报假设来源": cfg["来源"],
        })

        a = a_next

    asset_df = pd.DataFrame(rows_asset)
    summary = detect_inflections(asset_df, code, cfg["label"])
    return pd.DataFrame(rows_ret), pd.DataFrame(rows_other), asset_df, summary


def detect_inflections(asset: pd.DataFrame, code: str, label: str) -> dict:
    """识别资产峰值、净现金流拐点、经济净流入拐点。"""
    peak_year = None
    peak_a = None
    for _, row in asset.iterrows():
        if row["总资产_期末_亿港元"] < row["总资产_期初_亿港元"]:
            peak_year = int(row["年份"])
            peak_a = float(row["总资产_期初_亿港元"])
            break

    # 供款 < 提取 首年
    cf_neg = None
    for _, row in asset.iterrows():
        if row["净现金流_供款减提取_亿港元"] < 0:
            cf_neg = int(row["年份"])
            break

    # 供款+回报 < 提取 首年
    econ_neg = None
    for _, row in asset.iterrows():
        if row["经济净流入_含回报_亿港元"] < 0:
            econ_neg = int(row["年份"])
            break

    last = asset.iloc[-1]
    return {
        "情景": code,
        "情景标签": label,
        "初值资产_亿港元": A0_2026,
        "期末资产_亿港元": round(float(last["总资产_期末_亿港元"]), 2),
        "期末年份": int(last["年份"]),
        "资产峰值年份": peak_year if peak_year is not None else "不适用",
        "资产峰值_亿港元": round(peak_a, 2) if peak_a is not None else "不适用",
        "投影期内资产始终上升": peak_year is None,
        "净现金流拐点年份_提取大于供款": cf_neg if cf_neg is not None else "不适用",
        "经济净流入拐点年份_提取大于供款加回报": econ_neg if econ_neg is not None else "不适用",
        "累计供款_亿港元": round(float(asset["总供款_亿港元"].sum()), 2),
        "累计提取_亿港元": round(float(asset["总提取_亿港元"].sum()), 2),
        "平均回报率": round(float(asset["加权净回报率"].mean()), 4),
        "来源或假设": "峰值=首个期末<期初年份；净现金流=C−W；经济净流入=C−W+rA",
    }


def write_dictionary() -> None:
    text = f"""# 强积金领取层与资产演化 · 数据字典

> **输入**：人口层 `P02`（60–64）、缴费层 `C02`  
> **输出**：`withdrawal_asset_layer/`  
> **初值**：A_2026 = {A0_2026:.0f} 亿港元（2026年中锚点）

## 表清单

| 文件 | 内容 |
|------|------|
| `W01_retirement_withdrawals.csv` | 退休提取人数与金额（男/女/混合） |
| `W02_other_withdrawals.csv` | 其他提取分理由 |
| `W03_asset_evolution.csv` | 总资产演化（三情景） |
| `W04_inflection_points.csv` | 拐点识别摘要 |
| `W00_data_dictionary.md` | 本字典 |

## 核心公式

```
新达65岁人数 ≈ Pop(60–64) / 5
退休提取 = 人数 × 提取比例 × 人均余额
总提取 = 退休提取 / (1 − 其他占比)
A(t+1) = A(t)×(1+r) + C(t) − W(t)
```

## 情景（回报 × 对齐供款情景）

| 码 | 标签 | r | 供款情景 |
|----|------|---|----------|
| 低 | 保守 | 3.0% | 低 |
| 中 | 基准 | 4.9% | 中 |
| 高 | 乐观 | 7.0% | 高 |

## 关键假设

- 达龄提取比例 100%（一笔过主导，分期可忽略）**[假设]**
- 其他提取 = 总提取 12% **[假设]**
- 人均余额 = (A/账户数)×{RETIREE_BALANCE_FACTOR} **[假设]**
- 账户数自 1100 万起年增约 0.5% **[假设]**
"""
    (OUT / "W00_data_dictionary.md").write_text(text, encoding="utf-8")


def main() -> None:
    np.random.seed(RANDOM_SEED)
    pop, contrib = load_inputs()
    all_ret, all_other, all_asset, summaries = [], [], [], []

    for code in ("低", "中", "高"):
        ret, other, asset, summary = run_scenario(code, pop, contrib)
        all_ret.append(ret)
        all_other.append(other)
        all_asset.append(asset)
        summaries.append(summary)
        print(f"[{code}/{summary['情景标签']}] 2056末资产={summary['期末资产_亿港元']} 峰值={summary['资产峰值年份']} "
              f"C<W@{summary['净现金流拐点年份_提取大于供款']} 经济拐点@{summary['经济净流入拐点年份_提取大于供款加回报']}")

    pd.concat(all_ret).to_csv(OUT / "W01_retirement_withdrawals.csv", index=False, encoding="utf-8-sig")
    pd.concat(all_other).to_csv(OUT / "W02_other_withdrawals.csv", index=False, encoding="utf-8-sig")
    pd.concat(all_asset).to_csv(OUT / "W03_asset_evolution.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summaries).to_csv(OUT / "W04_inflection_points.csv", index=False, encoding="utf-8-sig")
    write_dictionary()

    # 2026 基准 sanity
    mid = pd.concat(all_asset)
    row = mid[(mid["情景"] == "中") & (mid["年份"] == 2026)].iloc[0]
    print("\n=== 2026 基准 ===")
    print(f"期初A={row['总资产_期初_亿港元']:.0f} 供款={row['总供款_亿港元']:.1f} "
          f"退休提取={row['退休提取_亿港元']:.1f} 总提取={row['总提取_亿港元']:.1f} "
          f"期末A={row['总资产_期末_亿港元']:.1f}")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
