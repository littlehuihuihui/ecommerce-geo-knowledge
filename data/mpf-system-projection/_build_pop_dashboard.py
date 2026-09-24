# -*- coding: utf-8 -*-
"""Build single-file HTML for HK population CCM year-by-year view."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "population_ccm" / "_embed_pop.json").read_text(encoding="utf-8"))
OUT = ROOT / "population_ccm_dashboard.html"

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>香港人口队列成分法 · 逐年结构（2026–2056）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
:root{
  --bg:#0b1524; --panel:#122236; --line:rgba(148,178,210,.22);
  --text:#e8eef6; --muted:#8fa6c0; --gold:#d4b45a; --cyan:#5eb3d4; --coral:#e07a6a; --green:#5cba8f;
  --font:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
}
*{box-sizing:border-box}
body{margin:0;font-family:var(--font);background:linear-gradient(180deg,#08111d,#0b1524 40%,#101c2e);color:var(--text);min-height:100vh}
.wrap{max-width:1280px;margin:0 auto;padding:18px 16px 40px}
header{padding:18px 20px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(18,34,54,.95),rgba(11,21,36,.9))}
.eyebrow{color:var(--gold);font-size:12px;letter-spacing:.12em;font-weight:600}
h1{margin:6px 0 0;font-size:clamp(1.25rem,2.2vw,1.7rem)}
.sub{margin:8px 0 0;color:var(--muted);font-size:.92rem;line-height:1.55;max-width:78ch}
.controls{margin-top:14px;display:grid;grid-template-columns:1.2fr 1fr;gap:12px}
@media(max-width:900px){.controls{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.panel h2{margin:0 0 10px;font-size:.88rem;color:var(--gold);letter-spacing:.04em}
.btns{display:flex;flex-wrap:wrap;gap:8px}
.btns button{border:1px solid rgba(143,166,192,.35);background:transparent;color:var(--text);padding:7px 14px;border-radius:999px;cursor:pointer;font:inherit}
.btns button.active{background:linear-gradient(135deg,var(--gold),#b8943a);color:#1a1408;border-color:transparent;font-weight:700}
.year-row{display:grid;grid-template-columns:72px 1fr 64px;gap:10px;align-items:center;margin-top:12px}
.year-row input[type=range]{width:100%;accent-color:var(--gold)}
.year-val{font-size:1.35rem;font-weight:700;color:var(--gold);text-align:right}
label{font-size:.86rem;color:var(--muted)}
.kpis{margin-top:14px;display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
@media(max-width:980px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:linear-gradient(160deg,rgba(30,58,90,.55),rgba(11,21,36,.85));border:1px solid rgba(212,180,90,.22);border-radius:12px;padding:12px 14px}
.kpi .l{font-size:.72rem;color:var(--muted);letter-spacing:.05em}
.kpi .v{margin-top:4px;font-size:1.2rem;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .v.gold{color:var(--gold)}
.grid{margin-top:14px;display:grid;grid-template-columns:1.15fr .85fr;gap:12px}
@media(max-width:980px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;min-height:360px;display:flex;flex-direction:column}
.card.wide{grid-column:1/-1}
.card h3{margin:0;font-size:.95rem}
.card p{margin:6px 0 8px;font-size:.78rem;color:var(--muted);line-height:1.45}
.chart{flex:1;min-height:300px;width:100%}
.chart.tall{min-height:340px}
footer{margin-top:18px;padding:14px 16px;border-top:1px solid var(--line);color:var(--muted);font-size:.78rem;line-height:1.6}
code{color:var(--gold);font-size:.85em}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">POPULATION LAYER · COHORT COMPONENT</div>
    <h1>香港人口队列成分法 · 逐年结构（2026–2056）</h1>
    <p class="sub">强积金模型第一层：分性别、5岁年龄组。拖动时间轴查看任意一年的年龄结构与关键队列（劳动人口 / 准退休 / 退休）。基准人口与死亡率来自政府统计处；生育与迁移见页脚说明。</p>
  </header>

  <section class="controls">
    <div class="panel">
      <h2>情景 · 性别 · 年份</h2>
      <div class="btns" id="scBtns">
        <button type="button" data-v="中" class="active">基准</button>
        <button type="button" data-v="高">较高</button>
        <button type="button" data-v="低">较低</button>
      </div>
      <div class="btns" id="sexBtns" style="margin-top:10px">
        <button type="button" data-v="混合" class="active">混合</button>
        <button type="button" data-v="男">男</button>
        <button type="button" data-v="女">女</button>
      </div>
      <div class="year-row">
        <label for="year">时间轴</label>
        <input type="range" id="year" min="2026" max="2056" step="1" value="2026" />
        <div class="year-val" id="yearLab">2026</div>
      </div>
    </div>
    <div class="panel">
      <h2>怎么读</h2>
      <p style="margin:0;color:var(--muted);font-size:.85rem;line-height:1.6">
        <b style="color:var(--text)">准退休 55–59</b> 是未来约 5–10 年进入强积金可提取年龄的前置队列；
        <b style="color:var(--text)">退休 65+</b> 对应领取层规模；
        <b style="color:var(--text)">劳动 15–64</b> 约束缴费层。切换性别可看男女结构差。
      </p>
    </div>
  </section>

  <section class="kpis">
    <div class="kpi"><div class="l">总人口</div><div class="v gold" id="kTot">—</div></div>
    <div class="kpi"><div class="l">劳动人口 15–64</div><div class="v" id="kLab">—</div></div>
    <div class="kpi"><div class="l">准退休 55–59</div><div class="v" id="kPre">—</div></div>
    <div class="kpi"><div class="l">退休 65+</div><div class="v" id="kRet">—</div></div>
    <div class="kpi"><div class="l">老龄化率</div><div class="v" id="kAge">—</div></div>
  </section>

  <section class="grid">
    <div class="card">
      <h3>当年年龄结构（5岁组）</h3>
      <p>这张图在说什么：选定年份的人口金字塔式条形分布，一眼看出哪一段「鼓」——缴费主力还是退休压力。</p>
      <div class="chart" id="cBar"></div>
    </div>
    <div class="card">
      <h3>当年人口构成占比</h3>
      <p>这张图在说什么：少儿 / 劳动年龄 / 退休的相对份额；老龄化时退休扇区会变大。</p>
      <div class="chart" id="cPie"></div>
    </div>
    <div class="card wide">
      <h3>关键队列时间路径（2026–2056）</h3>
      <p>这张图在说什么：劳动人口、准退休、退休人数随年份怎么走；竖线标出当前选中年。</p>
      <div class="chart tall" id="cLine"></div>
    </div>
    <div class="card wide">
      <h3>年龄组热力表 · 选定情景（万人）</h3>
      <p>这张图在说什么：行=年龄组，列=年份，颜色深浅表示人数；适合扫一眼「哪一队何时变厚」。</p>
      <div class="chart tall" id="cHeat"></div>
    </div>
  </section>

  <footer>
    <strong>数据来源</strong>：死亡率 C&amp;SD 表 115-01023；基准人口表 110-01001A（2026年中，不含外佣）；
    生育 ASFR 形状取《香港人口推算 2022–2046》表5，TFR 基准 2023=751→2046=938（高/低±10%）；
    迁移总量级对齐官方净移入、年龄结构为研究假设。生成：<code>population_ccm/</code> · 方法：队列成分法。
    本页为研究可视化，非统计处官方推算页面。
  </footer>
</div>
<script>
window.POP_DATA = __DATA__;
(function(){
  const D = window.POP_DATA;
  const AGES = ["0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64","65-69","70-74","75-79","80-84","85+"];
  const state = { scenario:"中", sex:"混合", year:2026 };
  const charts = {};

  function fmt(n){
    if(n==null||isNaN(n)) return "—";
    if(Math.abs(n)>=1e4) return (n/1e4).toFixed(1)+" 万";
    return Math.round(n).toLocaleString("zh-CN");
  }
  function fmtWan(n){ return (n/1e4).toFixed(2); }

  function sumForYear(){
    const rows = D.summary.filter(r => r["情景"]===state.scenario && r["性别"]===state.sex && r["年份"]===state.year);
    return rows[0] || null;
  }

  function ageRows(){
    if(state.sex==="混合"){
      const m = D.pop.filter(r=>r["情景"]===state.scenario && r["年份"]===state.year && r["性别"]==="男");
      const f = D.pop.filter(r=>r["情景"]===state.scenario && r["年份"]===state.year && r["性别"]==="女");
      const map={};
      m.forEach(r=>{ map[r["年龄组"]]=(map[r["年龄组"]]||0)+r["人数"]; });
      f.forEach(r=>{ map[r["年龄组"]]=(map[r["年龄组"]]||0)+r["人数"]; });
      return AGES.map(a=>({年龄组:a, 人数:map[a]||0}));
    }
    return D.pop.filter(r=>r["情景"]===state.scenario && r["年份"]===state.year && r["性别"]===state.sex)
      .sort((a,b)=>AGES.indexOf(a["年龄组"])-AGES.indexOf(b["年龄组"]));
  }

  function updateKpi(){
    const s = sumForYear();
    if(!s){ return; }
    document.getElementById("kTot").textContent = fmt(s["总人口"]);
    document.getElementById("kLab").textContent = fmt(s["劳动人口15_64"]);
    document.getElementById("kPre").textContent = fmt(s["准退休55_59"]);
    document.getElementById("kRet").textContent = fmt(s["退休65及以上"]);
    document.getElementById("kAge").textContent = ((s["老龄化率_65plus占比"]||0)*100).toFixed(1)+"%";
  }

  function renderBar(){
    const rows = ageRows();
    const colors = rows.map(r=>{
      const a=r["年龄组"];
      if(a==="55-59") return "#d4b45a";
      if(["65-69","70-74","75-79","80-84","85+"].includes(a)) return "#e07a6a";
      if(["0-4","5-9","10-14"].includes(a)) return "#5eb3d4";
      return "#5cba8f";
    });
    charts.bar.setOption({
      backgroundColor:"transparent",
      tooltip:{ trigger:"axis", backgroundColor:"rgba(11,21,36,.92)", borderColor:"rgba(212,180,90,.3)",
        textStyle:{color:"#e8eef6"}, valueFormatter:v=>fmt(+v) },
      grid:{ left:70, right:20, top:16, bottom:28 },
      xAxis:{ type:"value", axisLabel:{ color:"#8fa6c0", formatter:v=>fmtWan(v)+"万" },
        splitLine:{ lineStyle:{ color:"rgba(148,178,210,.12)" } } },
      yAxis:{ type:"category", data:rows.map(r=>r["年龄组"]), inverse:true,
        axisLabel:{ color:"#8fa6c0", fontSize:11 }, axisLine:{ lineStyle:{ color:"rgba(148,178,210,.25)" } } },
      series:[{ type:"bar", data:rows.map((r,i)=>({ value:r["人数"], itemStyle:{ color:colors[i], borderRadius:[0,3,3,0] } })),
        barWidth:"62%" }]
    }, true);
  }

  function renderPie(){
    const s = sumForYear(); if(!s) return;
    const labour = s["劳动人口15_64"] - s["准退休55_59"]; // 15-54 近似展示：劳动含55-59，饼图把准退休单列
    const child = s["少儿0_14"];
    const pre = s["准退休55_59"];
    const ret = s["退休65及以上"];
    // 15-64 = labour_full; 饼：少儿 + (15-54) + 准退休 + 退休
    const mid = Math.max(0, s["劳动人口15_64"] - pre);
    charts.pie.setOption({
      backgroundColor:"transparent",
      tooltip:{ trigger:"item", backgroundColor:"rgba(11,21,36,.92)", borderColor:"rgba(212,180,90,.3)",
        textStyle:{color:"#e8eef6"}, formatter:p=>p.name+"<br/><b>"+fmt(p.value)+"</b>（"+p.percent+"%）" },
      legend:{ bottom:0, textStyle:{ color:"#8fa6c0", fontSize:11 } },
      series:[{
        type:"pie", radius:["38%","68%"], center:["50%","46%"],
        label:{ color:"#e8eef6", formatter:"{b}\n{d}%" },
        data:[
          { name:"少儿 0–14", value:child, itemStyle:{ color:"#5eb3d4" } },
          { name:"劳动 15–54", value:mid, itemStyle:{ color:"#5cba8f" } },
          { name:"准退休 55–59", value:pre, itemStyle:{ color:"#d4b45a" } },
          { name:"退休 65+", value:ret, itemStyle:{ color:"#e07a6a" } },
        ]
      }]
    }, true);
  }

  function renderLine(){
    const years=[]; for(let y=2026;y<=2056;y++) years.push(y);
    const seriesKeys=[
      {k:"劳动人口15_64", name:"劳动 15–64", color:"#5cba8f"},
      {k:"准退休55_59", name:"准退休 55–59", color:"#d4b45a"},
      {k:"退休65及以上", name:"退休 65+", color:"#e07a6a"},
      {k:"总人口", name:"总人口", color:"#5eb3d4"},
    ];
    const series = seriesKeys.map(sk=>({
      name: sk.name, type:"line", showSymbol:false, smooth:true,
      lineStyle:{ width: sk.k==="总人口"?2.5:2, type: sk.k==="总人口"?"solid":"solid" },
      itemStyle:{ color: sk.color },
      data: years.map(y=>{
        const r=D.summary.find(x=>x["年份"]===y && x["情景"]===state.scenario && x["性别"]===state.sex);
        return r? r[sk.k] : null;
      })
    }));
    charts.line.setOption({
      backgroundColor:"transparent",
      tooltip:{ trigger:"axis", backgroundColor:"rgba(11,21,36,.92)", borderColor:"rgba(212,180,90,.3)",
        textStyle:{color:"#e8eef6"}, valueFormatter:v=>fmt(+v) },
      legend:{ top:0, textStyle:{ color:"#8fa6c0", fontSize:11 } },
      grid:{ left:58, right:24, top:36, bottom:36 },
      xAxis:{ type:"category", data:years, axisLabel:{ color:"#8fa6c0", fontSize:10 },
        axisLine:{ lineStyle:{ color:"rgba(148,178,210,.25)" } } },
      yAxis:{ type:"value", axisLabel:{ color:"#8fa6c0", formatter:v=>fmtWan(v)+"万" },
        splitLine:{ lineStyle:{ color:"rgba(148,178,210,.12)" } } },
      series: series.concat([{
        type:"line", markLine:{ symbol:"none",
          label:{ color:"#d4b45a", formatter:String(state.year) },
          lineStyle:{ color:"#d4b45a", type:"dotted" },
          data:[{ xAxis:String(state.year) }] },
        data:[]
      }])
    }, true);
  }

  function renderHeat(){
    // 万人，按混合或当前性别
    const years=[]; for(let y=2026;y<=2056;y+=2) years.push(y); // 隔年减负
    const data=[];
    let vmax=0;
    AGES.forEach((age,yi)=>{
      years.forEach((y,xi)=>{
        let v=0;
        if(state.sex==="混合"){
          D.pop.filter(r=>r["情景"]===state.scenario && r["年份"]===y && r["年龄组"]===age)
            .forEach(r=>{ v+=r["人数"]; });
        }else{
          const r=D.pop.find(x=>x["情景"]===state.scenario && x["年份"]===y && x["年龄组"]===age && x["性别"]===state.sex);
          v=r? r["人数"]:0;
        }
        const wan=v/1e4;
        vmax=Math.max(vmax, wan);
        data.push([xi, yi, +wan.toFixed(2)]);
      });
    });
    charts.heat.setOption({
      backgroundColor:"transparent",
      tooltip:{ position:"top", backgroundColor:"rgba(11,21,36,.92)", borderColor:"rgba(212,180,90,.3)",
        textStyle:{color:"#e8eef6"},
        formatter:p=>{
          const y=years[p.value[0]], a=AGES[p.value[1]];
          return y+" · "+a+"<br/><b>"+p.value[2]+"</b> 万人";
        }},
      grid:{ left:70, right:24, top:20, bottom:40 },
      xAxis:{ type:"category", data:years, axisLabel:{ color:"#8fa6c0", fontSize:10 }, splitArea:{ show:false } },
      yAxis:{ type:"category", data:AGES, axisLabel:{ color:"#8fa6c0", fontSize:10 }, inverse:true },
      visualMap:{ min:0, max:Math.ceil(vmax), calculable:true, orient:"horizontal", left:"center", bottom:0,
        textStyle:{ color:"#8fa6c0" },
        inRange:{ color:["#122236","#1e4d7a","#c9a227","#f0d78c"] } },
      series:[{ type:"heatmap", data, emphasis:{ itemStyle:{ shadowBlur:6, shadowColor:"rgba(0,0,0,.4)" } } }]
    }, true);
  }

  function refresh(){
    updateKpi();
    renderBar();
    renderPie();
    renderLine();
    renderHeat();
  }

  function bind(){
    document.querySelectorAll("#scBtns button").forEach(b=>{
      b.addEventListener("click",()=>{
        document.querySelectorAll("#scBtns button").forEach(x=>x.classList.remove("active"));
        b.classList.add("active"); state.scenario=b.dataset.v; refresh();
      });
    });
    document.querySelectorAll("#sexBtns button").forEach(b=>{
      b.addEventListener("click",()=>{
        document.querySelectorAll("#sexBtns button").forEach(x=>x.classList.remove("active"));
        b.classList.add("active"); state.sex=b.dataset.v; refresh();
      });
    });
    const y=document.getElementById("year");
    y.addEventListener("input",()=>{
      state.year=+y.value;
      document.getElementById("yearLab").textContent=String(state.year);
      refresh();
    });
    window.addEventListener("resize",()=>Object.values(charts).forEach(c=>c.resize()));
  }

  function init(){
    charts.bar=echarts.init(document.getElementById("cBar"));
    charts.pie=echarts.init(document.getElementById("cPie"));
    charts.line=echarts.init(document.getElementById("cLine"));
    charts.heat=echarts.init(document.getElementById("cHeat"));
    bind(); refresh();
  }
  init();
})();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False, separators=(",", ":")))
OUT.write_text(html, encoding="utf-8")
print("Wrote", OUT, "MB", round(OUT.stat().st_size / 1e6, 2))
