# -*- coding: utf-8 -*-
"""生成养老金全链路业务讲解页（从 CSV 嵌入数据）。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)


def _read_csv(name: str) -> list[dict]:
    path = ROOT / name
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    stages = _read_csv("role_stage_matrix.csv")
    tickets = _read_csv("ticket_interpretation.csv")
    data = json.dumps({"stages": stages, "tickets": tickets}, ensure_ascii=False)
    html = _HTML.replace("__DATA__", data)
    (ROOT / "business_chain_dashboard.html").write_text(html, encoding="utf-8")
    (OUT / "business_chain_dashboard.html").write_text(html, encoding="utf-8")
    (OUT / "B01_stages.json").write_text(
        json.dumps(stages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "B02_tickets.json").write_text(
        json.dumps(tickets, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"stages={len(stages)} tickets={len(tickets)}")
    print(ROOT / "business_chain_dashboard.html")


_HTML = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>养老金全链路 · 四角色业务诉求</title>
<style>
:root{
  --navy:#1a3a5c; --navy-2:#244a73; --gold:#c9a227; --bg:#f4f5f7; --card:#fff;
  --text:#1e293b; --muted:#64748b; --line:#e2e8f0;
  --er:#3b82a0; --mb:#2f9e7a; --tr:#d4655a; --pf:#8b6bb5;
  --font:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
}
*{box-sizing:border-box}
body{margin:0;font-family:var(--font);background:var(--bg);color:var(--text)}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px 48px}
.hero{
  background:linear-gradient(135deg,var(--navy),var(--navy-2));color:#fff;
  border-radius:14px;padding:20px 22px;box-shadow:0 8px 24px rgba(26,58,92,.16);
}
.eyebrow{font-size:.72rem;letter-spacing:.12em;color:#e8d48a;font-weight:600}
h1{margin:6px 0 0;font-size:1.4rem}
.hero p{margin:8px 0 0;opacity:.92;font-size:.88rem;line-height:1.55;max-width:78ch}
.verdict{
  margin-top:12px;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;
}
@media(max-width:800px){.verdict{grid-template-columns:1fr 1fr}}
.verdict .v{
  background:rgba(255,255,255,.1);border-radius:10px;padding:10px 12px;font-size:.78rem;line-height:1.45;
}
.verdict strong{display:block;color:#e8d48a;margin-bottom:4px;font-size:.72rem;letter-spacing:.06em}
details.how{
  margin-top:14px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;
}
details.how>summary{
  cursor:pointer;list-style:none;padding:14px 16px;font-weight:700;color:var(--navy);
  display:flex;align-items:center;gap:10px;
}
details.how>summary::-webkit-details-marker{display:none}
.badge{font-size:.68rem;background:var(--gold);color:#1a1405;padding:3px 8px;border-radius:999px}
.how-body{padding:0 16px 16px;border-top:1px solid var(--line);font-size:.84rem;color:var(--muted);line-height:1.6}
.how-body h3{color:var(--navy);font-size:.9rem;margin:14px 0 6px}
.flow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}
.pill{background:rgba(201,162,39,.15);border:1px solid rgba(201,162,39,.4);padding:4px 9px;border-radius:999px;font-size:.76rem;font-weight:600;color:var(--navy)}
.arr{color:var(--gold);font-weight:700}
.panel{margin-top:14px;display:grid;grid-template-columns:1fr 1.2fr;gap:12px}
@media(max-width:900px){.panel{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h2{margin:0 0 8px;font-size:.95rem;color:var(--navy)}
.hint{font-size:.78rem;color:var(--muted);margin:0 0 10px;line-height:1.45}
.roles{display:flex;flex-wrap:wrap;gap:6px}
.roles button{
  border:1px solid var(--line);background:#fff;color:var(--navy);padding:7px 12px;border-radius:999px;
  cursor:pointer;font:inherit;font-size:.8rem;
}
.roles button.active{color:#fff;border-color:transparent}
.roles button[data-role="all"].active{background:var(--navy)}
.roles button[data-role="雇主"].active{background:var(--er)}
.roles button[data-role="参保人"].active{background:var(--mb)}
.roles button[data-role="受托人"].active{background:var(--tr)}
.roles button[data-role="平台"].active{background:var(--pf)}
.stages{display:grid;gap:8px;max-height:520px;overflow:auto}
.stage{
  border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fafbfc;font-size:.78rem;line-height:1.45;
}
.stage h3{margin:0 0 4px;font-size:.86rem;color:var(--navy)}
.stage .meta{color:var(--muted);margin-bottom:6px}
.stage .cell{margin-top:4px}
.stage .cell b{color:var(--navy)}
.stage.dim{opacity:.35}
.tickets{display:grid;gap:8px;max-height:620px;overflow:auto}
.ticket{
  border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fff;font-size:.78rem;line-height:1.45;
}
.ticket.hidden{display:none}
.ticket .q{font-weight:700;color:var(--navy);margin:0 0 6px}
.tags{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}
.tag{font-size:.68rem;padding:2px 7px;border-radius:999px;background:#eef2f5;color:var(--muted)}
.tag.er{background:rgba(59,130,160,.15);color:var(--er)}
.tag.mb{background:rgba(47,158,122,.15);color:var(--mb)}
.tag.tr{background:rgba(212,101,90,.15);color:var(--tr)}
.tag.pf{background:rgba(139,107,181,.15);color:var(--pf)}
.ticket dl{margin:0;display:grid;gap:4px}
.ticket dt{font-size:.68rem;color:var(--muted)}
.ticket dd{margin:0}
.search{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;margin-bottom:10px}
.kpis{margin-top:12px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:800px){.kpis{grid-template-columns:1fr 1fr}}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.kpi .l{font-size:.72rem;color:var(--muted)}
.kpi .v{margin-top:4px;font-size:1.15rem;font-weight:700;color:var(--navy)}
footer{margin-top:18px;padding-top:12px;border-top:1px solid var(--line);font-size:.76rem;color:var(--muted);line-height:1.55}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">JD 对齐补充 · 对象一～四之外</div>
    <h1>养老金全链路业务流程 · 四角色诉求解读</h1>
    <p>对照岗位要求「受托人、雇主、参保人、平台全流程，精准解读业务诉求」。现成宏观/充足度建模<strong>未覆盖</strong>此条；本页补流程地图 + 20 条诉求拆解。</p>
    <div class="verdict">
      <div class="v"><strong>覆盖判定</strong>部分覆盖：钱与替代率强；角色流程弱</div>
      <div class="v"><strong>雇主</strong>规则参数有；开户→月供→催收链此前缺</div>
      <div class="v"><strong>受托人/平台</strong>面试包写明未建模；此处补业务叙事</div>
      <div class="v"><strong>参保人</strong>充足度有；办业务/工单解读此前缺</div>
    </div>
  </div>

  <details class="how" open>
    <summary><span class="badge">思路</span>这个补充模块怎么用、和对象一～四什么关系</summary>
    <div class="how-body">
      <h3>岗位要什么 vs 仓库原有什么</h3>
      <p>原有对象一～四回答「池子多大、综援多少、个人够不够、年金怎么对冲长寿」。岗位这句话要的是<strong>运营与业务理解</strong>：谁发起、谁审批、卡在哪、原话怎么翻译成可查指标。</p>
      <h3>主链路</h3>
      <div class="flow">
        <span class="pill">雇主登记</span><span class="arr">→</span>
        <span class="pill">成员开户</span><span class="arr">→</span>
        <span class="pill">供款入账</span><span class="arr">→</span>
        <span class="pill">投资服务</span><span class="arr">→</span>
        <span class="pill">转移整合</span><span class="arr">→</span>
        <span class="pill">提取支付</span><span class="arr">→</span>
        <span class="pill">投诉合规</span>
      </div>
      <p>每一环都有四角色分工；平台（eMPF）横贯标准化。宏观模型把 eMPF 当费率，本页把平台当<strong>流程角色</strong>。</p>
      <h3>解读四步（背这个）</h3>
      <p>① 定角色 → ② 定阶段 → ③ 定对象（账户/款项/时效/资格/系统）→ ④ 定证据（指标或模型表）。下方工单卡按此结构写好。</p>
    </div>
  </details>

  <div class="kpis" id="kpis"></div>

  <div class="panel">
    <div class="card">
      <h2>① 按角色看生命周期职责</h2>
      <p class="hint">点角色高亮其主责阶段；「成功标准 / 失败诉求」用于面试举例。</p>
      <div class="roles" id="role-btns">
        <button type="button" data-role="all" class="active">全部</button>
        <button type="button" data-role="雇主">雇主</button>
        <button type="button" data-role="参保人">参保人</button>
        <button type="button" data-role="受托人">受托人</button>
        <button type="button" data-role="平台">平台</button>
      </div>
      <div class="stages" id="stages" style="margin-top:10px"></div>
    </div>
    <div class="card">
      <h2>② 业务诉求解读台</h2>
      <p class="hint">搜索原话或按角色筛选；每张卡含解读要点、先查什么、建议动作、挂到哪张指标/模型。</p>
      <input class="search" id="q" type="search" placeholder="搜索：到账、对冲、合并账户、eMPF…"/>
      <div class="roles" id="ticket-roles" style="margin-bottom:10px">
        <button type="button" data-trole="all" class="active">全部诉求</button>
        <button type="button" data-trole="雇主">雇主</button>
        <button type="button" data-trole="参保人">参保人</button>
        <button type="button" data-trole="受托人">受托人</button>
        <button type="button" data-trole="平台">平台</button>
      </div>
      <div class="tickets" id="tickets"></div>
    </div>
  </div>

  <footer>
    文档：<code>00_coverage_vs_jd.md</code> · <code>01_full_chain_concepts.md</code> ·
    数据：<code>role_stage_matrix.csv</code> · <code>ticket_interpretation.csv</code> ·
    再生：<code>python build_dashboard.py</code> · 教学向，非正式合规意见
  </footer>
</div>
<script>
const DATA = __DATA__;
const roleKey = {
  "雇主": "雇主_职责",
  "参保人": "参保人_职责",
  "受托人": "受托人_职责",
  "平台": "平台_职责",
};
const tagClass = { "雇主":"er", "参保人":"mb", "受托人":"tr", "平台":"pf" };
let role = "all";
let trole = "all";
let q = "";

function renderKpis(){
  document.getElementById("kpis").innerHTML = `
    <div class="kpi"><div class="l">生命周期阶段</div><div class="v">${DATA.stages.length}</div></div>
    <div class="kpi"><div class="l">诉求解读样本</div><div class="v">${DATA.tickets.length}</div></div>
    <div class="kpi"><div class="l">覆盖角色</div><div class="v">4</div></div>
    <div class="kpi"><div class="l">与宏观模型</div><div class="v">衔接表</div></div>`;
}

function renderStages(){
  const box = document.getElementById("stages");
  const sorted = [...DATA.stages].sort((a,b)=>Number(a.排序)-Number(b.排序));
  box.innerHTML = sorted.map(s => {
    const focus = role === "all" ? null : s[roleKey[role]];
    const dim = role !== "all" && (!focus || focus === "—" || focus.startsWith("—"));
    const duty = role === "all"
      ? `<div class="cell"><b>雇主</b> ${s.雇主_职责}</div>
         <div class="cell"><b>参保人</b> ${s.参保人_职责}</div>
         <div class="cell"><b>受托人</b> ${s.受托人_职责}</div>
         <div class="cell"><b>平台</b> ${s.平台_职责}</div>`
      : `<div class="cell"><b>${role}主责</b> ${focus || "—"}</div>`;
    return `<div class="stage ${dim?"dim":""}">
      <h3>${s.阶段ID} · ${s.阶段名称}</h3>
      <div class="meta">成功：${s.成功标准}</div>
      ${duty}
      <div class="cell"><b>失败诉求</b> ${s.失败时典型诉求}</div>
      <div class="cell"><b>衔接</b> ${s.衔接现有建模}</div>
    </div>`;
  }).join("");
}

function matchTicket(t){
  if (trole !== "all" && t.主角色 !== trole && !(t.涉及角色||"").includes(trole)) return false;
  if (!q) return true;
  const blob = [t.原话诉求,t.解读要点,t.根因假设_优先查,t.建议动作,t.关联指标或模型,t.所处阶段].join(" ");
  return blob.toLowerCase().includes(q.toLowerCase());
}

function renderTickets(){
  const box = document.getElementById("tickets");
  const list = DATA.tickets.filter(matchTicket);
  box.innerHTML = list.map(t => {
    const roles = [t.主角色].concat((t.涉及角色||"").split("|").filter(Boolean));
    const tags = [...new Set(roles)].map(r => `<span class="tag ${tagClass[r]||""}">${r}</span>`).join("");
    return `<div class="ticket">
      <div class="q">${t.诉求ID} · 「${t.原话诉求}」</div>
      <div class="tags">${tags}<span class="tag">${t.所处阶段}</span><span class="tag">${t.难度}</span></div>
      <dl>
        <dt>解读要点</dt><dd>${t.解读要点}</dd>
        <dt>优先查</dt><dd>${t.根因假设_优先查}</dd>
        <dt>建议动作</dt><dd>${t.建议动作}</dd>
        <dt>挂到</dt><dd>${t.关联指标或模型}</dd>
      </dl>
    </div>`;
  }).join("") || '<div class="hint">无匹配诉求，试试换角色或清空搜索。</div>';
}

document.getElementById("role-btns").addEventListener("click", e => {
  const btn = e.target.closest("button[data-role]");
  if (!btn) return;
  role = btn.dataset.role;
  document.querySelectorAll("#role-btns button").forEach(b => b.classList.toggle("active", b===btn));
  renderStages();
});
document.getElementById("ticket-roles").addEventListener("click", e => {
  const btn = e.target.closest("button[data-trole]");
  if (!btn) return;
  trole = btn.dataset.trole;
  document.querySelectorAll("#ticket-roles button").forEach(b => b.classList.toggle("active", b===btn));
  renderTickets();
});
document.getElementById("q").addEventListener("input", e => { q = e.target.value.trim(); renderTickets(); });

renderKpis();
renderStages();
renderTickets();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
