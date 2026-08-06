// 公共JS文件
document.addEventListener('DOMContentLoaded', function() {
  // 导航栏下拉菜单点击展开/收起
  const dropdownToggles = document.querySelectorAll('.nav-dropdown-toggle');

  dropdownToggles.forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      const dropdown = this.closest('.nav-dropdown');
      const menu = dropdown.querySelector('.nav-dropdown-menu');

      if (menu.style.opacity === '1') {
        menu.style.opacity = '0';
        menu.style.visibility = 'hidden';
        menu.style.transform = 'translateY(-8px)';
      } else {
        document.querySelectorAll('.nav-dropdown-menu').forEach(function (m) {
          m.style.opacity = '0';
          m.style.visibility = 'hidden';
          m.style.transform = 'translateY(-8px)';
        });

        menu.style.opacity = '1';
        menu.style.visibility = 'visible';
        menu.style.transform = 'translateY(0)';
      }
    });
  });

  // 点击页面其他地方关闭下拉菜单
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-dropdown')) {
      document.querySelectorAll('.nav-dropdown-menu').forEach(function (menu) {
        menu.style.opacity = '0';
        menu.style.visibility = 'hidden';
        menu.style.transform = 'translateY(-8px)';
      });
    }
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

    const dropdown = navLinks.querySelector('.nav-dropdown');
    if (dropdown) {
      navLinks.insertBefore(gallery, dropdown);
      navLinks.insertBefore(platform, dropdown);
    } else {
      navLinks.appendChild(gallery);
      navLinks.appendChild(platform);
    }
  }
});
