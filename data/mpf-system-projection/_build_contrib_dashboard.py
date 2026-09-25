# -*- coding: utf-8 -*-
"""Build contribution-layer dashboard HTML."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "contribution_layer"
OUT = ROOT / "contribution_layer_dashboard.html"

c01 = pd.read_csv(SRC / "C01_contributors_by_age_sex.csv")
c02 = pd.read_csv(SRC / "C02_contribution_breakdown.csv")
c04 = pd.read_csv(SRC / "C04_growth_drivers.csv")

# slim embed
c01s = c01[c01["性别"].isin(["男", "女", "混合"])][
    ["年份", "年龄组", "性别", "缴费人数_人", "劳动参与率", "情景", "情景标签"]
].copy()
c01s["缴费人数_人"] = c01s["缴费人数_人"].round(0).astype(int)

payload = {
    "contributors": c01s.to_dict(orient="records"),
    "annual": c02.to_dict(orient="records"),
    "drivers": c04.to_dict(orient="records"),
    "meta": {
        "start": 2026,
        "end": 2056,
        "anchor": "2025总供款约907亿；模型2026基准≈906亿",
        "y_min": 7100,
        "y_max": 30000,
    },
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>强积金缴费层 · 逐年供款（2026–2056）</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
:root{--bg:#0b1524;--panel:#122236;--line:rgba(148,178,210,.22);--text:#e8eef6;--muted:#8fa6c0;--gold:#d4b45a;--cyan:#5eb3d4;--coral:#e07a6a;--green:#5cba8f;--font:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
*{box-sizing:border-box}body{margin:0;font-family:var(--font);background:linear-gradient(180deg,#08111d,#0b1524 45%,#101c2e);color:var(--text);min-height:100vh}
.wrap{max-width:1280px;margin:0 auto;padding:18px 16px 40px}
header{padding:18px 20px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(18,34,54,.95),rgba(11,21,36,.9))}
.eyebrow{color:var(--gold);font-size:12px;letter-spacing:.12em;font-weight:600}
h1{margin:6px 0 0;font-size:clamp(1.2rem,2.2vw,1.65rem)}
.sub{margin:8px 0 0;color:var(--muted);font-size:.9rem;line-height:1.55;max-width:80ch}
.controls{margin-top:14px;display:grid;grid-template-columns:1.2fr 1fr;gap:12px}
@media(max-width:900px){.controls{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.panel h2{margin:0 0 10px;font-size:.88rem;color:var(--gold)}
.btns{display:flex;flex-wrap:wrap;gap:8px}
.btns button{border:1px solid rgba(143,166,192,.35);background:transparent;color:var(--text);padding:7px 14px;border-radius:999px;cursor:pointer;font:inherit}
.btns button.active{background:linear-gradient(135deg,var(--gold),#b8943a);color:#1a1408;border:none;font-weight:700}
.year-row{display:grid;grid-template-columns:72px 1fr 64px;gap:10px;align-items:center;margin-top:12px}
.year-row input{width:100%;accent-color:var(--gold)}
.year-val{font-size:1.35rem;font-weight:700;color:var(--gold);text-align:right}
label{font-size:.86rem;color:var(--muted)}
.kpis{margin-top:14px;display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
@media(max-width:980px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:linear-gradient(160deg,rgba(30,58,90,.55),rgba(11,21,36,.85));border:1px solid rgba(212,180,90,.22);border-radius:12px;padding:12px 14px}
.kpi .l{font-size:.72rem;color:var(--muted)}.kpi .v{margin-top:4px;font-size:1.15rem;font-weight:700}.kpi .v.gold{color:var(--gold)}
.grid{margin-top:14px;display:grid;grid-template-columns:1.1fr .9fr;gap:12px}
@media(max-width:980px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;min-height:340px;display:flex;flex-direction:column}
.card.wide{grid-column:1/-1}
.card h3{margin:0;font-size:.95rem}.card p{margin:6px 0 8px;font-size:.78rem;color:var(--muted);line-height:1.45}
.chart{flex:1;min-height:280px;width:100%}.chart.tall{min-height:320px}
footer{margin-top:18px;padding:14px 16px;border-top:1px solid var(--line);color:var(--muted);font-size:.78rem;line-height:1.6}
code{color:var(--gold)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">MPF CONTRIBUTION LAYER</div>
  <h1>强积金缴费层 · 逐年供款与人数（2026–2056）</h1>
  <p class="sub">缴费人数 = 人口×劳动参与率×就业率×覆盖率；强制供款含有关入息上下限规则；自愿按占总供款约 25.5% 回推。拖动时间轴查看任一年；支持情景与男/女/混合切换。</p>
</header>

<section class="controls">
  <div class="panel">
    <h2>情景 · 性别 · 年份</h2>
    <div class="btns" id="scBtns">
      <button type="button" data-v="中" class="active">基准</button>
      <button type="button" data-v="高">乐观</button>
      <button type="button" data-v="低">悲观</button>
    </div>
    <div class="btns" id="sexBtns" style="margin-top:10px">
      <button type="button" data-v="混合" class="active">混合</button>
      <button type="button" data-v="男">男</button>
      <button type="button" data-v="女">女</button>
    </div>
    <div class="year-row">
      <label for="year">时间轴</label>
      <input type="range" id="year" min="2026" max="2056" value="2026"/>
      <div class="year-val" id="yearLab">2026</div>
    </div>
  </div>
  <div class="panel">
    <h2>校准锚点</h2>
    <p style="margin:0;color:var(--muted);font-size:.85rem;line-height:1.65">
      2025 年总供款约 <b style="color:var(--text)">907 亿</b>；本模型 2026 基准约 <b style="color:var(--gold)">906 亿</b>（同量级校准）。
      有关入息下限 $7,100 / 上限 $30,000 为可替换参数。
    </p>
  </div>
</section>

<section class="kpis">
  <div class="kpi"><div class="l">缴费人数</div><div class="v gold" id="kN">—</div></div>
  <div class="kpi"><div class="l">强制性供款</div><div class="v" id="kF">—</div></div>
  <div class="kpi"><div class="l">自愿性供款</div><div class="v" id="kV">—</div></div>
  <div class="kpi"><div class="l">总供款</div><div class="v gold" id="kT">—</div></div>
  <div class="kpi"><div class="l">平均有关入息</div><div class="v" id="kY">—</div></div>
</section>

<section class="grid">
  <div class="card">
    <h3>当年缴费人数 · 分年龄组</h3>
    <p>这张图在说什么：选定年各年龄组缴费人分布；金色为 55–59 准退休衔接段。</p>
    <div class="chart" id="cBar"></div>
  </div>
  <div class="card">
    <h3>当年供款结构</h3>
    <p>这张图在说什么：强制 vs 自愿的构成；自愿约占总额 25.5%。</p>
    <div class="chart" id="cPie"></div>
  </div>
  <div class="card wide">
    <h3>总供款与缴费人数演化</h3>
    <p>这张图在说什么：三情景总供款路径 + 当前情景缴费人数（右轴）；竖线为选中年。</p>
    <div class="chart tall" id="cLine"></div>
  </div>
  <div class="card wide">
    <h3>同比增长驱动拆解</h3>
    <p>这张图在说什么：总供款同比变动有多少来自「人数变化」vs「人均入息/供款变化」。</p>
    <div class="chart tall" id="cDrv"></div>
  </div>
</section>

<footer>
  <strong>数据与假设</strong>：人口层 <code>population_ccm</code>；LFPR 参考表 230-28001 关键值；就业率=1−3.7%；覆盖率 85%[假设]；
  入息名义增速基准 3%；自愿占比 25.5%。详情见 <code>contribution_layer/C00_data_dictionary.md</code>。
</footer>
</div>
<script>
window.C_DATA=__DATA__;
(function(){
  const D=window.C_DATA;
  const AGES=["15-19","20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64"];
  const state={scenario:"中", sex:"混合", year:2026};
  const charts={};

  function fmtYi(n){return (n==null||isNaN(n))?"—":(+n).toFixed(1)+" 亿";}
  function fmtWan(n){return (n==null||isNaN(n))?"—":(n/1e4).toFixed(1)+" 万";}

  function annual(){
    return D.annual.find(r=>r["情景"]===state.scenario && r["年份"]===state.year);
  }

  function ageRows(){
    return D.contributors
      .filter(r=>r["情景"]===state.scenario && r["年份"]===state.year && r["性别"]===state.sex)
      .sort((a,b)=>AGES.indexOf(a["年龄组"])-AGES.indexOf(b["年龄组"]));
  }

  function updateKpi(){
    const a=annual(); if(!a) return;
    let n=a["缴费人数_万人"]*1e4;
    if(state.sex==="男") n=a["缴费人数_男_万人"]*1e4;
    if(state.sex==="女") n=a["缴费人数_女_万人"]*1e4;
    // 供款暂无分性别拆总额，按人数占比分摊展示
    const share = (a["缴费人数_万人"]>0)? (n/(a["缴费人数_万人"]*1e4)) : 1;
    document.getElementById("kN").textContent=fmtWan(n);
    document.getElementById("kF").textContent=fmtYi(a["年强制性供款_亿港元"]*share);
    document.getElementById("kV").textContent=fmtYi(a["年自愿性供款_亿港元"]*share);
    document.getElementById("kT").textContent=fmtYi(a["年总供款_亿港元"]*share);
    document.getElementById("kY").textContent=Math.round(a["平均有关入息_港元每月"]).toLocaleString()+" 港元/月";
  }

  function renderBar(){
    const rows=ageRows();
    charts.bar.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",borderColor:"rgba(212,180,90,.3)",textStyle:{color:"#e8eef6"},
        valueFormatter:v=>fmtWan(+v)},
      grid:{left:64,right:16,top:12,bottom:28},
      xAxis:{type:"value",axisLabel:{color:"#8fa6c0",formatter:v=>(v/1e4).toFixed(1)+"万"},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
      yAxis:{type:"category",inverse:true,data:rows.map(r=>r["年龄组"]),axisLabel:{color:"#8fa6c0",fontSize:11}},
      series:[{type:"bar",barWidth:"62%",data:rows.map(r=>({
        value:r["缴费人数_人"],
        itemStyle:{color:r["年龄组"]==="55-59"?"#d4b45a":"#5cba8f",borderRadius:[0,3,3,0]}
      }))}]
    },true);
  }

  function renderPie(){
    const a=annual(); if(!a) return;
    charts.pie.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"item",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"},
        formatter:p=>p.name+"<br/><b>"+ (+p.value).toFixed(1)+" 亿</b>（"+p.percent+"%）"},
      legend:{bottom:0,textStyle:{color:"#8fa6c0"}},
      series:[{type:"pie",radius:["40%","68%"],center:["50%","46%"],
        label:{color:"#e8eef6",formatter:"{b}\n{d}%"},
        data:[
          {name:"强制性供款",value:+a["年强制性供款_亿港元"].toFixed(2),itemStyle:{color:"#d4b45a"}},
          {name:"自愿性供款",value:+a["年自愿性供款_亿港元"].toFixed(2),itemStyle:{color:"#5eb3d4"}},
        ]}]
    },true);
  }

  function renderLine(){
    const years=[]; for(let y=2026;y<=2056;y++) years.push(y);
    const scColors={低:"#e07a6a",中:"#d4b45a",高:"#5cba8f"};
    const series=["低","中","高"].map(sc=>({
      name:({低:"悲观",中:"基准",高:"乐观"})[sc]+"·总供款",
      type:"line",smooth:true,showSymbol:false,
      lineStyle:{width:sc===state.scenario?3:1.5,type:sc===state.scenario?"solid":"dashed"},
      itemStyle:{color:scColors[sc]},
      data:years.map(y=>{const r=D.annual.find(x=>x["年份"]===y&&x["情景"]===sc);return r?r["年总供款_亿港元"]:null;})
    }));
    series.push({
      name:"缴费人数(当前情景)",type:"line",yAxisIndex:1,smooth:true,showSymbol:false,
      lineStyle:{width:2,color:"#5eb3d4"},itemStyle:{color:"#5eb3d4"},
      data:years.map(y=>{
        const r=D.annual.find(x=>x["年份"]===y&&x["情景"]===state.scenario);
        if(!r) return null;
        if(state.sex==="男") return r["缴费人数_男_万人"];
        if(state.sex==="女") return r["缴费人数_女_万人"];
        return r["缴费人数_万人"];
      })
    });
    charts.line.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"}},
      legend:{top:0,textStyle:{color:"#8fa6c0",fontSize:11}},
      grid:{left:52,right:52,top:40,bottom:36},
      xAxis:{type:"category",data:years,axisLabel:{color:"#8fa6c0",fontSize:10}},
      yAxis:[
        {type:"value",name:"亿港元",nameTextStyle:{color:"#8fa6c0"},axisLabel:{color:"#8fa6c0"},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
        {type:"value",name:"万人",nameTextStyle:{color:"#8fa6c0"},axisLabel:{color:"#8fa6c0"},splitLine:{show:false}}
      ],
      series:series.concat([{type:"line",markLine:{symbol:"none",label:{color:"#d4b45a",formatter:String(state.year)},
        lineStyle:{color:"#d4b45a",type:"dotted"},data:[{xAxis:String(state.year)}]},data:[]}])
    },true);
  }

  function renderDrv(){
    const rows=D.drivers.filter(r=>r["情景"]===state.scenario).sort((a,b)=>a["年份"]-b["年份"]);
    charts.drv.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"},
        valueFormatter:v=>(+v).toFixed(2)+" 亿"},
      legend:{top:0,textStyle:{color:"#8fa6c0"}},
      grid:{left:52,right:20,top:36,bottom:36},
      xAxis:{type:"category",data:rows.map(r=>r["年份"]),axisLabel:{color:"#8fa6c0",fontSize:10}},
      yAxis:{type:"value",name:"亿港元",axisLabel:{color:"#8fa6c0"},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
      series:[
        {name:"人数驱动",type:"bar",stack:"d",data:rows.map(r=>+r["驱动_缴费人数_亿港元"].toFixed(2)),itemStyle:{color:"#5cba8f"}},
        {name:"入息/人均驱动",type:"bar",stack:"d",data:rows.map(r=>+r["驱动_人均供款入息_亿港元"].toFixed(2)),itemStyle:{color:"#d4b45a"}},
        {name:"交叉项",type:"bar",stack:"d",data:rows.map(r=>+r["驱动_交叉项_亿港元"].toFixed(2)),itemStyle:{color:"#5eb3d4"}},
        {name:"同比变动",type:"line",data:rows.map(r=>+r["总供款同比变动_亿港元"].toFixed(2)),itemStyle:{color:"#e07a6a"},lineStyle:{width:2}}
      ]
    },true);
  }

  function refresh(){updateKpi();renderBar();renderPie();renderLine();renderDrv();}
  function bind(){
    document.querySelectorAll("#scBtns button").forEach(b=>b.addEventListener("click",()=>{
      document.querySelectorAll("#scBtns button").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.scenario=b.dataset.v;refresh();
    }));
    document.querySelectorAll("#sexBtns button").forEach(b=>b.addEventListener("click",()=>{
      document.querySelectorAll("#sexBtns button").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.sex=b.dataset.v;refresh();
    }));
    const y=document.getElementById("year");
    y.addEventListener("input",()=>{state.year=+y.value;document.getElementById("yearLab").textContent=String(state.year);refresh();});
    window.addEventListener("resize",()=>Object.values(charts).forEach(c=>c.resize()));
  }
  function init(){
    charts.bar=echarts.init(document.getElementById("cBar"));
    charts.pie=echarts.init(document.getElementById("cPie"));
    charts.line=echarts.init(document.getElementById("cLine"));
    charts.drv=echarts.init(document.getElementById("cDrv"));
    bind();refresh();
  }
  init();
})();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
OUT.write_text(html, encoding="utf-8")
print("Wrote", OUT, "MB", round(OUT.stat().st_size / 1e6, 2))
