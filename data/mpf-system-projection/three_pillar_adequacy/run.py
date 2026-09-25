# -*- coding: utf-8 -*-
"""三层替代率 · 主入口（教学向）。

情景设计（帮助理解概念）：
  A. 代表性中产（对象三基准余额）——通常因资产过高领不到长津
  B. 同上但高比例年金化——年金入息可能又撞长津入息上限
  C. 低收入少资产画像——可能领长津
  D. 极低收入极低资产——示意综援
  E. 70 岁改领生果金（无资产审查，但与长津互斥）

用法::

    python run.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_PKG = Path(__file__).resolve().parent
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from combine import combine_replacement
from pillar1 import (
    CSSA_ELDERLY_MONTHLY,
    OAA_MONTHLY,
    OALA_ASSET_LIMIT_SINGLE,
    OALA_INCOME_LIMIT_SINGLE,
    OALA_MONTHLY_2026,
    FirstPillarChoice,
    PersonMeans,
)

OUT = _PKG / "output"
OUT.mkdir(parents=True, exist_ok=True)

ANN_CSV = _PKG.parent / "mpf_annuity_model" / "output" / "T01_income_by_annuitize_ratio.csv"
IND_CSV = (
    _PKG.parent
    / "mpf_individual_model"
    / "output"
    / "T01_retirement_balance_by_sex_return.csv"
)


def load_base_person(sex: str = "男", scenario: str = "基准", ann_ratio: float = 0.0) -> Dict[str, float]:
    """从对象三/四读取代表性个体。"""
    if ANN_CSV.exists():
        a = pd.read_csv(ANN_CSV)
        row = a[
            (a["性别"] == sex)
            & (a["回报情景"] == scenario)
            & (abs(a["年金化比例"] - ann_ratio) < 1e-9)
        ].iloc[0]
        return {
            "balance": float(row["退休余额_港元"]),
            "pre_salary": float(row["退休前年薪_港元"]),
            "annuity_annual": float(row["年金年收入_港元"]),
            "mpf_draw_annual": float(row["剩余年提取_港元"]),
            "residual": float(row["剩余余额_港元"]),
            "ann_ratio": float(row["年金化比例"]),
        }
    # 回退硬编码近似
    return {
        "balance": 4241010.0,
        "pre_salary": 802461.0,
        "annuity_annual": 0.0 if ann_ratio == 0 else 4241010.0 * ann_ratio * 0.0696,
        "mpf_draw_annual": 401230.0,
        "residual": 4241010.0 * (1 - ann_ratio),
        "ann_ratio": ann_ratio,
    }


def run_scenarios() -> pd.DataFrame:
    """教学情景表。"""
    rows: List[Dict[str, Any]] = []

    def add(name: str, sex: str, ann_ratio: float, choice: FirstPillarChoice, age: int, asset_override=None, income_extra=0.0):
        p = load_base_person(sex, "基准", ann_ratio)
        # 计入审查的资产：剩余 MPF（年金保费一般不计入——社署 FAQ）
        assets = p["residual"] if asset_override is None else asset_override
        # 入息：年金月付 + 其他
        ann_m = p["annuity_annual"] / 12.0
        means = PersonMeans(
            age=age,
            monthly_income_ex_welfare=ann_m + income_extra,
            countable_assets=assets,
            on_cssa=(choice == FirstPillarChoice.CSSA),
            on_oala=(choice == FirstPillarChoice.OALA),
            on_oaa=(choice == FirstPillarChoice.OAA),
        )
        # 注意：申请检查时不应先把自己标成已领取；用干净 means 做资格
        means_check = PersonMeans(
            age=age,
            monthly_income_ex_welfare=ann_m + income_extra,
            countable_assets=assets,
        )
        r = combine_replacement(
            p["pre_salary"],
            choice,
            means_check,
            p["mpf_draw_annual"],
            p["annuity_annual"],
        )
        r["情景名"] = name
        r["性别"] = sex
        r["年龄"] = age
        r["年金化比例"] = ann_ratio
        r["计入资产_港元"] = round(assets, 2)
        r["计入入息_月_港元"] = round(ann_m + income_extra, 2)
        r["MPF余额_港元"] = round(p["balance"], 2)
        rows.append(r)

    # A 中产 · 无年金 · 想领长津 → 通常资产爆表失败
    add("A_中产无年金_申长津", "男", 0.0, FirstPillarChoice.OALA, 65)
    # A2 中产 · 不申第一支柱
    add("A2_中产无年金_无第一支柱", "男", 0.0, FirstPillarChoice.NONE, 65)
    # B 中产 · 50%年金 · 申长津 → 资产下降但年金入息可能超限
    add("B_中产50%年金_申长津", "男", 0.5, FirstPillarChoice.OALA, 65)
    # B2 中产 · 50%年金 · 无第一支柱（现实常见）
    add("B2_中产50%年金_无第一支柱", "男", 0.5, FirstPillarChoice.NONE, 65)
    # B3 100%年金 · 申长津
    add("B3_中产100%年金_申长津", "男", 1.0, FirstPillarChoice.OALA, 65)
    # C 低收入少资产画像（覆盖对象三余额，改资产/薪）
    # 手工：小余额 + 低前年薪
    low = {
        "balance": 180000.0,
        "pre_salary": 240000.0,  # 月薪约 2 万偏低职涯终点简化
        "annuity_annual": 0.0,
        "mpf_draw_annual": 120000.0 * 0.5,  # 简化
        "residual": 180000.0,
        "ann_ratio": 0.0,
    }
    means_c = PersonMeans(age=65, monthly_income_ex_welfare=0.0, countable_assets=180000.0)
    r = combine_replacement(
        low["pre_salary"],
        FirstPillarChoice.OALA,
        means_c,
        low["mpf_draw_annual"],
        0.0,
    )
    r.update(
        {
            "情景名": "C_低收入少资产_申长津",
            "性别": "男",
            "年龄": 65,
            "年金化比例": 0.0,
            "计入资产_港元": 180000.0,
            "计入入息_月_港元": 0.0,
            "MPF余额_港元": 180000.0,
        }
    )
    rows.append(r)

    # D 极低资产综援示意
    means_d = PersonMeans(age=65, monthly_income_ex_welfare=0.0, countable_assets=40000.0)
    r = combine_replacement(
        180000.0,
        FirstPillarChoice.CSSA,
        means_d,
        0.0,
        0.0,
    )
    r.update(
        {
            "情景名": "D_极低资产_申综援",
            "性别": "男",
            "年龄": 65,
            "年金化比例": 0.0,
            "计入资产_港元": 40000.0,
            "计入入息_月_港元": 0.0,
            "MPF余额_港元": 50000.0,
        }
    )
    rows.append(r)

    # E 70岁生果金 · 中产有MPF提取（无资产审查）
    add("E_中产70岁_申生果金", "男", 0.0, FirstPillarChoice.OAA, 70)
    # E2 70岁仍申长津（对比）
    add("E2_中产70岁_申长津", "男", 0.0, FirstPillarChoice.OALA, 70)

    # 女 · 50%年金 · 无第一支柱（费率已用官方女表）
    add("F_女中产50%年金_无第一支柱", "女", 0.5, FirstPillarChoice.NONE, 65)

    return pd.DataFrame(rows)


def write_concepts() -> None:
    text = f"""# 三层退休收入 · 概念说明书（P0+P1）

