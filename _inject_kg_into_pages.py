# -*- coding: utf-8 -*-
"""向 metrics / methodology / interview 注入全屏知识图谱视图切换。"""
from pathlib import Path

ROOT = Path(__file__).parent

HEAD_SNIPPET = """
  <link rel="stylesheet" href="knowledge-graph-embed.css" />
  <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
"""

SWITCH_HTML = """
  <div class="view-switch-wrap">
    <div class="view-switch" role="tablist">
      <button type="button" class="view-btn active" data-view="list">列表浏览</button>
      <button type="button" class="view-btn" data-view="graph">知识图谱</button>
    </div>
  </div>
"""

MOUNT_HTML = """
  <div id="kgPageMount" class="kg-embed" style="display:none;" data-plate="{plate}"></div>
  <script src="knowledge-graph-data.js"></script>
  <script src="knowledge-graph-app.js"></script>
  <script>
  (function () {{
    var plate = "{plate}";
    var kg = null;
    var mount = document.getElementById("kgPageMount");
    var switchWrap = document.querySelector(".view-switch-wrap");
    function setView(mode) {{
      document.querySelectorAll(".view-btn").forEach(function (b) {{
        b.classList.toggle("active", b.getAttribute("data-view") === mode);
      }});
      if (mode === "graph") {{
        document.body.classList.add("kg-graph-mode");
        mount.style.display = "flex";
        mount.classList.add("is-on");
        if (!kg) {{
          kg = window.initKnowledgeGraph({{
            root: mount,
            plate: plate,
            showTabs: true,
            injectShell: true
          }});
        }} else if (kg.resize) {{
          setTimeout(function () {{ kg.resize(); }}, 80);
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
    ("metrics.html", "metric", "指标字典"),
    ("methodology.html", "methodology", "方法论"),
    ("interview.html", "business_problem", "业务问题拆解"),
]


def inject(path: Path, plate: str):
    t = path.read_text(encoding="utf-8")
    if "knowledge-graph-embed.css" in t and "kgPageMount" in t:
        print("skip (already)", path.name)
        return

    if "knowledge-graph-embed.css" not in t:
        if "</head>" in t:
            t = t.replace("</head>", HEAD_SNIPPET + "\n</head>", 1)
        else:
            raise SystemExit(f"no head in {path}")

    # insert view switch after </nav>
    if "view-switch-wrap" not in t:
        idx = t.find("</nav>")
        if idx < 0:
            raise SystemExit(f"no nav in {path}")
        insert_at = idx + len("</nav>")
        t = t[:insert_at] + "\n" + SWITCH_HTML + t[insert_at:]

    # before common.js or </body>
    mount = MOUNT_HTML.format(plate=plate)
    if "kgPageMount" not in t:
        if '<script src="common.js"></script>' in t:
            t = t.replace(
                '<script src="common.js"></script>',
                mount + '\n  <script src="common.js"></script>',
                1,
            )
        elif "</body>" in t:
            t = t.replace("</body>", mount + "\n</body>", 1)
        else:
            t += mount

    # mark list sections - wrap isn't needed if CSS hides by selectors
    # ensure metrics active nav stays
    path.write_text(t, encoding="utf-8")
    print("updated", path.name, "plate=", plate)


def main():
    for name, plate, _ in PAGES:
        inject(ROOT / name, plate)


if __name__ == "__main__":
    main()
