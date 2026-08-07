# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path(__file__).parent

SCRIPT_TMPL = """
  <div id="kgPageMount" class="kg-embed" style="display:none;" data-module="{mod}"></div>
  <script src="knowledge-graph-data.js"></script>
  <script src="knowledge-graph-app.js"></script>
  <script>
  (function () {{
    var mod = "{mod}";
    var kg = null;
    var mount = document.getElementById("kgPageMount");
    function setView(mode) {{
      document.querySelectorAll(".view-btn").forEach(function (b) {{
        b.classList.toggle("active", b.getAttribute("data-view") === mode);
      }});
      if (mode === "graph") {{
        document.body.classList.add("kg-graph-mode");
        mount.style.display = "block";
        mount.classList.add("is-on");
        if (!kg) {{
          kg = window.initKnowledgeGraph({{ root: mount, startModule: mod }});
        }}
      }} else {{
        document.body.classList.remove("kg-graph-mode");
        mount.style.display = "none";
        mount.classList.remove("is-on");
      }}
    }}
    document.querySelectorAll(".view-btn").forEach(function (btn) {{
      btn.addEventListener("click", function () {{
        setView(btn.getAttribute("data-view"));
      }});
    }});
    if (location.hash === "#graph" || /[?&]view=graph/.test(location.search)) {{
      setView("graph");
    }}
  }})();
  </script>
"""

PAGES = [
    ("metrics.html", "metric"),
    ("methodology.html", "methodology"),
    ("interview.html", "business_problem"),
]

for name, mod in PAGES:
    p = ROOT / name
    t = p.read_text(encoding="utf-8")
    new_script = SCRIPT_TMPL.format(mod=mod)
    idx = t.find('<div id="kgPageMount"')
    if idx < 0:
        print("skip no mount", name)
        continue
    end = t.find('<script src="common.js"></script>', idx)
    if end < 0:
        end = t.rfind("</body>")
    t2 = t[:idx] + new_script + "\n" + t[end:]
    # ensure view switch points label 知识图谱
    t2 = t2.replace(">知识图谱</button>", ">知识图谱</button>")
    p.write_text(t2, encoding="utf-8")
    print("ok", name)

# index tool card
idxp = ROOT / "index.html"
it = idxp.read_text(encoding="utf-8")
it2 = it.replace(
    'href="metrics.html?view=graph"',
    'href="knowledge-graph.html"',
)
# simplify nav: knowledge graph primary, optional keep 行业图谱
if "行业图谱" in it2 and "knowledge-graph.html" in it2:
    pass
idxp.write_text(it2, encoding="utf-8")
print("index ok")

# graph.html soft redirect banner at top - optional rewrite link in nav already
gp = ROOT / "graph.html"
if gp.exists():
    gt = gp.read_text(encoding="utf-8")
    if "knowledge-graph.html" not in gt[:800]:
        # ensure nav has knowledge-graph
        pass
    print("graph.html kept as 行业图谱")