> 目的：搞清 **综援 / 长者生活津贴 / 生果金 / 强积金 / 年金** 各是什么，以及如何合并算替代率。  
> 金额锚点以社署公开资料为准（标注生效日）；模型为教学简化，**不能当申请结论**。

---

## 1. 一张图看懂「谁发钱」

| 名称 | 支柱 | 谁发 | 要不要审资产入息 | 典型月额（约） | 和谁互斥 |
|------|------|------|------------------|----------------|----------|
| **综援**（长者） | 第一 | 政府（社署） | **严格**审查 | ~{CSSA_ELDERLY_MONTHLY:,.0f}（教学量级） | 长津、生果金等 |
| **长者生活津贴 (OALA)** | 第一 | 政府（公共福利金） | **有**入息·资产上限 | **{OALA_MONTHLY_2026:,.0f}**（2026-02-01 起） | 综援、生果金、伤残津贴 |
| **高龄津贴 / 生果金 (OAA)** | 第一 | 政府 | **不审**经济 | **{OAA_MONTHLY:,.0f}** | 长津、综援等 |
| **强积金 MPF** | 第二 | 自己账户 | 无「福利审查」 | 看余额怎么取 | 不与上列互斥 |
| **香港年金** | 第三（产品） | 年金公司 | 产品合同 | 男65约5800/百万；女约5300/百万 | 不阻止申长津，但**年金入息计入长津入息** |

长津单身限额（2026-02-01）：入息 ≤ **{OALA_INCOME_LIMIT_SINGLE:,.0f}/月**，资产 ≤ **{OALA_ASSET_LIMIT_SINGLE:,.0f}**。

---

## 2. 容易混的点

1. **长津不是综援**  
   长津是「有经济需要但未到综援那么穷」的补助；综援保障更全面、审查更严。

2. **长津不是生果金**  
   生果金（高龄津贴）70 岁+、**不看身家**；长津 65 岁+、**看身家**。两者**不能同领**。

3. **年金不是政府津贴**  
   年金是你用自己的钱（往往来自强积金一笔过）买的**终身现金流**；对冲长寿，但降低流动性。

4. **强积金余额很大时，通常领不到长津**  
   未提取的强积金权益一般计入资产 → 中产账户（百万级）轻松超过约 41.5 万资产上限。

5. **买年金可能降低「计入资产」，但提高「计入入息」**  
   社署说明：投放年金的保费可不计入资产；但每月年金计入入息。  
   → 可能出现：资产合格了，入息又超标（见情景 B / B3）。

