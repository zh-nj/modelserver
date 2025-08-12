/**
 * 慧儿模型园 - 导航栏管理
 */

// 更新导航栏显示页面标题和返回按钮，保持Logo不变
function updateNavbarForPage(title, showBackButton = true) {
  const navbarContent = document.querySelector('.navbar-content');
  if (!navbarContent) return;

  // 保存原始导航栏内容
  if (!navbarContent.dataset.originalContent) {
    navbarContent.dataset.originalContent = navbarContent.innerHTML;
  }

  if (showBackButton) {
    navbarContent.innerHTML = `
      <div style="display: flex; align-items: center; gap: 16px;">
        <a href="#" class="logo">
          <svg width="48" height="48" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="g2" x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                <stop offset="0" stop-color="#12B8A6"/>
                <stop offset="1" stop-color="#4F46E5"/>
              </linearGradient>
            </defs>
            <circle cx="16" cy="16" r="12" stroke="url(#g2)" stroke-width="2.2" fill="none"/>
            <g transform="translate(16,16)">
              <circle cx="0" cy="-12" r="1.3" fill="#F5B700"/>
              <g transform="rotate(120)"><circle cx="0" cy="-12" r="1.3" fill="#12B8A6"/></g>
              <g transform="rotate(240)"><circle cx="0" cy="-12" r="1.3" fill="#4F46E5"/></g>
            </g>
            <rect x="11" y="10.8" width="2.8" height="10.4" rx="1.4" fill="#0F172A"/>
            <rect x="18.2" y="10.8" width="2.8" height="10.4" rx="1.4" fill="#0F172A"/>
            <path d="M13.4 16 H20" stroke="#0F172A" stroke-width="2.2" stroke-linecap="round"/>
          </svg>
          <span>慧儿模型园</span>
        </a>
        
        <div class="page-title-nav" style="
          font-size: 18px;
          font-weight: 600;
          color: var(--text-primary);
          display: flex;
          align-items: center;
          gap: 8px;
        ">
          <span>${title}</span>
        </div>
      </div>
      
      <div class="nav-actions" style="display: flex; align-items: center; gap: 16px;">
        <div class="last-update">
          <span id="nav-last-update-time">最后更新: --</span>
        </div>
        
        <button class="btn btn-secondary" onclick="backToHome()" style="
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          font-size: 14px;
          background: var(--surface-color);
          border: 1px solid var(--border-color);
          color: var(--text-primary);
          text-decoration: none;
          border-radius: var(--border-radius);
          transition: var(--transition);
        " onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='var(--surface-color)'">
          <i class="fas fa-arrow-left"></i>
          <span>返回</span>
        </button>
      </div>
    `;
  }
}

// 恢复导航栏到原始状态
function restoreNavbar() {
  const navbarContent = document.querySelector('.navbar-content');
  if (!navbarContent || !navbarContent.dataset.originalContent) return;

  navbarContent.innerHTML = navbarContent.dataset.originalContent;
  delete navbarContent.dataset.originalContent;
}

function backToHome() {
  // 恢复导航栏到原始状态
  restoreNavbar();

  // 移除所有可能的页面
  const pagesToRemove = [
    'model-management-page',
    'task-scheduler-page',
    'task-history-page',
    'system-config-page',
    'log-viewer-page'
  ];

  pagesToRemove.forEach(pageId => {
    const page = document.getElementById(pageId);
    if (page) {
      page.remove();
    }
  });

  // 清理定时器
  if (typeof logUpdateInterval !== 'undefined' && logUpdateInterval) {
    clearInterval(logUpdateInterval);
    logUpdateInterval = null;
  }

  // 显示主页内容
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.style.display = 'block';
  }

  Utils.showNotification('已返回主页', 'info');
}