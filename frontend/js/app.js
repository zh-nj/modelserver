/**
 * 慧儿模型园 - 核心应用逻辑
 */

// 全局状态管理
const AppState = {
  backendStatus: 'unknown',
  lastCheck: null,
  autoRefresh: true,
  refreshInterval: 500, // 0.5秒刷新间隔
  dashboardData: {
    models: [],
    gpuInfo: [],
    systemMetrics: {},
    serviceUptime: 0
  }
};

// 工具函数
const Utils = {
  formatTime: (date) => {
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(date);
  },

  showNotification: (message, type = 'info') => {
    const notification = document.getElementById('notification');
    notification.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
      </div>
    `;
    notification.className = `notification ${type} show`;

    setTimeout(() => {
      notification.classList.remove('show');
    }, 3000);
  },

  apiRequest: async (endpoint, options = {}) => {
    try {
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        // 尝试获取详细错误信息
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          }
        } catch (e) {
          // 如果无法解析错误响应，使用默认错误信息
        }
        
        const error = new Error(errorMessage);
        error.status = response.status;
        error.response = response;
        throw error;
      }

      return await response.json();
    } catch (error) {
      console.error('API请求失败:', error);
      throw error;
    }
  }
};

// 应用初始化
document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 慧儿模型园管理平台已加载');
  console.log('快捷键: Ctrl+R 刷新仪表板, Ctrl+D 打开API文档');
  
  // 初始化仪表板
  if (typeof Dashboard !== 'undefined') {
    Dashboard.init();
  }
  
  // 绑定快捷键
  document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'r') {
      e.preventDefault();
      if (typeof Dashboard !== 'undefined') {
        Dashboard.forceRefresh();
      }
    }
    
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      window.open('http://localhost:8000/docs', '_blank');
    }
  });

  // 监听网络状态
  window.addEventListener('online', function () {
    Utils.showNotification('网络连接已恢复', 'success');
  });

  window.addEventListener('offline', function () {
    Utils.showNotification('网络连接已断开', 'error');
  });
});