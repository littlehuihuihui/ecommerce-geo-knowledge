# -*- coding: utf-8 -*-
"""Generate single-file MPF 30y interactive dashboard HTML."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "_embed_data.json").read_text(encoding="utf-8"))
OUT = ROOT.parent / "mpf_30y_cashflow_dashboard.html"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>強積金制度總賬戶 · 30年現金流演化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
  :root {
    --navy-950: #070f1c;
    --navy-900: #0a1628;
    --navy-800: #0f2744;
    --navy-700: #163a5f;
    --navy-600: #1e4d7a;
    --gold-400: #e8c547;
    --gold-500: #c9a227;
    --gold-600: #a8841a;
    --slate-100: #e8eef6;
    --slate-300: #9bb0c9;
    --slate-400: #7a92ad;
    --card: rgba(15, 39, 68, 0.72);
    --stroke: rgba(201, 162, 39, 0.28);
    --ok: #3dba8a;
    --warn: #e0a45a;
    --danger: #d96b6b;
    --font: "Segoe UI", "PingFang TC", "Microsoft JhengHei", "Noto Sans TC", sans-serif;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    font-family: var(--font);
    color: var(--slate-100);
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(201,162,39,0.12), transparent 55%),
      radial-gradient(900px 500px at 90% 0%, rgba(30,77,122,0.35), transparent 50%),
      linear-gradient(180deg, var(--navy-950), var(--navy-900) 40%, #0b1a30);
    min-height: 100vh;
  }
  .wrap { max-width: 1280px; margin: 0 auto; padding: 20px 18px 48px; }
  header.hero {
    display: grid;
    gap: 8px;
    padding: 22px 22px 18px;
    border: 1px solid var(--stroke);
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(15,39,68,0.9), rgba(10,22,40,0.85));
    box-shadow: 0 12px 40px rgba(0,0,0,0.28);
  }
  .eyebrow {
    color: var(--gold-500);
    letter-spacing: 0.14em;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
  }
  h1 {
    margin: 0;
    font-size: clamp(1.35rem, 2.4vw, 1.85rem);
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  .subtitle { margin: 0; color: var(--slate-300); font-size: 0.95rem; line-height: 1.55; max-width: 72ch; }
  details.model-note {
    margin-top: 14px;
    border: 1px solid rgba(155,176,201,0.22);
    border-radius: 10px;
    background: rgba(7,15,28,0.45);
    overflow: hidden;
  }
  details.model-note summary {
    cursor: pointer;
    padding: 12px 14px;
    font-weight: 600;
    color: var(--gold-400);
    list-style: none;
  }
  details.model-note summary::-webkit-details-marker { display: none; }
  details.model-note summary::after { content: " ▾"; color: var(--slate-400); }
  details.model-note[open] summary::after { content: " ▴"; }
  .note-body { padding: 0 14px 14px; color: var(--slate-300); font-size: 0.9rem; line-height: 1.65; }
  .note-body ul { margin: 8px 0 0; padding-left: 1.2em; }
  .note-body code { color: var(--gold-400); font-size: 0.85em; }

  .controls {
    margin-top: 16px;
    display: grid;
    grid-template-columns: 1.1fr 1.4fr;
    gap: 12px;
  }
  @media (max-width: 900px) { .controls { grid-template-columns: 1fr; } }
  .panel {
    border: 1px solid rgba(155,176,201,0.18);
    border-radius: 12px;
    background: var(--card);
    backdrop-filter: blur(8px);
    padding: 14px 16px;
  }
  .panel h2 {
    margin: 0 0 10px;
    font-size: 0.92rem;
    color: var(--gold-400);
    font-weight: 650;
    letter-spacing: 0.04em;
  }
  .scenario-btns { display: flex; flex-wrap: wrap; gap: 8px; }
  .scenario-btns button {
    border: 1px solid rgba(155,176,201,0.35);
    background: transparent;
    color: var(--slate-100);
    padding: 8px 14px;
    border-radius: 999px;
    cursor: pointer;
    font: inherit;
    transition: 0.15s ease;
  }
  .scenario-btns button:hover { border-color: var(--gold-500); color: var(--gold-400); }
  .scenario-btns button.active {
    background: linear-gradient(135deg, var(--gold-500), var(--gold-600));
    border-color: transparent;
    color: #1a1405;
    font-weight: 700;
  }
  .sliders { display: grid; gap: 12px; }
  .slider-row { display: grid; grid-template-columns: 110px 1fr 64px; align-items: center; gap: 10px; }
  .slider-row label { font-size: 0.86rem; color: var(--slate-300); }
  .slider-row output { text-align: right; color: var(--gold-400); font-variant-numeric: tabular-nums; font-size: 0.86rem; }
  input[type=range] {
    width: 100%;
    accent-color: var(--gold-500);
    height: 4px;
  }
  .year-bar {
    margin-top: 12px;
    display: grid;
    grid-template-columns: 90px 1fr 70px;
    gap: 10px;
    align-items: center;
  }
  .year-bar .year-val {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--gold-400);
    text-align: right;
  }

  .kpis {
    margin-top: 14px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  @media (max-width: 980px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
  .kpi {
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid rgba(201,162,39,0.22);
    background: linear-gradient(160deg, rgba(22,58,95,0.55), rgba(10,22,40,0.8));
  }
  .kpi .label { font-size: 0.78rem; color: var(--slate-400); letter-spacing: 0.06em; }
  .kpi .value {
    margin-top: 6px;
    font-size: clamp(1.15rem, 2vw, 1.45rem);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: #fff;
  }
  .kpi .hint { margin-top: 4px; font-size: 0.75rem; color: var(--slate-400); }
  .kpi.accent .value { color: var(--gold-400); }

  .grid {
    margin-top: 14px;
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 12px;
  }
  @media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }
  .chart-card {
    border: 1px solid rgba(155,176,201,0.18);
    border-radius: 12px;
    background: var(--card);
    padding: 12px 12px 8px;
    min-height: 360px;
    display: flex;
    flex-direction: column;
  }
  .chart-card.wide { grid-column: 1 / -1; }
  .chart-head { padding: 4px 6px 8px; }
  .chart-head h3 { margin: 0; font-size: 0.98rem; font-weight: 650; }
  .chart-head p { margin: 6px 0 0; font-size: 0.8rem; color: var(--slate-400); line-height: 1.5; }
  .chart { flex: 1; min-height: 300px; width: 100%; }
  .chart.tall { min-height: 340px; }

  footer.sources {
    margin-top: 22px;
    padding: 16px 18px;
    border-top: 1px solid rgba(155,176,201,0.2);
    color: var(--slate-400);
    font-size: 0.8rem;
    line-height: 1.65;
  }
  footer.sources strong { color: var(--slate-300); }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid rgba(201,162,39,0.35);
    color: var(--gold-400);
    font-size: 0.72rem;
    margin-left: 6px;
    vertical-align: middle;
  }
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="eyebrow">MPF System Projection · Research Dashboard</div>
    <h1>強積金制度總賬戶 · 30年現金流演化 <span class="badge">Prompt 1-3 輸出</span></h1>
    <p class="subtitle">
      基於 Prompt 1-1 數據集與 Prompt 1-2 模型框架，展示 2026–2056 制度總資產、供款流入、提取流出與投資回報的路徑演進。
      金額單位：<strong>億港元</strong>。本頁為研究／教學可視化，非積金局官方精算。
    </p>
    <details class="model-note">
      <summary>模型說明（假設與局限）</summary>
      <div class="note-body">
        <p><strong>核心恆等式</strong>：
          <code>A<sub>t+1</sub> = A<sub>t</sub>·(1+r<sub>t</sub>) + C<sub>t</sub> − W<sub>t</sub> − E<sub>t</sub></code>
          （期初存量先計息，再加減當年流量）。
        </p>
        <ul>
          <li>初值資產 A<sub>2026</sub> = 16,700 億港元（真實錨點）；三情景共用初值。</li>
          <li>有關入息上下限 7,100 / 30,000；低於下限僱員免供、僱主仍繳；自僱單邊 5%。</li>
          <li>提取含達齡（簡化為 65 歲）與提前取款（永久離港等強度 λ 代理）。</li>
          <li>回報為股票／混合／DIS 核心／保守四類加權淨回報，含老齡化配置滑移。</li>
          <li><strong>本頁滑塊</strong>為敏感性覆寫：在選中情景路徑上調整回報、供款倍率與退休年齡對提取的近似影響，並即時重算資產軌跡；非重新抽樣蒙特卡洛。</li>
          <li>局限：無完整入息分佈、提取行為粗粒度、確定性情景無置信區間。</li>
        </ul>
      </div>
    </details>
  </header>

  <section class="controls">
    <div class="panel">
      <h2>情景切換</h2>
      <div class="scenario-btns" id="scenarioBtns">
        <button type="button" data-s="基准" class="active">基准</button>
        <button type="button" data-s="乐观">乐观</button>
        <button type="button" data-s="悲观">悲观</button>
      </div>
      <div class="year-bar">
        <label for="yearSlider">時間軸</label>
        <input type="range" id="yearSlider" min="2026" max="2055" step="1" value="2026" />
        <div class="year-val" id="yearLabel">2026</div>
      </div>
    </div>
    <div class="panel">
      <h2>參數滑塊（敏感性）</h2>
      <div class="sliders">
        <div class="slider-row">
          <label for="retSlider">投資回報率</label>
          <input type="range" id="retSlider" min="0" max="10" step="0.1" value="4.6" />
          <output id="retOut">4.6%</output>
        </div>
        <div class="slider-row">
          <label for="contribSlider">供款率（合計）</label>
          <input type="range" id="contribSlider" min="5" max="15" step="0.5" value="10" />
          <output id="contribOut">10%</output>
        </div>
        <div class="slider-row">
          <label for="retireSlider">退休年齡</label>
          <input type="range" id="retireSlider" min="60" max="70" step="1" value="65" />
          <output id="retireOut">65歲</output>
        </div>
      </div>
    </div>
  </section>

  <section class="kpis" id="kpiRow">
    <div class="kpi accent"><div class="label">當前總資產（期末）</div><div class="value" id="kpiAum">—</div><div class="hint" id="kpiAumHint">選定年份</div></div>
    <div class="kpi"><div class="label">預計拐點年份</div><div class="value" id="kpiInflect">—</div><div class="hint">資產開始下降的首年</div></div>
    <div class="kpi"><div class="label">累計淨現金流</div><div class="value" id="kpiNet">—</div><div class="hint">供款 − 提取 − 費用（至選定年）</div></div>
    <div class="kpi"><div class="label">資產耗盡年份</div><div class="value" id="kpiDeplete">—</div><div class="hint">期末資產 ≤ 0 的首年</div></div>
  </section>

  <section class="grid">
    <div class="chart-card wide">
      <div class="chart-head">
        <h3>總資產 30 年演化（三情景對比）</h3>
        <p>這張圖在說什麼：在悲觀／基準／樂觀路徑下，制度總資產如何從 2026 走到 2056。實線為當前情景（含滑塊覆寫），虛線為其餘情景原始路徑。</p>
      </div>
      <div class="chart tall" id="chartLine"></div>
    </div>

    <div class="chart-card">
      <div class="chart-head">
        <h3>資金流向桑基圖</h3>
        <p>這張圖在說什麼：把選定年份的供款分項流入資產池，再流向達齡提取、提前取款、費用，並標示投資回報對資產池的貢獻。</p>
      </div>
      <div class="chart" id="chartSankey"></div>
    </div>

    <div class="chart-card">
      <div class="chart-head">
        <h3>瀑布圖 · 當年收支結構</h3>
        <p>這張圖在說什麼：從期初資產出發，依次疊加投資損益、供款、扣除提取與費用，得到期末資產——單年「從哪裡來到哪裡去」。</p>
      </div>
      <div class="chart" id="chartWaterfall"></div>
    </div>

    <div class="chart-card wide">
      <div class="chart-head">
        <h3>堆疊面積圖 · 年度流量構成</h3>
        <p>這張圖在說什麼：每年流入（供款、投資回報）與流出（提取、費用）的相對體量如何隨時間變化；面積越大表示該項對當年流量的貢獻越高。</p>
      </div>
      <div class="chart tall" id="chartArea"></div>
    </div>
  </section>

  <footer class="sources">
    <strong>數據來源</strong>：
    Prompt 1-1 基礎數據集（<code>01_core_parameters.csv</code> … <code>05_withdrawal_behavior.csv</code>）→
    Prompt 1-2 模型框架 →
    Prompt 1-3 Python 引擎輸出（<code>cashflow_model/output/*.csv</code>）。
    公開錨點：強積金總資產約 1.67 萬億港元（2026 情景初值）；有關入息與供款比例依據強積金條例。
    情景參數與強度 λ、自願供款 κ、行政費率 φ 等為研究假設，見同目錄 <code>10_cashflow_model_framework.md</code>。
    隨機種子 42；圖表庫 ECharts 5。單位除另註外均為億港元。
  </footer>
</div>

<script>
window.MPF_DATA = __MPF_DATA__;

(function () {
  const DATA = window.MPF_DATA;
  const COLORS = {
    gold: '#c9a227',
    goldLite: '#e8c547',
    navy: '#6fa8d8',
    green: '#3dba8a',
    coral: '#d96b6b',
    purple: '#9b8cff',
    slate: '#9bb0c9',
    white: '#e8eef6',
  };

  const state = {
    scenario: '基准',
    year: 2026,
    retPct: 4.6,       // 覆寫年化回報 %
    contribPct: 10,    // 合計供款率 %（基準 10）
    retireAge: 65,
  };

  const charts = {};

  function rowsOf(label) {
    return DATA.annual
      .filter(r => r['情景标签'] === label)
      .sort((a, b) => a['年份'] - b['年份']);
  }

  function fmt(n, d = 1) {
    if (n == null || Number.isNaN(n)) return '—';
    const abs = Math.abs(n);
    const s = abs >= 1000 ? n.toLocaleString('zh-HK', { maximumFractionDigits: d })
      : n.toLocaleString('zh-HK', { maximumFractionDigits: d });
    return s;
  }

  function contribScale() {
    return state.contribPct / 10;
  }

  /** 退休年齡相對 65：每提早 1 歲，達齡提取約 +8%；每延後 1 歲約 −6%（近似） */
  function withdrawScale() {
    const d = state.retireAge - 65;
    if (d <= 0) return 1 - d * 0.08;
    return Math.max(0.55, 1 - d * 0.06);
  }

  /**
   * 在選中情景原始路徑上，用滑塊覆寫回報／供款／提取，重算資產軌跡。
   * 回報：用固定 retPct 替代原加權 r_t（敏感性模式）。
   */
  function recomputePath(label) {
    const base = rowsOf(label);
    const r = state.retPct / 100;
    const cs = contribScale();
    const ws = withdrawScale();
    let a = DATA.meta.aum0;
    const out = [];
    for (const row of base) {
      const C = row['总供款_亿港元'] * cs;
      const W = row['总提取_亿港元'] * ws;
      const E = row['费用_亿港元']; // 隨原路徑費用率×期初，略保持比例：用 φ≈E/期初
      const phi = row['总资产_期初_亿港元'] > 0 ? row['费用_亿港元'] / row['总资产_期初_亿港元'] : 0.002;
      const e = phi * a;
      const inv = a * r;
      const aNext = Math.max(0, a * (1 + r) + C - W - e);
      const scaleC = cs;
      out.push({
        ...row,
        _A0: a,
        _r: r,
        _C: C,
        _W: W,
        _E: e,
        _inv: inv,
        _net: C - W - e,
        _A1: aNext,
        _C_ee: (row['其中_雇员强制'] || 0) * scaleC,
        _C_er: (row['其中_雇主强制'] || 0) * scaleC,
        _C_se: (row['其中_自雇强制'] || 0) * scaleC,
        _C_vol: (row['其中_自愿供款'] || 0) * scaleC,
        _W65: (row['其中_达龄提取'] || 0) * ws,
        _Wearly: (row['其中_提前提取'] || 0) * ws,
      });
      a = aNext;
    }
    return out;
  }

  function findYear(path, year) {
    return path.find(r => r['年份'] === year) || path[0];
  }

  function detectInflection(path) {
    for (const r of path) {
      if (r._A1 < r._A0) return r['年份'];
    }
    return null;
  }

  function detectDepletion(path) {
    for (const r of path) {
      if (r._A1 <= 0) return r['年份'];
    }
    return null;
  }

  function updateKpis(path) {
    const row = findYear(path, state.year);
    const cumNet = path.filter(r => r['年份'] <= state.year).reduce((s, r) => s + r._net, 0);
    const inf = detectInflection(path);
    const dep = detectDepletion(path);
    document.getElementById('kpiAum').textContent = fmt(row._A1, 1) + ' 億';
    document.getElementById('kpiAumHint').textContent = state.year + ' 年末 · ' + state.scenario;
    document.getElementById('kpiInflect').textContent = inf == null ? '不適用' : String(inf);
    document.getElementById('kpiNet').textContent = fmt(cumNet, 1) + ' 億';
    document.getElementById('kpiDeplete').textContent = dep == null ? '不適用' : String(dep);
  }

  function axisStyle() {
    return {
      axisLine: { lineStyle: { color: 'rgba(155,176,201,0.35)' } },
      axisLabel: { color: COLORS.slate, fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(155,176,201,0.12)' } },
    };
  }

  function renderLine(path) {
    const years = DATA.asset_path.map(r => r['年份']);
    // 原始三情景
    const raw = {
      '悲观': DATA.asset_path.map(r => r['总资产_悲观']),
      '基准': DATA.asset_path.map(r => r['总资产_基准']),
      '乐观': DATA.asset_path.map(r => r['总资产_乐观']),
    };
    // 當前情景覆寫路徑（期初序列 + 最後期末）
    const adjYears = path.map(r => r['年份']).concat([path[path.length - 1]['年份'] + 1]);
    const adjAssets = path.map(r => r._A0).concat([path[path.length - 1]._A1]);

    const series = [
      {
        name: '悲观（原始）',
        type: 'line',
        data: raw['悲观'],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: state.scenario === '悲观' ? 0 : 1.5, type: 'dashed', color: COLORS.coral },
        itemStyle: { color: COLORS.coral },
        z: 1,
      },
      {
        name: '基准（原始）',
        type: 'line',
        data: raw['基准'],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: state.scenario === '基准' ? 0 : 1.5, type: 'dashed', color: COLORS.navy },
        itemStyle: { color: COLORS.navy },
        z: 1,
      },
      {
        name: '乐观（原始）',
        type: 'line',
        data: raw['乐观'],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: state.scenario === '乐观' ? 0 : 1.5, type: 'dashed', color: COLORS.green },
        itemStyle: { color: COLORS.green },
        z: 1,
      },
      {
        name: state.scenario + '（當前覆寫）',
        type: 'line',
        data: adjYears.map((y, i) => [y, adjAssets[i]]),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3.2, color: COLORS.gold },
        itemStyle: { color: COLORS.gold },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(201,162,39,0.28)' },
            { offset: 1, color: 'rgba(201,162,39,0.02)' },
          ]),
        },
        markLine: {
          symbol: 'none',
          label: { color: COLORS.goldLite, formatter: state.year + '' },
          lineStyle: { color: COLORS.goldLite, type: 'dotted' },
          data: [{ xAxis: state.year }],
        },
        z: 3,
      },
    ];

    charts.line.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(10,22,40,0.92)',
        borderColor: 'rgba(201,162,39,0.35)',
        textStyle: { color: COLORS.white, fontSize: 12 },
        valueFormatter: v => (v == null ? '—' : fmt(+v, 1) + ' 億'),
      },
      legend: {
        top: 0,
        textStyle: { color: COLORS.slate, fontSize: 11 },
        data: series.map(s => s.name),
      },
      grid: { left: 56, right: 24, top: 36, bottom: 36 },
      xAxis: {
        type: 'value',
        min: 2026,
        max: 2056,
        interval: 5,
        name: '年',
        nameTextStyle: { color: COLORS.slate },
        ...axisStyle(),
      },
      yAxis: {
        type: 'value',
        name: '億港元',
        nameTextStyle: { color: COLORS.slate },
        axisLabel: { color: COLORS.slate, formatter: v => (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v) },
        splitLine: { lineStyle: { color: 'rgba(155,176,201,0.12)' } },
      },
      series,
    }, true);
  }

  function renderSankey(row) {
    const nodes = [
      { name: '期初资产' },
      { name: '雇员强制' },
      { name: '雇主强制' },
      { name: '自雇强制' },
      { name: '自愿供款' },
      { name: '投资回报' },
      { name: '总资产池' },
      { name: '达龄提取' },
      { name: '提前取款' },
      { name: '行政费用' },
      { name: '期末资产' },
    ];
    // 守恒：A0 + Inv + C = A1 + W + E
    const links = [
      { source: '期初资产', target: '总资产池', value: Math.max(row._A0, 0.01) },
      { source: '雇员强制', target: '总资产池', value: Math.max(row._C_ee, 0.01) },
      { source: '雇主强制', target: '总资产池', value: Math.max(row._C_er, 0.01) },
      { source: '自雇强制', target: '总资产池', value: Math.max(row._C_se, 0.01) },
      { source: '自愿供款', target: '总资产池', value: Math.max(row._C_vol, 0.01) },
      { source: '投资回报', target: '总资产池', value: Math.max(row._inv, 0.01) },
      { source: '总资产池', target: '达龄提取', value: Math.max(row._W65, 0.01) },
      { source: '总资产池', target: '提前取款', value: Math.max(row._Wearly, 0.01) },
      { source: '总资产池', target: '行政费用', value: Math.max(row._E, 0.01) },
      { source: '总资产池', target: '期末资产', value: Math.max(row._A1, 0.01) },
    ];

    charts.sankey.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(10,22,40,0.92)',
        borderColor: 'rgba(201,162,39,0.35)',
        textStyle: { color: COLORS.white },
        formatter: p => {
          if (p.dataType === 'edge') {
            return p.data.source + ' → ' + p.data.target + '<br/><b>' + fmt(p.data.value, 2) + '</b> 亿港元';
          }
          return p.name;
        },
      },
      series: [{
        type: 'sankey',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'justify',
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.35 },
        label: { color: COLORS.white, fontSize: 11 },
        data: nodes,
        links,
      }],
    }, true);
  }

  function renderWaterfall(row) {
    const steps = [
      { name: '期初資產', value: row._A0 },
      { name: '投資損益', value: row._inv },
      { name: '總供款', value: row._C },
      { name: '總提取', value: -row._W },
      { name: '費用', value: -row._E },
      { name: '期末資產', value: row._A1 },
    ];
    // 瀑布輔助：透明底 + 實際柱
    let running = 0;
    const helpers = [];
    const display = [];
    const colors = [];
    steps.forEach((s, i) => {
      if (i === 0 || i === steps.length - 1) {
        helpers.push(0);
        display.push(s.value);
        colors.push(i === 0 ? COLORS.navy : COLORS.gold);
        running = s.value;
      } else {
        const v = s.value;
        if (v >= 0) {
          helpers.push(running);
          display.push(v);
          colors.push(COLORS.green);
          running += v;
        } else {
          helpers.push(running + v);
          display.push(-v);
          colors.push(COLORS.coral);
          running += v;
        }
      }
    });

    charts.waterfall.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(10,22,40,0.92)',
        borderColor: 'rgba(201,162,39,0.35)',
        textStyle: { color: COLORS.white },
        formatter: params => {
          const i = params[0].dataIndex;
          const raw = steps[i].value;
          return steps[i].name + '<br/><b>' + fmt(raw, 2) + '</b> 億港元';
        },
      },
      grid: { left: 52, right: 16, top: 24, bottom: 48 },
      xAxis: {
        type: 'category',
        data: steps.map(s => s.name),
        axisLabel: { color: COLORS.slate, fontSize: 10, interval: 28 },
        axisLine: { lineStyle: { color: 'rgba(155,176,201,0.35)' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: COLORS.slate, fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(155,176,201,0.12)' } },
      },
      series: [
        { type: 'bar', stack: 'wf', data: helpers, itemStyle: { color: 'transparent' }, emphasis: { itemStyle: { color: 'transparent' } }, silent: true },
        {
          type: 'bar',
          stack: 'wf',
          data: display.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] } })),
          barWidth: '48%',
        },
      ],
    }, true);
  }

  function renderArea(path) {
    const years = path.map(r => r['年份']);
    charts.area.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(10,22,40,0.92)',
        borderColor: 'rgba(201,162,39,0.35)',
        textStyle: { color: COLORS.white, fontSize: 12 },
        valueFormatter: v => fmt(+v, 1) + ' 億',
      },
      legend: {
        top: 0,
        textStyle: { color: COLORS.slate, fontSize: 11 },
      },
      grid: { left: 52, right: 20, top: 36, bottom: 36 },
      xAxis: {
        type: 'category',
        data: years,
        axisLabel: { color: COLORS.slate, fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(155,176,201,0.35)' } },
      },
      yAxis: {
        type: 'value',
        name: '億港元',
        nameTextStyle: { color: COLORS.slate },
        axisLabel: { color: COLORS.slate },
        splitLine: { lineStyle: { color: 'rgba(155,176,201,0.12)' } },
      },
      series: [
        {
          name: '供款',
          type: 'line',
          stack: 'in',
          areaStyle: { opacity: 0.55 },
          showSymbol: false,
          color: COLORS.gold,
          data: path.map(r => +r._C.toFixed(2)),
        },
        {
          name: '投資回報',
          type: 'line',
          stack: 'in',
          areaStyle: { opacity: 0.45 },
          showSymbol: false,
          color: COLORS.green,
          data: path.map(r => +r._inv.toFixed(2)),
        },
        {
          name: '提取',
          type: 'line',
          stack: 'out',
          areaStyle: { opacity: 0.4 },
          showSymbol: false,
          color: COLORS.coral,
          data: path.map(r => +r._W.toFixed(2)),
        },
        {
          name: '費用',
          type: 'line',
          stack: 'out',
          areaStyle: { opacity: 0.35 },
          showSymbol: false,
          color: COLORS.purple,
          data: path.map(r => +r._E.toFixed(2)),
        },
      ],
    }, true);
  }

  function refresh() {
    const path = recomputePath(state.scenario);
    const row = findYear(path, state.year);
    updateKpis(path);
    renderLine(path);
    renderSankey(row);
    renderWaterfall(row);
    renderArea(path);
  }

  function bind() {
    document.querySelectorAll('#scenarioBtns button').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#scenarioBtns button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.scenario = btn.getAttribute('data-s');
        // 切情景時把回報滑塊對準該情景平均回報
        const sum = DATA.summary.find(s => s['情景标签'] === state.scenario);
        if (sum && sum['平均加权回报率'] != null) {
          state.retPct = +(sum['平均加权回报率'] * 100).toFixed(1);
          document.getElementById('retSlider').value = state.retPct;
          document.getElementById('retOut').textContent = state.retPct.toFixed(1) + '%';
        }
        refresh();
      });
    });

    const yearSlider = document.getElementById('yearSlider');
    yearSlider.addEventListener('input', () => {
      state.year = +yearSlider.value;
      document.getElementById('yearLabel').textContent = String(state.year);
      refresh();
    });

    const retSlider = document.getElementById('retSlider');
    retSlider.addEventListener('input', () => {
      state.retPct = +retSlider.value;
      document.getElementById('retOut').textContent = state.retPct.toFixed(1) + '%';
      refresh();
    });

    const contribSlider = document.getElementById('contribSlider');
    contribSlider.addEventListener('input', () => {
      state.contribPct = +contribSlider.value;
      document.getElementById('contribOut').textContent = state.contribPct.toFixed(1) + '%';
      refresh();
    });

    const retireSlider = document.getElementById('retireSlider');
    retireSlider.addEventListener('input', () => {
      state.retireAge = +retireSlider.value;
      document.getElementById('retireOut').textContent = state.retireAge + '歲';
      refresh();
    });

    window.addEventListener('resize', () => {
      Object.values(charts).forEach(c => c.resize());
    });
  }

  function init() {
    charts.line = echarts.init(document.getElementById('chartLine'));
    charts.sankey = echarts.init(document.getElementById('chartSankey'));
    charts.waterfall = echarts.init(document.getElementById('chartWaterfall'));
    charts.area = echarts.init(document.getElementById('chartArea'));
    bind();
    // 基準情景平均回報對齊滑塊
    const sum = DATA.summary.find(s => s['情景标签'] === '基准');
    if (sum) {
      state.retPct = +(sum['平均加权回报率'] * 100).toFixed(1);
      document.getElementById('retSlider').value = state.retPct;
      document.getElementById('retOut').textContent = state.retPct.toFixed(1) + '%';
    }
    refresh();
  }

  init();
})();
</script>
</body>
</html>
"""

# Fix: the JSON uses Simplified Chinese keys from pandas (情景标签 etc.)
# The HTML JS already references 情景标签, 总供款_亿港元, etc.
# Title uses Traditional for HK feel — keep mixed as user asked 中文界面.

html = HTML_TEMPLATE.replace("__MPF_DATA__", json.dumps(DATA, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print("Wrote", OUT, "size", OUT.stat().st_size)
