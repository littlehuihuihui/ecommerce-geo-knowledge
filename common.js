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
});
