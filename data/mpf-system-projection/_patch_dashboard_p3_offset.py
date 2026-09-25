# -*- coding: utf-8 -*-
"""向 P3 集成仪表盘注入：模块8对冲图 + 模块9设计思路面板。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "mpf_integrated_30y_dashboard.html"
OFF = ROOT / "mpf_model" / "output" / "offsetting" / "O01_offsetting_flow_by_year.csv"

df = pd.read_csv(OFF)
offset_payload = {
    "years": [int(y) for y in df["年份"].tolist()],
    # 转制日前入职 = pre + hybrid（渐进归零主力）
    "pre_hire": [
        round(float(a) + float(b), 4)
        for a, b in zip(df["对冲流出_pre_亿港元"], df["对冲流出_hybrid_亿港元"])
    ],
    "post_hire": [round(float(x), 4) for x in df["对冲流出_post_亿港元"].tolist()],
    "total": [round(float(x), 4) for x in df["对冲流出_亿港元"].tolist()],
    "transition_year": 2025,
    "transition_label": "2025-05-01 转制日",
}
OFFSET_JSON = json.dumps(offset_payload, ensure_ascii=False, separators=(",", ":"))

CSS_EXTRA = r"""
/* —— 模块9 设计思路面板 —— */
details.design-panel{
  margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;
  box-shadow:0 4px 16px rgba(26,58,92,.06);overflow:hidden;
}
details.design-panel>summary{
  cursor:pointer;list-style:none;padding:14px 18px;display:flex;align-items:center;gap:10px;
  font-weight:700;color:var(--navy);font-size:.98rem;user-select:none;
}
details.design-panel>summary::-webkit-details-marker{display:none}
details.design-panel>summary .chev{
  margin-left:auto;width:10px;height:10px;border-right:2px solid var(--gold);border-bottom:2px solid var(--gold);
  transform:rotate(45deg);transition:transform .2s;
}
details.design-panel[open]>summary .chev{transform:rotate(-135deg);margin-top:6px}
details.design-panel>summary .badge{
  font-size:.68rem;font-weight:600;letter-spacing:.06em;color:#1a1405;background:var(--gold);
  padding:3px 8px;border-radius:999px;
}
.design-body{padding:4px 18px 18px;border-top:1px solid var(--line)}
.design-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.design-card{
  background:linear-gradient(165deg,#f8fafc,#fff);border:1px solid var(--line);border-radius:12px;padding:14px 14px 12px;
}
.design-card .ico{
  width:36px;height:36px;border-radius:10px;display:grid;place-items:center;font-size:1.05rem;
  background:rgba(26,58,92,.08);margin-bottom:8px;
}
.design-card h4{margin:0 0 6px;font-size:.9rem;color:var(--navy)}
.design-card p,.design-card li{margin:0;font-size:.8rem;color:var(--muted);line-height:1.55}
.design-card ul{margin:6px 0 0;padding-left:1.1em}
.design-card.wide{grid-column:1/-1}
.flow-mini{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:8px;font-size:.78rem;font-weight:600;color:var(--navy)}
.flow-mini span.pill{background:rgba(201,162,39,.18);border:1px solid rgba(201,162,39,.45);padding:4px 8px;border-radius:999px}
.flow-mini span.arr{color:var(--gold);font-weight:700}
.callout-offset{
  margin-top:8px;padding:10px 12px;border-left:3px solid var(--gold);background:rgba(201,162,39,.08);
  font-size:.8rem;color:var(--navy);line-height:1.5;border-radius:0 8px 8px 0;
}
#chartOffset{max-height:360px}
@media (max-width:900px){
  .design-grid{grid-template-columns:1fr}
  body{min-width:0}
}
"""

DESIGN_PANEL = r"""
  <!-- 模块9 · 模型设计思路（默认折叠） -->
  <details class="design-panel" id="designPanel">
    <summary>
      <span class="badge">面试速览</span>
      模块9 · 模型设计思路
      <span class="chev" aria-hidden="true"></span>
    </summary>
    <div class="design-body">
      <p style="margin:10px 0 0;font-size:.84rem;color:var(--muted);line-height:1.55">
        队列化人口、对冲分层、上下限过渡、全自由行边界、eMPF 降费与四层反馈——面试时按卡片扫一遍即可。
      </p>
      <div class="design-grid">
        <div class="design-card">
          <div class="ico" aria-hidden="true">👥</div>
          <h4>1. 为何用队列成分法，而非线性外推</h4>
          <ul>
            <li>养老金压力来自<strong>年龄结构</strong>，不是总人口一条直线。</li>
            <li>每年新领取 ≈ 准退休队列推进，不是「总量×固定增速」。</li>
            <li>婴儿潮集中达龄 → 领取<strong>非线性</strong>抬升。</li>
          </ul>
        </div>
        <div class="design-card">
          <div class="ico" aria-hidden="true">⚖️</div>
          <h4>2. 为何取消对冲要按入职年份分层</h4>
          <ul>
            <li>取消对冲<strong>不具追溯力</strong>（转制日 2025-05-01）。</li>
            <li>转制前在职：转制前部分仍可被雇主强制供款对冲。</li>
            <li>转制后入职：雇主强制完全不可对冲；自愿仍可。</li>
            <li>流出<strong>渐进归零</strong>，不是一刀切。</li>
          </ul>
        </div>
        <div class="design-card">
          <div class="ico" aria-hidden="true">📏</div>
          <h4>3. 为什么供款上下限要分阶段处理</h4>
          <ul>
            <li>现行仍为 <strong>$7,100 / $30,000</strong>（约 12–13 年未调）。</li>
            <li>截至约 2026-09：积金局仍在进行 2022–2026 周期检讨，目标 <strong>2026 年中</strong>向政府提交报告及建议；<strong>最终幅度与时间表尚未公布</strong>。</li>
            <li>模型：<strong>2026–2027 用旧值</strong>；<strong>2028 起</strong>上调至 $10,500 / $40,000 为【基准情景假设】，非法定值。</li>
            <li>敏感性保留「维持旧上限 / 现行 $30,000」对照情景。</li>
          </ul>
        </div>
        <div class="design-card">
          <div class="ico" aria-hidden="true">🔄</div>
          <h4>4. 全自由行对模型的影响</h4>
          <ul>
            <li><strong>首阶段</strong>：2025年9月完成修例，预计<strong>2026年Q4</strong>实际实施。允许2025年5月1日或之后入职的雇员，将雇主强制性供款转移至自选计划。</li>
            <li><strong>次阶段</strong>：2027年上半年提交修订条例草案，覆盖其余雇员。</li>
            <li><strong>对模型的影响</strong>：不改变制度总资产，但影响账户分布和市场竞争。本次建模未纳入受托人层面，在「模型局限」中说明。</li>
          </ul>
        </div>
        <div class="design-card">
          <div class="ico" aria-hidden="true">📉</div>
          <h4>5. eMPF 费率的动态下降路径</h4>
          <ul>
            <li><strong>0.37% → 0.29%</strong>（2026-04-01）→ 线性降至 <strong>0.22%</strong>（2030），其后持平。</li>
            <li>费率下降直接抬升净投资回报（相对 0.29% 口径逐年代入）。</li>
          </ul>
        </div>
        <div class="design-card">
          <div class="ico" aria-hidden="true">🔗</div>
          <h4>6. 四层架构与反馈回路</h4>
          <div class="flow-mini">
            <span class="pill">人口</span><span class="arr">→</span>
            <span class="pill">缴费</span><span class="arr">→</span>
            <span class="pill">领取</span><span class="arr">→</span>
            <span class="pill">资产</span>
          </div>
          <p style="margin-top:8px">反馈：回报抬高 A → 余额↑ → 提取↑。恒等式含对冲：<code style="color:var(--navy)">A(t+1)=A(t)(1+r)+C−W−Offset</code></p>
        </div>
        <div class="design-card wide">
          <div class="ico" aria-hidden="true">⚠️</div>
          <h4>7. 关键假设与局限（摘要）</h4>
          <ul>
            <li>长期回报用制度以来中枢（约 4.9%），不用近年单年高回报外推。</li>
            <li>提取比例默认 100%（一笔过约 94%+）；永久离港独立建模（2025=58.86 亿，年减 10% 至 2035 趋稳）。</li>
            <li>全自由行首阶段预计 2026 Q4 落地、次阶段 2027 立法；受托人/账户迁移未纳入资产方程。</li>
            <li>上下限 2028 新值 $10,500 / $40,000 为基准情景假设（未生效）；对照可维持现行 $7,100 / $30,000。</li>
          </ul>
        </div>
      </div>
    </div>
  </details>
"""

MODULE8 = r"""
    <div class="mod wide">
      <h3>模块8 · 对冲流出趋势（2020–2056）</h3>
      <p class="desc">堆叠柱：底层＝转制日前入职（含 hybrid 转制前服务仍可对冲）；上层＝转制日后入职（仅雇主自愿可对冲，长期趋近残差）。竖虚线＝转制日。</p>
      <div class="callout-offset">取消对冲不具追溯力，转制前部分仍可对冲，流出逐步归零。</div>
      <div class="chart" style="min-height:340px;margin-top:10px"><canvas id="chartOffset"></canvas></div>
    </div>
"""

JS_OFFSET = r"""
  // —— 模块8：对冲流出堆叠图 ——
  let chartOffset = null;
  function buildOffsetChart() {
    const O = window.MPF_OFFSET;
    if (!O || !document.getElementById("chartOffset")) return;
    const ctx = document.getElementById("chartOffset").getContext("2d");
    const years = O.years;
    const transIdx = years.indexOf(O.transition_year);

    const vertLinePlugin = {
      id: "transitionLine",
      afterDraw(chart) {
        if (transIdx < 0) return;
        const meta = chart.getDatasetMeta(0);
        if (!meta.data.length) return;
        const xScale = chart.scales.x;
        const yScale = chart.scales.y;
        // 柱中心：转制年
        const x = xScale.getPixelForValue(transIdx);
        const { top, bottom } = chart.chartArea;
        const c = chart.ctx;
        c.save();
        c.beginPath();
        c.setLineDash([6, 5]);
        c.strokeStyle = "#c9a227";
        c.lineWidth = 2;
        c.moveTo(x, top);
        c.lineTo(x, bottom);
        c.stroke();
        c.setLineDash([]);
        c.fillStyle = "#c9a227";
        c.font = "600 11px system-ui,sans-serif";
        c.textAlign = "center";
        c.fillText(O.transition_label, x, top + 14);
        c.restore();
      },
    };

    chartOffset = new Chart(ctx, {
      type: "bar",
      data: {
        labels: years,
        datasets: [
          {
            label: "转制日前入职（pre+hybrid）",
            data: O.pre_hire,
            backgroundColor: "rgba(26,58,92,0.82)",
            borderWidth: 0,
            stack: "off",
            barPercentage: 0.9,
            categoryPercentage: 0.92,
          },
          {
            label: "转制日后入职（post，自愿残差）",
            data: O.post_hire,
            backgroundColor: "rgba(201,162,39,0.85)",
            borderWidth: 0,
            stack: "off",
            barPercentage: 0.9,
            categoryPercentage: 0.92,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              footer(items) {
                const i = items[0].dataIndex;
                return "合计 " + O.total[i].toFixed(2) + " 亿";
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            ticks: {
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 12,
              font: { size: 10 },
            },
            grid: { display: false },
          },
          y: {
            stacked: true,
            title: { display: true, text: "对冲流出（亿港元）", font: { size: 11 } },
            grid: { color: "rgba(226,232,240,.9)" },
            ticks: { font: { size: 10 } },
          },
        },
      },
      plugins: [vertLinePlugin],
    });
  }
"""

def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    # 1) CSS
    if "details.design-panel" not in html:
        html = html.replace(
            "footer strong{color:var(--navy)}\n</style>",
            "footer strong{color:var(--navy)}\n" + CSS_EXTRA + "\n</style>",
        )

    # 2) Design panel：若已存在则整块替换，确保最新文案
    import re

    if 'id="designPanel"' in html:
        html = re.sub(
            r"\s*<!-- 模块9 · 模型设计思路（默认折叠） -->\s*<details class=\"design-panel\" id=\"designPanel\">.*?</details>",
            "\n" + DESIGN_PANEL,
            html,
            count=1,
            flags=re.DOTALL,
        )
    else:
        html = html.replace(
            "  </header>\n\n  <section class=\"controls\">",
            "  </header>\n" + DESIGN_PANEL + "\n  <section class=\"controls\">",
        )

    # 3) Module 8 before closing grid / before footer
    if 'id="chartOffset"' not in html:
        html = html.replace(
            "    </div>\n  </section>\n\n  <footer>",
            "    </div>\n" + MODULE8 + "  </section>\n\n  <footer>",
        )

    # 4) Update identity mention in hero note
    html = html.replace(
        "A<sub>t+1</sub> = A<sub>t</sub>×(1+r) + C<sub>t</sub> − W<sub>t</sub>",
        "A<sub>t+1</sub> = A<sub>t</sub>×(1+r) + C<sub>t</sub> − W<sub>t</sub> − Offset<sub>t</sub>",
    )

    # 5) Embed / refresh offset JSON
    if "MPF_OFFSET" not in html:
        html = html.replace(
            "<script>\nwindow.MPF = ",
            "<script>\nwindow.MPF_OFFSET = " + OFFSET_JSON + ";\nwindow.MPF = ",
        )
    else:
        html = re.sub(
            r"window\.MPF_OFFSET = \{.*?\};",
            "window.MPF_OFFSET = " + OFFSET_JSON + ";",
            html,
            count=1,
            flags=re.DOTALL,
        )

    if "buildOffsetChart" not in html:
        html = html.replace(
            "  function init() {\n    sankey = echarts.init(document.getElementById(\"sankey\"));",
            JS_OFFSET
            + "\n  function init() {\n    sankey = echarts.init(document.getElementById(\"sankey\"));",
        )
        html = html.replace(
            "    buildRetireChart();\n    bind();\n    applyPreset(\"基准\");",
            "    buildRetireChart();\n    buildOffsetChart();\n    bind();\n    applyPreset(\"基准\");",
        )
        html = html.replace(
            "      sankey && sankey.resize();\n      waterfall && waterfall.resize();",
            "      sankey && sankey.resize();\n      waterfall && waterfall.resize();\n      chartOffset && chartOffset.resize();",
        )

    # footer note
    if "对冲流出" not in html[html.find("<footer>") : html.find("</footer>") + 10]:
        html = html.replace(
            "本页计算基于项目内 Prompt 1-1 人口层、1-2 缴费层、1-3 领取与资产层 CSV。",
            "本页计算基于项目内人口/缴费/领取/资产层及对冲模块（转制日 2025-05-01）CSV。",
        )

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"updated {HTML_PATH}")
    print(f"offset years {offset_payload['years'][0]}-{offset_payload['years'][-1]} n={len(offset_payload['years'])}")


if __name__ == "__main__":
    main()
