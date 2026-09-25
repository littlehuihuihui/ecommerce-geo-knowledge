# -*- coding: utf-8 -*-
"""个体强积金充足率模型 · 主入口。

用法::

    python run.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from career import retirement_summary, simulate_career
from data_loader import load_real_individual
from longevity import monte_carlo_depletion, run_longevity_by_sex
from params import (
    E65_FEMALE,
    E65_MALE,
    LE_FEMALE,
    LE_MALE,
    MEDIAN_MONTHLY_INCOME_2025,
    R_BASE,
    RETURN_SCENARIOS,
    IndividualProfile,
    e65_for_sex,
    profile_variants_grid,
)
from retirement import analyze_withdrawal_modes, withdrawal_path

OUT = _PKG / "output"
OUT.mkdir(parents=True, exist_ok=True)


def run_baseline_by_sex_and_return() -> Dict[str, Any]:
    """基准个体：入职25、退休65、中位数入息；分性别×三回报。"""
    careers = []
    summaries = []
    withdraw_tables = []
    for sex in ("男", "女"):
        for code, sc in RETURN_SCENARIOS.items():
            prof = IndividualProfile(
                sex=sex,
                entry_age=25,
                retire_age=65,
                start_monthly_income=MEDIAN_MONTHLY_INCOME_2025,
                income_growth=0.03,
                r=sc.r,
                name=f"{sex}/入职25/{sc.label}",
            )
            career = simulate_career(prof)
            career.to_csv(
                OUT / f"career_{sex}_{sc.label}.csv",
                index=False,
                encoding="utf-8-sig",
            )
            careers.append(career)
            sm = retirement_summary(career, prof)
            sm["回报情景"] = sc.label
            summaries.append(sm)
            last = career.iloc[-1]
            bal = float(last["期末余额_港元"])
            sal = float(sm["退休前年薪_港元"])
            wtab = analyze_withdrawal_modes(bal, sal, 65, sex)
            wtab.insert(0, "性别", sex)
            wtab.insert(1, "回报情景", sc.label)
            wtab.insert(2, "退休余额_港元", round(bal, 2))
            withdraw_tables.append(wtab)
    sum_df = pd.DataFrame(summaries)
    sum_df.to_csv(OUT / "T01_retirement_balance_by_sex_return.csv", index=False, encoding="utf-8-sig")
    w_df = pd.concat(withdraw_tables, ignore_index=True)
    w_df.to_csv(OUT / "T02_depletion_age_by_withdrawal.csv", index=False, encoding="utf-8-sig")
    return {"summaries": sum_df, "withdrawals": w_df, "careers": careers}


def run_grid_table() -> pd.DataFrame:
    """表1扩展：入职年龄 × 入息档 × 回报。"""
    rows = []
    for prof in profile_variants_grid():
        for sex in ("男", "女"):
            p = IndividualProfile(**{**prof.__dict__, "sex": sex, "name": f"{sex}/{prof.name}"})
            career = simulate_career(p)
            sm = retirement_summary(career, p)
            rows.append(sm)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "T01b_grid_entry_income_return.csv", index=False, encoding="utf-8-sig")
    return df


def run_longevity_layer(sum_df: pd.DataFrame) -> Dict[str, Any]:
    """第四层：以基准回报退休余额做 MC。"""
    m = sum_df[(sum_df["性别"] == "男") & (sum_df["回报情景"] == "基准")].iloc[0]
    f = sum_df[(sum_df["性别"] == "女") & (sum_df["回报情景"] == "基准")].iloc[0]
    lon_sum, lon_det = run_longevity_by_sex(
        float(m["退休时账户余额_港元"]),
        float(f["退休时账户余额_港元"]),
        float(m["退休前年薪_港元"]),
        float(f["退休前年薪_港元"]),
        retire_age=65,
        n_sim=2000,
    )
    lon_sum.to_csv(OUT / "T03_longevity_P10_P50_P90.csv", index=False, encoding="utf-8-sig")
    # 直方图数据：基准个体、4%规则、男女
    hist_rows = []
    for sex, row in (("男", m), ("女", f)):
        detail, _ = monte_carlo_depletion(
            float(row["退休时账户余额_港元"]),
            float(row["退休前年薪_港元"]),
            65,
            sex,
            mode="pct4",
            n_sim=2000,
        )
        detail.to_csv(
            OUT / f"T03_detail_pct4_{sex}.csv", index=False, encoding="utf-8-sig"
        )
        ages = detail["账户耗尽年龄"].values
        counts, edges = np.histogram(ages, bins=20)
        for i, c in enumerate(counts):
            hist_rows.append(
                {
                    "性别": sex,
                    "bin_left": round(float(edges[i]), 2),
                    "bin_right": round(float(edges[i + 1]), 2),
                    "count": int(c),
                }
            )
    hist_df = pd.DataFrame(hist_rows)
    hist_df.to_csv(OUT / "T03_depletion_age_hist.csv", index=False, encoding="utf-8-sig")
    return {"summary": lon_sum, "hist": hist_df, "male": m, "female": f}


def build_chart_payload(sum_df: pd.DataFrame, hist_df: pd.DataFrame) -> dict:
    """供 HTML 图使用的 JSON。"""
    # 积累曲线：男/基准
    prof = IndividualProfile(sex="男", r=R_BASE, name="男基准")
    career = simulate_career(prof)
    ages = career["年龄"].tolist()
    bal = career["期末余额_港元"].tolist()
    cum_c = career["累计供款_港元"].tolist()
    cum_i = career["累计投资收益_港元"].tolist()

    # 三情景退休余额（男）
    male = sum_df[sum_df["性别"] == "男"]
    female = sum_df[sum_df["性别"] == "女"]

    def hist_for(sex: str):
        h = hist_df[hist_df["性别"] == sex]
        labels = [f"{a:.0f}-{b:.0f}" for a, b in zip(h["bin_left"], h["bin_right"])]
        return {"labels": labels, "counts": h["count"].tolist()}

    return {
        "accumulation": {
            "ages": ages,
            "balance": bal,
            "cum_contrib": cum_c,
            "cum_invest": cum_i,
        },
        "retire_balance": {
            "labels": male["回报情景"].tolist(),
            "male": male["退休时账户余额_港元"].tolist(),
            "female": female["退休时账户余额_港元"].tolist(),
        },
        "hist_male": hist_for("男"),
        "hist_female": hist_for("女"),
        "anchors": {
            "median_income": MEDIAN_MONTHLY_INCOME_2025,
            "le_male": LE_MALE,
            "le_female": LE_FEMALE,
            "e65_male": E65_MALE,
            "e65_female": E65_FEMALE,
        },
        "disclaimer": "强积金不提供长寿风险保障：账户耗尽后无自动续付，长寿风险由个人承担。",
    }


def write_html(payload: dict) -> Path:
    """单文件图表页。"""
    data_json = json.dumps(payload, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<title>强积金个体账户 · 充足率与长寿风险</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --ink:#1a1a1a; --muted:#5a5a5a; --line:#ddd; --bg:#fafafa; --accent:#0b3d5c; --gold:#b08d3c; }}
  body {{ margin:0; font-family:"Microsoft YaHei","PingFang TC",sans-serif; background:var(--bg); color:var(--ink); }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:24px 18px 48px; }}
  h1 {{ font-size:1.45rem; margin:0 0 6px; color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:.9rem; line-height:1.5; margin-bottom:16px; }}
  .warn {{ background:#fff8e8; border-left:4px solid var(--gold); padding:10px 12px; margin:12px 0 20px; font-size:.88rem; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media(max-width:800px){{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .card h2 {{ font-size:1rem; margin:0 0 10px; }}
  canvas {{ max-height:320px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.82rem; margin-top:8px; }}
  th,td {{ border:1px solid var(--line); padding:4px 6px; text-align:left; }}
  th {{ background:#f0f0f0; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>强积金个体账户 · 积累、充足率与长寿风险</h1>
  <p class="sub">视角：代表性个体（非制度总账户）。入职25岁、退休65岁、起薪约入息中位数 $20,500/月；供款5%+5%，现行/假设上下限按年切换。单位：港元。</p>
  <div class="warn" id="disclaimer"></div>
  <div class="grid">
    <div class="card"><h2>图1 · 账户积累曲线（男·基准回报）</h2><canvas id="c1"></canvas></div>
    <div class="card"><h2>图2 · 退休时余额（三情景×性别）</h2><canvas id="c2"></canvas></div>
    <div class="card"><h2>图3 · 账户耗尽年龄分布（男·4%规则 MC）</h2><canvas id="c3"></canvas></div>
    <div class="card"><h2>图4 · 账户耗尽年龄分布（女·4%规则 MC）</h2><canvas id="c4"></canvas></div>
  </div>
  <div class="card" style="margin-top:16px">
    <h2>寿命锚点</h2>
    <div id="anchors"></div>
  </div>
</div>
<script>
const D = {data_json};
document.getElementById('disclaimer').textContent = D.disclaimer;
document.getElementById('anchors').innerHTML =
  `入息中位数 $${{D.anchors.median_income.toLocaleString()}}/月；` +
  `预期寿命 男 ${{D.anchors.le_male}} / 女 ${{D.anchors.le_female}}；` +
  `65岁余命 男≈${{D.anchors.e65_male}}年 / 女≈${{D.anchors.e65_female}}年。`;

new Chart(document.getElementById('c1'), {{
  type:'line',
  data:{{
    labels:D.accumulation.ages,
    datasets:[
      {{label:'期末余额', data:D.accumulation.balance, borderColor:'#0b3d5c', tension:.2, pointRadius:0}},
      {{label:'累计供款', data:D.accumulation.cum_contrib, borderColor:'#b08d3c', tension:.2, pointRadius:0}},
      {{label:'累计投资收益', data:D.accumulation.cum_invest, borderColor:'#5a8f6b', tension:.2, pointRadius:0}},
    ]
  }},
  options:{{responsive:true, plugins:{{legend:{{position:'bottom'}}}}, scales:{{y:{{title:{{display:true,text:'港元'}}}}, x:{{title:{{display:true,text:'年龄'}}}}}}
}});

new Chart(document.getElementById('c2'), {{
  type:'bar',
  data:{{
    labels:D.retire_balance.labels,
    datasets:[
      {{label:'男', data:D.retire_balance.male, backgroundColor:'#0b3d5c'}},
      {{label:'女', data:D.retire_balance.female, backgroundColor:'#b08d3c'}},
    ]
  }},
  options:{{responsive:true, plugins:{{legend:{{position:'bottom'}}}}, scales:{{y:{{title:{{display:true,text:'退休余额（港元）'}}}}}}
}});

function histChart(id, pack, color){{
  new Chart(document.getElementById(id), {{
    type:'bar',
    data:{{ labels:pack.labels, datasets:[{{label:'频数', data:pack.counts, backgroundColor:color}}] }},
    options:{{responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{x:{{ticks:{{maxRotation:60, minRotation:45, font:{{size:9}}}}}}, y:{{title:{{display:true,text:'模拟次数'}}}}}}
  }});
}}
histChart('c3', D.hist_male, '#0b3d5c99');
histChart('c4', D.hist_female, '#b08d3c99');
</script>
</body>
</html>
"""
    path = _PKG / "mpf_individual_adequacy_dashboard.html"
    path.write_text(html, encoding="utf-8")
    # also copy next to package parent for consistency
    (OUT / "mpf_individual_adequacy_dashboard.html").write_text(html, encoding="utf-8")
    return path