---

## 3. 替代率怎么算（P0）

```
替代率 = 退休后月收入 ÷ 退休前月收入

退休后月收入 =
    第一支柱（综援 或 长津 或 生果金，互斥）
  + 第二支柱（强积金剩余提取，可花光）
  + 第三支柱（年金终身月付）
```

对照：世界银行常用建议带大约 **40%–70%**（百科 methodology 同口径）。

区分两个替代率：
- **初期替代率**：还有强积金提取时  
- **地板替代率**：强积金剩余花光后（只剩第一支柱 + 年金）← 看长寿

---

## 4. 跑模型会看到什么（直觉）

| 情景 | 直觉结论 |
|------|----------|
| 中产、余额几百万、申长津 | **失败**（资产超限） |
| 中产、50%年金、申长津 | 资产降了，但年金月入常 **仍超入息上限** |
| 低收入、资产 < 约41.5万、入息低 | **可能**拿长津，替代率被抬高一截 |
| 资产极低 | 示意走 **综援**（月额更高量级） |
| 70 岁、申生果金 | **无资产审查**，可与强积金并存；月额较小 |

---

## 5. 和对象一～四的关系

- 对象一：制度池子（不管你个人领不领长津）  
- 对象二：综援**财政加总**开支  
- 对象三/四：个人强积金 + 年金  
- **本模块**：把第一支柱「个人能不能领」接上三/四，算合并替代率  

---

*金额请以社署最新公布为准；本页为学习笔记。*
"""
    (_PKG / "00_concepts.md").write_text(text, encoding="utf-8")


def enrich_module_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把第一支柱拆成可独立开关的模块列。"""
    out = df.copy()

    def _amt(row, label: str) -> float:
        if row.get("第一支柱") == label and bool(row.get("第一支柱_获批")):
            return float(row.get("第一支柱_月_港元") or 0)
        return 0.0

    out["长津_月_港元"] = out.apply(lambda r: _amt(r, "长者生活津贴"), axis=1)
    out["综援_月_港元"] = out.apply(lambda r: _amt(r, "综援(长者)"), axis=1)
    out["生果金_月_港元"] = out.apply(lambda r: _amt(r, "高龄津贴(生果金)"), axis=1)
    out["强积金_月_港元"] = out["第二支柱_MPF提取_月_港元"].astype(float)
    out["年金_月_港元"] = out["第三支柱_年金_月_港元"].astype(float)
    return out


