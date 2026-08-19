// 公共JS文件
(function () {
  function boot() {
    var path = currentPageName();

    // 行业平铺条：根据当前路径高亮
    document.querySelectorAll('.nav-ind-link').forEach(function (a) {
      var href = (a.getAttribute('href') || '').split('/').pop();
      a.classList.toggle('active', href === path);
    });

    // 三站互链（若导航尚未写入）
    var navLinks = document.querySelector('.encyclopedia-nav .nav-links');
    if (navLinks && !navLinks.querySelector('a[href*="data-analyst-gallery"]')) {
      var gallery = document.createElement('a');
      gallery.href = 'https://littlehuihuihui.github.io/data-analyst-gallery/';
      gallery.className = 'nav-link';
      gallery.target = '_blank';
      gallery.rel = 'noopener';
      gallery.textContent = '个人展馆';

      var platform = document.createElement('a');
      platform.href = 'https://littlehuihuihui.github.io/financial-data-portfolio/';
      platform.className = 'nav-link';
      platform.target = '_blank';
      platform.rel = 'noopener';
      platform.textContent = '数据平台';

      navLinks.appendChild(gallery);
      navLinks.appendChild(platform);
    }

    // 多北极星切换
    document.querySelectorAll('.ns-switch').forEach(function (root) {
      var tabs = root.querySelectorAll('.ns-tab');
      var panels = root.querySelectorAll('.ns-panel');
      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          var id = tab.getAttribute('data-ns');
          tabs.forEach(function (t) {
            t.classList.toggle('is-active', t === tab);
            t.setAttribute('aria-selected', t === tab ? 'true' : 'false');
          });
          panels.forEach(function (p) {
            p.classList.toggle('is-active', p.getAttribute('data-ns') === id);
          });
        });
      });
    });

    wireFrameworkDeepLinks(path);
  }

  function currentPageName() {
    var p = location.pathname || '';
    try { p = decodeURIComponent(p); } catch (e) {}
    var name = (p.split('/').filter(Boolean).pop() || '').split('?')[0].split('#')[0];
    if (!name) name = 'index.html';
    if (name.indexOf('.') < 0) name += '.html';
    return name.toLowerCase();
  }

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

  function resolveIndustry(path) {
    var fromBody = document.body && document.body.getAttribute('data-industry');
    if (fromBody) return fromBody;
    var fromMain = document.querySelector('main[data-industry], .container[data-industry]');
    if (fromMain) return fromMain.getAttribute('data-industry');
    return FRAMEWORK_INDUSTRY_MAP[path] || null;
  }

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

  function hintText(kind) {
    if (kind === 'metric') return '指标字典 →';
    if (kind === 'scenario') return '业务问题 →';
    return '方法论 →';
  }

  /** 把元素变成真实 <a>，不依赖 click 监听也能跳 */
  function promoteToAnchor(el, url, kind) {
    if (!el || el.getAttribute('data-fw-wired') === '1') return;
    el.setAttribute('data-fw-wired', '1');

    var a;
    if (el.tagName === 'A') {
      a = el;
      a.setAttribute('href', url);
    } else {
      a = document.createElement('a');
      a.href = url;
      a.className = el.className;
      Array.prototype.slice.call(el.attributes).forEach(function (attr) {
        if (attr.name === 'class') return;
        if (attr.name === 'id' || attr.name.indexOf('data-') === 0 || attr.name.indexOf('aria-') === 0) {
          a.setAttribute(attr.name, attr.value);
        }
      });
      while (el.firstChild) a.appendChild(el.firstChild);
      if (el.parentNode) el.parentNode.replaceChild(a, el);
    }

    a.classList.add('fw-jump', 'fw-jump-' + kind);
    a.style.textDecoration = 'none';
    a.style.color = 'inherit';
    a.setAttribute('title', hintText(kind).replace(' →', ''));

    if (!a.querySelector('.fw-jump-hint')) {
      var hint = document.createElement('span');
      hint.className = 'fw-jump-hint';
      hint.setAttribute('aria-hidden', 'true');
      hint.textContent = hintText(kind);
      a.appendChild(hint);
    }
    return a;
  }

  function wireFrameworkDeepLinks(path) {
    var industry = resolveIndustry(path);
    if (!industry) return;
    if (document.body) document.body.setAttribute('data-industry', industry);

    document.querySelectorAll('.mc-item').forEach(function (item) {
      var nameEl = item.querySelector('.mc-name');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(item, buildModuleUrl('metrics.html', q, industry), 'metric');
    });

    document.querySelectorAll('.ns-name').forEach(function (el) {
      var q = normalizeJumpQuery(el.textContent);
      if (!q) return;
      var wrap = el.closest('.north-star-card') || el;
      promoteToAnchor(wrap, buildModuleUrl('metrics.html', q, industry), 'metric');
    });

    document.querySelectorAll('.scenario-card').forEach(function (card) {
      var nameEl = card.querySelector('.scenario-name');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent)
        .replace(/(优化|评估|分析|归因|提升|策略)$/g, '')
        .trim();
      if (!q) q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(card, buildModuleUrl('interview.html', q, industry), 'scenario');
    });

    document.querySelectorAll('.framework-card').forEach(function (card) {
      var nameEl = card.querySelector('.framework-name');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent)
        .replace(/(分析|模型|评估|框架)$/g, '')
        .trim();
      if (!q) q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(card, buildModuleUrl('methodology.html', q, null), 'method');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
