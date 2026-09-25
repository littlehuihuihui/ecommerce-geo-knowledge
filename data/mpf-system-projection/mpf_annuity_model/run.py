# -*- coding: utf-8 -*-
"""强积金年金化模型 · 主入口。

用法::

    python run.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from data_loader import load_annuity_pricer
from engine import income_structure_for_chart, run_income_grid
from input_bridge import load_age65_balances
from longevity_hedge import (
    depletion_age_distribution_points,
    hedge_table_all,
)
from pricing import (
    ANNUITY_ANNUAL_RATE_FEMALE,
    ANNUITY_ANNUAL_RATE_MALE,
    ANNUITY_MONTHLY_MALE_PER_1M,
    GUARANTEE_RATIO,
    HK_ANNUITY_SALES_2025_YI,
    SimpleHKAnnuityPricer,
)

OUT = _PKG / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    pricer = load_annuity_pricer()  # 预留接口
    balances = load_age65_balances()
    balances.to_csv(OUT / "I00_age65_balances_from_obj3.csv", index=False, encoding="utf-8-sig")

    grid = run_income_grid(balances, pricer=pricer)
    grid.to_csv(OUT / "T01_income_by_annuitize_ratio.csv", index=False, encoding="utf-8-sig")

    # 表2：耗尽年龄影响（滤掉制度局限行风格——grid 已含）
    dep = grid[
        [
            "性别",
            "回报情景",
            "年金化比例",
            "退休余额_港元",
            "年金年收入_港元",
            "剩余余额_港元",
            "剩余年提取_港元",
            "账户耗尽年龄",
            "预期死亡年龄",
            "剩余账户是否覆盖余命",
            "权衡",
        ]
    ].copy()
    dep.to_csv(OUT / "T02_depletion_age_vs_annuitize.csv", index=False, encoding="utf-8-sig")

    hedge = hedge_table_all(balances, n_sim=2000)
    hedge.to_csv(OUT / "T03_longevity_hedge_uplift.csv", index=False, encoding="utf-8-sig")

    # 图数据
    struct_m = income_structure_for_chart(grid, "男", "基准")
    struct_f = income_structure_for_chart(grid, "女", "基准")
    struct_m.to_csv(OUT / "G01_income_structure_male_base.csv", index=False, encoding="utf-8-sig")
    struct_f.to_csv(OUT / "G01_income_structure_female_base.csv", index=False, encoding="utf-8-sig")

    dep_pts_m = depletion_age_distribution_points(balances, "男", "基准")
    dep_pts_f = depletion_age_distribution_points(balances, "女", "基准")
    dep_pts_m.to_csv(OUT / "G02_depletion_by_ratio_male.csv", index=False, encoding="utf-8-sig")
    dep_pts_f.to_csv(OUT / "G02_depletion_by_ratio_female.csv", index=False, encoding="utf-8-sig")

    # 定价说明
    sp = SimpleHKAnnuityPricer()
    price_info = pd.DataFrame(
        [
            {
                "项目": "男65岁每月给付/百万保费",
                "数值": ANNUITY_MONTHLY_MALE_PER_1M,
                "来源": "[真实数据量级] 香港年金计划公开口径",
            },
            {
                "项目": "男年化转换率",
                "数值": round(ANNUITY_ANNUAL_RATE_MALE, 6),
                "来源": "5800×12/1e6",
            },
            {
                "项目": "女年化转换率",
                "数值": round(ANNUITY_ANNUAL_RATE_FEMALE, 6),
                "来源": "[真实数据] 官方表示例女65岁5300×12/1e6",
            },
            {
                "项目": "女每月给付/百万保费",
                "数值": round(sp.monthly_per_1m("女"), 2),
                "来源": "[真实数据] 香港年金示例表女65岁",
            },
            {
                "项目": "保证领取比例",
                "数值": GUARANTEE_RATIO,
                "来源": "[真实数据] 至少105%保费",
            },
            {
                "项目": "男领满保证约需年数",
                "数值": round(sp.years_to_guarantee("男"), 2),
                "来源": "1.05/年化转换率",
            },
            {
                "项目": "2025年金销售额_亿",
                "数值": HK_ANNUITY_SALES_2025_YI,
                "来源": "[真实数据量级] 背景（较2024约44亿翻倍）",
            },
            {
                "项目": "权衡",
                "数值": "年金化对冲长寿风险，但降低流动性",
                "来源": "分析结论",
            },
        ]
    )
    price_info.to_csv(OUT / "S00_annuity_pricing_sources.csv", index=False, encoding="utf-8-sig")

    payload = build_payload(struct_m, struct_f, dep_pts_m, dep_pts_f, grid, hedge)
    html_path = write_html(payload)
    write_dictionary(grid, hedge, sp)

    # 控制台摘要：基准×男
    sub = grid[(grid["性别"] == "男") & (grid["回报情景"] == "基准")]
    print("=== 定价 ===")
    print(f"  男转换率={ANNUITY_ANNUAL_RATE_MALE:.4%}  女={ANNUITY_ANNUAL_RATE_FEMALE:.4%}")
    print(f"  保证105% → 男约 {sp.years_to_guarantee('男'):.1f} 年领满")
    print("=== 基准·男：年金化比例 vs 收入/耗尽 ===")
    print(
        sub[
            [
                "年金化比例",
                "年金年收入_港元",
                "剩余年提取_港元",
                "退休初期年收入_港元",
                "耗尽后年收入_港元_终身地板",
                "替代率_地板_vs前年薪",
                "账户耗尽年龄",
            ]
        ].to_string(index=False)
    )
    print("\n=== 长寿对冲（基准·分性别·50%年金化）===")
    h50 = hedge[
        (hedge["回报情景"] == "基准") & (hedge["年金化比例"] == 0.5)
    ]
    print(
        h50[
            [
                "性别",
                "终身地板_年收入_港元",
                "地板覆盖目标_pct",
                "相对0%年金_地板覆盖提升_pp",
                "MC长寿缺口发生率_收入归零",
                "相对0%_缺口发生率下降_pp",
            ]
        ].to_string(index=False)
    )
    print(f"\n图表: {html_path}")
    print("权衡: 年金化解决长寿风险，但降低流动性")


def build_payload(struct_m, struct_f, dep_m, dep_f, grid, hedge) -> dict:
    def struct_pack(df):
        return {
            "ratios": [f"{int(x*100)}%" for x in df["年金化比例"]],
            "annuity": df["年金年收入_港元"].tolist(),
            "draw": df["剩余年提取_港元"].tolist(),
            "floor": df["耗尽后年收入_港元_终身地板"].tolist(),
            "total": df["退休初期年收入_港元"].tolist(),
        }

    def dep_pack(df):
        # 将 ∞ 显示为 120 封顶柱
        ages = []
        for _, r in df.iterrows():
            ages.append(float(r["账户耗尽年龄"]))
        return {
            "labels": [f"{int(x*100)}%" for x in df["年金化比例"]],
            "ages": ages,
            "floors": df["终身地板_港元"].tolist(),
        }

    base_bal = float(
        grid[(grid["性别"] == "男") & (grid["回报情景"] == "基准") & (grid["年金化比例"] == 0)][
            "退休余额_港元"
        ].iloc[0]
    )
    return {
        "struct_male": struct_pack(struct_m),
        "struct_female": struct_pack(struct_f),
        "dep_male": dep_pack(dep_m),
        "dep_female": dep_pack(dep_f),
        "base_balance": base_bal,
        "disclaimer": "年金化对冲长寿风险，但降低流动性与遗产弹性；跨境支付通等为产品演进背景，未入定价方程。",
    }


def write_html(payload: dict) -> Path:
    data = json.dumps(payload, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<title>强积金年金化 · 终身收入与长寿对冲</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --ink:#1a1a1a; --muted:#555; --line:#ddd; --bg:#f7f7f5; --navy:#0b3d5c; --gold:#b08d3c; --green:#4a7c59; }}
  body {{ margin:0; font-family:"Microsoft YaHei","PingFang TC",sans-serif; background:var(--bg); color:var(--ink); }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:24px 18px 48px; }}
  h1 {{ font-size:1.4rem; color:var(--navy); margin:0 0 6px; }}
  .sub {{ color:var(--muted); font-size:.9rem; line-height:1.5; }}
  .warn {{ background:#fff8e8; border-left:4px solid var(--gold); padding:10px 12px; margin:14px 0 18px; font-size:.88rem; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  @media(max-width:800px){{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .card h2 {{ font-size:.98rem; margin:0 0 10px; }}
  canvas {{ max-height:300px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>强积金年金化 · 退休收入结构与长寿对冲</h1>
  <p class="sub">对象三「65岁账户余额」→ 部分/全部转为香港年金式终身给付；剩余余额按对象三方式提取。基准个体入职25/退休65/中位数入息。</p>
  <div class="warn" id="disc"></div>
  <div class="grid">
    <div class="card"><h2>图1 · 退休收入结构（男·基准）年金 + 剩余提取</h2><canvas id="c1"></canvas></div>
    <div class="card"><h2>图2 · 退休收入结构（女·基准）</h2><canvas id="c2"></canvas></div>
    <div class="card"><h2>图3 · 账户耗尽年龄 vs 年金化比例（男）</h2><canvas id="c3"></canvas></div>
    <div class="card"><h2>图4 · 账户耗尽年龄 vs 年金化比例（女）</h2><canvas id="c4"></canvas></div>
  </div>
</div>
<script>
const D = {data};
document.getElementById('disc').textContent = D.disclaimer + ' 基准退休余额约 $' + Math.round(D.base_balance).toLocaleString() + '。';

function stackChart(id, pack) {{
  new Chart(document.getElementById(id), {{
    type:'bar',
    data:{{
      labels: pack.ratios,
      datasets:[
        {{label:'年金（终身）', data:pack.annuity, backgroundColor:'#0b3d5c', stack:'s'}},
        {{label:'剩余余额提取', data:pack.draw, backgroundColor:'#b08d3c', stack:'s'}},
      ]
    }},
    options:{{
      responsive:true,
      plugins:{{legend:{{position:'bottom'}}, title:{{display:false}}}},
      scales:{{
        x:{{stacked:true, title:{{display:true, text:'年金化比例'}}}},
        y:{{stacked:true, title:{{display:true, text:'年收入（港元）'}}}}
      }}
    }}
  }});
}}
function depChart(id, pack, color) {{
  new Chart(document.getElementById(id), {{
    type:'line',
    data:{{
      labels: pack.labels,
      datasets:[
        {{label:'账户耗尽年龄（剩余部分；120≈不耗尽）', data:pack.ages, borderColor:color, tension:.25, fill:false}},
      ]
    }},
    options:{{
      responsive:true,
      plugins:{{legend:{{position:'bottom'}}}},
      scales:{{
        y:{{min:65, max:125, title:{{display:true, text:'年龄'}}}},
        x:{{title:{{display:true, text:'年金化比例'}}}}
      }}
    }}
  }});
}}
stackChart('c1', D.struct_male);
stackChart('c2', D.struct_female);
depChart('c3', D.dep_male, '#0b3d5c');
depChart('c4', D.dep_female, '#b08d3c');
</script>
</body>
</html>
"""
    path = _PKG / "mpf_annuity_dashboard.html"
    path.write_text(html, encoding="utf-8")
    (OUT / "mpf_annuity_dashboard.html").write_text(html, encoding="utf-8")
    return path


