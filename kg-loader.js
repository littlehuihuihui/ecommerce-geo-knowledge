/* 按需加载知识图谱：列表页首屏不拉取 vis-network / 图谱数据 */
(function (w, d) {
  "use strict";

  var VIS_SRC = "https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js";
  var inflight = {};

  function loadScript(src) {
    if (inflight[src]) return inflight[src];
    inflight[src] = new Promise(function (resolve, reject) {
      var s = d.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error("failed: " + src)); };
      d.head.appendChild(s);
    });
    return inflight[src];
  }

  w.loadKgData = function () {
    if (w.KNOWLEDGE_GRAPH_DATA) return Promise.resolve();
    return loadScript("knowledge-graph-data.js");
  };

  w.loadKgGraph = function () {
    var chain = Promise.resolve();
    if (!w.vis) chain = chain.then(function () { return loadScript(VIS_SRC); });
    chain = chain.then(function () { return w.loadKgData(); });
    chain = chain.then(function () {
      if (w.initKnowledgeGraph) return;
      return loadScript("knowledge-graph-app.js");
    });
    return chain;
  };

  w.bindKgViewSwitch = function (mod) {
    var kg = null;
    var loading = false;
    var mount = d.getElementById("kgPageMount");
    if (!mount) return;

    function setView(mode) {
      d.querySelectorAll(".view-btn").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-view") === mode);
      });
      if (mode !== "graph") {
        d.body.classList.remove("kg-graph-mode");
        mount.style.display = "none";
        mount.classList.remove("is-on");
        return;
      }
      d.body.classList.add("kg-graph-mode");
      mount.style.display = "block";
      mount.classList.add("is-on");
      if (kg || loading) return;
      loading = true;
      mount.setAttribute("aria-busy", "true");
      w.loadKgGraph().then(function () {
        kg = w.initKnowledgeGraph({ root: mount, startModule: mod });
        mount.removeAttribute("aria-busy");
        loading = false;
      }).catch(function () {
        loading = false;
        mount.removeAttribute("aria-busy");
        mount.innerHTML = '<p class="kg2-panel-empty">图谱资源加载失败，请刷新后重试</p>';
      });
    }

    d.querySelectorAll(".view-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setView(btn.getAttribute("data-view"));
      });
    });
    if (location.hash === "#graph" || /[?&]view=graph/.test(location.search)) {
      setView("graph");
    }
  };

  w.idleLoadKgData = function (after) {
    var run = function () {
      w.loadKgData().then(function () {
        if (typeof after === "function") after();
      }).catch(function () {});
    };
    if (w.requestIdleCallback) w.requestIdleCallback(run, { timeout: 1800 });
    else setTimeout(run, 400);
  };
})(window, document);
