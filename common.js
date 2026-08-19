// 公共JS文件
document.addEventListener('DOMContentLoaded', function() {
  // 行业平铺条：根据当前路径高亮
  var path = (location.pathname || '').split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-ind-link').forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('/').pop();
    a.classList.toggle('active', href === path);
  });

  // 三站互链（若导航尚未写入）
  const navLinks = document.querySelector('.encyclopedia-nav .nav-links');
  if (navLinks && !navLinks.querySelector('a[href*="data-analyst-gallery"]')) {
    const gallery = document.createElement('a');
    gallery.href = 'https://littlehuihuihui.github.io/data-analyst-gallery/';
    gallery.className = 'nav-link';
    gallery.target = '_blank';
    gallery.rel = 'noopener';
    gallery.textContent = '个人展馆';

    const platform = document.createElement('a');
    platform.href = 'https://littlehuihuihui.github.io/financial-data-portfolio/';
    platform.className = 'nav-link';
    platform.target = '_blank';
    platform.rel = 'noopener';
    platform.textContent = '数据平台';

    navLinks.appendChild(gallery);
    navLinks.appendChild(platform);
  }

  // 多北极星切换
  document.querySelectorAll(".ns-switch").forEach(function (root) {
    var tabs = root.querySelectorAll(".ns-tab");
    var panels = root.querySelectorAll(".ns-panel");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var id = tab.getAttribute("data-ns");
        tabs.forEach(function (t) {
          t.classList.toggle("is-active", t === tab);
          t.setAttribute("aria-selected", t === tab ? "true" : "false");
        });
        panels.forEach(function (p) {
          p.classList.toggle("is-active", p.getAttribute("data-ns") === id);
        });
      });
    });
  });

  // 知识框架页：指标 / 场景 / 方法 → 对应模块深链
  wireFrameworkDeepLinks(path);
});

/** 行业页文件名 → 指标字典 / 业务问题里的 category key */
var FRAMEWORK_INDUSTRY_MAP = {
  'ecommerce.html': 'ecommerce',
  'finance.html': 'finance',
  'game.html': 'game',
  'content.html': 'content',
  'saas.html': 'saas',
  'live-ecommerce.html': 'live-ecommerce',
  'local-life.html': 'local-life',
  'fmcg.html': 'fmcg',
  'manufacturing.html': 'manufacturing',
  'healthcare.html': 'healthcare',
  'new-energy.html': 'newenergy',
  'logistics.html': 'logistics'
};

function normalizeJumpQuery(raw) {
  var s = String(raw || '').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  s = s.replace(/[（(].*$/, '').trim();
  if (s.indexOf('/') >= 0) {
    var parts = s.split('/').map(function (p) { return p.trim(); }).filter(Boolean);
    var acronym = parts.find(function (p) {
      return /^[A-Za-z][A-Za-z0-9+._-]{0,12}$/.test(p);
    });
    if (acronym) {
      s = acronym;
    } else {
      var cn = parts.filter(function (p) { return /[\u4e00-\u9fff]/.test(p); });
      s = (cn.length ? cn[cn.length - 1] : parts[0]) || s;
    }
  }
  s = s.replace(/\s+[A-Za-z][A-Za-z0-9+._-]{1,12}\s*$/, '').trim();
  return s;
}

function buildModuleUrl(page, q, industry) {
  var params = [];
  if (q) params.push('q=' + encodeURIComponent(q));
  if (industry) params.push('industry=' + encodeURIComponent(industry));
  return page + (params.length ? '?' + params.join('&') : '');
}

function wireFrameworkDeepLinks(path) {
  var industry = FRAMEWORK_INDUSTRY_MAP[path];
  if (!industry) return;

  function markClickable(el, kind) {
    el.classList.add('fw-jump', 'fw-jump-' + kind);
    el.setAttribute('role', 'link');
    el.setAttribute('tabindex', '0');
    if (!el.querySelector('.fw-jump-hint')) {
      var hint = document.createElement('span');
      hint.className = 'fw-jump-hint';
      hint.setAttribute('aria-hidden', 'true');
      if (kind === 'metric') hint.textContent = '指标字典 →';
      else if (kind === 'scenario') hint.textContent = '业务问题 →';
      else hint.textContent = '方法论 →';
      el.appendChild(hint);
    }
  }

  function bind(el, url) {
    function go() { location.href = url; }
    el.addEventListener('click', go);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        go();
      }
    });
  }

  document.querySelectorAll('.mc-item').forEach(function (item) {
    var nameEl = item.querySelector('.mc-name');
    if (!nameEl) return;
    var q = normalizeJumpQuery(nameEl.textContent);
    if (!q) return;
    markClickable(item, 'metric');
    bind(item, buildModuleUrl('metrics.html', q, industry));
  });

  document.querySelectorAll('.ns-name').forEach(function (el) {
    var q = normalizeJumpQuery(el.textContent);
    if (!q) return;
    var wrap = el.closest('.north-star-card') || el;
    markClickable(wrap, 'metric');
    bind(wrap, buildModuleUrl('metrics.html', q, industry));
  });

  document.querySelectorAll('.scenario-card').forEach(function (card) {
    var nameEl = card.querySelector('.scenario-name');
    if (!nameEl) return;
    // 场景名常带「优化/评估」等后缀，保留核心词便于业务问题页匹配
    var q = normalizeJumpQuery(nameEl.textContent)
      .replace(/(优化|评估|分析|归因|提升|策略)$/g, '')
      .trim();
    if (!q) q = normalizeJumpQuery(nameEl.textContent);
    if (!q) return;
    markClickable(card, 'scenario');
    bind(card, buildModuleUrl('interview.html', q, industry));
  });

  document.querySelectorAll('.framework-card').forEach(function (card) {
    var nameEl = card.querySelector('.framework-name');
    if (!nameEl) return;
    var q = normalizeJumpQuery(nameEl.textContent)
      .replace(/(分析|模型|评估|框架)$/g, '')
      .trim();
    if (!q) q = normalizeJumpQuery(nameEl.textContent);
    if (!q) return;
    markClickable(card, 'method');
    bind(card, buildModuleUrl('methodology.html', q, null));
  });
}