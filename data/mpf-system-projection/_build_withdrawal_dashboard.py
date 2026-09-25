# -*- coding: utf-8 -*-
"""Build withdrawal + asset evolution dashboard."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "withdrawal_asset_layer"
OUT = ROOT / "withdrawal_asset_dashboard.html"

w01 = pd.read_csv(SRC / "W01_retirement_withdrawals.csv")
w02 = pd.read_csv(SRC / "W02_other_withdrawals.csv")
w03 = pd.read_csv(SRC / "W03_asset_evolution.csv")
w04 = pd.read_csv(SRC / "W04_inflection_points.csv")

# slim
w01s = w01[["年份", "性别", "新达65岁人数_人", "退休提取人数_人", "退休提取金额_亿港元",
            "人均账户余额_万港元", "情景", "情景标签"]].copy()
w02s = w02[w02["提取理由"] != "其他合计"][["年份", "提取理由", "金额_亿港元", "情景", "情景标签"]]
w03s = w03.copy()

payload = {
    "retire": w01s.to_dict(orient="records"),
    "other": w02s.to_dict(orient="records"),
    "asset": w03s.to_dict(orient="records"),
    "inflection": w04.to_dict(orient="records"),
    "meta": {"a0": 16700, "anchor_retire_2025": 195.66},
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>强积金领取层与资产演化 · 2026–2056</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
:root{--bg:#0b1524;--panel:#122236;--line:rgba(148,178,210,.22);--text:#e8eef6;--muted:#8fa6c0;--gold:#d4b45a;--cyan:#5eb3d4;--coral:#e07a6a;--green:#5cba8f;--font:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
*{box-sizing:border-box}body{margin:0;font-family:var(--font);background:linear-gradient(180deg,#08111d,#0b1524 40%,#101c2e);color:var(--text);min-height:100vh}
.wrap{max-width:1280px;margin:0 auto;padding:18px 16px 40px}
header{padding:18px 20px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(18,34,54,.95),rgba(11,21,36,.9))}
.eyebrow{color:var(--gold);font-size:12px;letter-spacing:.12em;font-weight:600}
h1{margin:6px 0 0;font-size:clamp(1.2rem,2.2vw,1.65rem)}
.sub{margin:8px 0 0;color:var(--muted);font-size:.9rem;line-height:1.55;max-width:82ch}
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
@media(max-width:1100px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:linear-gradient(160deg,rgba(30,58,90,.55),rgba(11,21,36,.85));border:1px solid rgba(212,180,90,.22);border-radius:12px;padding:12px 14px}
.kpi .l{font-size:.72rem;color:var(--muted)}.kpi .v{margin-top:4px;font-size:1.1rem;font-weight:700}.kpi .v.gold{color:var(--gold)}.kpi .v.warn{color:var(--coral)}
.grid{margin-top:14px;display:grid;grid-template-columns:1.1fr .9fr;gap:12px}
@media(max-width:980px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;min-height:340px;display:flex;flex-direction:column}
.card.wide{grid-column:1/-1}
.card h3{margin:0;font-size:.95rem}.card p{margin:6px 0 8px;font-size:.78rem;color:var(--muted);line-height:1.45}
.chart{flex:1;min-height:280px}.chart.tall{min-height:330px}
footer{margin-top:18px;padding:14px 16px;border-top:1px solid var(--line);color:var(--muted);font-size:.78rem;line-height:1.6}
code{color:var(--gold)}
.flags{margin-top:10px;font-size:.82rem;color:var(--muted);line-height:1.55}
.flags b{color:var(--text)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">MPF WITHDRAWAL &amp; ASSET EVOLUTION</div>
  <h1>领取层与制度总资产演化（2026–2056）</h1>
  <p class="sub">退休提取人数 ≈ (60–64岁人口)/5 × 提取比例；总资产 A<sub>t+1</sub>=A<sub>t</sub>(1+r)+C−W。识别资产峰值与「提取&gt;供款」「提取&gt;供款+回报」拐点。</p>
</header>

<section class="controls">
  <div class="panel">
    <h2>情景 · 性别 · 年份</h2>
    <div class="btns" id="scBtns">
      <button type="button" data-v="中" class="active">基准 4.9%</button>
      <button type="button" data-v="高">乐观 7.0%</button>
      <button type="button" data-v="低">保守 3.0%</button>
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
    <h2>拐点速览（当前情景）</h2>
    <div class="flags" id="flags">—</div>
  </div>
</section>

<section class="kpis">
  <div class="kpi"><div class="l">总资产（期末）</div><div class="v gold" id="kA">—</div></div>
  <div class="kpi"><div class="l">退休提取人数</div><div class="v" id="kN">—</div></div>
  <div class="kpi"><div class="l">总提取</div><div class="v" id="kW">—</div></div>
  <div class="kpi"><div class="l">总供款</div><div class="v" id="kC">—</div></div>
  <div class="kpi"><div class="l">经济净流入</div><div class="v" id="kE">—</div></div>
</section>

<section class="grid">
  <div class="card">
    <h3>当年提取结构</h3>
    <p>这张图在说什么：退休提取 vs 其他理由（提早退休、离港、抵销等）的金额构成。</p>
    <div class="chart" id="cPie"></div>
  </div>
  <div class="card">
    <h3>当年现金流瀑布</h3>
    <p>这张图在说什么：期初资产 → 投资损益 → 供款 → 提取 → 期末资产。</p>
    <div class="chart" id="cWf"></div>
  </div>
  <div class="card wide">
    <h3>总资产三情景路径</h3>
    <p>这张图在说什么：保守/基准/乐观下制度总资产如何演化；竖线为选中年。</p>
    <div class="chart tall" id="cLine"></div>
  </div>
  <div class="card wide">
    <h3>供款 vs 提取 vs 投资回报</h3>
    <p>这张图在说什么：何时提取超过供款（净现金流拐点），以及投资回报能否继续「托住」资产。</p>
    <div class="chart tall" id="cFlow"></div>
  </div>
</section>

<footer>
  初值 A<sub>2026</sub>=16,700 亿；账户约 1,100 万。退休提取校准贴近 2025 年约 195.66 亿。
  数据：<code>withdrawal_asset_layer/</code> · 字典 <code>W00_data_dictionary.md</code>。
</footer>
</div>
<script>
window.W_DATA=__DATA__;
(function(){
  const D=window.W_DATA;
  const state={scenario:"中", sex:"混合", year:2026};
  const charts={};
  const scName={低:"保守",中:"基准",高:"乐观"};

  function fmtYi(n){if(n==null||isNaN(n))return "—"; return Math.abs(n)>=1000?(n/1000).toFixed(2)+" 千亿":(+n).toFixed(1)+" 亿";}
  function fmtN(n){if(n==null||isNaN(n))return "—"; return n>=1e4?(n/1e4).toFixed(2)+" 万":Math.round(n).toLocaleString();}

  function assetRow(){return D.asset.find(r=>r["情景"]===state.scenario&&r["年份"]===state.year);}
  function retireRow(){return D.retire.find(r=>r["情景"]===state.scenario&&r["年份"]===state.year&&r["性别"]===state.sex);}
  function inf(){return D.inflection.find(r=>r["情景"]===state.scenario);}

  function updateKpi(){
    const a=assetRow(), r=retireRow(), f=inf();
    if(!a||!r) return;
    document.getElementById("kA").textContent=fmtYi(a["总资产_期末_亿港元"]);
    document.getElementById("kN").textContent=fmtN(r["退休提取人数_人"]);
    document.getElementById("kW").textContent=fmtYi(a["总提取_亿港元"]);
    document.getElementById("kC").textContent=fmtYi(a["总供款_亿港元"]);
    const e=a["经济净流入_含回报_亿港元"];
    const el=document.getElementById("kE");
    el.textContent=fmtYi(e);
    el.className="v "+(e<0?"warn":"gold");
    if(f){
      document.getElementById("flags").innerHTML=
        "资产峰值：<b>"+f["资产峰值年份"]+"</b><br/>"+
        "提取&gt;供款首年：<b>"+f["净现金流拐点年份_提取大于供款"]+"</b><br/>"+
        "提取&gt;供款+回报首年：<b>"+f["经济净流入拐点年份_提取大于供款加回报"]+"</b><br/>"+
        "2056末资产：<b>"+fmtYi(+f["期末资产_亿港元"])+"</b>";
    }
  }

  function renderPie(){
    const a=assetRow(); if(!a) return;
    const others=D.other.filter(r=>r["情景"]===state.scenario&&r["年份"]===state.year);
    const data=[{name:"退休提取",value:+a["退休提取_亿港元"].toFixed(2),itemStyle:{color:"#d4b45a"}}]
      .concat(others.map((o,i)=>({name:o["提取理由"],value:+o["金额_亿港元"].toFixed(2),
        itemStyle:{color:["#e07a6a","#5eb3d4","#9b8cff","#5cba8f"][i%4]}})));
    charts.pie.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"item",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"},
        formatter:p=>p.name+"<br/><b>"+p.value+" 亿</b>（"+p.percent+"%）"},
      legend:{type:"scroll",bottom:0,textStyle:{color:"#8fa6c0",fontSize:10}},
      series:[{type:"pie",radius:["36%","64%"],center:["50%","45%"],label:{color:"#e8eef6",fontSize:11},data}]
    },true);
  }

  function renderWf(){
    const a=assetRow(); if(!a) return;
    const steps=[
      {name:"期初资产",v:a["总资产_期初_亿港元"]},
      {name:"投资损益",v:a["投资损益_亿港元"]},
      {name:"总供款",v:a["总供款_亿港元"]},
      {name:"总提取",v:-a["总提取_亿港元"]},
      {name:"期末资产",v:a["总资产_期末_亿港元"]},
    ];
    let run=0; const help=[], disp=[], col=[];
    steps.forEach((s,i)=>{
      if(i===0||i===steps.length-1){help.push(0);disp.push(s.v);col.push(i===0?"#5eb3d4":"#d4b45a");run=s.v;}
      else if(s.v>=0){help.push(run);disp.push(s.v);col.push("#5cba8f");run+=s.v;}
      else{help.push(run+s.v);disp.push(-s.v);col.push("#e07a6a");run+=s.v;}
    });
    charts.wf.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"},
        formatter:ps=>{const i=ps[0].dataIndex;return steps[i].name+"<br/><b>"+(+steps[i].v).toFixed(1)+" 亿</b>";}},
      grid:{left:52,right:12,top:20,bottom:48},
      xAxis:{type:"category",data:steps.map(s=>s.name),axisLabel:{color:"#8fa6c0",fontSize:10,interval:0,rotate:20}},
      yAxis:{type:"value",axisLabel:{color:"#8fa6c0",fontSize:10},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
      series:[
        {type:"bar",stack:"w",data:help,itemStyle:{color:"transparent"},silent:true},
        {type:"bar",stack:"w",barWidth:"48%",data:disp.map((v,i)=>({value:v,itemStyle:{color:col[i],borderRadius:[3,3,0,0]}}))}
      ]
    },true);
  }

  function renderLine(){
    const years=[];for(let y=2026;y<=2056;y++)years.push(y);
    const colors={低:"#e07a6a",中:"#d4b45a",高:"#5cba8f"};
    const series=["低","中","高"].map(sc=>({
      name:scName[sc],type:"line",smooth:true,showSymbol:false,
      lineStyle:{width:sc===state.scenario?3:1.5,type:sc===state.scenario?"solid":"dashed"},
      itemStyle:{color:colors[sc]},
      data:years.map(y=>{const r=D.asset.find(x=>x["年份"]===y&&x["情景"]===sc);return r?r["总资产_期末_亿港元"]:null;})
    }));
    charts.line.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"},valueFormatter:v=>fmtYi(+v)},
      legend:{top:0,textStyle:{color:"#8fa6c0"}},
      grid:{left:60,right:24,top:36,bottom:36},
      xAxis:{type:"category",data:years,axisLabel:{color:"#8fa6c0",fontSize:10}},
      yAxis:{type:"value",axisLabel:{color:"#8fa6c0",formatter:v=>v>=1000?(v/1000).toFixed(0)+"k":v},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
      series:series.concat([{type:"line",markLine:{symbol:"none",label:{color:"#d4b45a",formatter:String(state.year)},
        lineStyle:{color:"#d4b45a",type:"dotted"},data:[{xAxis:String(state.year)}]},data:[]}])
    },true);
  }

  function renderFlow(){
    const rows=D.asset.filter(r=>r["情景"]===state.scenario).sort((a,b)=>a["年份"]-b["年份"]);
    charts.flow.setOption({
      backgroundColor:"transparent",
      tooltip:{trigger:"axis",backgroundColor:"rgba(11,21,36,.92)",textStyle:{color:"#e8eef6"}},
      legend:{top:0,textStyle:{color:"#8fa6c0"}},
      grid:{left:52,right:20,top:36,bottom:36},
      xAxis:{type:"category",data:rows.map(r=>r["年份"]),axisLabel:{color:"#8fa6c0",fontSize:10}},
      yAxis:{type:"value",name:"亿港元",axisLabel:{color:"#8fa6c0"},splitLine:{lineStyle:{color:"rgba(148,178,210,.12)"}}},
      series:[
        {name:"总供款",type:"line",showSymbol:false,data:rows.map(r=>+r["总供款_亿港元"].toFixed(1)),itemStyle:{color:"#5cba8f"},areaStyle:{opacity:.15}},
        {name:"总提取",type:"line",showSymbol:false,data:rows.map(r=>+r["总提取_亿港元"].toFixed(1)),itemStyle:{color:"#e07a6a"},areaStyle:{opacity:.12}},
        {name:"投资损益",type:"line",showSymbol:false,data:rows.map(r=>+r["投资损益_亿港元"].toFixed(1)),itemStyle:{color:"#d4b45a"}},
        {name:"经济净流入",type:"line",showSymbol:false,lineStyle:{width:2,type:"dotted"},data:rows.map(r=>+r["经济净流入_含回报_亿港元"].toFixed(1)),itemStyle:{color:"#5eb3d4"}}
      ]
    },true);
  }

  function refresh(){updateKpi();renderPie();renderWf();renderLine();renderFlow();}
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
    charts.pie=echarts.init(document.getElementById("cPie"));
    charts.wf=echarts.init(document.getElementById("cWf"));
    charts.line=echarts.init(document.getElementById("cLine"));
    charts.flow=echarts.init(document.getElementById("cFlow"));
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
