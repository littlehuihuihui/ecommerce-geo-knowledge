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

    setupMobileNav();
    setupNavSearch();

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

  /** 手机端：折叠导航链接，避免固定顶栏搜索/链接叠在内容上 */
  function setupMobileNav() {
    var nav = document.querySelector('.encyclopedia-nav');
    if (!nav || nav.querySelector('.nav-toggle')) return;
    var links = nav.querySelector('.nav-links');
    if (!links) return;

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-toggle';
    btn.setAttribute('aria-label', '打开菜单');
    btn.setAttribute('aria-expanded', 'false');
    btn.textContent = '☰';

    var right = nav.querySelector('.nav-right');
    if (right) {
      nav.insertBefore(btn, right);
    } else {
      nav.appendChild(btn);
    }

    nav.classList.add('nav-enhanced');

    function setOpen(open) {
      nav.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
      btn.textContent = open ? '✕' : '☰';
    }

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      setOpen(!nav.classList.contains('nav-open'));
    });

    links.addEventListener('click', function (e) {
      if (e.target.closest('a.nav-link')) setOpen(false);
    });

    document.addEventListener('click', function (e) {
      if (!nav.classList.contains('nav-open')) return;
      if (nav.contains(e.target)) return;
      setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });
  }

  /** 顶栏搜索回车 → 智能搜索（GitHub Pages 可用本地检索） */
  function setupNavSearch() {
    var input = document.querySelector('.encyclopedia-nav .nav-search input');
    if (!input || input.getAttribute('data-nav-search') === '1') return;
    input.setAttribute('data-nav-search', '1');
    input.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      var q = (input.value || '').trim();
      if (!q) return;
      e.preventDefault();
      var path = (location.pathname || '').replace(/\\/g, '/');
      var inRag = /\/rag\//.test(path);
      var base = '';
      var scripts = document.querySelectorAll('script[src*="common.js"]');
      if (scripts.length) {
        var src = scripts[scripts.length - 1].getAttribute('src') || '';
        if (src.indexOf('../') === 0) base = '../';
      }
      if (inRag) location.href = 'search.html?q=' + encodeURIComponent(q);
      else location.href = base + 'rag/search.html?q=' + encodeURIComponent(q);
    });
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
    'banking.html': 'banking',
    'insurance.html': 'insurance',
    'securities.html': 'securities',
    'payment.html': 'payment',
    'pension.html': 'pension',
    'game.html': 'game',
    'content.html': 'content',
    'saas.html': 'saas',
    'live-ecommerce.html': 'live-ecommerce',
    'local-life.html': 'local-life',
    'fmcg.html': 'fmcg',
    'manufacturing.html': 'manufacturing',
    'healthcare.html': 'healthcare',
    'new-energy.html': 'newenergy',
    'logistics.html': 'logistics',
    'tourism.html': 'general'
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

    // 框架常用名 → 字典/题库更易命中的词
    var ALIAS = {
      '访客数': 'UV',
      '浏览量': 'PV',
      '点击率': 'CTR',
      '跳失率': '跳出',
      '访问深度': 'PV',
      '下单转化率': '转化率',
      '支付转化率': '转化率',
      '支付成功率': '支付',
      '新客数': '获客',
      '老客数': '复购',
      '客服响应时长': '客服',
      '物流时效': '履约',
      '发货时效': '履约',
      'DSR 评分': 'DSR',
      'DSR评分': 'DSR',
      '人均GMV': 'GMV',
      '转化漏斗': '漏斗',
      '用户生命周期': '生命周期',
      'GMV 拆解': 'GMV',
      '营销效果': 'ROI',
      '营销 ROI': 'ROI',
      '营销ROI': 'ROI',
      'AARRR 海盗模型': 'AARRR',
      'AARRR海盗模型': 'AARRR',
      'ABC 分类法': 'ABC',
      'PDCA 循环': 'PDCA',
      'SPC 统计过程控制': 'SPC',
      '牛鞭效应说明': '牛鞭',
      '客户分层运营': '分层',
      '用户分层运营': '分层'
    };
    if (ALIAS[s]) s = ALIAS[s];
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

  function isConcretePageLink(el) {
    if (!el || el.tagName !== 'A') return false;
    var href = (el.getAttribute('href') || '').trim();
    if (!href || href.charAt(0) === '#') return false;
    if (/^(https?:|mailto:)/i.test(href)) return true;
    // 指标字典 / 方法论 / 业务问题 仍允许按卡片名改写搜索
    if (/^(metrics|interview|methodology)\.html/i.test(href)) return false;
    return /\.html/i.test(href);
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

    // 部分行业页用 metric-card / metric-name（物流、新能源、金融等）
    document.querySelectorAll('.metric-card').forEach(function (card) {
      if (card.getAttribute('data-fw-wired') === '1') return;
      var nameEl = card.querySelector('.metric-name, h3');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(card, buildModuleUrl('metrics.html', q, industry), 'metric');
    });

    document.querySelectorAll('.ns-name').forEach(function (el) {
      var q = normalizeJumpQuery(el.textContent);
      if (!q) return;
      var wrap = el.closest('.north-star-card') || el;
      promoteToAnchor(wrap, buildModuleUrl('metrics.html', q, industry), 'metric');
    });

    document.querySelectorAll('.scenario-card').forEach(function (card) {
      // 金融总览等：卡片本身已链到细分行业页，不要改成题库关键词搜索
      if (isConcretePageLink(card)) return;
      var nameEl = card.querySelector('.scenario-name');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent)
        .replace(/(优化|评估|分析|归因|提升|策略|规划)$/g, '')
        .trim();
      if (!q) q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(card, buildModuleUrl('interview.html', q, industry), 'scenario');
    });

    document.querySelectorAll('.framework-card').forEach(function (card) {
      if (isConcretePageLink(card)) return;
      var nameEl = card.querySelector('.framework-name');
      if (!nameEl) return;
      var q = normalizeJumpQuery(nameEl.textContent)
        .replace(/(分析|模型|评估|框架)$/g, '')
        .trim();
      if (!q) q = normalizeJumpQuery(nameEl.textContent);
      if (!q) return;
      promoteToAnchor(card, buildModuleUrl('methodology.html', q, null), 'method');
    });

    // 区块说明：提示可点击跳转（全行业统一）
    document.querySelectorAll('.section').forEach(function (section) {
      var desc = section.querySelector('.section-desc');
      if (!desc || /跳转|指标字典|方法论|业务问题/.test(desc.textContent)) return;
      if (section.querySelector('.mc-item, .metric-card, .ns-switch')) {
        desc.innerHTML = desc.innerHTML.replace(/\s*$/, '') +
          ' · 指标可点击跳转<strong>指标字典</strong>';
      } else if (section.querySelector('.framework-card')) {
        desc.innerHTML = desc.innerHTML.replace(/\s*$/, '') +
          ' · 点击卡片跳转<strong>方法论</strong>';
      } else if (section.querySelector('.scenario-card')) {
        var plainScenario = false;
        section.querySelectorAll('.scenario-card').forEach(function (card) {
          if (!isConcretePageLink(card)) plainScenario = true;
        });
        if (plainScenario) {
          desc.innerHTML = desc.innerHTML.replace(/\s*$/, '') +
            ' · 点击卡片跳转<strong>业务问题拆解</strong>';
        }
      }
    });

    // 用户价值分层 / ABC：整块出口，不逐张分层卡跳转
    document.querySelectorAll('.tier-grid').forEach(function (grid) {
      if (grid.getAttribute('data-fw-wired') === '1') return;
      grid.setAttribute('data-fw-wired', '1');
      var section = grid.closest('.section') || grid.parentElement;
      var titleEl = section && section.querySelector('.section-title');
      var title = titleEl ? titleEl.textContent : '';
      var methodQ = '分层';
      var problemQ = '分层';
      if (/RFM/i.test(title) || /用户价值|用户分层|客户分层/.test(title)) {
        methodQ = 'RFM';
        problemQ = 'RFM';
      } else if (/ABC/i.test(title) || /库存.*分类/.test(title)) {
        methodQ = 'ABC';
        problemQ = 'ABC';
      } else if (/鲸鱼|大R|付费/.test(title)) {
        methodQ = '分层';
        problemQ = '付费';
      }

      var bar = document.createElement('div');
      bar.className = 'fw-tier-jumps';
      var html =
        '<a class="fw-tier-jump" href="' + buildModuleUrl('methodology.html', methodQ, null) + '">方法论 · ' + methodQ + ' →</a>' +
        '<a class="fw-tier-jump" href="' + buildModuleUrl('interview.html', problemQ, industry) + '">业务问题 · ' + problemQ + ' →</a>';
      if (methodQ === 'RFM') {
        html += '<a class="fw-tier-jump" href="' + buildModuleUrl('metrics.html', 'RFM', industry) + '">指标字典 · RFM →</a>';
      }
      bar.innerHTML = html;
      grid.parentNode.insertBefore(bar, grid);

      var desc = section && section.querySelector('.section-desc');
      if (desc && !/跳转|方法论|业务问题/.test(desc.textContent)) {
        desc.textContent = String(desc.textContent || '').replace(/\s*$/, '') + ' · 可跳转相关方法论与业务问题';
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
