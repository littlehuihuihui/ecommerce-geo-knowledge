/* 知识图谱 2.0 — 三阶段导航检索 */
(function () {
  "use strict";

  var TYPE = {
    business_problem: { key: "business_problem", label: "业务问题", color: "#f97316", dark: "#ea580c", glow: "rgba(249,115,22,0.55)", cls: "bp", icon: "❓" },
    methodology: { key: "methodology", label: "分析方法", color: "#10b981", dark: "#059669", glow: "rgba(16,185,129,0.55)", cls: "md", icon: "📐" },
    metric: { key: "metric", label: "指标字典", color: "#3b82f6", dark: "#2563eb", glow: "rgba(59,130,246,0.55)", cls: "mt", icon: "📊" }
  };

  /** 行业切换：通用 = 通用分类；单行业严格过滤（方法始终通用） */
  var INDUSTRY_ALIAS = {
    general: ["general"],
    retail: ["ecommerce"], // legacy → 电商
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
    tourism: ["general"], // legacy → 通用
    healthcare: ["healthcare"],
    fmcg: ["fmcg"],
    banking: ["banking"],
    insurance: ["insurance"],
    securities: ["securities"],
    payment: ["payment"],
    pension: ["pension"]
  };

  var INDUSTRY_OPTIONS = [
    ["general", "通用"],
    ["ecommerce", "电商"],
    ["finance", "金融通用"],
    ["banking", "银行"],
    ["insurance", "保险"],
    ["securities", "证券与资管"],
    ["payment", "支付与金融科技"],
    ["pension", "养老金与公共金融"],
    ["game", "游戏"],
    ["content", "内容/短视频"],
    ["saas", "SaaS"],
    ["live-ecommerce", "直播电商"],
    ["local-life", "本地生活"],
    ["fmcg", "快消"],
    ["manufacturing", "制造"],
    ["healthcare", "医疗健康"],
    ["newenergy", "新能源"],
    ["logistics", "物流"]
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
    var expandedId = null; // 第2层已展开的节点，用于挂载第3层；最多三层
    var layerOf = {}; // nodeId -> 1|2|3
    var sideCollapsed = false;
    var panelCollapsed = false;
    var panelWidth = 360; // 右侧详情栏宽度（可拖拽）
    var history = [];
    var showMore = { business_problem: 6, methodology: 6, metric: 6 };
    var showMoreL3 = { business_problem: 5, methodology: 5, metric: 5 };
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
      // 分析方法跨行业通用
      if (node.type === "methodology") return true;
      // 「通用」：仅展示通用分类（不再等同于全部）
      if (industry === "general") {
        return node.category === "general";
      }
      // 单行业：严格按 category 匹配（不再因标签含「通用」而串台）
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
      // 通用：仅展示通用分类；单行业：只展示该行业分类
      if (industry === "general") {
        return DATA.nodes.filter(function (n) {
          return n.isCategory && n.type === type && n.category === "general";
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

    /** 仅真实交叉引用（正向 + 反向），不补弱关联 */
    function linkedExact(node) {
      var byType = { business_problem: [], methodology: [], metric: [] };
      var seen = {};
      function add(n) {
        if (!n || n.id === node.id || seen[n.id] || !TYPE[n.type]) return;
        if (n.isRoot || n.isCategory) return;
        seen[n.id] = true;
        byType[n.type].push(n);
      }
      (node.crossRefs || []).forEach(function (id) { add(byId.get(id)); });
      DATA.nodes.forEach(function (n) {
        if (n.isRoot || n.isCategory) return;
        var refs = n.crossRefs || [];
        if (refs.indexOf(node.id) < 0) return;
        add(n);
      });
      return byType;
    }

    /** 指标详情：可用于解决 / 相关方法 / 口径提示（与指标字典翻面一致） */
    function metricUsageDetail(node) {
      var linked = linkedExact(node);
      var d = node.detail || {};
      var problems = linked.business_problem.map(function (n) { return n.name; });
      var methods = linked.methodology.map(function (n) { return n.name; });
      if (!problems.length) {
        problems = [
          "监控「" + node.name + "」异常波动，定位业务表现变化",
          "结合公式拆解驱动因子，找到可干预环节",
          "用于阶段复盘与目标拆解，对齐团队关注点"
        ];
      }
      if (!methods.length && d.applicableScenarios && d.applicableScenarios.length) {
        methods = d.applicableScenarios.slice(0, 4);
      }
      var tips = [];
      if (d.formula) tips.push(d.formula);
      if (d.definition) tips.push(d.definition);
      if (!tips.length && node.description) tips.push(node.description);
      return {
        problems: problems.slice(0, 5),
        methods: methods.slice(0, 6),
        tips: tips.slice(0, 3),
        linked: linked
      };
    }

    function relatedFor(center, needPerType) {
      needPerType = needPerType == null ? 5 : needPerType;
      var refs = (center.crossRefs || []).map(function (id) { return byId.get(id); }).filter(Boolean);
      var byType = { business_problem: [], methodology: [], metric: [] };
      refs.forEach(function (n) {
        if (!TYPE[n.type]) return;
        if (n.type !== "methodology" && !matchIndustry(n)) return;
        byType[n.type].push(n);
      });

      function nameScore(n) {
        var a = String(center.name || "");
        var b = String(n.name || "");
        if (!a || !b) return 0;
        var score = 0;
        // 短词命中加分（如 GMV、留存、转化）
        var tokens = a.replace(/[（）()\/\s]+/g, " ").split(" ").filter(function (t) { return t.length >= 2; });
        tokens.forEach(function (t) {
          if (b.indexOf(t) >= 0) score += 3;
        });
        if (n.category && n.category === center.category) score += 2;
        return score;
      }

      // 若关联不足，用同分类叶子 / 名称弱补
      function fill(type, need) {
        if (byType[type].length >= need) return;
        var pool = leavesOfType(type).filter(function (n) {
          return n.id !== center.id && byType[type].every(function (x) { return x.id !== n.id; });
        });
        pool.sort(function (a, b) {
          return nameScore(b) - nameScore(a);
        });
        while (byType[type].length < need && pool.length) byType[type].push(pool.shift());
      }
      fill("business_problem", needPerType);
      fill("methodology", needPerType);
      fill("metric", needPerType);
      return byType;
    }

    function setFocusMode(on) {
      document.body.classList.toggle("kg-focus-mode", !!on);
      if (!on) {
        document.body.classList.remove("kg2-resizing");
        var leftover = document.querySelector(".kg2-resize-mask");
        if (leftover) leftover.remove();
      }
    }

    // ---------- render stages ----------
    function render() {
      if (stage === "landing") renderLanding();
      else if (stage === "overview") renderOverview();
      else renderFocus();
    }

    function renderLanding() {
      setFocusMode(false);
      destroyNet();
      var bpN = leavesOfType("business_problem").length;
      var mdN = leavesOfType("methodology").length;
      var mtN = leavesOfType("metric").length;
      // 独立图谱页已有行业框架式顶栏，引导区不再重复大标题
      var standalone = mount && mount.id === "kgAutoRoot";
      var headHtml = standalone
        ? ""
        : (
          '<div class="kg2-page-head">' +
          '  <div class="kg2-page-head-main">' +
          '    <h1 class="kg2-landing-title">数据分析知识导航图谱</h1>' +
          '    <p class="kg2-landing-sub">从业务问题、分析方法、指标字典任意入口出发，辐射式探索关联知识</p>' +
          "  </div>" +
          '  <div class="kg2-page-stats">' +
          '    <div class="kg2-ps"><div class="n">' + bpN + '</div><div class="l">业务问题</div></div>' +
          '    <div class="kg2-ps"><div class="n">' + mdN + '</div><div class="l">分析方法</div></div>' +
          '    <div class="kg2-ps"><div class="n">' + mtN + '</div><div class="l">指标字典</div></div>' +
          "  </div>" +
          "</div>"
        );

      stageEl.innerHTML =
        '<div class="kg2-landing' + (standalone ? " kg2-landing--under-header" : "") + '">' +
        headHtml +
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
      setFocusMode(false);
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
        var leafItems;
        if (mod === "metric") {
          leafItems = leaves.map(function (n) {
            var usage = metricUsageDetail(n);
            var d = n.detail || {};
            var def = d.definition || n.description || "";
            var formula = d.formula || "";
            return (
              '<div class="kg2-mflip" data-id="' + n.id + '">' +
              '  <div class="kg2-mflip-inner">' +
              '    <div class="kg2-mflip-face kg2-mflip-front" data-open="' + n.id + '">' +
              '      <div class="kg2-mflip-name">' + esc(n.name) + "</div>" +
              (def ? '<p class="kg2-mflip-desc">' + esc(trunc(def, 72)) + "</p>" : "") +
              (formula ? '<div class="kg2-mflip-formula">' + esc(trunc(formula, 56)) + "</div>" : "") +
              '      <div class="kg2-mflip-hint">正面点击 → 图谱 · 右下角翻面看用途</div>' +
              '      <button type="button" class="kg2-mflip-btn" title="翻面查看详情" aria-label="翻面查看详情">↻</button>' +
              "    </div>" +
              '    <div class="kg2-mflip-face kg2-mflip-back">' +
              '      <div class="kg2-mflip-name">' + esc(n.name) + "</div>" +
              '      <p class="kg2-mflip-sub">详细用途：这个指标常用来解决什么问题</p>' +
              '      <div class="kg2-mflip-sec"><h5>可用于解决</h5><ul>' +
              usage.problems.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") +
              "</ul></div>" +
              (usage.methods.length
                ? '<div class="kg2-mflip-sec"><h5>相关方法 / 场景</h5><div class="kg2-chips">' +
                  usage.methods.map(function (m) { return "<span>" + esc(trunc(m, 18)) + "</span>"; }).join("") +
                  "</div></div>"
                : "") +
              (usage.tips.length
                ? '<div class="kg2-mflip-sec"><h5>口径提示</h5><ul>' +
                  usage.tips.map(function (t) { return "<li>" + esc(trunc(t, 80)) + "</li>"; }).join("") +
                  "</ul></div>"
                : "") +
              '      <button type="button" class="kg2-mflip-open" data-open="' + n.id + '">打开知识图谱辐射图</button>' +
              '      <button type="button" class="kg2-mflip-btn" title="翻回正面" aria-label="翻回正面">↻</button>' +
              "    </div>" +
              "  </div>" +
              "</div>"
            );
          }).join("");
        } else {
          leafItems = leaves.map(function (n) {
            return '<button type="button" class="kg2-leaf" data-id="' + n.id + '">' + esc(n.name) + "</button>";
          }).join("");
        }
        listHtml =
          '<div class="kg2-ov-list"><h4>' + esc(catName) + " · 共 " + leaves.length +
          (mod === "metric" ? " 项（正面进图谱，右下角翻面看用途）" : " 项（点击进入图谱）") + "</h4>" +
          (leaves.length
            ? '<div class="kg2-leaf-grid' + (mod === "metric" ? " kg2-leaf-grid-flip" : "") + '">' + leafItems + "</div>"
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
          // 分类网格较高时，列表在下方，滚入视口避免「点了没反应」
          setTimeout(function () {
            var list = stageEl.querySelector(".kg2-ov-list");
            if (list && list.scrollIntoView) {
              list.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          }, 30);
        });
      });
      stageEl.querySelectorAll(".kg2-leaf").forEach(function (el) {
        el.addEventListener("click", function () {
          enterFocus(el.getAttribute("data-id"), true);
        });
      });
      stageEl.querySelectorAll(".kg2-mflip").forEach(function (card) {
        card.querySelectorAll(".kg2-mflip-btn").forEach(function (btn) {
          btn.addEventListener("click", function (e) {
            e.stopPropagation();
            card.classList.toggle("is-flipped");
          });
        });
        card.querySelectorAll("[data-open]").forEach(function (el) {
          el.addEventListener("click", function (e) {
            if (e.target.closest(".kg2-mflip-btn")) return;
            enterFocus(el.getAttribute("data-open"), true);
          });
        });
      });
    }

    function enterFocus(id, pushHist) {
      var node = byId.get(id);
      if (!node || node.isRoot || node.isCategory) return;
      if (pushHist && centerId && centerId !== id) history.push(centerId);
      centerId = id;
      selectedId = id;
      expandedId = null;
      layerOf = {};
      showMore = { business_problem: 6, methodology: 6, metric: 6 };
      showMoreL3 = { business_problem: 5, methodology: 5, metric: 5 };
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
        var layer = layerOf[id] || (id === centerId ? 1 : 2);
        var isCenter = layer === 1;
        var isSel = id === selectedId;
        var isExp = id === expandedId;
        var meta = TYPE[n.type] || TYPE.metric;
        var baseSize = isCenter ? 65 : layer === 3 ? 20 : 30;
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
              size: isSel ? baseSize + 6 : isExp ? baseSize + 4 : baseSize,
              borderWidth: isSel || isExp ? 3 : layer === 3 ? 1.5 : 2,
              color: {
                background: isSel || isExp ? meta.color : meta.dark,
                border: isSel || isExp ? "#fff" : layer === 3 ? "rgba(255,255,255,0.45)" : meta.color,
                highlight: { background: meta.color, border: "#fff" },
                hover: { background: meta.color, border: "#fff" }
              },
              opacity: layer === 3 ? 0.92 : 1
            });
          }
        } catch (e) {}
      });
    }

    function renderFocus() {
      setFocusMode(true);
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
        '<div class="kg2-focus' + (sideCollapsed ? " is-side-collapsed" : "") + (panelCollapsed ? " is-panel-collapsed" : "") + '">' +
        '  <aside class="kg2-side' + (sideCollapsed ? " is-collapsed" : "") + '" id="kg2Side">' +
        '    <button type="button" class="kg2-btn" id="kg2Back">← 返回</button>' +
        '    <div class="kg2-search-mini"><input id="kg2FocusSearch" type="search" placeholder="搜索…" /></div>' +
        '    <div class="kg2-search-drop" id="kg2FocusDrop" style="position:relative;top:0;display:none"></div>' +
        industrySwitcherHtml("side") +
        '    <div class="kg2-legend-box">' +
        '      <div class="row"><span class="kg2-dot" style="background:#f97316;color:#f97316"></span>业务问题</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#10b981;color:#10b981"></span>分析方法</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#3b82f6;color:#3b82f6"></span>指标字典</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#a855f7;color:#a855f7"></span>当前中心（第1层）</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#94a3b8;color:#94a3b8"></span>周围关联（第2层）</div>' +
        '      <div class="row"><span class="kg2-dot" style="background:#64748b;color:#64748b"></span>展开外环（第3层）</div>' +
        "    </div>" +
        '    <div class="kg2-more-btns" id="kg2More"></div>' +
        '    <div class="kg2-path-hist"><div style="margin-bottom:4px;font-weight:600">探索路径</div><div id="kg2Hist"></div></div>' +
        "  </aside>" +
        '  <div class="kg2-canvas-wrap">' +
        '    <button type="button" class="kg2-rail-btn kg2-rail-left" id="kg2ToggleSide" title="' + (sideCollapsed ? "展开左侧栏" : "收起左侧栏") + '">' + (sideCollapsed ? "»" : "«") + "</button>" +
        '    <div class="kg2-network" id="kg2Net"></div>' +
        '    <div class="kg2-canvas-hint">点击第2层节点展开第3层 · 左右「« »」可收起侧栏腾出画布</div>' +
        '    <div class="kg2-ctrl"><button type="button" id="kg2ZoomIn">＋</button><button type="button" id="kg2ZoomOut">－</button><button type="button" id="kg2Fit">◎</button></div>' +
        '    <button type="button" class="kg2-rail-btn kg2-rail-right" id="kg2TogglePanel" title="' + (panelCollapsed ? "展开右侧详情" : "收起右侧详情") + '">' + (panelCollapsed ? "«" : "»") + "</button>" +
        "  </div>" +
        '  <aside class="kg2-panel open ' + (panelCollapsed ? "is-collapsed " : "") + (TYPE[panelNode.type] ? TYPE[panelNode.type].cls : "") + '" id="kg2Panel" style="width:' + panelWidth + 'px">' +
        '    <div class="kg2-panel-resizer" id="kg2PanelResizer" title="拖拽左边缘调整宽度" aria-label="拖拽调整右侧栏宽度"></div>' +
        '    <div class="kg2-panel-body" id="kg2PanelBody"></div>' +
        "  </aside>" +
        "</div>";

      bindIndustrySwitcher(stageEl);
      function refitGraph() {
        setTimeout(function () {
          try {
            if (network) network.fit({ animation: { duration: 280, easingFunction: "easeInOutCubic" } });
          } catch (e) {}
        }, 320);
      }
      bindPanelResize(stageEl.querySelector("#kg2Panel"), stageEl.querySelector("#kg2PanelResizer"), refitGraph);
      stageEl.querySelector("#kg2ToggleSide").addEventListener("click", function () {
        sideCollapsed = !sideCollapsed;
        var focus = stageEl.querySelector(".kg2-focus");
        var side = stageEl.querySelector("#kg2Side");
        var btn = stageEl.querySelector("#kg2ToggleSide");
        focus.classList.toggle("is-side-collapsed", sideCollapsed);
        side.classList.toggle("is-collapsed", sideCollapsed);
        btn.textContent = sideCollapsed ? "»" : "«";
        btn.title = sideCollapsed ? "展开左侧栏" : "收起左侧栏";
        refitGraph();
      });
      stageEl.querySelector("#kg2TogglePanel").addEventListener("click", function () {
        panelCollapsed = !panelCollapsed;
        var focus = stageEl.querySelector(".kg2-focus");
        var panel = stageEl.querySelector("#kg2Panel");
        var btn = stageEl.querySelector("#kg2TogglePanel");
        focus.classList.toggle("is-panel-collapsed", panelCollapsed);
        panel.classList.toggle("is-collapsed", panelCollapsed);
        btn.textContent = panelCollapsed ? "«" : "»";
        btn.title = panelCollapsed ? "展开右侧详情" : "收起右侧详情";
        refitGraph();
      });
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
      var rel = relatedFor(center, 12);
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
          highlightSelection();
          updateMoreButtons(center);
        });
        box.appendChild(btn);
      });
      if (expandedId && byId.get(expandedId)) {
        var rel3 = relatedFor(byId.get(expandedId), 12);
        ["business_problem", "methodology", "metric"].forEach(function (t) {
          var total3 = (rel3[t] || []).filter(function (n) {
            return n.id !== centerId && n.id !== expandedId;
          }).length;
          if (total3 <= showMoreL3[t]) return;
          var btn3 = document.createElement("button");
          btn3.type = "button";
          btn3.textContent = "第3层更多" + TYPE[t].label + "（" + showMoreL3[t] + "/" + total3 + "）";
          btn3.addEventListener("click", function () {
            showMoreL3[t] = Math.min(total3, showMoreL3[t] + 4);
            drawGraph(center);
            highlightSelection();
            updateMoreButtons(center);
          });
          box.appendChild(btn3);
        });
        var collapse = document.createElement("button");
        collapse.type = "button";
        collapse.textContent = "收起第3层（" + trunc(byId.get(expandedId).name, 12) + "）";
        collapse.addEventListener("click", function () {
          expandedId = null;
          drawGraph(center);
          highlightSelection();
          updateMoreButtons(center);
        });
        box.appendChild(collapse);
      }
    }

    function collectL3(parent, occupied) {
      // 多取候选：第3层会与第2层大量重叠，需要更大补全池
      var rel = relatedFor(parent, 10);
      var out = [];
      ["business_problem", "methodology", "metric"].forEach(function (t) {
        (rel[t] || []).forEach(function (n) {
          if (occupied[n.id]) return;
          out.push(n);
        });
      });
      // 仍不足时，再从同行业/同模块池里硬补（避开已占用）
      function hardFill(type, need) {
        var have = out.filter(function (n) { return n.type === type; }).length;
        if (have >= need) return;
        var pool = leavesOfType(type).filter(function (n) {
          return !occupied[n.id] && out.every(function (x) { return x.id !== n.id; });
        });
        pool.sort(function (a, b) {
          var sa = a.category === parent.category ? 0 : 1;
          var sb = b.category === parent.category ? 0 : 1;
          return sa - sb;
        });
        while (have < need && pool.length) {
          out.push(pool.shift());
          have += 1;
        }
      }
      hardFill("business_problem", showMoreL3.business_problem);
      hardFill("methodology", showMoreL3.methodology);
      hardFill("metric", showMoreL3.metric);

      var capped = [];
      var used = { business_problem: 0, methodology: 0, metric: 0 };
      out.forEach(function (n) {
        if (used[n.type] >= showMoreL3[n.type]) return;
        used[n.type] += 1;
        capped.push(n);
      });
      return capped;
    }

    function sectorAngle(type) {
      // 左上问题、右上方法、正下指标（屏幕坐标 y 向下）
      if (type === "business_problem") return (135 * Math.PI) / 180;
      if (type === "methodology") return (45 * Math.PI) / 180;
      return (270 * Math.PI) / 180;
    }

    function drawGraph(center) {
      // 第2层多取一些，保证 showMore 切片够用
      var rel = relatedFor(center, 10);
      var nodeObjs = [];
      var edgeObjs = [];
      var cx = 0, cy = 0;
      layerOf = {};
      layerOf[center.id] = 1;

      var occupied = {};
      occupied[center.id] = true;

      // center XL — 第1层
      nodeObjs.push({
        id: center.id,
        label: trunc(center.name, 8),
        title: center.name + "（第1层·中心）",
        x: cx, y: cy, fixed: true,
        shape: "dot",
        size: 65,
        color: { background: "#a855f7", border: "#e9d5ff", highlight: { background: "#c084fc", border: "#fff" } },
        borderWidth: 3,
        font: { color: "#fff", size: 12, face: "Noto Sans SC, Microsoft YaHei, sans-serif", strokeWidth: 2, strokeColor: "rgba(10,14,26,0.8)" },
        shadow: { enabled: true, color: "rgba(168,85,247,0.65)", size: 32, x: 0, y: 0 },
        mass: 4
      });

      var l2Positions = {};

      ["business_problem", "methodology", "metric"].forEach(function (t) {
        var list = rel[t].slice(0, showMore[t]);
        var base = sectorAngle(t);
        var meta = TYPE[t];
        var n = list.length;
        var spread = Math.min(0.9, 0.18 * Math.max(n, 1));
        list.forEach(function (node, i) {
          if (occupied[node.id]) return;
          occupied[node.id] = true;
          layerOf[node.id] = 2;
          var ang = n === 1 ? base : base - spread / 2 + (spread * i) / Math.max(n - 1, 1);
          var r = 220 + (i % 3) * 28;
          var x = Math.cos(ang) * r;
          var y = -Math.sin(ang) * r;
          l2Positions[node.id] = { x: x, y: y, ang: ang, r: r };
          // 从中心内侧弹出，交给弹簧拉到目标半径（对齐数据平台入场）
          var x0 = x * 0.58;
          var y0 = y * 0.58;
          var isExp = expandedId === node.id;
          nodeObjs.push({
            id: node.id,
            label: trunc(node.name, 6),
            title: node.name + (isExp ? "（第2层·已展开）" : "（第2层·点击展开第3层）"),
            x: x0, y: y0, fixed: false,
            shape: "dot",
            size: isExp ? 34 : 30,
            color: {
              background: isExp ? meta.color : meta.dark,
              border: isExp ? "#fff" : meta.color,
              highlight: { background: meta.color, border: "#fff" },
              hover: { background: meta.color, border: "#fff" }
            },
            borderWidth: isExp ? 3 : 2,
            font: { color: "#f8fafc", size: 11, face: "Noto Sans SC, Microsoft YaHei, sans-serif", strokeWidth: 2, strokeColor: "rgba(10,14,26,0.75)" },
            shadow: { enabled: true, color: meta.glow, size: isExp ? 20 : 16, x: 0, y: 0 },
            mass: 1.2
          });
          edgeObjs.push({
            id: "e_" + center.id + "_" + node.id,
            from: center.id,
            to: node.id,
            color: { color: meta.color, opacity: 0.55 },
            width: 2.4,
            length: r,
            smooth: { enabled: true, type: "curvedCW", roundness: 0.28 },
            arrows: { to: { enabled: true, scaleFactor: 0.4 } }
          });
        });
      });

      // 若展开节点已不在第2层可见集合中，自动清除
      if (expandedId && !l2Positions[expandedId]) {
        expandedId = null;
      }

      // 第3层：挂在已展开的第2层节点外侧
      if (expandedId && l2Positions[expandedId]) {
        var parent = byId.get(expandedId);
        var pos = l2Positions[expandedId];
        var l3list = collectL3(parent, occupied);
        var n3 = l3list.length;
        var fan = Math.min(1.1, 0.22 * Math.max(n3, 1));
        l3list.forEach(function (child, j) {
          occupied[child.id] = true;
          layerOf[child.id] = 3;
          var meta3 = TYPE[child.type] || TYPE.metric;
          var ang3 = n3 === 1 ? pos.ang : pos.ang - fan / 2 + (fan * j) / Math.max(n3 - 1, 1);
          var r3 = pos.r + 115 + (j % 2) * 18;
          var x3 = Math.cos(ang3) * r3;
          var y3 = -Math.sin(ang3) * r3;
          var edgeLen3 = Math.hypot(x3 - pos.x, y3 - pos.y) || 120;
          var x30 = pos.x * 0.42 + x3 * 0.58;
          var y30 = pos.y * 0.42 + y3 * 0.58;
          nodeObjs.push({
            id: child.id,
            label: trunc(child.name, 5),
            title: child.name + "（第3层·终点，仅查看详情）",
            x: x30, y: y30, fixed: false,
            shape: "dot",
            size: 20,
            color: {
              background: meta3.dark,
              border: "rgba(255,255,255,0.4)",
              highlight: { background: meta3.color, border: "#fff" },
              hover: { background: meta3.color, border: "#fff" }
            },
            borderWidth: 1.5,
            font: { color: "#e2e8f0", size: 10, face: "Noto Sans SC, Microsoft YaHei, sans-serif", strokeWidth: 2, strokeColor: "rgba(10,14,26,0.75)" },
            shadow: { enabled: true, color: meta3.glow, size: 10, x: 0, y: 0 },
            mass: 0.7,
            opacity: 0.92
          });
          edgeObjs.push({
            id: "e3_" + expandedId + "_" + child.id,
            from: expandedId,
            to: child.id,
            color: { color: meta3.color, opacity: 0.35 },
            width: 1.4,
            length: edgeLen3,
            dashes: true,
            smooth: { enabled: true, type: "curvedCW", roundness: 0.35 },
            arrows: { to: { enabled: true, scaleFactor: 0.3 } }
          });
        });
      }

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
            barnesHut: {
              gravitationalConstant: -1600,
              centralGravity: 0.012,
              springLength: 180,
              springConstant: 0.16,
              damping: 0.28,
              avoidOverlap: 0.82
            },
            stabilization: { enabled: true, iterations: 70, fit: false },
            maxVelocity: 42,
            minVelocity: 0.08
          },
          layout: { improvedLayout: false }
        });
        network.on("click", function (p) {
          if (!p.nodes.length) return;
          var id = p.nodes[0];
          var layer = layerOf[id] || 1;
          var center = byId.get(centerId);
          if (layer === 2) {
            // 第2层：展开/切换第3层；再次点击同一节点则收起
            if (expandedId === id) {
              expandedId = null;
            } else {
              expandedId = id;
              showMoreL3 = { business_problem: 5, methodology: 5, metric: 5 };
            }
            selectedId = id;
            renderPanel(byId.get(id));
            drawGraph(center);
            highlightSelection();
            updateMoreButtons(center);
            return;
          }
          // 第1层 / 第3层：只更新右侧详情，不再向外扩展
          selectNode(id);
        });
        network.on("hoverNode", function (p) {
          hoverId = p.node;
          var layer = layerOf[p.node] || 1;
          var base = layer === 1 ? 65 : layer === 3 ? 20 : 30;
          try {
            nodesDS.update({ id: p.node, size: base * 1.2 });
          } catch (e) {}
        });
        network.on("blurNode", function (p) {
          hoverId = null;
          var layer = layerOf[p.node] || 1;
          var base = layer === 1 ? 65 : layer === 3 ? 20 : (p.node === expandedId ? 34 : 30);
          try {
            nodesDS.update({ id: p.node, size: base });
          } catch (e) {}
        });
        network.on("stabilizationIterationsDone", function () {
          if (!network) return;
          // 稳定后仍保留弹簧，拖动能回弹，而不是把阻尼拧死
          network.setOptions({
            physics: {
              barnesHut: {
                gravitationalConstant: -1200,
                centralGravity: 0.01,
                springLength: 180,
                springConstant: 0.1,
                damping: 0.38,
                avoidOverlap: 0.7
              },
              minVelocity: 0.06,
              maxVelocity: 24,
              stabilization: { enabled: false }
            }
          });
          try {
            network.fit({ animation: { duration: 420, easingFunction: "easeInOutCubic" } });
          } catch (e) {}
        });
        network.on("dragEnd", function () {
          if (!network) return;
          network.startSimulation();
        });
      }

      nodesDS.clear();
      edgesDS.clear();
      nodesDS.add(nodeObjs);
      edgesDS.add(edgeObjs);
      network.setOptions({ physics: { enabled: true, stabilization: { enabled: true, iterations: 70, fit: false } } });
      network.startSimulation();
      setTimeout(function () {
        try { if (network) network.redraw(); } catch (e) {}
      }, 60);
      startPulse(center.id);
    }

    function bindPanelResize(panel, handle, onDone) {
      if (!panel || !handle || handle.getAttribute("data-bound") === "1") return;
      handle.setAttribute("data-bound", "1");
      var dragging = false;
      var startX = 0;
      var startW = 0;
      var mask = null;

      function clampW(w) {
        var focus = stageEl.querySelector(".kg2-focus");
        var maxByViewport = Math.floor(window.innerWidth * 0.62);
        var maxByFocus = focus ? Math.floor(focus.clientWidth * 0.58) : maxByViewport;
        var max = Math.max(320, Math.min(720, maxByViewport, maxByFocus));
        return Math.max(260, Math.min(max, Math.round(w)));
      }

      function cleanup() {
        dragging = false;
        panel.classList.remove("is-resizing");
        document.body.classList.remove("kg2-resizing");
        if (mask && mask.parentNode) mask.parentNode.removeChild(mask);
        mask = null;
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        document.removeEventListener("pointercancel", onUp);
        window.removeEventListener("blur", cleanup);
      }

      function onMove(e) {
        if (!dragging) return;
        var x = e.clientX;
        if (x == null && e.touches && e.touches[0]) x = e.touches[0].clientX;
        if (x == null) return;
        var next = clampW(startW + (startX - x));
        panelWidth = next;
        panel.style.width = next + "px";
      }

      function onUp() {
        if (!dragging) return;
        cleanup();
        if (typeof onDone === "function") onDone();
      }

      handle.addEventListener("pointerdown", function (e) {
        if (panelCollapsed || panel.classList.contains("is-collapsed")) return;
        if (window.matchMedia && window.matchMedia("(max-width: 960px)").matches) return;
        if (e.button != null && e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        dragging = true;
        startX = e.clientX;
        startW = panel.getBoundingClientRect().width || panelWidth;
        panel.classList.add("is-resizing");
        document.body.classList.add("kg2-resizing");
        mask = document.createElement("div");
        mask.className = "kg2-resize-mask";
        document.body.appendChild(mask);
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
        document.addEventListener("pointercancel", onUp);
        window.addEventListener("blur", cleanup);
      });
    }

    function renderPanel(node) {
      var panel = stageEl.querySelector("#kg2Panel");
      var body = stageEl.querySelector("#kg2PanelBody") || panel;
      if (!panel) return;
      var meta = TYPE[node.type] || TYPE.metric;
      var d = node.detail || {};
      var rel = relatedFor(node);
      var layer = layerOf[node.id] || (node.id === centerId ? 1 : 2);
      var html =
        "<h2>" + esc(node.name) + "</h2>" +
        '<span class="kg2-tag ' + meta.cls + '">' + meta.label + "</span>" +
        '<span class="kg2-tag" style="margin-left:6px;opacity:.85">第' + layer + "层</span>";
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

      // 指标：与指标字典翻面一致的用途说明
      if (node.type === "metric") {
        var usage = metricUsageDetail(node);
        html +=
          '<div class="kg2-sec kg2-usage">' +
          "<h3>可用于解决</h3>" +
          '<p class="kg2-usage-sub">这个指标常用来解决什么问题</p>' +
          "<ul>" + usage.problems.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul>" +
          "</div>";
        if (usage.methods.length) {
          html +=
            '<div class="kg2-sec"><h3>相关方法 / 场景</h3><div class="kg2-chips">' +
            usage.methods.map(function (m) { return "<span>" + esc(m) + "</span>"; }).join("") +
            "</div></div>";
        }
        if (usage.tips.length) {
          html +=
            '<div class="kg2-sec"><h3>口径提示</h3><ul>' +
            usage.tips.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") +
            "</ul></div>";
        }
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

      if (layer === 2) {
        html +=
          '<div class="kg2-sec">' +
          '<button type="button" class="kg2-explore-center" id="kg2ToggleL3">' +
          (expandedId === node.id ? "收起第3层关联" : "在图上展开第3层关联") +
          "</button></div>";
      }
      if (node.id !== centerId) {
        html +=
          '<div class="kg2-sec">' +
          '<button type="button" class="kg2-explore-center" id="kg2ExploreCenter">以此为中心重新探索图谱</button>' +
          "</div>";
      }

      body.innerHTML = html;
      panel.className = "kg2-panel open " + (panelCollapsed ? "is-collapsed " : "") + meta.cls;
      panel.style.width = panelWidth + "px";
      body.querySelectorAll("[data-jump]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          enterFocus(btn.getAttribute("data-jump"), true);
        });
      });
      var toggleL3 = body.querySelector("#kg2ToggleL3");
      if (toggleL3) {
        toggleL3.addEventListener("click", function () {
          var center = byId.get(centerId);
          if (expandedId === node.id) expandedId = null;
          else {
            expandedId = node.id;
            showMoreL3 = { business_problem: 5, methodology: 5, metric: 5 };
          }
          drawGraph(center);
          highlightSelection();
          updateMoreButtons(center);
          renderPanel(node);
        });
      }
      var exploreBtn = body.querySelector("#kg2ExploreCenter");
      if (exploreBtn) {
        exploreBtn.addEventListener("click", function () {
          enterFocus(node.id, true);
        });
      }
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

    function nodeSearchText(n) {
      if (n._kgSearchBlob) return n._kgSearchBlob;
      var d = n.detail || {};
      var parts = [
        n.name,
        n.description,
        n.categoryName,
        n.subtitle,
        (n.tags || []).join(" "),
        d.definition,
        d.formula,
        (d.notes || []).join(" "),
        (d.applicableScenarios || []).join(" "),
        (d.steps || []).join(" "),
        n._search_text
      ];
      n._kgSearchBlob = parts
        .filter(Boolean)
        .join("\n")
        .toLowerCase();
      return n._kgSearchBlob;
    }

    /** 常见同义词 / 近义扩展，提升短词召回（如「利润」→净利率/毛利率） */
    var SEARCH_ALIASES = {
      利润: ["净利率", "毛利率", "盈利", "利润率", "ROE", "ROA", "净利润", "毛利", "盈亏"],
      收入: ["营收", "销售额", "GMV", "MRR", "ARR", "流水", "成交额"],
      成本: ["费用", "CAC", "获客成本", "物流成本", "制造成本"],
      留存: ["留存率", "次日留存", "7日留存", "30日留存", "NDR", "GRR", "复购"],
      转化: ["转化率", "漏斗", "下单", "支付成功率", "激活率"],
      用户: ["UV", "DAU", "MAU", "访客", "客户", "会员"],
      活跃: ["DAU", "MAU", "活跃率", "在线时长"],
      流失: ["流失率", "Churn", "召回", "流失预警"],
      风控: ["不良率", "通过率", "信用评分", "反欺诈", "逾期"],
      库存: ["周转", "缺货", "动销", "售罄", "呆滞"],
      roi: ["ROI", "ROAS", "投入产出", "营销效果"],
      gmv: ["GMV", "成交总额", "销售额"]
    };

    function searchTermsFor(q) {
      var raw = String(q || "").trim();
      var terms = [raw];
      var key = raw.toLowerCase();
      var aliases = SEARCH_ALIASES[raw] || SEARCH_ALIASES[key];
      if (aliases) terms = terms.concat(aliases);
      // 短词也试拆：如「净利率」已在名中；「利润率」等
      return terms.filter(Boolean);
    }

    function scoreNode(n, q, terms) {
      var name = String(n.name || "").toLowerCase();
      var ql = q.toLowerCase();
      var score = 0;
      if (name.indexOf(ql) >= 0) score += 100;
      if (name === ql) score += 50;
      var blob = nodeSearchText(n);
      for (var i = 0; i < terms.length; i++) {
        var t = String(terms[i]).toLowerCase();
        if (!t) continue;
        if (name.indexOf(t) >= 0) score += 40;
        else if (blob.indexOf(t) >= 0) score += 10;
      }
      return score;
    }

    function wireSearch(input, drop) {
      if (!input || !drop) return;
      function run() {
        var q = (input.value || "").trim();
        if (!q) { drop.classList.remove("open"); drop.style.display = "none"; drop.innerHTML = ""; return; }
        var terms = searchTermsFor(q);
        var groups = { business_problem: [], methodology: [], metric: [] };
        var scored = { business_problem: [], methodology: [], metric: [] };
        DATA.nodes.forEach(function (n) {
          if (n.isRoot || n.isCategory) return;
          if (!TYPE[n.type]) return;
          if (n.type !== "methodology" && !matchIndustry(n)) return;
          var sc = scoreNode(n, q, terms);
          if (sc <= 0) return;
          scored[n.type].push({ n: n, sc: sc });
        });
        ["business_problem", "methodology", "metric"].forEach(function (t) {
          scored[t].sort(function (a, b) { return b.sc - a.sc; });
          groups[t] = scored[t].slice(0, 10).map(function (x) { return x.n; });
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
    function resolveStartNode(raw) {
      if (!raw) return null;
      if (byId.has(raw)) return raw;
      // 允许用名称定位（指标字典跳转兜底）
      var hit = DATA.nodes.find(function (n) {
        return !n.isRoot && !n.isCategory && n.name === raw;
      });
      return hit ? hit.id : null;
    }

    var bootNode = resolveStartNode(opts.startNode);
    if (opts.startIndustry && INDUSTRY_ALIAS[opts.startIndustry]) {
      industry = opts.startIndustry;
    } else if (opts.startIndustry) {
      // liveecommerce → live-ecommerce 等
      var aliasHit = Object.keys(INDUSTRY_ALIAS).find(function (k) {
        return (INDUSTRY_ALIAS[k] || []).indexOf(opts.startIndustry) >= 0;
      });
      if (aliasHit) industry = aliasHit;
      else industry = opts.startIndustry;
    } else if (bootNode) {
      var boot = byId.get(bootNode);
      if (boot && boot.category && boot.category !== "general" && boot.type !== "methodology") {
        var indHit = Object.keys(INDUSTRY_ALIAS).find(function (k) {
          return (INDUSTRY_ALIAS[k] || []).indexOf(boot.category) >= 0;
        });
        if (indHit) industry = indHit;
      }
    }

    if (bootNode) {
      enterFocus(bootNode, false);
    } else if (opts.startModule && TYPE[opts.startModule]) {
      enterOverview(opts.startModule);
    } else {
      render();
    }

    return {
      goLanding: function () { stage = "landing"; render(); },
      enterFocus: enterFocus,
      destroy: function () { setFocusMode(false); destroyNet(); }
    };
  }

  window.initKnowledgeGraph = initKnowledgeGraph;

  function autoStartKg() {
    var auto = document.getElementById("kgAutoRoot");
    if (!auto || window.__kgInstance) return;
    var params = new URLSearchParams(location.search);
    window.__kgInstance = initKnowledgeGraph({
      root: auto,
      startModule: params.get("module") || auto.dataset.module || null,
      startNode: params.get("node") || params.get("q") || null,
      startIndustry: params.get("industry") || params.get("category") || null
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoStartKg);
  } else {
    autoStartKg();
  }
})();