def write_dictionary(sum_df: pd.DataFrame, lon_sum: pd.DataFrame) -> None:
    m = sum_df[(sum_df["性别"] == "男") & (sum_df["回报情景"] == "基准")].iloc[0]
    text = f"""# 强积金个体账户充足率模型 · 数据字典

> 视角：**代表性个体**（非制度总账户加总）  
> 制度局限：**强积金不提供长寿风险保障**

## 与制度总账户模型的区别

| 维度 | 制度总账户 | 本模型（个体） |
|------|------------|----------------|
| 对象 | 全港资金池 | 单一职业生涯 |
| 核心问题 | 制度现金流/拐点 | **够不够用、何时耗尽** |
| 长寿 | 队列领取流量 | **余命分布 vs 耗尽年龄** |

## 核心公式

```
A(t+1) = A(t)×(1+r) + 雇员供款(t) + 雇主供款(t)
退休余额倍数 ≈ 余额 / 退休前年薪
耗尽年龄 = 退休年龄 + 可支撑年数
```

## 锚点

| 参数 | 数值 | 来源 |
|------|------|------|
| 入息中位数 | $20,500/月 | [真实数据量级] 2025 Q3 |
| 供款率 | 5%+5% | [真实数据] |
| 上下限 | 7,100/30,000；2028+ 假设 10,500/40,000 | [真实]/假设] |
| 回报 | 3% / 4.9% / 7% | [假设/制度量级] |
| 预期寿命 | 男 83.3 / 女 88.7 | [真实数据量级] |
| 65岁余命 | 男≈18 / 女≈24 | [真实数据量级] |

## 基准结果摘要（男·基准回报）

| 项 | 数值 |
|----|------|
| 退休余额 | {m['退休时账户余额_港元']:,.0f} 港元 |
| 累计供款占比 | {m['供款占余额_pct']}% |
| 投资收益占比 | {m['投资收益占余额_pct']}% |
| 余额/前年薪 | {m['余额相对前年薪倍数']} 倍 |

## 输出

- `T01_*.csv` 退休余额
- `T02_*.csv` 提取方式 × 耗尽年龄
- `T03_*.csv` 长寿风险 P10/P50/P90 与直方图
- `mpf_individual_adequacy_dashboard.html` 图1–4

## 预留接口

```python
from data_loader import load_real_individual
rec = load_real_individual("id", csv_path="individuals.csv")
```
"""
    (_PKG / "00_data_dictionary.md").write_text(text, encoding="utf-8")