def write_html(df: pd.DataFrame) -> Path:
    """可勾选成品：每模块独立「展示 / 计入统计」。"""
    enriched = enrich_module_columns(df)
    cols = [
        "情景名",
        "性别",
        "年龄",
        "第一支柱",
        "第一支柱_获批",
        "第一支柱_说明",
        "长津_月_港元",
        "综援_月_港元",
        "生果金_月_港元",
        "强积金_月_港元",
        "年金_月_港元",
        "退休前年薪_月_港元",
        "计入资产_港元",
        "计入入息_月_港元",
        "年金化比例",
        "MPF余额_港元",
    ]
    records = enriched[cols].to_dict(orient="records")
    data = json.dumps(records, ensure_ascii=False)
    meta = json.dumps(
        {
            "oala": OALA_MONTHLY_2026,
            "oaa": OAA_MONTHLY,
            "cssa": CSSA_ELDERLY_MONTHLY,
            "oala_income": OALA_INCOME_LIMIT_SINGLE,
            "oala_asset": OALA_ASSET_LIMIT_SINGLE,
        },
        ensure_ascii=False,
    )
    html = _STUDIO_HTML.replace("__DATA__", data).replace("__META__", meta)
    path = _PKG / "three_pillar_dashboard.html"
    path.write_text(html, encoding="utf-8")
    (OUT / "three_pillar_dashboard.html").write_text(html, encoding="utf-8")
    (OUT / "T02_modules_for_studio.json").write_text(
        json.dumps({"meta": json.loads(meta), "rows": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


# 交互成品模板（展示 / 统计双开关）
_STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>三层退休收入 · 可勾选成品</title>
<style>
:root{
  --navy:#1a3a5c; --navy-2:#244a73; --gold:#c9a227; --bg:#f4f5f7; --card:#fff;
  --text:#1e293b; --muted:#64748b; --line:#e2e8f0;
  --mpf:#3b82a0; --oala:#2f9e7a; --cssa:#d4655a; --oaa:#8b6bb5; --ann:#c9a227;
  --font:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
}
*{box-sizing:border-box}
body{margin:0;font-family:var(--font);background:var(--bg);color:var(--text)}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px 48px}
.hero{
  background:linear-gradient(135deg,var(--navy),var(--navy-2));color:#fff;
  border-radius:14px;padding:20px 22px;box-shadow:0 8px 24px rgba(26,58,92,.16);
}
.hero .eyebrow{font-size:.72rem;letter-spacing:.12em;color:#e8d48a;font-weight:600}
.hero h1{margin:6px 0 0;font-size:1.45rem}
.hero p{margin:8px 0 0;opacity:.9;font-size:.88rem;line-height:1.55;max-width:70ch}
.warn{
  margin-top:14px;background:rgba(255,255,255,.1);border-radius:10px;padding:10px 12px;
  font-size:.82rem;line-height:1.5;
}
.panel{margin-top:14px;display:grid;grid-template-columns:1.1fr .9fr;gap:12px}
@media(max-width:900px){.panel{grid-template-columns:1fr}}
.card{
  background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;
  box-shadow:0 3px 12px rgba(26,58,92,.05);
}
.card h2{margin:0 0 10px;font-size:.95rem;color:var(--navy)}
.hint{font-size:.78rem;color:var(--muted);margin:0 0 12px;line-height:1.45}
.mod-table{width:100%;border-collapse:collapse;font-size:.84rem}
.mod-table th{text-align:left;font-size:.72rem;color:var(--muted);font-weight:600;padding:4px 6px}
.mod-table td{padding:8px 6px;border-top:1px solid var(--line);vertical-align:middle}
.mod-table .name{font-weight:600;color:var(--navy)}
.mod-table .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.tog{display:flex;gap:18px;align-items:center}
.tog label{display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;font-size:.82rem}
.tog input{width:15px;height:15px;accent-color:var(--navy)}
.presets{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.presets button{
  border:1px solid var(--line);background:#fff;color:var(--navy);padding:6px 10px;
  border-radius:999px;cursor:pointer;font:inherit;font-size:.78rem;
}
.presets button:hover{border-color:var(--navy)}
.scen{display:flex;flex-wrap:wrap;gap:6px;max-height:220px;overflow:auto}
.scen label{
  display:flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid var(--line);
  border-radius:8px;font-size:.76rem;cursor:pointer;background:#fafbfc;
}
.scen label.on{border-color:var(--navy);background:#eef3f8;font-weight:600}
.kpis{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:800px){.kpis{grid-template-columns:1fr 1fr}}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.kpi .l{font-size:.72rem;color:var(--muted)}
.kpi .v{margin-top:4px;font-size:1.2rem;font-weight:700;color:var(--navy);font-variant-numeric:tabular-nums}
.kpi .h{margin-top:2px;font-size:.72rem;color:var(--muted)}
.kpi .v.ok{color:#2f9e7a}.kpi .v.bad{color:#d4655a}
.grid{margin-top:14px;display:grid;grid-template-columns:1.2fr .8fr;gap:12px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.chart-wrap{min-height:320px;position:relative}
.chart-wrap canvas{width:100%!important;max-height:340px}
.concept{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-top:12px}
.concept .c{border:1px solid var(--line);border-radius:10px;padding:10px;font-size:.78rem;line-height:1.45}
.concept .c h3{margin:0 0 4px;font-size:.86rem;color:var(--navy)}
.concept .c.hidden{display:none}
table.data{width:100%;border-collapse:collapse;font-size:.76rem;background:#fff;margin-top:4px}
table.data th,table.data td{border:1px solid var(--line);padding:6px 7px;text-align:left;vertical-align:top}
table.data th{background:#eef2f5;position:sticky;top:0}
.ok{color:#2a7a4b;font-weight:600}.no{color:#a33;font-weight:600}
.formula{
  margin-top:10px;padding:10px 12px;background:#f8fafc;border-radius:8px;font-size:.8rem;
  color:var(--muted);line-height:1.5;font-family:ui-monospace,Consolas,monospace;
}
details.how{
  margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:12px;
  box-shadow:0 3px 12px rgba(26,58,92,.05);overflow:hidden;
}
details.how>summary{
  cursor:pointer;list-style:none;padding:14px 16px;display:flex;align-items:center;gap:10px;
  font-weight:700;color:var(--navy);font-size:.98rem;user-select:none;
}
details.how>summary::-webkit-details-marker{display:none}
details.how>summary .badge{
  font-size:.68rem;font-weight:600;letter-spacing:.04em;color:#1a1405;background:var(--gold);
  padding:3px 8px;border-radius:999px;
}
details.how>summary .chev{
  margin-left:auto;width:9px;height:9px;border-right:2px solid var(--gold);border-bottom:2px solid var(--gold);
  transform:rotate(45deg);transition:transform .2s;
}
details.how[open]>summary .chev{transform:rotate(-135deg);margin-top:4px}
.how-body{padding:0 16px 16px;border-top:1px solid var(--line)}
.how-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
@media(max-width:800px){.how-grid{grid-template-columns:1fr}}
.how-card{
  background:linear-gradient(165deg,#f8fafc,#fff);border:1px solid var(--line);border-radius:10px;padding:12px 14px;
}
.how-card.wide{grid-column:1/-1}
.how-card h3{margin:0 0 6px;font-size:.88rem;color:var(--navy)}
.how-card p,.how-card li{margin:0;font-size:.8rem;color:var(--muted);line-height:1.55}
.how-card ul{margin:6px 0 0;padding-left:1.15em}
.how-card ol{margin:6px 0 0;padding-left:1.2em}
.how-card code{font-size:.78rem;background:#eef2f5;padding:1px 5px;border-radius:4px;color:var(--navy)}
.flow{
  display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:8px;font-size:.78rem;font-weight:600;color:var(--navy);
}
.flow span.pill{background:rgba(201,162,39,.16);border:1px solid rgba(201,162,39,.4);padding:4px 8px;border-radius:999px}
.flow span.arr{color:var(--gold)}
footer{margin-top:20px;padding-top:14px;border-top:1px solid var(--line);font-size:.76rem;color:var(--muted);line-height:1.55}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">P0 + P1 · 可勾选成品</div>
    <h1>三层退休收入 · 自由选择展示与统计</h1>
    <p>每个模块可独立开关：<strong>展示</strong>（卡片 / 表列 / 图例）与 <strong>计入统计</strong>（重算替代率与合计）。长津、综援、生果金在真实规则下互斥，本页按情景已发放额计入，不会双计。</p>
    <div class="warn">教学模型，非正式资格审查。长津限额（单身，2026-02）：入息 ≤ $<span id="m-inc"></span> / 资产 ≤ $<span id="m-ast"></span>；月额约 $<span id="m-oala"></span>。</div>
  </div>

  <details class="how" open>
    <summary>
      <span class="badge">必读</span>
      这个模型是怎么得出来的？思路是什么
      <span class="chev"></span>
    </summary>
    <div class="how-body">
      <div class="how-grid">
        <div class="how-card wide">
          <h3>要回答的问题</h3>
          <p>一个人退休后，靠<strong>政府津贴 + 强积金 + 年金</strong>，每月大概能有多少钱？相对退休前工资的比例（替代率）够不够？  
          中产为何常领不到长津？买年金后会不会反而撞上入息上限？花光强积金后还剩什么「地板」？</p>
        </div>
        <div class="how-card">
          <h3>1. 三层收入思路（世界银行口径）</h3>
          <p>把退休月收入拆成三层再相加，再除以退休前月收入：</p>
          <div class="flow">
            <span class="pill">第一支柱 政府</span><span class="arr">+</span>
            <span class="pill">第二支柱 强积金</span><span class="arr">+</span>
            <span class="pill">第三支柱 年金</span><span class="arr">→</span>
            <span class="pill">÷ 退休前月薪 = 替代率</span>
          </div>
          <ul>
            <li><strong>第一支柱</strong>：综援 / 长者生活津贴 / 生果金（三者互斥，只能选一条路）</li>
            <li><strong>第二支柱</strong>：强积金剩余账户按年提取（会花光）</li>
            <li><strong>第三支柱</strong>：用一部分余额买的终身年金月付</li>
          </ul>
        </div>
        <div class="how-card">
          <h3>2. 数字从哪来</h3>
          <ul>
            <li><strong>强积金余额、前年薪、年金月付、剩余提取</strong>：接对象三/四已跑出的代表性个体（中产基准、不同年金化比例、男女费率）</li>
            <li><strong>长津 / 生果金月额与限额</strong>：社署公开数字（本页标注 2026-02 起长津约 $4,345；入息/资产上限见页眉）</li>
            <li><strong>综援月额</strong>：教学量级约 $8,600（非正式资格结论）</li>
            <li><strong>低收入 / 极低资产情景</strong>：手工设定资产与薪，用来对照「谁能领长津/综援」</li>
          </ul>
        </div>
        <div class="how-card">
          <h3>3. 第一支柱怎么判定「发不发」</h3>
          <ol>
            <li>先选定申请哪一种（长津 / 生果金 / 综援 / 不申）</li>
            <li>用<strong>计入入息</strong>（含年金月付）和<strong>计入资产</strong>（剩余强积金一般计入；已付年金保费通常不计入资产）做示意审查</li>
            <li>通过 → 加上对应月额；不通过 → 记 $0，并在表里写明原因（资产超限 / 入息超限 / 年龄不够等）</li>
          </ol>
          <p style="margin-top:8px">这就是「中产申长津失败、50% 年金后入息仍超限」等情景的来源。</p>
        </div>
        <div class="how-card">
          <h3>4. 为什么有两个替代率</h3>
          <ul>
            <li><strong>初期</strong>：刚退休，还有强积金提取 +（可能的）津贴 + 年金</li>
            <li><strong>地板（长寿）</strong>：强积金剩余花光后，只剩津贴 + 年金 —— 看活得久时还够不够</li>
          </ul>
          <p style="margin-top:8px">对照带约 <code>40%–70%</code>（世界银行常用区间）。页面 KPI 会标是否落在建议带。</p>
        </div>
        <div class="how-card wide">
          <h3>5. 本页「展示 / 计入统计」在干什么</h3>
          <p>上面算好的是各模块<strong>原始月额</strong>（情景表里已定）。本页不重跑资格，只让你自由组合：</p>
          <ul>
            <li><strong>展示</strong>：概念卡、堆叠图系列、表列是否出现 —— 方便讲概念时藏掉干扰项</li>
            <li><strong>计入统计</strong>：是否加进合计与替代率 —— 例如关掉强积金 = 只看长寿地板；只开长津+年金 = 学「津贴与年金如何叠」</li>
          </ul>
          <p style="margin-top:8px">长津/综援/生果金在数据里同一情景只有一列非零，勾选多个也不会双计政府津贴。</p>
        </div>
        <div class="how-card wide">
          <h3>6. 和对象一～四怎么接</h3>
          <div class="flow">
            <span class="pill">对象一 制度池</span><span class="arr">·</span>
            <span class="pill">对象二 综援财政加总</span><span class="arr">·</span>
            <span class="pill">对象三 个人强积金</span><span class="arr">·</span>
            <span class="pill">对象四 年金化</span><span class="arr">→</span>
            <span class="pill">本页：个人能不能领第一支柱 + 合并替代率</span>
          </div>
          <p style="margin-top:8px">对象一/二管「系统有多大」；对象三/四管「个人账户与年金」；<strong>本模块补上「个人侧第一支柱资格 + 三层合并」</strong>，方便面试讲清概念。</p>
        </div>
        <div class="how-card wide">
          <h3>7. 局限（诚实边界）</h3>
          <ul>
            <li>资格是<strong>示意规则</strong>，不是社署正式批核；家庭、租金、豁免资产等未建模</li>
            <li>中产画像来自对象三/四基准路径，不是人口抽样</li>
            <li>综援为量级示意；伤残津贴等其他公共福利金未纳入</li>
            <li>金额以社署最新公布为准；本页为学习与面试叙事工具</li>
          </ul>
        </div>
      </div>
    </div>
  </details>

  <div class="panel">
    <div class="card">
      <h2>① 模块开关</h2>
      <p class="hint">左边「展示」控制是否看见；右边「计入统计」控制是否算进替代率。可先关强积金，只看长寿地板。</p>
      <table class="mod-table">
        <thead><tr><th>模块</th><th>展示</th><th>计入统计</th></tr></thead>
        <tbody id="mod-body"></tbody>
      </table>
      <div class="presets">
        <button type="button" data-preset="all">全开</button>
        <button type="button" data-preset="floor">只看长寿地板</button>
        <button type="button" data-preset="mpf-ann">只看强积金+年金</button>
        <button type="button" data-preset="p1">只看第一支柱</button>
        <button type="button" data-preset="oala-learn">学长津（展示全开，统计含长津+年金）</button>
      </div>
      <div class="formula" id="formula">—</div>
    </div>
    <div class="card">
      <h2>② 情景（可多选）</h2>
      <p class="hint">勾选要对比的情景；统计 KPI 取<strong>当前选中情景的平均值</strong>，图与表按选中项刷新。</p>
      <div class="scen" id="scen"></div>
      <div class="presets" style="margin-top:10px">
        <button type="button" id="scen-all">全选</button>
        <button type="button" id="scen-mid">中产相关</button>
        <button type="button" id="scen-low">低收入/综援</button>
      </div>
    </div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="grid">
    <div class="card">
      <h2>③ 收入构成（按「展示」画图，「计入统计」决定合计）</h2>
      <div class="chart-wrap"><canvas id="chart"></canvas></div>
    </div>
    <div class="card">
      <h2>④ 概念卡（随「展示」显隐）</h2>
      <div class="concept" id="concepts">
        <div class="c" data-mod="oala"><h3>长者生活津贴</h3><p>65+·审入息资产·约 $4,345/月·与综援/生果金互斥</p></div>
        <div class="c" data-mod="cssa"><h3>综援（长者）</h3><p>安全网·审查更严·月额量级更高·与长津互斥</p></div>
        <div class="c" data-mod="oaa"><h3>生果金</h3><p>70+·不审身家·约 $1,640/月·与长津互斥</p></div>
        <div class="c" data-mod="mpf"><h3>强积金</h3><p>自己账户提取·可花光·余额大时常领不到长津</p></div>
        <div class="c" data-mod="ann"><h3>年金</h3><p>买的终身现金流·对冲长寿·入息计入长津审查</p></div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:12px">
    <h2>⑤ 明细表</h2>
    <div style="overflow:auto;max-height:420px">
      <table class="data" id="t"><thead></thead><tbody></tbody></table>
    </div>
  </div>

  <footer>
    成品路径：<code>three_pillar_dashboard.html</code> · 概念详见页内「必读」与 <code>00_concepts.md</code> ·
    重新生成：<code>python run.py</code>
  </footer>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const ROWS = __DATA__;
const META = __META__;

const MODULES = [
  {id:"mpf",  name:"强积金 MPF",   key:"强积金_月_港元", color:"var(--mpf)",  hex:"#3b82a0", floor:false},
  {id:"oala", name:"长者生活津贴", key:"长津_月_港元",   color:"var(--oala)", hex:"#2f9e7a", floor:true},
  {id:"cssa", name:"综援（长者）", key:"综援_月_港元",   color:"var(--cssa)", hex:"#d4655a", floor:true},
  {id:"oaa",  name:"生果金",       key:"生果金_月_港元", color:"var(--oaa)",  hex:"#8b6bb5", floor:true},
  {id:"ann",  name:"年金",         key:"年金_月_港元",   color:"var(--ann)",  hex:"#c9a227", floor:true},
];

const state = {
  show:  Object.fromEntries(MODULES.map(m => [m.id, true])),
  count: Object.fromEntries(MODULES.map(m => [m.id, true])),
  scen:  new Set(ROWS.map(r => r.情景名)),
};

document.getElementById("m-oala").textContent = META.oala.toLocaleString();
document.getElementById("m-inc").textContent = META.oala_income.toLocaleString();
document.getElementById("m-ast").textContent = META.oala_asset.toLocaleString();

function money(n){ return (n||0).toLocaleString(undefined,{maximumFractionDigits:0}); }
function pct(n){ return (n||0).toFixed(1) + "%"; }
function band(rr){
  if (!(rr >= 0)) return "—";
  if (rr < 40) return "低于40%（可能不足）";
  if (rr <= 70) return "落在40%–70%建议带";
  return "高于70%";
}

function buildModUI(){
  const tb = document.getElementById("mod-body");
  tb.innerHTML = MODULES.map(m => `
    <tr>
      <td class="name"><span class="dot" style="background:${m.hex}"></span>${m.name}</td>
      <td><div class="tog"><label><input type="checkbox" data-kind="show" data-id="${m.id}" ${state.show[m.id]?"checked":""}/> 展示</label></div></td>
      <td><div class="tog"><label><input type="checkbox" data-kind="count" data-id="${m.id}" ${state.count[m.id]?"checked":""}/> 计入统计</label></div></td>
    </tr>`).join("");
  tb.querySelectorAll("input").forEach(inp => {
    inp.addEventListener("change", () => {
      const id = inp.dataset.id, kind = inp.dataset.kind;
      if (kind === "show") state.show[id] = inp.checked;
      else state.count[id] = inp.checked;
      render();
    });
  });
}

function buildScenUI(){
  const box = document.getElementById("scen");
  box.innerHTML = ROWS.map(r => {
    const on = state.scen.has(r.情景名);
    return `<label class="${on?"on":""}"><input type="checkbox" data-scen="${r.情景名}" ${on?"checked":""}/> ${r.情景名}</label>`;
  }).join("");
  box.querySelectorAll("input").forEach(inp => {
    inp.addEventListener("change", () => {
      if (inp.checked) state.scen.add(inp.dataset.scen);
      else state.scen.delete(inp.dataset.scen);
      inp.parentElement.classList.toggle("on", inp.checked);
      render();
    });
  });
}

function selectedRows(){
  return ROWS.filter(r => state.scen.has(r.情景名));
}

function calcRow(r){
  let early = 0, floor = 0;
  const parts = {};
  MODULES.forEach(m => {
    const v = Number(r[m.key] || 0);
    parts[m.id] = v;
    if (state.count[m.id]) {
      early += v;
      if (m.floor) floor += v;
    }
  });
  const pre = Number(r.退休前年薪_月_港元 || 0);
  const rrE = pre > 0 ? 100 * early / pre : NaN;
  const rrF = pre > 0 ? 100 * floor / pre : NaN;
  return { early, floor, rrE, rrF, parts, pre };
}

function formulaText(){
  const on = MODULES.filter(m => state.count[m.id]).map(m => m.name);
  const floorOn = MODULES.filter(m => state.count[m.id] && m.floor).map(m => m.name);
  return "初期 = (" + (on.join(" + ") || "0") + ") ÷ 退休前月收入\n"
       + "地板 = (" + (floorOn.join(" + ") || "0") + ") ÷ 退休前月收入   ← 强积金提取不进入地板";
}

let chart;
function renderChart(rows){
  const labels = rows.map(r => r.情景名.replace(/_/g, "\n"));
  const datasets = MODULES.filter(m => state.show[m.id]).map(m => ({
    label: m.name,
    data: rows.map(r => Number(r[m.key] || 0)),
    backgroundColor: m.hex,
    stack: "inc",
  }));
  const ctx = document.getElementById("chart");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { callbacks: { label: (c) => c.dataset.label + ": $" + money(c.raw) } },
      },
      scales: {
        x: { stacked: true, ticks: { font: { size: 9 }, maxRotation: 0 } },
        y: { stacked: true, ticks: { callback: v => "$" + money(v) } },
      },
    },
  });
}

function renderKpis(calcs){
  if (!calcs.length) {
    document.getElementById("kpis").innerHTML = '<div class="kpi"><div class="l">提示</div><div class="v">请至少选一个情景</div></div>';
    return;
  }
  const avg = (fn) => calcs.reduce((s,c) => s + fn(c), 0) / calcs.length;
  const rrE = avg(c => c.rrE);
  const rrF = avg(c => c.rrF);
  const early = avg(c => c.early);
  const floor = avg(c => c.floor);
  const inBand = rrF >= 40 && rrF <= 70;
  document.getElementById("kpis").innerHTML = `
    <div class="kpi"><div class="l">初期替代率（均）</div><div class="v">${pct(rrE)}</div><div class="h">含当前「计入统计」的全部模块</div></div>
    <div class="kpi"><div class="l">地板替代率（均）</div><div class="v ${inBand?"ok":"bad"}">${pct(rrF)}</div><div class="h">${band(rrF)}</div></div>
    <div class="kpi"><div class="l">初期月收入（均）</div><div class="v">$${money(early)}</div><div class="h">仅统计开关打开的模块</div></div>
    <div class="kpi"><div class="l">长寿地板月收入（均）</div><div class="v">$${money(floor)}</div><div class="h">不含强积金提取</div></div>`;
}

function renderTable(rows, calcs){
  const showMods = MODULES.filter(m => state.show[m.id]);
  const head = ["情景", "第一支柱", "获批", ...showMods.map(m => m.name), "初期替代率*", "地板替代率*", "说明"];
  const th = document.querySelector("#t thead");
  const tb = document.querySelector("#t tbody");
  th.innerHTML = "<tr>" + head.map(h => "<th>"+h+"</th>").join("") + "</tr>";
  tb.innerHTML = rows.map((r,i) => {
    const c = calcs[i];
    const cells = [
      r.情景名,
      r.第一支柱,
      r.第一支柱_获批 ? '<span class="ok">是</span>' : '<span class="no">否</span>',
      ...showMods.map(m => "$" + money(r[m.key])),
      pct(c.rrE),
      pct(c.rrF),
      r.第一支柱_说明 || "",
    ];
    return "<tr>" + cells.map(x => "<td>"+x+"</td>").join("") + "</tr>";
  }).join("");
}

function renderConcepts(){
  document.querySelectorAll("#concepts .c").forEach(el => {
    el.classList.toggle("hidden", !state.show[el.dataset.mod]);
  });
}

function render(){
  const rows = selectedRows();
  const calcs = rows.map(calcRow);
  document.getElementById("formula").textContent = formulaText();
  renderKpis(calcs);
  renderChart(rows);
  renderTable(rows, calcs);
  renderConcepts();
}

document.querySelectorAll("[data-preset]").forEach(btn => {
  btn.addEventListener("click", () => {
    const p = btn.dataset.preset;
    MODULES.forEach(m => { state.show[m.id] = true; state.count[m.id] = true; });
    if (p === "floor") {
      state.count.mpf = false;
    } else if (p === "mpf-ann") {
      MODULES.forEach(m => { state.count[m.id] = (m.id === "mpf" || m.id === "ann"); });
    } else if (p === "p1") {
      MODULES.forEach(m => { state.count[m.id] = (m.id === "oala" || m.id === "cssa" || m.id === "oaa"); });
    } else if (p === "oala-learn") {
      MODULES.forEach(m => { state.count[m.id] = (m.id === "oala" || m.id === "ann"); });
    }
    buildModUI();
    render();
  });
});

document.getElementById("scen-all").onclick = () => {
  ROWS.forEach(r => state.scen.add(r.情景名));
  buildScenUI(); render();
};
document.getElementById("scen-mid").onclick = () => {
  state.scen = new Set(ROWS.filter(r => /中产|女/.test(r.情景名)).map(r => r.情景名));
  buildScenUI(); render();
};
document.getElementById("scen-low").onclick = () => {
  state.scen = new Set(ROWS.filter(r => /低收入|综援/.test(r.情景名)).map(r => r.情景名));
  buildScenUI(); render();
};

buildModUI();
buildScenUI();
render();
</script>
</body>
</html>
"""


def main() -> None:
    write_concepts()
    df = run_scenarios()
    df = enrich_module_columns(df)
    df.to_csv(OUT / "T01_three_pillar_replacement.csv", index=False, encoding="utf-8-sig")
    html = write_html(df)
    print("=== 三层替代率情景（节选）===")
    cols = [
        "情景名",
        "第一支柱",
        "第一支柱_获批",
        "第一支柱_月_港元",
        "第三支柱_年金_月_港元",
        "替代率_初期_pct",
        "替代率_地板_pct",
        "第一支柱_说明",
    ]
    print(df[cols].to_string(index=False))
    print(f"\n概念说明: {_PKG / '00_concepts.md'}")
    print(f"图表: {html}")
    print("记住: 长津 ≠ 综援 ≠ 生果金 ≠ 年金")


if __name__ == "__main__":
    main()