def write_dictionary(grid: pd.DataFrame, hedge: pd.DataFrame, sp: SimpleHKAnnuityPricer) -> None:
    m50 = grid[(grid["性别"] == "男") & (grid["回报情景"] == "基准") & (grid["年金化比例"] == 0.5)].iloc[0]
    m0 = grid[(grid["性别"] == "男") & (grid["回报情景"] == "基准") & (grid["年金化比例"] == 0.0)].iloc[0]
    text = f"""# 强积金年金化提取模型 · 数据字典

> 对象三自然延伸：65岁余额 → 终身年金 + 剩余提取  
> **权衡：年金化解决长寿风险，但降低流动性**

## 定价锚点

| 项 | 数值 | 来源 |
|----|------|------|
| 男65岁 / 百万保费 | 月付约 {ANNUITY_MONTHLY_MALE_PER_1M:,.0f} | [真实数据量级] |
| 男年化转换率 | {ANNUITY_ANNUAL_RATE_MALE:.4%} | 推算 |
| 女年化转换率 | {ANNUITY_ANNUAL_RATE_FEMALE:.4%} | [假设] ×(18/24) |
| 保证领取 | 105% 保费 | [真实数据] |
| 2025年金销售 | 约 90 亿 | [真实数据量级] |

## 核心公式

```
年金年收入 = 余额 × 年金化比例 × 分性别转换率
剩余余额 = 余额 × (1 − 年金化比例)
初期年收入 = 年金 + max(0, 目标支出 − 年金)（来自剩余提取）
终身地板 = 年金 + 其他收入   # 不随账户耗尽归零
```

## 基准·男·50%年金化（摘要）

| 项 | 0%年金 | 50%年金 |
|----|--------|---------|
| 年金年收入 | {m0['年金年收入_港元']:,.0f} | {m50['年金年收入_港元']:,.0f} |
| 终身地板 | {m0['耗尽后年收入_港元_终身地板']:,.0f} | {m50['耗尽后年收入_港元_终身地板']:,.0f} |
| 账户耗尽年龄 | {m0['账户耗尽年龄']} | {m50['账户耗尽年龄']} |

## 预留接口

```python
from data_loader import load_annuity_pricer
pricer = load_annuity_pricer("annuity_rates.csv")  # 列: sex,age,annual_rate
```
"""
    (_PKG / "00_data_dictionary.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
