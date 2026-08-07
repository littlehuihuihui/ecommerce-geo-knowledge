/* 知识图谱 2.0 — 三阶段导航检索 */
(function () {
  "use strict";

  var TYPE = {
    business_problem: { key: "business_problem", label: "业务问题", color: "#f97316", dark: "#ea580c", glow: "rgba(249,115,22,0.55)", cls: "bp", icon: "❓" },
    methodology: { key: "methodology", label: "分析方法", color: "#10b981", dark: "#059669", glow: "rgba(16,185,129,0.55)", cls: "md", icon: "📐" },
    metric: { key: "metric", label: "指标字典", color: "#3b82f6", dark: "#2563eb", glow: "rgba(59,130,246,0.55)", cls: "mt", icon: "📊" }
  };

  /** 行业切换：通用 = 全量；单行业过滤问题/指标（方法始终通用） */
  var INDUSTRY_ALIAS = {
    general: ["general"],
    retail: ["retail"],
    ecommerce: ["ecommerce"],
    finance: ["finance"],
    game: ["game"],
    saas: ["saas"],
    manufacturing: ["manufacturing"],
    "live-ecommerce": ["live-ecommerce", "liveecommerce"],
    "local-life": ["local-life", "locallife"],
    content: ["content"],
    logistics: ["logistics"],
    newenergy: ["newenergy"],
    tourism: ["tourism"],
    healthcare: ["healthcare"],
    fmcg: ["fmcg"]
  };

  var INDUSTRY_OPTIONS = [
    ["general", "通用数据分析"],
    ["ecommerce", "电商"],
    ["retail", "零售"],
    ["finance", "金融"],
    ["game", "游戏"],
    ["saas", "SaaS"],
    ["manufacturing", "制造"],
    ["live-ecommerce", "直播电商"],
    ["local-life", "本地生活"],
    ["content", "内容/短视频"],
    ["logistics", "物流"],
    ["newenergy", "新能源"],
    ["tourism", "文旅"],
    ["healthcare", "医疗健康"],
    ["fmcg", "快消"]
  ];

  var METHOD_CATS = ["user", "marketing", "operation", "finance", "strategy", "quality", "statistics", "datascience"];

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function trunc(s, n) {
    s = String(s || "");
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }
  function hilite(text, q) {
    if (!q) return esc(text);
    var i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc(text);
    return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
  }

  function buildPageHtml() {
    return (
      '<div class="kg2-page" id="kg2Root">' +
      '  <div class="kg2-bgfx"><div class="kg2-particles" id="kg2Particles"></div></div>' +
      '  <div class="kg2-stage" id="kg2Stage"></div>' +
      "</div>"
    );
  }

  function initKnowledgeGraph(userOpts) {
    var DATA = window.KNOWLEDGE_GRAPH_DATA;
    if (!DATA || typeof vis === "undefined") {
      console.error("KG 2.0: data or vis missing");
      return null;
    }

    var opts = Object.assign({ root: null, startModule: null, startNode: null }, userOpts || {});
    var mount = typeof opts.root === "string" ? document.querySelector(opts.root) : opts.root;
    if (!mount) return null;

    mount.classList.add("kg-embed", "is-on");
    mount.innerHTML = buildPageHtml();
    var stageEl = mount.querySelector("#kg2Stage");
    var particles = mount.querySelector("#kg2Particles");
    for (var i = 0; i < 18; i++) {
      var sp = document.createElement("span");
      sp.style.left = Math.random() * 100 + "%";
      sp.style.animationDelay = Math.random() * 18 + "s";
      sp.style.animationDuration = 14 + Math.random() * 12 + "s";
      particles.appendChild(sp);
    }

    var byId = new Map(DATA.nodes.map(function (n) { return [n.id, n]; }));
    var childrenOf = new Map();
    DATA.nodes.forEach(function (n) {
      (n.childrenIds || []).forEach(function (cid) {
        if (!childrenOf.has(n.id)) childrenOf.set(n.id, []);
        childrenOf.get(n.id).push(cid);
      });
    });
    DATA.edges.forEach(function (e) {
      if (e.style === "solid" || e.plate) {
        if (!childrenOf.has(e.source)) childrenOf.set(e.source, []);
        var arr = childrenOf.get(e.source);
        if (arr.indexOf(e.target) < 0) arr.push(e.target);
      }
    });

    var industry = "general";
    var stage = "landing"; // landing | overview | focus
    var overviewModule = null; // business_problem | methodology | metric
    var overviewCat = null;
    var centerId = null;
    var selectedId = null; // 右侧详情当前节点；可与中心不同（点图画布只换详情）
    var history = [];
    var showMore = { business_problem: 5, methodology: 5, metric: 5 };
    var network = null;
    var nodesDS = null;
    var edgesDS = null;
    var pulseTimer = null;
    var breathe = 0;
    var hoverId = null;

    function industryKeys() {
      return INDUSTRY_ALIAS[industry] || [industry];
    }

    function matchIndustry(node) {
      // 通用数据分析：三板全量内容
      if (industry === "general") return true;
      // 分析方法跨行业通用
      if (node.type === "methodology") return true;
      // 带「通用」标签的指标/问题在各行业下仍可见
      var tags = node.tags || (node.detail && node.detail.notes) || [];
      if (tags.indexOf("通用") >= 0) return true;
      if (node.category === "general") return true;
      var keys = industryKeys();
      return keys.indexOf(node.category) >= 0;
    }

    function leavesOfType(type) {
      return DATA.nodes.filter(function (n) {
        return n.type === type && !n.isRoot && !n.isCategory && matchIndustry(n);
      });
    }

    function catsOfModule(type) {
      if (type === "methodology") {
        return DATA.nodes.filter(function (n) {
          return n.isCategory && n.type === "methodology";
        });
      }
      // 通用：展示该模块下全部行业/分类节点
      if (industry === "general") {
        return DATA.nodes.filter(function (n) {
          return n.isCategory && n.type === type;
        });
      }
      var keys = industryKeys();
      return DATA.nodes.filter(function (n) {
        return n.isCategory && n.type === type && keys.indexOf(n.category) >= 0;
      });
    }

    function countLeaves(catId) {
      return (childrenOf.get(catId) || []).filter(function (id) {
        var n = byId.get(id);
        return n && matchIndustry(n);
      }).length;
    }

    /** 业务问题/指标：单行业或仅 1 个分类时，直接展开列表，避免多点一次 */
    function autoPickOverviewCat() {
      if (!overviewModule || overviewModule === "methodology") {
        overviewCat = null;
        return;
      }
      var cats = catsOfModule(overviewModule);
      if (cats.length === 1) {
        overviewCat = cats[0].id;
      } else if (industry !== "general" && cats.length > 1) {
        overviewCat = cats[0].id;
      } else if (overviewCat) {
        // 校验当前分类是否仍属于当前行业/模块
        var still = cats.some(function (c) { return c.id === overviewCat; });
        if (!still) overviewCat = null;
      } else {
        overviewCat = null;
      }
    }

    function enterOverview(mod) {
      overviewModule = mod;
      stage = "overview";
      autoPickOverviewCat();
      render();
    }

    function industrySwitcherHtml(variant) {
      var chips = INDUSTRY_OPTIONS.map(function (o) {
        var active = industry === o[0] ? " is-active" : "";
        return (
          '<button type="button" class="kg2-ind-chip' + active + '" data-ind="' + o[0] + '">' +
          esc(o[1]) +
          "</button>"
        );
      }).join("");
      var cls = variant === "side" ? "kg2-industry kg2-industry-side" : "kg2-industry";
      return (
        '<div class="' + cls + '">' +
        '<div class="kg2-industry-label">行业</div>' +
        '<div class="kg2-ind-chips" id="kg2IndChips">' + chips + "</div>" +
        "</div>"
      );
    }

    function bindIndustrySwitcher(root) {
      if (!root) return;
      root.querySelectorAll(".kg2-ind-chip").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var next = btn.getAttribute("data-ind");
          if (!next) return;
          var same = next === industry;
          industry = next;

          if (stage === "focus" && centerId) {
            // 行业变更后重绘关联；若当前中心不属于该行业，退回模块概览
            var cur = byId.get(centerId);
            if (cur && cur.type !== "methodology" && !matchIndustry(cur)) {
              history = [];
              centerId = null;
              if (overviewModule) enterOverview(overviewModule);
              else {
                stage = "landing";
                render();
              }
            } else {
              enterFocus(centerId, false);
            }
            return;
          }

          if (stage === "overview" && overviewModule) {
            // 从「通用」切到具体行业：直接进入该行业内容列表
            autoPickOverviewCat();
            render();
            return;
          }

          // 引导页：切换行业刷新数量；若点的是具体行业，保持三入口可见
          if (!same || stage === "landing") {
            overviewCat = null;
            stage = "landing";
            render();
          }
        });
      });
    }

    function relatedFor(center) {
      var refs = (center.crossRefs || []).map(function (id) { return byId.get(id); }).filter(Boolean);
      var byType = { business_problem: [], methodology: [], metric: [] };
      refs.forEach(function (n) {
        if (!TYPE[n.type]) return;
        if (n.type !== "methodology" && !matchIndustry(n)) return;
        byType[n.type].push(n);
      });
      // 若关联不足，用同分类叶子 / 名称弱补（仅同行业）
      function fill(type, need) {
        if (byType[type].length >= need) return;
        var pool = leavesOfType(type).filter(function (n) {
          return n.id !== center.id && byType[type].every(function (x) { return x.id !== n.id; });
        });
        // 优先同 category
        pool.sort(function (a, b) {
          var sa = a.category === center.category ? 0 : 1;
          var sb = b.category === center.category ? 0 : 1;
          return sa - sb;
        });
        while (byType[type].length < need && pool.length) byType[type].push(pool.shift());
      }
      fill("business_problem", 3);
      fill("methodology", 3);
      fill("metric", 3);
      return byType;
    }

    // ---------- render stages ----------
    function render() {
      if (stage === "landing") renderLanding();
      else if (stage === "overview") renderOverview();
      else renderFocus();
    }

    function renderLanding() {
      destroyNet();
      var bpN = leavesOfType("business_problem").length;
      var mdN = leavesOfType("methodology").length;
      var mtN = leavesOfType("metric").length;

      stageEl.innerHTML =
        '<div class="kg2-landing">' +
        '  <h1 class="kg2-landing-title">数据分析知识导航图谱</h1>' +
        '  <p class="kg2-landing-sub">从业务问题、分析方法、指标字典任意入口出发，辐射式探索关联知识</p>' +
        '  <div class="kg2-search-hero">' +
        '    <input id="kg2HeroSearch" type="search" placeholder="搜索业务问题、分析方法、指标..." autocomplete="off" />' +
        '    <div class="kg2-search-drop" id="kg2HeroDrop"></div>' +
        "  </div>" +
        industrySwitcherHtml("landing") +
        '  <div class="kg2-cards">' +
        '    <div class="kg2-card bp" data-mod="business_problem"><div class="ico">❓</div><h3>业务问题</h3><div class="num">' + bpN + '</div><div class="hint">点击进入</div></div>' +
        '    <div class="kg2-card md" data-mod="methodology"><div class="ico">📐</div><h3>分析方法</h3><div class="num">' + mdN + '</div><div class="hint">点击进入</div></div>' +
        '    <div class="kg2-card mt" data-mod="metric"><div class="ico">📊</div><h3>指标字典</h3><div class="num">' + mtN + '</div><div class="hint">点击进入</div></div>' +
        "  </div>" +
        '  <div class="kg2-hot"><h4>热门入口</h4><div class="kg2-hot-tags" id="kg2Hot"></div></div>' +
        "</div>";

      bindIndustrySwitcher(stageEl);
      stageEl.querySelectorAll(".kg2-card").forEach(function (card) {
        card.addEventListener("click", function () {
          enterOverview(card.getAttribute("data-mod"));
        });
      });
      wireSearch(stageEl.querySelector("#kg2HeroSearch"), stageEl.querySelector("#kg2HeroDrop"));

      var hotNames = ["RFM模型", "留存率", "销售额下降了，你怎么分析原因？", "转化率", "AARRR海盗模型", "GMV"];
      var hotEl = stageEl.querySelector("#kg2Hot");
      hotNames.forEach(function (name) {
        var node = DATA.nodes.find(function (n) { return n.name === name || (n.name && n.name.indexOf(name) === 0); });
        if (!node) return;
        if (!matchIndustry(node) && node.type !== "methodology") return;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = trunc(node.name, 16);
        btn.addEventListener("click", function () { enterFocus(node.id, true); });
        hotEl.appendChild(btn);
      });
    }

    function renderOverview() {
      destroyNet();
      var mod = overviewModule;
      var meta = TYPE[mod];
      if (!meta) {
        stage = "landing";
        renderLanding();
        return;
      }

      // 进入概览时：单行业业务问题/指标自动展开，避免二次点击
      if (mod !== "methodology" && !overviewCat) autoPickOverviewCat();

      var cats = catsOfModule(mod);
      var showCatGrid = mod === "methodology" || (industry === "general" && !overviewCat);
      // 已展开具体列表时，通用模式下仍显示分类网格便于切换；单行业则只显示列表
      if (mod !== "methodology" && industry !== "general" && overviewCat) {
        showCatGrid = false;
      }

      var grid = "";
      if (showCatGrid) {
        grid = cats.map(function (c) {
          var cnt = countLeaves(c.id);
          var active = overviewCat === c.id ? " is-on" : "";
          return (
            '<div class="kg2-ov-node ' + meta.cls + active + '" data-cat="' + c.id + '">' +
            '<div class="count" style="color:' + meta.color + '">' + cnt + "</div>" +
            '<div class="name">' + esc(c.name) + "</div>" +
            '<div class="sub">' + (mod === "methodology" ? "点击查看方法" : "点击查看内容") + "</div></div>"
          );
        }).join("");
      }

      var listHtml = "";
      if (overviewCat) {
        var leaves = (childrenOf.get(overviewCat) || []).map(function (id) { return byId.get(id); }).filter(Boolean);
        leaves = leaves.filter(function (n) { return matchIndustry(n); });
        var catName = (byId.get(overviewCat) || {}).name || "";
        listHtml =
          '<div class="kg2-ov-list"><h4>' + esc(catName) + " · 共 " + leaves.length + " 项（点击进入图谱）</h4>" +
          (leaves.length
            ? '<div class="kg2-leaf-grid">' +
              leaves.map(function (n) {
                return '<button type="button" class="kg2-leaf" data-id="' + n.id + '">' + esc(n.name) + "</button>";
              }).join("") +
              "</div>"
            : '<p class="kg2-empty">该分类下暂无条目</p>') +
          "</div>";
      } else if (mod !== "methodology" && industry !== "general" && !cats.length) {
        listHtml = '<div class="kg2-ov-list"><p class="kg2-empty">当前行业暂无「' + esc(meta.label) + '」内容，可切换其他行业或查看分析方法</p></div>';
      } else if (mod !== "methodology" && industry === "general" && !overviewCat) {
        listHtml = '<div class="kg2-ov-list"><p class="kg2-empty-hint">请选择上方行业分类，或顶部切换到具体行业直接查看</p></div>';
      }

      stageEl.innerHTML =
        '<div class="kg2-overview">' +
        '  <div class="kg2-ov-bar">' +
        '    <button type="button" class="kg2-btn" id="kg2BackLanding">← 返回</button>' +
        '    <h2 class="kg2-ov-title ' + meta.cls + '">' + meta.label +
        (industry !== "general" ? ' · ' + esc((INDUSTRY_OPTIONS.find(function (o) { return o[0] === industry; }) || [])[1] || "") : "") +
        "</h2>" +
        "  </div>" +
        industrySwitcherHtml("overview") +
        (showCatGrid ? '<div class="kg2-ov-grid">' + grid + "</div>" : "") +
        listHtml +
        "</div>";

      bindIndustrySwitcher(stageEl);
      stageEl.querySelector("#kg2BackLanding").addEventListener("click", function () {
        stage = "landing";
        overviewCat = null;
        overviewModule = null;
        render();
      });
      stageEl.querySelectorAll(".kg2-ov-node").forEach(function (el) {
        el.addEventListener("click", function () {
          var catId = el.getAttribute("data-cat");
          overviewCat = catId;
          // 通用模式下点某个行业分类：同步行业芯片，便于继续切换
          var catNode = byId.get(catId);
          if (industry === "general" && catNode && catNode.category && mod !== "methodology") {
            var mapped = null;
            INDUSTRY_OPTIONS.forEach(function (o) {
              var keys = INDUSTRY_ALIAS[o[0]] || [o[0]];
              if (keys.indexOf(catNode.category) >= 0) mapped = o[0];
            });
            if (mapped) industry = mapped;
          }
          renderOverview();
        });
      });
      stageEl.querySelectorAll(".kg2-leaf").forEach(function (el) {
        el.addEventListener("click", function () {
          enterFocus(el.getAttribute("data-id"), true);
        });
      });
    }

    function enterFocus(id, pushHist) {
      var node = byId.get(id);
      if (!node || node.isRoot || node.isCategory) return;
      if (pushHist && centerId && centerId !== id) history.push(centerId);
      centerId = id;
      selectedId = id;
      showMore = { business_problem: 5, methodology: 5, metric: 5 };
      stage = "focus";
      renderFocus();
    }

    /** 仅更新右侧详情，不重建中间图谱 */
    function selectNode(id) {
      var node = byId.get(id);
      if (!node || node.isRoot || node.isCategory) return;
      selectedId = id;
      renderPanel(node);
      highlightSelection();
    }

    function highlightSelection() {
      if (!nodesDS || !network) return;
      var ids = nodesDS.getIds();
      ids.forEach(function (id) {
        var n = byId.get(id);
        if (!n) return;
        var isCenter = id === centerId;
        var isSel = id === selectedId;
        var meta = TYPE[n.type] || TYPE.metric;
        try {
          if (isCenter) {
            nodesDS.update({
              id: id,
              size: isSel ? 70 : 65,
              borderWidth: isSel ? 4 : 3,
              color: { background: "#a855f7", border: isSel ? "#fff" : "#e9d5ff", highlight: { background: "#c084fc", border: "#fff" } }
            });
          } else {
            nodesDS.update({
              id: id,
              size: isSel ? 36 : 30,
              borderWidth: isSel ? 3 : 2,
              color: {
                background: isSel ? meta.color : meta.dark,
                border: isSel ? "#fff" : meta.color,
                highlight: { background: meta.color, border: "#fff" },
                hover: { background: meta.color, border: "#fff" }
              }
            });
          }
        } catch (e) {}
      });
    }

    function renderFocus() {
      var center = byId.get(centerId);
      if (!center) {
        stage = "landing";
        renderLanding();
        return;
      }
      if (!selectedId || !byId.get(selectedId)) selectedId = centerId;
      var panelNode = byId.get(selectedId) || center;

      // 每次重建聚焦页 DOM 前必须销毁旧 network，否则画布会画在已卸载节点上导致「中间图消失」
      destroyNet();

      stageEl.innerHTML =
        '<div class="kg2-focus">' +
        '  <aside class="kg2-side">' +
        '    <button type="button" class="kg2-btn" id="kg2Back">← 返回</button>' +
        '    <div class="kg2-search-mini"><input id="kg2FocusSearch" type="search" placeholder="搜索…" /></div>' +
        '    <div class="kg2-search-drop" id="kg2FocusDrop" style="position:relative;top:0;display:none"></div>' +
        industrySwitcherHtml("side") +
        '    <div class="kg2-legend-box">' +
        '      <div class="row"><span class="kg2-dot" style="background:#f97316;color:#f97316"></span>业务问题</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#10b981;color:#10b981"></span>分析方法</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#3b82f6;color:#3b82f6"></span>指标字典</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#a855f7;color:#a855f7"></span>当前中心</div>' +
        "    </div>" +
        '    <div class="kg2-more-btns" id="kg2More"></div>' +
        '    <div class="kg2-path-hist"><div style="margin-bottom:4px;font-weight:600">探索路径</div><div id="kg2Hist"></div></div>' +
        "  </aside>" +
        '  <div class="kg2-canvas-wrap">' +
        '    <div class="kg2-network" id="kg2Net"></div>' +
        '    <div class="kg2-canvas-hint">点击节点查看右侧详情 · 点右侧「相关推荐」切换探索中心</div>' +
        '    <div class="kg2-ctrl"><button type="button" id="kg2ZoomIn">＋</button><button type="button" id="kg2ZoomOut">－</button><button type="button" id="kg2Fit">◎</button></div>' +
        "  </div>" +
        '  <aside class="kg2-panel open ' + (TYPE[panelNode.type] ? TYPE[panelNode.type].cls : "") + '" id="kg2Panel"></aside>' +
        "</div>";

      bindIndustrySwitcher(stageEl);
      stageEl.querySelector("#kg2Back").addEventListener("click", function () {
        if (history.length) {
          centerId = history.pop();
          selectedId = centerId;
          renderFocus();
        } else if (overviewModule) {
          stage = "overview";
          render();
        } else {
          stage = "landing";
          render();
        }
      });

      var histEl = stageEl.querySelector("#kg2Hist");
      var pathIds = history.concat([centerId]);
      histEl.innerHTML = pathIds.map(function (id, idx) {
        var n = byId.get(id);
        return '<button type="button" data-hist="' + id + '" data-idx="' + idx + '">' + (idx + 1) + ". " + esc(trunc(n ? n.name : id, 18)) + "</button>";
      }).join("");
      histEl.querySelectorAll("[data-hist]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var idx = +btn.getAttribute("data-idx");
          var id = btn.getAttribute("data-hist");
          history = pathIds.slice(0, idx);
          enterFocus(id, false);
        });
      });

      wireSearch(stageEl.querySelector("#kg2FocusSearch"), stageEl.querySelector("#kg2FocusDrop"));
      renderPanel(panelNode);
      drawGraph(center);
      highlightSelection();
      updateMoreButtons(center);

      stageEl.querySelector("#kg2ZoomIn").addEventListener("click", function () {
        if (!network) return;
        network.moveTo({ scale: Math.min(2.5, network.getScale() * 1.2), animation: { duration: 200 } });
      });
      stageEl.querySelector("#kg2ZoomOut").addEventListener("click", function () {
        if (!network) return;
        network.moveTo({ scale: Math.max(0.3, network.getScale() / 1.2), animation: { duration: 200 } });
      });
      stageEl.querySelector("#kg2Fit").addEventListener("click", function () {
        if (network) network.fit({ animation: { duration: 400 } });
      });
    }

    function updateMoreButtons(center) {
      var rel = relatedFor(center);
      var box = stageEl.querySelector("#kg2More");
      if (!box) return;
      box.innerHTML = "";
      ["business_problem", "methodology", "metric"].forEach(function (t) {
        var total = rel[t].length;
        var shown = showMore[t];
        if (total <= shown) return;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "显示更多" + TYPE[t].label + "（" + shown + "/" + total + "）";
        btn.addEventListener("click", function () {
          showMore[t] = Math.min(total, showMore[t] + 5);
          drawGraph(center);
          updateMoreButtons(center);
        });
        box.appendChild(btn);
      });
    }

    function renderPanel(node) {
      var panel = stageEl.querySelector("#kg2Panel");
      var meta = TYPE[node.type] || TYPE.metric;
      var d = node.detail || {};
      var rel = relatedFor(node);
      var html =
        "<h2>" + esc(node.name) + "</h2>" +
        '<span class="kg2-tag ' + meta.cls + '">' + meta.label + "</span>";
      if (d.definition) html += '<div class="kg2-sec"><h3>定义 / 说明</h3><p>' + esc(d.definition) + "</p></div>";
      if (d.formula) html += '<div class="kg2-sec"><h3>公式 / 要点</h3><pre>' + esc(d.formula) + "</pre></div>";
      if (d.applicableScenarios && d.applicableScenarios.length) {
        html += '<div class="kg2-sec"><h3>适用场景</h3><div class="kg2-chips">' +
          d.applicableScenarios.map(function (s) { return "<span>" + esc(s) + "</span>"; }).join("") +
          "</div></div>";
      }
      if (node.categoryName) html += '<div class="kg2-sec"><h3>分类 / 行业</h3><div class="kg2-chips"><span>' + esc(node.categoryName) + "</span></div></div>";
      if (d.steps && d.steps.length) {
        html += '<div class="kg2-sec"><h3>拆解思路</h3><ul>' +
          d.steps.slice(0, 12).map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") +
          "</ul></div>";
      }

      function refBlock(title, list) {
        if (!list.length) return "";
        return '<div class="kg2-sec"><h3>' + title + "</h3>" +
          list.slice(0, 8).map(function (n) {
            return '<button type="button" class="kg2-ref" data-jump="' + n.id + '"><span class="tiny">' +
              (TYPE[n.type] ? TYPE[n.type].label : "") + "</span>" + esc(trunc(n.name, 28)) + "</button>";
          }).join("") + "</div>";
      }
      html += refBlock("相关业务问题", rel.business_problem);
      html += refBlock("相关分析方法", rel.methodology);
      html += refBlock("相关指标", rel.metric);

      if (node.id !== centerId) {
        html +=
          '<div class="kg2-sec">' +
          '<button type="button" class="kg2-explore-center" id="kg2ExploreCenter">以此为中心重新探索图谱</button>' +
          "</div>";
      }

      panel.innerHTML = html;
      panel.className = "kg2-panel open " + meta.cls;
      panel.querySelectorAll("[data-jump]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          // 右侧相关推荐：切换探索中心并刷新图谱
          enterFocus(btn.getAttribute("data-jump"), true);
        });
      });
      var exploreBtn = panel.querySelector("#kg2ExploreCenter");
      if (exploreBtn) {
        exploreBtn.addEventListener("click", function () {
          enterFocus(node.id, true);
        });
      }
    }

    function sectorAngle(type) {
      // 左上问题、右上方法、正下指标（屏幕坐标 y 向下）
      if (type === "business_problem") return (135 * Math.PI) / 180;
      if (type === "methodology") return (45 * Math.PI) / 180;
      return (270 * Math.PI) / 180;
    }

    function drawGraph(center) {
      var rel = relatedFor(center);
      var nodeObjs = [];
      var edgeObjs = [];
      var cx = 0, cy = 0;

      // center XL
      nodeObjs.push({
        id: center.id,
        label: trunc(center.name, 8),
        title: center.name,
        x: cx, y: cy, fixed: true,
        shape: "dot",
        size: 65,
        color: { background: "#a855f7", border: "#e9d5ff", highlight: { background: "#c084fc", border: "#fff" } },
        borderWidth: 3,
        font: { color: "#fff", size: 12, face: "Noto Sans SC, Microsoft YaHei, sans-serif", strokeWidth: 2, strokeColor: "rgba(10,14,26,0.8)" },
        shadow: { enabled: true, color: "rgba(168,85,247,0.65)", size: 32, x: 0, y: 0 },
        mass: 4
      });

      ["business_problem", "methodology", "metric"].forEach(function (t) {
        var list = rel[t].slice(0, showMore[t]);
        var base = sectorAngle(t);
        var meta = TYPE[t];
        var n = list.length;
        var spread = Math.min(0.9, 0.18 * Math.max(n, 1));
        list.forEach(function (node, i) {
          var ang = n === 1 ? base : base - spread / 2 + (spread * i) / Math.max(n - 1, 1);
          var r = 220 + (i % 3) * 28;
          var x = Math.cos(ang) * r;
          var y = -Math.sin(ang) * r;
          nodeObjs.push({
            id: node.id,
            label: trunc(node.name, 6),
            title: node.name,
            x: x, y: y, fixed: false,
            shape: "dot",
            size: 30,
            color: {
              background: meta.dark,
              border: meta.color,
              highlight: { background: meta.color, border: "#fff" },
              hover: { background: meta.color, border: "#fff" }
            },
            borderWidth: 2,
            font: { color: "#f8fafc", size: 11, face: "Noto Sans SC, Microsoft YaHei, sans-serif", strokeWidth: 2, strokeColor: "rgba(10,14,26,0.75)" },
            shadow: { enabled: true, color: meta.glow, size: 16, x: 0, y: 0 },
            mass: 1
          });
          edgeObjs.push({
            id: "e_" + center.id + "_" + node.id,
            from: center.id,
            to: node.id,
            color: { color: meta.color, opacity: 0.55 },
            width: 2.4,
            smooth: { enabled: true, type: "curvedCW", roundness: 0.28 },
            arrows: { to: { enabled: true, scaleFactor: 0.4 } }
          });
        });
      });

      var netEl = stageEl.querySelector("#kg2Net");
      if (!netEl) return;

      // 容器已换新时强制重建 Network（避免挂在旧 DOM 上）
      if (network && network.body && network.body.container && network.body.container !== netEl) {
        destroyNet();
      }

      if (!nodesDS || !network) {
        nodesDS = new vis.DataSet([]);
        edgesDS = new vis.DataSet([]);
        network = new vis.Network(netEl, { nodes: nodesDS, edges: edgesDS }, {
          interaction: { hover: true, dragNodes: true, dragView: true, zoomView: true, tooltipDelay: 80 },
          physics: {
            enabled: true,
            barnesHut: { gravitationalConstant: -1800, centralGravity: 0.05, springLength: 120, springConstant: 0.04, damping: 0.5, avoidOverlap: 0.7 },
            stabilization: { enabled: true, iterations: 60, fit: true },
            maxVelocity: 30,
            minVelocity: 0.4
          },
          layout: { improvedLayout: false }
        });
        network.on("click", function (p) {
          if (!p.nodes.length) return;
          // 画布点击：只更新右侧详情，不刷新图谱
          selectNode(p.nodes[0]);
        });
        network.on("hoverNode", function (p) {
          hoverId = p.node;
          try {
            nodesDS.update({ id: p.node, size: (p.node === centerId ? 65 : 30) * 1.2 });
          } catch (e) {}
        });
        network.on("blurNode", function (p) {
          hoverId = null;
          try {
            nodesDS.update({ id: p.node, size: p.node === centerId ? 65 : 30 });
          } catch (e) {}
        });
        network.on("stabilizationIterationsDone", function () {
          if (!network) return;
          network.setOptions({
            physics: {
              barnesHut: { gravitationalConstant: -800, centralGravity: 0.02, springLength: 140, springConstant: 0.02, damping: 0.72, avoidOverlap: 0.5 },
              minVelocity: 0.15,
              maxVelocity: 10,
              stabilization: { enabled: false }
            }
          });
        });
      }

      nodesDS.clear();
      edgesDS.clear();
      nodesDS.add(nodeObjs);
      edgesDS.add(edgeObjs);
      network.setOptions({ physics: { enabled: true, stabilization: { enabled: true, iterations: 50, fit: true } } });
      network.startSimulation();
      setTimeout(function () {
        try { if (network) network.fit({ animation: { duration: 500, easingFunction: "easeInOutCubic" } }); } catch (e) {}
      }, 80);
      startPulse(center.id);
    }

    function startPulse(id) {
      if (pulseTimer) clearInterval(pulseTimer);
      breathe = 0;
      pulseTimer = setInterval(function () {
        if (!nodesDS || !nodesDS.get(id)) return;
        breathe = (breathe + 1) % 48;
        var t = Math.sin((breathe / 48) * Math.PI * 2);
        try {
          nodesDS.update({
            id: id,
            size: 65 + t * 5,
            shadow: { enabled: true, color: "rgba(168,85,247,0.65)", size: 28 + t * 10, x: 0, y: 0 }
          });
        } catch (e) {}
      }, 55);
    }

    function destroyNet() {
      if (pulseTimer) clearInterval(pulseTimer);
      pulseTimer = null;
      if (network) {
        network.destroy();
        network = null;
      }
      nodesDS = null;
      edgesDS = null;
    }

    function wireSearch(input, drop) {
      if (!input || !drop) return;
      function run() {
        var q = (input.value || "").trim();
        if (!q) { drop.classList.remove("open"); drop.style.display = "none"; drop.innerHTML = ""; return; }
        var groups = { business_problem: [], methodology: [], metric: [] };
        DATA.nodes.forEach(function (n) {
          if (n.isRoot || n.isCategory) return;
          if (!n.name || n.name.toLowerCase().indexOf(q.toLowerCase()) < 0) return;
          if (n.type !== "methodology" && !matchIndustry(n)) return;
          if (groups[n.type] && groups[n.type].length < 8) groups[n.type].push(n);
        });
        var html = "";
        ["business_problem", "methodology", "metric"].forEach(function (t) {
          if (!groups[t].length) return;
          html += '<div class="kg2-search-group">' + TYPE[t].label + "</div>";
          groups[t].forEach(function (n) {
            html += '<div class="kg2-search-item" data-id="' + n.id + '">' + hilite(n.name, q) + "</div>";
          });
        });
        drop.innerHTML = html || '<div class="kg2-search-item">无匹配结果</div>';
        drop.classList.add("open");
        drop.style.display = "block";
        drop.querySelectorAll("[data-id]").forEach(function (el) {
          el.addEventListener("click", function () {
            drop.classList.remove("open");
            drop.style.display = "none";
            input.value = "";
            enterFocus(el.getAttribute("data-id"), true);
          });
        });
      }
      input.addEventListener("input", run);
      input.addEventListener("focus", run);
      document.addEventListener("click", function (e) {
        if (!e.target.closest(".kg2-search-hero") && !e.target.closest(".kg2-search-mini") && !e.target.closest(".kg2-search-drop")) {
          drop.classList.remove("open");
          drop.style.display = "none";
        }
      });
    }

    // boot
    if (opts.startNode && byId.has(opts.startNode)) {
      enterFocus(opts.startNode, false);
    } else if (opts.startModule && TYPE[opts.startModule]) {
      enterOverview(opts.startModule);
    } else {
      render();
    }

    return {
      goLanding: function () { stage = "landing"; render(); },
      enterFocus: enterFocus,
      destroy: function () { destroyNet(); }
    };
  }

  window.initKnowledgeGraph = initKnowledgeGraph;

  document.addEventListener("DOMContentLoaded", function () {
    var auto = document.getElementById("kgAutoRoot");
    if (auto) {
      var params = new URLSearchParams(location.search);
      window.__kgInstance = initKnowledgeGraph({
        root: auto,
        startModule: params.get("module") || auto.dataset.module || null,
        startNode: params.get("node") || null
      });
    }
  });
})();
