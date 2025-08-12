/**
 * 慧儿模型园 - 仪表板管理
 */

// 仪表板管理
const Dashboard = {
  updateInterval: null,
  isUpdating: false,
  lastUpdateTime: null,

  init() {
    console.log('🎛️ 初始化仪表板...');
    this.loadDashboardData();
    this.startAutoUpdate();
    this.setupVisibilityListener();
  },

  async loadDashboardData() {
    if (this.isUpdating) {
      console.log('⏳ 仪表板正在更新中，跳过本次更新');
      return;
    }

    this.isUpdating = true;
    console.log('🔄 开始更新仪表板数据...');

    try {
      await Promise.all([
        this.updateServiceStatus(),
        this.updateModelsData(),
        this.updateGPUData(),
        this.updateSystemData()
      ]);
      this.updateLastUpdateTime();
      this.lastUpdateTime = new Date();
      console.log('✅ 仪表板数据更新完成');
    } catch (error) {
      console.error('❌ 加载仪表板数据失败:', error);
      Utils.showNotification('加载仪表板数据失败', 'error');
    } finally {
      this.isUpdating = false;
    }
  },

  setupVisibilityListener() {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ 页面变为可见，立即更新仪表板数据');
        this.loadDashboardData();
      } else {
        console.log('🙈 页面变为隐藏，暂停自动更新');
      }
    });
  },

  async updateServiceStatus() {
    const navbar = document.querySelector('.navbar');

    try {
      const startTime = Date.now();
      const healthData = await Utils.apiRequest('/health');
      const responseTime = Date.now() - startTime;

      AppState.backendStatus = 'online';
      AppState.lastCheck = new Date();

      // 更新导航栏侧边颜色指示
      if (navbar) {
        navbar.className = 'navbar status-online';
      }

    } catch (error) {
      AppState.backendStatus = 'offline';

      // 更新导航栏侧边颜色指示
      if (navbar) {
        navbar.className = 'navbar status-offline';
      }
    }
  },

  async updateModelsData() {
    try {
      const models = await Utils.apiRequest('/api/models/');
      AppState.dashboardData.models = models;

      // 更新模型状态面板
      this.updateModelsStatusPanel(models);

    } catch (error) {
      console.error('更新模型数据失败:', error);
      // 显示错误状态在模型面板中
      const panel = document.getElementById('models-status');
      if (panel) {
        panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-exclamation-triangle"></i><span>无法获取模型数据</span></div>';
      }
    }
  },

  async updateGPUData() {
    const statusIndicator = document.getElementById('gpu-status-indicator');
    const statusText = document.getElementById('gpu-status-text');

    try {
      const gpuData = await Utils.apiRequest('/api/v1/system/gpu/');
      AppState.dashboardData.gpuInfo = gpuData;

      if (gpuData && gpuData.length > 0) {
        // 更新状态指示器
        if (statusIndicator) {
          statusIndicator.className = 'status-dot online';
        }
        if (statusText) {
          statusText.textContent = `${gpuData.length} GPU在线`;
        }

        // 更新GPU监控面板
        this.updateGPUMonitoringPanel(gpuData);
      } else {
        // 更新状态指示器
        if (statusIndicator) {
          statusIndicator.className = 'status-dot offline';
        }
        if (statusText) {
          statusText.textContent = '未检测到GPU';
        }

        // 显示无GPU状态
        const panel = document.getElementById('gpu-monitoring');
        if (panel) {
          panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-info-circle"></i><span>未检测到GPU设备</span></div>';
        }
      }

    } catch (error) {
      console.error('更新GPU数据失败:', error);

      // 更新状态指示器
      if (statusIndicator) {
        statusIndicator.className = 'status-dot offline';
      }
      if (statusText) {
        statusText.textContent = 'GPU数据获取失败';
      }

      // 显示错误状态
      const panel = document.getElementById('gpu-monitoring');
      if (panel) {
        panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-exclamation-triangle"></i><span>无法获取GPU数据</span></div>';
      }
    }
  },

  async updateSystemData() {
    const statusIndicator = document.getElementById('system-status-indicator');
    const statusText = document.getElementById('system-status-text');

    try {
      const systemData = await Utils.apiRequest('/api/monitoring/system/');
      AppState.dashboardData.systemMetrics = systemData;

      // 更新状态指示器
      if (statusIndicator) {
        statusIndicator.className = 'status-dot online';
      }
      if (statusText) {
        statusText.textContent = '系统正常';
      }

      // 更新系统监控面板
      this.updateSystemMonitoringPanel(systemData);

    } catch (error) {
      console.error('更新系统数据失败:', error);

      // 更新状态指示器
      if (statusIndicator) {
        statusIndicator.className = 'status-dot offline';
      }
      if (statusText) {
        statusText.textContent = '系统数据获取失败';
      }

      // 显示错误状态
      const panel = document.getElementById('system-monitoring');
      if (panel) {
        panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-exclamation-triangle"></i><span>无法获取系统数据</span></div>';
      }
    }
  },

  updateModelsStatusPanel(models) {
    const panel = document.getElementById('models-status');
    if (!panel) return;

    if (!models || models.length === 0) {
      panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-info-circle"></i><span>暂无模型配置</span></div>';
      return;
    }

    let html = '';
    models.forEach(model => {
      const statusClass = model.status === 'running' ? 'running' :
        model.status === 'stopped' ? 'stopped' : 'error';

      html += `
        <div class="model-item">
          <div class="model-info">
            <h4>${model.name}</h4>
            <div style="font-size: 14px; color: var(--text-secondary);">
              框架: ${model.framework} | 优先级: ${model.priority || 'N/A'}
            </div>
          </div>
          <div class="model-status-badge ${statusClass}">
            ${model.status || '未知'}
          </div>
        </div>
      `;
    });

    panel.innerHTML = html;
  },

  updateGPUMonitoringPanel(gpuData) {
    const panel = document.getElementById('gpu-monitoring');
    if (!panel) return;

    if (!gpuData || gpuData.length === 0) {
      panel.innerHTML = '<div class="loading-placeholder"><i class="fas fa-info-circle"></i><span>未检测到GPU设备</span></div>';
      return;
    }

    let html = '';
    gpuData.forEach(gpu => {
      const memoryPercent = (gpu.memory_used / gpu.memory_total) * 100;

      html += `
        <div class="gpu-item">
          <div class="gpu-info">
            <h4>GPU ${gpu.device_id}: ${gpu.name}</h4>
            <div class="gpu-stats">
              <span>利用率: ${gpu.utilization}%</span>
              <span>温度: ${gpu.temperature}°C</span>
              <span>功耗: ${gpu.power_usage}W</span>
            </div>
            <div class="gpu-usage-bar">
              <div class="gpu-usage-fill" style="width: ${memoryPercent}%"></div>
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
              内存: ${Math.round(gpu.memory_used / 1024)}GB / ${Math.round(gpu.memory_total / 1024)}GB
            </div>
          </div>
        </div>
      `;
    });

    panel.innerHTML = html;
  },

  updateSystemMonitoringPanel(systemData) {
    const panel = document.getElementById('system-monitoring');
    if (!panel) return;

    const cpuPercent = systemData.system_metrics?.cpu_percent || 0;
    const memoryPercent = systemData.system_metrics?.memory_percent || 0;
    const diskPercent = systemData.system_metrics?.disk_percent || 0;

    // 计算更多系统指标
    const totalGpuMemory = systemData.total_gpu_memory || 0;
    const usedGpuMemory = systemData.used_gpu_memory || 0;
    const gpuMemoryPercent = totalGpuMemory > 0 ? (usedGpuMemory / totalGpuMemory) * 100 : 0;

    // 获取系统运行时间
    const systemUptime = systemData.system_uptime || 0;
    const uptimeHours = Math.floor(systemUptime / 3600);
    const uptimeDays = Math.floor(uptimeHours / 24);
    const uptimeDisplay = uptimeDays > 0 ? `${uptimeDays}天${uptimeHours % 24}小时` : `${uptimeHours}小时`;

    panel.innerHTML = `
      <div class="system-resource-grid">
        <!-- 第一行：CPU和内存 -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">CPU使用率</span>
            <span class="resource-value">${cpuPercent.toFixed(1)}%</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">内存使用率</span>
            <span class="resource-value">${memoryPercent.toFixed(1)}%</span>
          </div>
        </div>
        
        <!-- 第二行：磁盘和GPU内存 -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">磁盘使用率</span>
            <span class="resource-value">${diskPercent.toFixed(1)}%</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">GPU内存</span>
            <span class="resource-value">${gpuMemoryPercent.toFixed(1)}%</span>
          </div>
        </div>
        
        <!-- 第三行：运行模型和可用GPU -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">运行模型</span>
            <span class="resource-value">${systemData.running_models || 0}个</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">可用GPU</span>
            <span class="resource-value">${systemData.available_gpus || 0}/${systemData.total_gpus || 0}</span>
          </div>
        </div>
        
        <!-- 第四行：系统负载和运行时间 -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">系统负载</span>
            <span class="resource-value">${(cpuPercent / 100 * 4).toFixed(2)}</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">运行时间</span>
            <span class="resource-value">${uptimeDisplay}</span>
          </div>
        </div>
        
        <!-- 第五行：GPU内存详情 -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">GPU已用</span>
            <span class="resource-value">${Math.round(usedGpuMemory / 1024)}GB</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">GPU总计</span>
            <span class="resource-value">${Math.round(totalGpuMemory / 1024)}GB</span>
          </div>
        </div>
        
        <!-- 第六行：模型统计 -->
        <div class="resource-row">
          <div class="resource-item-half">
            <span class="resource-label">总模型数</span>
            <span class="resource-value">${systemData.total_models || 0}个</span>
          </div>
          <div class="resource-item-half">
            <span class="resource-label">停止模型</span>
            <span class="resource-value">${(systemData.total_models || 0) - (systemData.running_models || 0)}个</span>
          </div>
        </div>
      </div>
    `;
  },

  updateLastUpdateTime() {
    const now = new Date();
    const timeElement = document.getElementById('nav-last-update-time');
    if (timeElement) {
      timeElement.textContent = `最后更新: ${now.toLocaleTimeString('zh-CN')}`;
    }
  },

  startAutoUpdate() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }

    console.log(`⏰ 启动自动更新，间隔: ${AppState.refreshInterval / 1000}秒`);

    this.updateInterval = setInterval(() => {
      if (document.visibilityState === 'visible' && !this.isUpdating) {
        console.log('🔄 自动更新触发');
        this.loadDashboardData();
      }
    }, AppState.refreshInterval);
  },

  stopAutoUpdate() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
      console.log('⏹️ 自动更新已停止');
    }
  },

  // 手动刷新所有数据
  async forceRefresh() {
    console.log('🔄 强制刷新仪表板数据');
    this.isUpdating = false; // 重置更新状态
    await this.loadDashboardData();
  },

  // 获取更新状态
  getUpdateStatus() {
    return {
      isUpdating: this.isUpdating,
      lastUpdateTime: this.lastUpdateTime,
      autoUpdateEnabled: !!this.updateInterval
    };
  }
};