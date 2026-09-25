# -*- coding: utf-8 -*-
"""Build integrated MPF 30y dashboard: ECharts sankey/waterfall + Chart.js lines."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "mpf_integrated_30y_dashboard.html"

c02 = pd.read_csv(ROOT / "contribution_layer" / "C02_contribution_breakdown.csv")
w03 = pd.read_csv(ROOT / "withdrawal_asset_layer" / "W03_asset_evolution.csv")
w01 = pd.read_csv(ROOT / "withdrawal_asset_layer" / "W01_retirement_withdrawals.csv")
w04 = pd.read_csv(ROOT / "withdrawal_asset_layer" / "W04_inflection_points.csv")
pop = pd.read_csv(ROOT / "population_ccm" / "P02_population_by_age_sex.csv")

# 对冲流出（模块8）
_off_path = ROOT / "mpf_model" / "output" / "offsetting" / "O01_offsetting_flow_by_year.csv"
if _off_path.exists():
    _off = pd.read_csv(_off_path)
    OFFSET_DATA = {
        "years": [int(y) for y in _off["年份"].tolist()],
        "pre_hire": [
            round(float(a) + float(b), 4)
            for a, b in zip(_off["对冲流出_pre_亿港元"], _off["对冲流出_hybrid_亿港元"])
        ],
        "post_hire": [round(float(x), 4) for x in _off["对冲流出_post_亿港元"].tolist()],
        "total": [round(float(x), 4) for x in _off["对冲流出_亿港元"].tolist()],
        "transition_year": 2025,
        "transition_label": "2025-05-01 转制日",
    }
else:
    OFFSET_DATA = {
        "years": list(range(2020, 2057)),
        "pre_hire": [0.0] * 37,
        "post_hire": [0.0] * 37,
        "total": [0.0] * 37,
        "transition_year": 2025,
        "transition_label": "2025-05-01 转制日",
    }

# Base series for JS resimulation (mid population path for 60-64)
years = list(range(2026, 2057))
base = {"years": years, "scenarios": {}}

for sc, label, r_default in [("低", "保守", 0.03), ("中", "基准", 0.049), ("高", "乐观", 0.07)]:
    c = c02[c02["情景"] == sc].set_index("年份")
    # forced / vol
    forced, vol, n_all, n_m, n_f = [], [], [], [], []
    for y in years:
        row = c.loc[y]
        forced.append(round(float(row["年强制性供款_亿港元"]), 4))
        vol.append(round(float(row["年自愿性供款_亿港元"]), 4))
        n_all.append(round(float(row["缴费人数_万人"]), 4))
        n_m.append(round(float(row["缴费人数_男_万人"]), 4))
        n_f.append(round(float(row["缴费人数_女_万人"]), 4))

    # new 65 by sex from W01 (at default 65)
    ret = w01[(w01["情景"] == sc)]
    n65_m, n65_f, n65_x = [], [], []
    bal = []  # not used directly; JS recomputes from A/accounts
    for y in years:
        for sex, bucket in [("男", n65_m), ("女", n65_f), ("混合", n65_x)]:
            r = ret[(ret["年份"] == y) & (ret["性别"] == sex)].iloc[0]
            bucket.append(round(float(r["新达65岁人数_人"]) / 1e4, 6))  # 万人

    # 60-64 pop for retire-age shift (mid pop scenario)
    p604 = []
    for y in years:
        sub = pop[(pop["年份"] == y) & (pop["情景"] == "中") & (pop["年龄组"] == "60-64")]
        p604.append({
            "男": round(float(sub[sub["性别"] == "男"]["人数"].sum()) / 1e4, 4),
            "女": round(float(sub[sub["性别"] == "女"]["人数"].sum()) / 1e4, 4),
        })

    inf = w04[w04["情景"] == sc].iloc[0].to_dict()
    # convert numpy types
    for k, v in list(inf.items()):
        if hasattr(v, "item"):
            inf[k] = v.item()
        elif pd.isna(v):
            inf[k] = None

    base["scenarios"][sc] = {
        "label": label,
        "r_default": r_default,
        "forced": forced,
        "vol": vol,
        "contrib_n": n_all,
        "contrib_n_m": n_m,
        "contrib_n_f": n_f,
        "n65_m": n65_m,
        "n65_f": n65_f,
        "n65_mix": n65_x,
        "pop_60_64": p604,
        "inflection_default": {
            "峰值年份": inf.get("资产峰值年份"),
            "峰值资产": inf.get("资产峰值_亿港元"),
            "净流出拐点": inf.get("净现金流拐点年份_提取大于供款"),
            "经济拐点": inf.get("经济净流入拐点年份_提取大于供款加回报"),
            "期末资产": inf.get("期末资产_亿港元"),
            "累计供款": inf.get("累计供款_亿港元"),
            "累计提取": inf.get("累计提取_亿港元"),
        },
    }

payload = {
    "meta": {
        "A0": 16700,
        "accounts0": 1100,
        "accounts_g": 0.005,
        "other_share": 0.12,
        "kappa_vol": 0.255,
        "y_min": 7100,
        "y_max": 30000,
        "coverage_default": 0.85,
        "wage_g_default": 0.03,
        "retire_age_default": 65,
        "withdraw_ratio_default": 1.0,
        "r_default": 0.049,
        "retiree_bal_factor": 1.05,
    },
    "presets": {
        "保守": {"sc": "低", "r": 3.0, "retireAge": 65, "withdraw": 100, "coverage": 83, "wageG": 2.0},
        "基准": {"sc": "中", "r": 4.9, "retireAge": 65, "withdraw": 100, "coverage": 85, "wageG": 3.0},
        "乐观": {"sc": "高", "r": 7.0, "retireAge": 65, "withdraw": 100, "coverage": 87, "wageG": 4.0},
    },
    **base,
}

DATA_JSON = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>强积金制度总账户 · 30年演化仪表盘（2026–2056）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{
  --navy:#1a3a5c; --navy-2:#244a73; --gold:#c9a227; --gold-soft:#e8d48a;
  --bg:#f5f6f8; --card:#ffffff; --text:#1e293b; --muted:#64748b; --line:#e2e8f0;
  --green:#2f9e7a; --coral:#d4655a; --cyan:#3b82a0;
  --font:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
}
*{box-sizing:border-box}
body{margin:0;font-family:var(--font);background:var(--bg);color:var(--text);min-width:1024px}
.wrap{max-width:1280px;margin:0 auto;padding:20px 20px 48px}
header.hero{
  background:linear-gradient(135deg,var(--navy),var(--navy-2));
  color:#fff;border-radius:16px;padding:22px 26px;box-shadow:0 10px 30px rgba(26,58,92,.18);
}
.eyebrow{color:var(--gold-soft);font-size:12px;letter-spacing:.14em;font-weight:600}
h1{margin:8px 0 0;font-size:1.65rem;font-weight:700}
.sub{margin:8px 0 0;opacity:.88;font-size:.92rem;line-height:1.55;max-width:85ch}
details.note{margin-top:14px;background:rgba(255,255,255,.08);border-radius:10px;padding:0}
details.note summary{cursor:pointer;padding:12px 14px;color:var(--gold-soft);font-weight:600;list-style:none}
details.note .body{padding:0 14px 14px;font-size:.86rem;line-height:1.65;opacity:.92}
details.note code{color:var(--gold-soft)}
.controls{margin-top:16px;display:grid;grid-template-columns:1.15fr 1fr;gap:14px}
.card{background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:0 4px 16px rgba(26,58,92,.06);border:1px solid var(--line)}
.card h2{margin:0 0 12px;font-size:.95rem;color:var(--navy)}
.btns{display:flex;flex-wrap:wrap;gap:8px}
.btns button{
  border:1px solid var(--line);background:#fff;color:var(--navy);padding:8px 14px;border-radius:999px;
  cursor:pointer;font:inherit;font-size:.88rem;
}
.btns button.active{background:var(--navy);color:#fff;border-color:var(--navy)}
.btns.gold button.active{background:var(--gold);border-color:var(--gold);color:#1a1405}
.sliders{display:grid;gap:10px}
.slider-row{display:grid;grid-template-columns:110px 1fr 70px;gap:10px;align-items:center}
.slider-row label{font-size:.84rem;color:var(--muted)}
.slider-row output{text-align:right;font-size:.84rem;color:var(--navy);font-weight:600;font-variant-numeric:tabular-nums}
input[type=range]{width:100%;accent-color:var(--gold)}
.year-row{display:grid;grid-template-columns:90px 1fr 64px;gap:10px;align-items:center;margin-top:12px}
.year-val{font-size:1.25rem;font-weight:700;color:var(--gold);text-align:right}
.kpis{margin-top:14px;display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.kpi{background:var(--card);border-radius:14px;padding:14px 16px;border:1px solid var(--line);box-shadow:0 4px 14px rgba(26,58,92,.05)}
.kpi .l{font-size:.72rem;color:var(--muted);letter-spacing:.04em}
.kpi .v{margin-top:6px;font-size:1.15rem;font-weight:700;color:var(--navy);font-variant-numeric:tabular-nums}
.kpi .v.gold{color:var(--gold)}
.kpi .h{margin-top:4px;font-size:.72rem;color:var(--muted)}
.grid{margin-top:14px;display:grid;grid-template-columns:1.15fr .85fr;gap:14px}
.mod{background:var(--card);border-radius:14px;padding:14px 16px;border:1px solid var(--line);box-shadow:0 4px 16px rgba(26,58,92,.05);min-height:380px;display:flex;flex-direction:column}
.mod.wide{grid-column:1/-1}
.mod h3{margin:0;font-size:1rem;color:var(--navy)}
.mod .desc{margin:6px 0 10px;font-size:.8rem;color:var(--muted);line-height:1.5}
.chart{flex:1;min-height:300px;position:relative}
.chart canvas{max-height:340px}
#sankey,#waterfall{min-height:320px}
footer{margin-top:22px;padding:16px 4px;color:var(--muted);font-size:.78rem;line-height:1.65;border-top:1px solid var(--line)}
footer strong{color:var(--navy)}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="eyebrow">MPF SYSTEM ACCOUNT · 30Y PROJECTION</div>
    <h1>强积金制度总账户 · 30年演化仪表盘</h1>
    <p class="sub">整合人口层、缴费层、领取层与资产演化（2026–2056）。拖动参数滑块将即时重算资产路径与图表；单位：金额亿港元、人数万人。</p>
    <details class="note">
      <summary>模型说明（假设、恒等式与数据来源）</summary>
      <div class="body">
        <p><strong>核心恒等式</strong>：<code>A<sub>t+1</sub> = A<sub>t</sub>×(1+r) + C<sub>t</sub> − W<sub>t</sub></code>（期初资产先计息，再加减当年流量）。</p>
        <ul>
          <li>缴费人数 ≈ 劳动年龄人口 × LFPR × 就业率 × 覆盖率；强制含有关入息 7,100–30,000 规则。</li>
          <li>达龄提取人数 ≈ (60–64)/5，并按退休年龄滑块平移；一笔过主导，默认提取比例 100%[假设]。</li>
          <li>其他提取 ≈ 总提取的 12%[假设]；自愿约占总额 25.5%。</li>
          <li>初值 A<sub>2026</sub>=16,700 亿；账户约 1,100 万。滑块为敏感性覆写，非蒙特卡洛。</li>
        </ul>
        <p>数据来源：积金局公开量级锚点；政府统计处人口/死亡率/劳动参与率相关表；本仓库 Prompt 1-1～1-3 模型产出。</p>
      </div>
    </details>
  </header>

  <section class="controls">
    <div class="card">
      <h2>情景切换</h2>
      <div class="btns gold" id="presetBtns">
        <button type="button" data-p="保守">保守</button>
        <button type="button" data-p="基准" class="active">基准</button>
        <button type="button" data-p="乐观">乐观</button>
      </div>
      <div class="year-row">
        <label for="yearSlider">时间轴（桑基/瀑布）</label>
        <input type="range" id="yearSlider" min="2026" max="2056" value="2026"/>
        <div class="year-val" id="yearLab">2026</div>
      </div>
    </div>
    <div class="card">
      <h2>参数滑块（实时重算）</h2>
      <div class="sliders">
        <div class="slider-row"><label>投资回报率</label><input type="range" id="rSlider" min="2" max="8" step="0.1" value="4.9"/><output id="rOut">4.9%</output></div>
        <div class="slider-row"><label>退休年龄</label><input type="range" id="ageSlider" min="60" max="70" step="1" value="65"/><output id="ageOut">65岁</output></div>
        <div class="slider-row"><label>提取比例</label><input type="range" id="wdSlider" min="50" max="100" step="5" value="100"/><output id="wdOut">100%</output></div>
        <div class="slider-row"><label>强积金覆盖率</label><input type="range" id="covSlider" min="75" max="95" step="1" value="85"/><output id="covOut">85%</output></div>
        <div class="slider-row"><label>入息增长率</label><input type="range" id="wgSlider" min="1" max="5" step="0.5" value="3"/><output id="wgOut">3.0%</output></div>
      </div>
    </div>
  </section>

  <section class="kpis">
    <div class="kpi"><div class="l">当前总资产（选中年末）</div><div class="v gold" id="kA">—</div><div class="h" id="kAh">—</div></div>
    <div class="kpi"><div class="l">资产峰值年份 / 金额</div><div class="v" id="kPeak">—</div><div class="h">期末&lt;期初的首年</div></div>
    <div class="kpi"><div class="l">净流出拐点（提取&gt;供款）</div><div class="v" id="kCf">—</div><div class="h">不含投资回报</div></div>
    <div class="kpi"><div class="l">30年累计供款 / 提取</div><div class="v" id="kCum">—</div><div class="h">当前滑块路径</div></div>
    <div class="kpi"><div class="l">资产耗尽年份</div><div class="v" id="kDep">—</div><div class="h">期末资产≤0</div></div>
  </section>

  <section class="grid">
    <div class="mod">
      <h3>模块1 · 资金流向桑基图</h3>
      <p class="desc">这张图在说什么：选定年份里，强制/自愿供款与投资收益如何流入总资产池，再流向退休提取、其他提取与年末留存。</p>
      <div class="chart" id="sankey"></div>
    </div>
    <div class="mod">
      <h3>模块5旁挂 · 当年收支瀑布</h3>
      <p class="desc">这张图在说什么：从期初资产出发，依次叠加投资损益、总供款，扣除总提取，得到期末资产。</p>
      <div class="chart" id="waterfall"></div>
    </div>

    <div class="mod wide">
      <h3>模块2 · 总资产演化（三情景对照 + 当前覆写）</h3>
      <p class="desc">这张图在说什么：保守/基准/乐观预设路径（虚线）与当前滑块重算路径（实线）；标注峰值与净流出拐点。</p>
      <div class="chart"><canvas id="chartAsset"></canvas></div>
    </div>

    <div class="mod wide">
      <h3>模块3 · 年度收支构成（正负堆叠）</h3>
      <p class="desc">这张图在说什么：上方为钱进（强制、自愿、投资回报），下方为钱出（退休提取、其他提取），看每年进出是否平衡。</p>
      <div class="chart"><canvas id="chartStack"></canvas></div>
    </div>

    <div class="mod wide">
      <h3>模块4 · 领取人数趋势</h3>
      <p class="desc">这张图在说什么：每年新进入领取的人数（万人）；可切换男/女/混合。受退休年龄滑块影响。</p>
      <div class="btns" id="sexBtns" style="margin-bottom:8px">
        <button type="button" data-s="混合" class="active">混合</button>
        <button type="button" data-s="男">男</button>
        <button type="button" data-s="女">女</button>
      </div>
      <div class="chart"><canvas id="chartRetire"></canvas></div>
    </div>
  </section>

  <footer>
    <strong>数据来源</strong>：强制性公积金计划管理局（积金局）公开资产/供款/提取量级；
    政府统计处人口推算、年龄性别死亡率、劳动参与率相关统计；
    本页计算基于项目内 Prompt 1-1 人口层、1-2 缴费层、1-3 领取与资产层 CSV。
    研究/教学用途，非官方精算结论。有关入息上下限 <code>7,100 / 30,000</code> 可在源码 META 中替换。
  </footer>
</div>

<script>
window.MPF = __DATA__;
</script>
<script>
(function () {
  const DATA = window.MPF;
  const META = DATA.meta;
  const YEARS = DATA.years;

  const state = {
    preset: "基准",
    sc: "中",
    year: 2026,
    sex: "混合",
    r: META.r_default,              // 小数
    retireAge: META.retire_age_default,
    withdraw: META.withdraw_ratio_default,
    coverage: META.coverage_default,
    wageG: META.wage_g_default,
  };

  let sim = null;
  let chartAsset = null, chartStack = null, chartRetire = null;
  let sankey = null, waterfall = null;

  /** 覆盖率相对默认的倍率 */
  function covScale() { return state.coverage / META.coverage_default; }

  /**
   * 入息增长偏离：对第 t 年供款乘以 ((1+g)/(1+g0))^(t-2026)
   * 同时覆盖率线性缩放人数与供款。
   */
  function scaleContrib(baseYi, yearIdx) {
    const g0 = META.wage_g_default;
    const ratio = Math.pow((1 + state.wageG) / (1 + g0), yearIdx);
    return baseYi * covScale() * ratio;
  }

  /** 退休年龄偏离 65：每提早1岁领取人数 +8%，延后 -6%（近似） */
  function ageScale() {
    const d = state.retireAge - 65;
    if (d <= 0) return 1 - d * 0.08;
    return Math.max(0.55, 1 - d * 0.06);
  }

  /**
   * 核心重算：输入当前 state → 输出全路径数组
   * 可替换为真实业务引擎，只要返回同样字段。
   */
  function computeModel(scCode) {
    const sc = DATA.scenarios[scCode];
    const r = state.r;
    const otherShare = META.other_share;
    let A = META.A0;
    const out = {
      A0: [], A1: [], C: [], Cf: [], Cv: [], W: [], Wr: [], Wo: [],
      inv: [], net: [], econ: [], n65: [], n65_m: [], n65_f: [],
    };

    for (let i = 0; i < YEARS.length; i++) {
      const forced = scaleContrib(sc.forced[i], i);
      const vol = scaleContrib(sc.vol[i], i);
      const C = forced + vol;

      const accounts = META.accounts0 * Math.pow(1 + META.accounts_g, i);
      const balWan = (A / accounts) * META.retiree_bal_factor; // 万港元
      const n65mix = (sc.n65_mix[i] * ageScale()); // 万人
      const n65m = sc.n65_m[i] * ageScale();
      const n65f = sc.n65_f[i] * ageScale();
      const Wr = n65mix * balWan * state.withdraw; // 万人×万港元=亿
      const W = Wr / (1 - otherShare);
      const Wo = W - Wr;

      const inv = A * r;
      const A1 = Math.max(0, A * (1 + r) + C - W);

      out.A0.push(+A.toFixed(4));
      out.A1.push(+A1.toFixed(4));
      out.C.push(+C.toFixed(4));
      out.Cf.push(+forced.toFixed(4));
      out.Cv.push(+vol.toFixed(4));
      out.W.push(+W.toFixed(4));
      out.Wr.push(+Wr.toFixed(4));
      out.Wo.push(+Wo.toFixed(4));
      out.inv.push(+inv.toFixed(4));
      out.net.push(+(C - W).toFixed(4));
      out.econ.push(+(C - W + inv).toFixed(4));
      out.n65.push(+n65mix.toFixed(4));
      out.n65_m.push(+n65m.toFixed(4));
      out.n65_f.push(+n65f.toFixed(4));

      A = A1;
    }
    return out;
  }

  function detectInflections(path) {
    let peakYear = null, peakA = null, cfYear = null, depYear = null;
    for (let i = 0; i < YEARS.length; i++) {
      if (path.A1[i] < path.A0[i] && peakYear == null) {
        peakYear = YEARS[i];
        peakA = path.A0[i];
      }
      if (path.net[i] < 0 && cfYear == null) cfYear = YEARS[i];
      if (path.A1[i] <= 0 && depYear == null) depYear = YEARS[i];
    }
    const cumC = path.C.reduce((a, b) => a + b, 0);
    const cumW = path.W.reduce((a, b) => a + b, 0);
    return { peakYear, peakA, cfYear, depYear, cumC, cumW };
  }

  function fmtYi(n) {
    if (n == null || isNaN(n)) return "—";
    if (Math.abs(n) >= 1000) return (n / 1000).toFixed(2) + " 千亿";
    return (+n).toFixed(1) + " 亿";
  }

  function yearIndex(y) { return y - 2026; }

  function updateKpis() {
    const i = yearIndex(state.year);
    const inf = detectInflections(sim);
    document.getElementById("kA").textContent = fmtYi(sim.A1[i]);
    document.getElementById("kAh").textContent = state.year + " 年末 · " + state.preset;
    document.getElementById("kPeak").textContent =
      inf.peakYear == null ? "不适用" : (inf.peakYear + " / " + fmtYi(inf.peakA));
    document.getElementById("kCf").textContent = inf.cfYear == null ? "不适用" : String(inf.cfYear);
    document.getElementById("kCum").textContent = fmtYi(inf.cumC) + " / " + fmtYi(inf.cumW);
    document.getElementById("kDep").textContent = inf.depYear == null ? "不适用" : String(inf.depYear);
  }

  // —— ECharts 桑基 ——
  function renderSankey() {
    const i = yearIndex(state.year);
    const nodes = [
      { name: "强制性供款" }, { name: "自愿性供款" }, { name: "投资收益" },
      { name: "强积金总资产池" },
      { name: "退休提取" }, { name: "其他提取" }, { name: "年末资产留存" },
    ];
    const links = [
      { source: "强制性供款", target: "强积金总资产池", value: Math.max(sim.Cf[i], 0.01) },
      { source: "自愿性供款", target: "强积金总资产池", value: Math.max(sim.Cv[i], 0.01) },
      { source: "投资收益", target: "强积金总资产池", value: Math.max(sim.inv[i], 0.01) },
      // 期初也并入池以便守恒观感：用期初作为隐含，桑基右侧留存=期末
      { source: "强积金总资产池", target: "退休提取", value: Math.max(sim.Wr[i], 0.01) },
      { source: "强积金总资产池", target: "其他提取", value: Math.max(sim.Wo[i], 0.01) },
      { source: "强积金总资产池", target: "年末资产留存", value: Math.max(sim.A1[i], 0.01) },
    ];
    // 为守恒：左侧再加期初资产节点
    nodes.unshift({ name: "期初资产" });
    links.unshift({ source: "期初资产", target: "强积金总资产池", value: Math.max(sim.A0[i], 0.01) });

    sankey.setOption({
      tooltip: {
        trigger: "item",
        formatter: (p) => {
          if (p.dataType === "edge") {
            return p.data.source + " → " + p.data.target + "<br/><b>" + (+p.data.value).toFixed(1) + "</b> 亿港元";
          }
          return p.name;
        },
      },
      series: [{
        type: "sankey",
        emphasis: { focus: "adjacency" },
        lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.4 },
        label: { color: varNavy(), fontSize: 12 },
        data: nodes,
        links: links,
        nodeAlign: "justify",
      }],
    }, true);
  }

  function varNavy() { return "#1a3a5c"; }

  // —— ECharts 瀑布 ——
  function renderWaterfall() {
    const i = yearIndex(state.year);
    const steps = [
      { name: "期初资产", v: sim.A0[i] },
      { name: "投资损益", v: sim.inv[i] },
      { name: "总供款", v: sim.C[i] },
      { name: "总提取", v: -sim.W[i] },
      { name: "期末资产", v: sim.A1[i] },
    ];
    let run = 0;
    const help = [], disp = [], colors = [];
    steps.forEach((s, idx) => {
      if (idx === 0 || idx === steps.length - 1) {
        help.push(0); disp.push(s.v);
        colors.push(idx === 0 ? "#3b82a0" : "#c9a227");
        run = s.v;
      } else if (s.v >= 0) {
        help.push(run); disp.push(s.v); colors.push("#2f9e7a"); run += s.v;
      } else {
        help.push(run + s.v); disp.push(-s.v); colors.push("#d4655a"); run += s.v;
      }
    });
    waterfall.setOption({
      tooltip: {
        trigger: "axis",
        formatter: (ps) => {
          const idx = ps[0].dataIndex;
          return steps[idx].name + "<br/><b>" + (+steps[idx].v).toFixed(1) + "</b> 亿港元";
        },
      },
      grid: { left: 56, right: 16, top: 24, bottom: 48 },
      xAxis: { type: "category", data: steps.map((s) => s.name), axisLabel: { color: "#64748b", fontSize: 11, rotate: 15 } },
      yAxis: { type: "value", axisLabel: { color: "#64748b" }, splitLine: { lineStyle: { color: "#e2e8f0" } } },
      series: [
        { type: "bar", stack: "wf", data: help, itemStyle: { color: "transparent" }, silent: true },
        {
          type: "bar", stack: "wf", barWidth: "48%",
          data: disp.map((v, idx) => ({ value: v, itemStyle: { color: colors[idx], borderRadius: [4, 4, 0, 0] } })),
        },
      ],
    }, true);
  }

  // —— Chart.js 资产折线 ——
  function buildAssetChart() {
    const ctx = document.getElementById("chartAsset");
    const inf = detectInflections(sim);
    const presetPaths = ["低", "中", "高"].map((code) => {
      // 用该情景默认参数快速算一条对照（固定默认滑块）
      return DATA.scenarios[code];
    });

    // 对照路径：用各情景默认 r 与原始供款（不覆盖率冲击）预计算一次缓存
    const cache = {};
    ["低", "中", "高"].forEach((code) => {
      const saved = { ...state };
      const p = DATA.presets[{ 低: "保守", 中: "基准", 高: "乐观" }[code]];
      state.r = p.r / 100; state.coverage = p.coverage / 100; state.wageG = p.wageG / 100;
      state.retireAge = p.retireAge; state.withdraw = p.withdraw / 100;
      cache[code] = computeModel(code);
      Object.assign(state, saved);
    });
    window._presetCache = cache;

    chartAsset = new Chart(ctx, {
      type: "line",
      data: {
        labels: YEARS,
        datasets: [
          { label: "保守（预设）", data: cache["低"].A1, borderColor: "#d4655a", borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, tension: 0.25 },
          { label: "基准（预设）", data: cache["中"].A1, borderColor: "#3b82a0", borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, tension: 0.25 },
          { label: "乐观（预设）", data: cache["高"].A1, borderColor: "#2f9e7a", borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, tension: 0.25 },
          { label: "当前覆写", data: sim.A1, borderColor: "#c9a227", borderWidth: 3, pointRadius: 0, tension: 0.25,
            backgroundColor: "rgba(201,162,39,.12)", fill: true },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#1a3a5c" } },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtYi(c.parsed.y) } },
          annotation: undefined,
        },
        scales: {
          x: { ticks: { color: "#64748b", maxTicksLimit: 12 }, grid: { color: "#eef2f6" } },
          y: { ticks: { color: "#64748b", callback: (v) => (v >= 1000 ? (v / 1000) + "k" : v) }, grid: { color: "#eef2f6" } },
        },
      },
    });
  }

  function updateAssetChart() {
    chartAsset.data.datasets[3].data = sim.A1;
    // 峰值/拐点用 point 标注在当前线上
    const inf = detectInflections(sim);
    chartAsset.data.datasets[3].pointRadius = YEARS.map((y) =>
      (y === inf.peakYear || y === inf.cfYear) ? 4 : 0
    );
    chartAsset.data.datasets[3].pointBackgroundColor = YEARS.map((y) =>
      y === inf.peakYear ? "#1a3a5c" : (y === inf.cfYear ? "#d4655a" : "#c9a227")
    );
    chartAsset.update();
  }

  // —— Chart.js 堆叠面积（正负） ——
  function buildStackChart() {
    const ctx = document.getElementById("chartStack");
    chartStack = new Chart(ctx, {
      type: "line",
      data: {
        labels: YEARS,
        datasets: [
          { label: "强制性供款", data: sim.Cf, borderColor: "#c9a227", backgroundColor: "rgba(201,162,39,.55)", fill: true, stack: "in", pointRadius: 0, tension: 0.25, borderWidth: 1 },
          { label: "自愿性供款", data: sim.Cv, borderColor: "#3b82a0", backgroundColor: "rgba(59,130,160,.45)", fill: true, stack: "in", pointRadius: 0, tension: 0.25, borderWidth: 1 },
          { label: "投资回报", data: sim.inv, borderColor: "#2f9e7a", backgroundColor: "rgba(47,158,122,.4)", fill: true, stack: "in", pointRadius: 0, tension: 0.25, borderWidth: 1 },
          { label: "退休提取", data: sim.Wr.map((v) => -v), borderColor: "#d4655a", backgroundColor: "rgba(212,101,90,.45)", fill: true, stack: "out", pointRadius: 0, tension: 0.25, borderWidth: 1 },
          { label: "其他提取", data: sim.Wo.map((v) => -v), borderColor: "#64748b", backgroundColor: "rgba(100,116,139,.35)", fill: true, stack: "out", pointRadius: 0, tension: 0.25, borderWidth: 1 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#1a3a5c", boxWidth: 12 } },
          tooltip: { callbacks: { label: (c) => c.dataset.label + ": " + fmtYi(Math.abs(c.parsed.y)) } },
        },
        scales: {
          x: { ticks: { color: "#64748b", maxTicksLimit: 12 }, grid: { display: false } },
          y: { stacked: true, ticks: { color: "#64748b" },
            grid: { color: "#eef2f6" }, title: { display: true, text: "亿港元（上进下出）", color: "#64748b" } },
        },
      },
    });
  }

  function updateStackChart() {
    chartStack.data.datasets[0].data = sim.Cf;
    chartStack.data.datasets[1].data = sim.Cv;
    chartStack.data.datasets[2].data = sim.inv;
    chartStack.data.datasets[3].data = sim.Wr.map((v) => -v);
    chartStack.data.datasets[4].data = sim.Wo.map((v) => -v);
    chartStack.update();
  }

  // —— 领取人数 ——
  function n65Series() {
    if (state.sex === "男") return sim.n65_m;
    if (state.sex === "女") return sim.n65_f;
    return sim.n65;
  }

  function buildRetireChart() {
    const ctx = document.getElementById("chartRetire");
    chartRetire = new Chart(ctx, {
      type: "line",
      data: {
        labels: YEARS,
        datasets: [{
          label: "领取人数（万人）",
          data: n65Series(),
          borderColor: "#1a3a5c",
          backgroundColor: "rgba(26,58,92,.12)",
          fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2.5,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => (+c.parsed.y).toFixed(2) + " 万人" } },
        },
        scales: {
          x: { ticks: { color: "#64748b", maxTicksLimit: 12 }, grid: { color: "#eef2f6" } },
          y: { ticks: { color: "#64748b" }, grid: { color: "#eef2f6" }, title: { display: true, text: "万人", color: "#64748b" } },
        },
      },
    });
  }

  function updateRetireChart() {
    chartRetire.data.datasets[0].data = n65Series();
    chartRetire.update();
  }

  function refreshAll() {
    sim = computeModel(state.sc);
    updateKpis();
    renderSankey();
    renderWaterfall();
    if (chartAsset) updateAssetChart();
    if (chartStack) updateStackChart();
    if (chartRetire) updateRetireChart();
  }

  function applyPreset(name) {
    const p = DATA.presets[name];
    state.preset = name;
    state.sc = p.sc;
    state.r = p.r / 100;
    state.retireAge = p.retireAge;
    state.withdraw = p.withdraw / 100;
    state.coverage = p.coverage / 100;
    state.wageG = p.wageG / 100;

    document.getElementById("rSlider").value = p.r;
    document.getElementById("rOut").textContent = p.r.toFixed(1) + "%";
    document.getElementById("ageSlider").value = p.retireAge;
    document.getElementById("ageOut").textContent = p.retireAge + "岁";
    document.getElementById("wdSlider").value = p.withdraw;
    document.getElementById("wdOut").textContent = p.withdraw + "%";
    document.getElementById("covSlider").value = p.coverage;
    document.getElementById("covOut").textContent = p.coverage + "%";
    document.getElementById("wgSlider").value = p.wageG;
    document.getElementById("wgOut").textContent = p.wageG.toFixed(1) + "%";

    document.querySelectorAll("#presetBtns button").forEach((b) => {
      b.classList.toggle("active", b.dataset.p === name);
    });
    refreshAll();
  }

  function bind() {
    document.querySelectorAll("#presetBtns button").forEach((b) => {
      b.addEventListener("click", () => applyPreset(b.dataset.p));
    });
    document.querySelectorAll("#sexBtns button").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#sexBtns button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        state.sex = b.dataset.s;
        updateRetireChart();
      });
    });

    const yearSlider = document.getElementById("yearSlider");
    yearSlider.addEventListener("input", () => {
      state.year = +yearSlider.value;
      document.getElementById("yearLab").textContent = String(state.year);
      updateKpis();
      renderSankey();
      renderWaterfall();
    });

    const bindSlider = (id, outId, fmt, setter) => {
      const el = document.getElementById(id);
      const out = document.getElementById(outId);
      el.addEventListener("input", () => {
        out.textContent = fmt(+el.value);
        setter(+el.value);
        refreshAll();
      });
    };
    bindSlider("rSlider", "rOut", (v) => v.toFixed(1) + "%", (v) => { state.r = v / 100; });
    bindSlider("ageSlider", "ageOut", (v) => v + "岁", (v) => { state.retireAge = v; });
    bindSlider("wdSlider", "wdOut", (v) => v + "%", (v) => { state.withdraw = v / 100; });
    bindSlider("covSlider", "covOut", (v) => v + "%", (v) => { state.coverage = v / 100; });
    bindSlider("wgSlider", "wgOut", (v) => v.toFixed(1) + "%", (v) => { state.wageG = v / 100; });

    window.addEventListener("resize", () => {
      sankey && sankey.resize();
      waterfall && waterfall.resize();
    });
  }

  function init() {
    sankey = echarts.init(document.getElementById("sankey"));
    waterfall = echarts.init(document.getElementById("waterfall"));
    sim = computeModel(state.sc);
    buildAssetChart();
    buildStackChart();
    buildRetireChart();
    bind();
    applyPreset("基准");
  }

  init();
})();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JSON)
OUT.write_text(html, encoding="utf-8")
print("Wrote", OUT, "MB", round(OUT.stat().st_size / 1e6, 2))

# 注入模块8（对冲图）与模块9（设计思路面板）
import runpy

runpy.run_path(str(ROOT / "_patch_dashboard_p3_offset.py"), run_name="__main__")