def main() -> None:
    # 证明接口可调用
    _ = load_real_individual()

    base = run_baseline_by_sex_and_return()
    run_grid_table()
    lon = run_longevity_layer(base["summaries"])

    # 基准男：4% 提取路径
    m = lon["male"]
    path = withdrawal_path(
        float(m["退休时账户余额_港元"]),
        float(m["退休时账户余额_港元"]) * 0.04,
        0.03,
        65,
    )
    path.to_csv(OUT / "T02b_withdrawal_path_male_pct4.csv", index=False, encoding="utf-8-sig")

    payload = build_chart_payload(base["summaries"], lon["hist"])
    html_path = write_html(payload)
    write_dictionary(base["summaries"], lon["summary"])

    print("=== 退休余额（分性别×回报）===")
    print(
        base["summaries"][
            [
                "性别",
                "回报情景",
                "退休时账户余额_港元",
                "供款占余额_pct",
                "投资收益占余额_pct",
                "余额相对前年薪倍数",
            ]
        ].to_string(index=False)
    )
    print("\n=== 长寿风险 P10/P50/P90（耗尽年龄）===")
    print(lon["summary"].to_string(index=False))
    print(f"\n图表: {html_path}")
    print(f"输出: {OUT}")
    print("制度局限: 强积金不提供长寿风险保障")


if __name__ == "__main__":
    main()
