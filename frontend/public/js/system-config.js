/**
 * 慧儿模型园 - 系统配置管理
 */

function openTaskScheduler() {
  // 导航到监控页面（包含任务调度功能）
  if (window.f7 && window.f7.views && window.f7.views.main) {
    window.f7.views.main.router.navigate('/monitoring');
    Utils.showNotification('正在打开任务调度页面...', 'info');
  } else {
    // 回退到传统页面创建方式
    createTaskSchedulerPage();
  }
}

function viewTaskHistory() {
  // 导航到监控页面（包含任务历史功能）
  if (window.f7 && window.f7.views && window.f7.views.main) {
    window.f7.views.main.router.navigate('/monitoring');
    Utils.showNotification('正在打开任务历史页面...', 'info');
  } else {
    // 回退到传统页面创建方式
    createTaskHistoryPage();
  }
}

function openSystemConfig() {
  // 导航到设置页面
  if (window.f7 && window.f7.views && window.f7.views.main) {
    window.f7.views.main.router.navigate('/settings');
    Utils.showNotification('正在打开系统配置页面...', 'info');
  } else {
    // 回退到传统页面创建方式
    createSystemConfigPage();
  }
}

function viewLogs() {
  // 导航到监控页面（包含日志查看功能）
  if (window.f7 && window.f7.views && window.f7.views.main) {
    window.f7.views.main.router.navigate('/monitoring');
    Utils.showNotification('正在打开日志查看页面...', 'info');
  } else {
    // 回退到传统页面创建方式
    createLogViewerPage();
  }
}

// 回退方案：创建传统页面
function createTaskSchedulerPage() {
  // 更新导航栏
  updateNavbarForPage('任务调度');
  
  // 隐藏主页内容
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.style.display = 'none';
  }
  
  // 创建任务调度页面
  const schedulerPage = document.createElement('div');
  schedulerPage.id = 'task-scheduler-page';
  schedulerPage.style.cssText = `
    position: fixed;
    top: 64px;
    left: 0;
    width: 100%;
    height: calc(100% - 64px);
    background: var(--background-color);
    z-index: 1000;
    overflow-y: auto;
  `;
  
  schedulerPage.innerHTML = `
    <div class="container" style="padding-top: 24px;">
      <div class="cards-grid fade-in">
        <!-- 调度状态概览 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <div class="card-icon primary">
                <i class="fas fa-tachometer-alt"></i>
              </div>
              <span>调度状态概览</span>
            </div>
            <div class="card-actions">
              <button class="btn btn-secondary" onclick="refreshSchedulerStatus()" style="font-size: 14px;">
                <i class="fas fa-sync-alt"></i>
                刷新
              </button>
            </div>
          </div>
          <div class="card-content">
            <div id="scheduler-overview">
              <p>正在加载调度状态...</p>
            </div>
          </div>
        </div>

        <!-- 资源分配状态 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <div class="card-icon success">
                <i class="fas fa-microchip"></i>
              </div>
              <span>GPU资源分配</span>
            </div>
          </div>
          <div class="card-content">
            <div id="gpu-allocation">
              <p>正在加载GPU资源信息...</p>
            </div>
          </div>
        </div>

        <!-- 模型调度队列 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <div class="card-icon warning">
                <i class="fas fa-list-ol"></i>
              </div>
              <span>模型调度队列</span>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary" onclick="showScheduleModelDialog()" style="font-size: 14px;">
                <i class="fas fa-plus"></i>
                手动调度
              </button>
            </div>
          </div>
          <div class="card-content">
            <div id="schedule-queue">
              <p>正在加载调度队列...</p>
            </div>
          </div>
        </div>

        <!-- 调度历史 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <div class="card-icon info">
                <i class="fas fa-history"></i>
              </div>
              <span>调度历史</span>
            </div>
            <div class="card-actions">
              <button class="btn btn-secondary" onclick="exportScheduleHistory()" style="font-size: 14px;">
                <i class="fas fa-download"></i>
                导出
              </button>
            </div>
          </div>
          <div class="card-content">
            <div id="schedule-history">
              <p>正在加载调度历史...</p>
            </div>
          </div>
        </div>

        <!-- 调度策略配置 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <div class="card-icon secondary">
                <i class="fas fa-cogs"></i>
              </div>
              <span>调度策略配置</span>
            </div>
            <div class="card-actions">
              <button class="btn btn-primary" onclick="showSchedulePolicyDialog()" style="font-size: 14px;">
                <i class="fas fa-edit"></i>
                编辑策略
              </button>
            </div>
          </div>
          <div class="card-content">
            <div id="schedule-policy">
              <p>正在加载调度策略...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(schedulerPage);
  
  // 加载调度数据
  loadSchedulerData();
  
  Utils.showNotification('任务调度页面已加载', 'success');
}

// 任务调度相关功能函数
async function loadSchedulerData() {
  console.log('开始加载调度数据');
  
  // 并行加载所有调度相关数据
  await Promise.all([
    loadSchedulerOverview(),
    loadGPUAllocation(),
    loadScheduleQueue(),
    loadScheduleHistory(),
    loadSchedulePolicy()
  ]);
}

// 加载调度状态概览
async function loadSchedulerOverview() {
  const overviewDiv = document.getElementById('scheduler-overview');
  if (!overviewDiv) return;
  
  try {
    overviewDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载调度状态...</p>';
    
    // 获取调度器状态数据
    const schedulerData = await Utils.apiRequest('/api/v1/scheduler/status');
    const systemData = await Utils.apiRequest('/api/v1/system/overview');
    
    // 从调度器状态获取统计信息
    const totalModels = schedulerData?.models?.total || 0;
    const runningModels = schedulerData?.models?.running || 0;
    const queuedModels = schedulerData?.models?.queued || 0;
    const failedModels = schedulerData?.models?.failed || 0;
    
    overviewDiv.innerHTML = `
      <div class="scheduler-stats" style="
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
        margin-bottom: 20px;
      ">
        <div class="stat-card" style="
          text-align: center;
          padding: 16px;
          background: var(--surface-color);
          border-radius: 8px;
          border-left: 4px solid var(--success-color);
        ">
          <div style="font-size: 28px; font-weight: bold; color: var(--success-color);">${runningModels}</div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">运行中</div>
        </div>
        
        <div class="stat-card" style="
          text-align: center;
          padding: 16px;
          background: var(--surface-color);
          border-radius: 8px;
          border-left: 4px solid var(--warning-color);
        ">
          <div style="font-size: 28px; font-weight: bold; color: var(--warning-color);">${queuedModels}</div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">队列中</div>
        </div>
        
        <div class="stat-card" style="
          text-align: center;
          padding: 16px;
          background: var(--surface-color);
          border-radius: 8px;
          border-left: 4px solid var(--error-color);
        ">
          <div style="font-size: 28px; font-weight: bold; color: var(--error-color);">${failedModels}</div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">失败</div>
        </div>
        
        <div class="stat-card" style="
          text-align: center;
          padding: 16px;
          background: var(--surface-color);
          border-radius: 8px;
          border-left: 4px solid var(--primary-color);
        ">
          <div style="font-size: 28px; font-weight: bold; color: var(--primary-color);">${totalModels}</div>
          <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">总计</div>
        </div>
      </div>
      
      <div class="scheduler-status" style="
        padding: 16px;
        background: var(--background-color);
        border-radius: 8px;
        border: 1px solid var(--border-color);
      ">
        <h4 style="margin: 0 0 12px 0; color: var(--text-primary);">
          <i class="fas fa-info-circle" style="color: var(--primary-color); margin-right: 8px;"></i>
          调度器状态
        </h4>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <span class="status-badge success" style="
              padding: 4px 12px;
              border-radius: 12px;
              font-size: 12px;
              font-weight: 500;
              color: white;
              background: var(--success-color);
            ">运行中</span>
            <span style="margin-left: 12px; color: var(--text-secondary); font-size: 14px;">
              自动调度已启用
            </span>
          </div>
          <div style="font-size: 14px; color: var(--text-secondary);">
            最后调度: ${new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
    `;
    
    console.log('调度状态概览加载成功');
  } catch (error) {
    console.error('加载调度状态概览失败:', error);
    overviewDiv.innerHTML = `
      <div style="color: var(--error-color); text-align: center; padding: 20px;">
        <i class="fas fa-exclamation-triangle"></i>
        <p>加载调度状态失败</p>
        <p style="font-size: 12px;">${error.message}</p>
      </div>
    `;
  }
}

// 加载GPU资源分配状态
async function loadGPUAllocation() {
  const allocationDiv = document.getElementById('gpu-allocation');
  if (!allocationDiv) return;
  
  try {
    allocationDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载GPU资源信息...</p>';
    
    // 获取GPU信息
    const gpuData = await Utils.apiRequest('/api/v1/system/gpu');
    const modelsData = await Utils.apiRequest('/api/models/');
    
    if (gpuData && gpuData.length > 0) {
      let allocationHtml = '';
      
      gpuData.forEach((gpu, index) => {
        // 查找使用此GPU的模型
        const modelsOnGPU = modelsData ? modelsData.filter(m => 
          m.gpu_devices && m.gpu_devices.includes(gpu.device_id) && m.status === 'running'
        ) : [];
        
        const memoryUsedPercent = Math.round((gpu.memory_used / gpu.memory_total) * 100);
        const utilizationPercent = Math.round(gpu.utilization || 0);
        
        allocationHtml += `
          <div class="gpu-allocation-card" style="
            margin-bottom: 16px;
            padding: 16px;
            background: var(--surface-color);
            border-radius: 8px;
            border: 1px solid var(--border-color);
          ">
            <div class="gpu-header" style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 12px;
            ">
              <div>
                <h4 style="margin: 0; color: var(--text-primary);">
                  <i class="fas fa-microchip" style="color: var(--primary-color); margin-right: 8px;"></i>
                  GPU ${gpu.device_id}: ${gpu.name}
                </h4>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                  温度: ${gpu.temperature}°C | 功耗: ${gpu.power_usage || 'N/A'}W
                </div>
              </div>
              <div class="gpu-status">
                <span class="status-badge ${modelsOnGPU.length > 0 ? 'success' : 'secondary'}" style="
                  padding: 4px 8px;
                  border-radius: 8px;
                  font-size: 11px;
                  font-weight: 500;
                  color: white;
                  background: ${modelsOnGPU.length > 0 ? 'var(--success-color)' : 'var(--text-secondary)'};
                ">${modelsOnGPU.length > 0 ? '使用中' : '空闲'}</span>
              </div>
            </div>
            
            <div class="gpu-metrics" style="margin-bottom: 12px;">
              <div class="metric-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; color: var(--text-secondary);">内存使用率</span>
                <span style="font-size: 14px; font-weight: 500; color: var(--text-primary);">${memoryUsedPercent}%</span>
              </div>
              <div class="progress-bar" style="
                width: 100%;
                height: 6px;
                background: var(--border-color);
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 8px;
              ">
                <div style="
                  width: ${memoryUsedPercent}%;
                  height: 100%;
                  background: ${memoryUsedPercent > 80 ? 'var(--error-color)' : memoryUsedPercent > 60 ? 'var(--warning-color)' : 'var(--success-color)'};
                  transition: width 0.3s ease;
                "></div>
              </div>
              
              <div class="metric-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; color: var(--text-secondary);">GPU利用率</span>
                <span style="font-size: 14px; font-weight: 500; color: var(--text-primary);">${utilizationPercent}%</span>
              </div>
              <div class="progress-bar" style="
                width: 100%;
                height: 6px;
                background: var(--border-color);
                border-radius: 3px;
                overflow: hidden;
              ">
                <div style="
                  width: ${utilizationPercent}%;
                  height: 100%;
                  background: ${utilizationPercent > 80 ? 'var(--error-color)' : utilizationPercent > 60 ? 'var(--warning-color)' : 'var(--success-color)'};
                  transition: width 0.3s ease;
                "></div>
              </div>
            </div>
            
            <div class="allocated-models">
              <div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 8px;">
                分配的模型 (${modelsOnGPU.length})
              </div>
              ${modelsOnGPU.length > 0 ? 
                modelsOnGPU.map(model => `
                  <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    margin: 4px 0;
                    background: var(--background-color);
                    border-radius: 6px;
                    border-left: 3px solid var(--primary-color);
                  ">
                    <div>
                      <div style="font-size: 13px; font-weight: 500; color: var(--text-primary);">${model.name}</div>
                      <div style="font-size: 11px; color: var(--text-secondary);">优先级: ${model.priority || 'N/A'}</div>
                    </div>
                    <div style="font-size: 11px; color: var(--success-color);">
                      <i class="fas fa-circle" style="margin-right: 4px;"></i>运行中
                    </div>
                  </div>
                `).join('') :
                '<div style="text-align: center; padding: 12px; color: var(--text-secondary); font-size: 13px;">暂无分配的模型</div>'
              }
            </div>
          </div>
        `;
      });
      
      allocationDiv.innerHTML = allocationHtml;
    } else {
      allocationDiv.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
          <i class="fas fa-microchip" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
          <p>未检测到GPU设备</p>
        </div>
      `;
    }
    
    console.log('GPU资源分配状态加载成功');
  } catch (error) {
    console.error('加载GPU资源分配失败:', error);
    allocationDiv.innerHTML = `
      <div style="color: var(--error-color); text-align: center; padding: 20px;">
        <i class="fas fa-exclamation-triangle"></i>
        <p>加载GPU资源信息失败</p>
        <p style="font-size: 12px;">${error.message}</p>
      </div>
    `;
  }
}

// 加载调度队列
async function loadScheduleQueue() {
  const queueDiv = document.getElementById('schedule-queue');
  if (!queueDiv) return;
  
  try {
    queueDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载调度队列...</p>';
    
    // 获取调度队列数据
    const queueData = await Utils.apiRequest('/api/v1/scheduler/queue');
    
    if (queueData && queueData.queue) {
      const queuedModels = queueData.queue;
      
      if (queuedModels.length > 0) {
        let queueHtml = `
          <div class="queue-header" style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding: 12px;
            background: var(--background-color);
            border-radius: 6px;
            border: 1px solid var(--border-color);
          ">
            <div style="font-size: 14px; font-weight: 500; color: var(--text-primary);">
              队列中的模型 (${queuedModels.length})
            </div>
            <div style="font-size: 12px; color: var(--text-secondary);">
              按优先级排序
            </div>
          </div>
        `;
        
        queuedModels.forEach((model, index) => {
          const statusColor = model.status === 'pending' ? 'var(--warning-color)' : 
                             model.status === 'error' ? 'var(--error-color)' : 
                             'var(--info-color)';
          
          queueHtml += `
            <div class="queue-item" style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              padding: 12px;
              margin: 8px 0;
              background: var(--surface-color);
              border-radius: 6px;
              border-left: 4px solid ${statusColor};
            ">
              <div class="queue-item-info">
                <div style="font-size: 14px; font-weight: 500; color: var(--text-primary);">
                  #${index + 1} ${model.name}
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                  框架: ${model.framework} | 优先级: ${model.priority || 'N/A'} | GPU: [${model.gpu_devices ? model.gpu_devices.join(', ') : 'N/A'}]
                </div>
              </div>
              <div class="queue-item-actions" style="display: flex; align-items: center; gap: 12px;">
                <span class="status-badge" style="
                  padding: 4px 8px;
                  border-radius: 8px;
                  font-size: 11px;
                  font-weight: 500;
                  color: white;
                  background: ${statusColor};
                ">${model.status || '队列中'}</span>
                <div class="action-buttons" style="display: flex; gap: 4px;">
                  <button class="btn btn-sm btn-primary" onclick="prioritizeModel('${model.id}')" style="
                    padding: 4px 8px;
                    font-size: 11px;
                    border-radius: 4px;
                  ">
                    <i class="fas fa-arrow-up"></i>
                  </button>
                  <button class="btn btn-sm btn-secondary" onclick="cancelModelSchedule('${model.id}')" style="
                    padding: 4px 8px;
                    font-size: 11px;
                    border-radius: 4px;
                  ">
                    <i class="fas fa-times"></i>
                  </button>
                </div>
              </div>
            </div>
          `;
        });
        
        queueDiv.innerHTML = queueHtml;
      } else {
        queueDiv.innerHTML = `
          <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
            <i class="fas fa-list-ol" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
            <p>调度队列为空</p>
            <p style="font-size: 12px;">所有模型都已完成调度</p>
          </div>
        `;
      }
    }
    
    console.log('调度队列加载成功');
  } catch (error) {
    console.error('加载调度队列失败:', error);
    queueDiv.innerHTML = `
      <div style="color: var(--error-color); text-align: center; padding: 20px;">
        <i class="fas fa-exclamation-triangle"></i>
        <p>加载调度队列失败</p>
        <p style="font-size: 12px;">${error.message}</p>
      </div>
    `;
  }
}

// 加载调度历史
async function loadScheduleHistory() {
  const historyDiv = document.getElementById('schedule-history');
  if (!historyDiv) return;
  
  try {
    historyDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载调度历史...</p>';
    
    // 获取调度历史数据
    const historyData = await Utils.apiRequest('/api/v1/scheduler/history?limit=20&hours=24');
    
    let historyRecords = [];
    if (historyData && historyData.history) {
      historyRecords = historyData.history;
    } else {
      // 如果API不可用，使用模拟数据
      historyRecords = [
        {
          id: '1',
          model_name: 'ChatGLM-6B',
          action: 'scheduled',
          timestamp: new Date(Date.now() - 5 * 60 * 1000),
          gpu_devices: [0, 1],
          result: 'success',
          reason: '资源充足，直接调度'
        },
        {
          id: '2',
          model_name: 'Llama2-7B',
          action: 'preempted',
          timestamp: new Date(Date.now() - 15 * 60 * 1000),
          gpu_devices: [2],
          result: 'success',
          reason: '被高优先级模型抢占'
        },
        {
          id: '3',
          model_name: 'Baichuan2-13B',
          action: 'failed',
          timestamp: new Date(Date.now() - 30 * 60 * 1000),
          gpu_devices: [0, 1, 2],
          result: 'failed',
          reason: 'GPU内存不足'
        },
        {
          id: '4',
          model_name: 'CodeLlama-7B',
          action: 'recovered',
          timestamp: new Date(Date.now() - 45 * 60 * 1000),
          gpu_devices: [3],
          result: 'success',
          reason: '资源释放后自动恢复'
        }
      ];
    }
    
    let historyHtml = `
      <div class="history-header" style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding: 12px;
        background: var(--background-color);
        border-radius: 6px;
        border: 1px solid var(--border-color);
      ">
        <div style="font-size: 14px; font-weight: 500; color: var(--text-primary);">
          最近调度记录 (${historyRecords.length})
        </div>
        <div style="font-size: 12px; color: var(--text-secondary);">
          最近24小时
        </div>
      </div>
    `;
    
    historyRecords.forEach(record => {
      const actionColor = record.action === 'scheduled' ? 'var(--success-color)' :
                         record.action === 'preempted' ? 'var(--warning-color)' :
                         record.action === 'failed' ? 'var(--error-color)' :
                         'var(--info-color)';
      
      const actionIcon = record.action === 'scheduled' ? 'fa-play' :
                        record.action === 'preempted' ? 'fa-pause' :
                        record.action === 'failed' ? 'fa-times' :
                        'fa-redo';
      
      const actionText = record.action === 'scheduled' ? '调度启动' :
                        record.action === 'preempted' ? '被抢占' :
                        record.action === 'failed' ? '调度失败' :
                        '恢复运行';
      
      // 处理时间戳格式
      const timestamp = record.timestamp instanceof Date ? 
                       record.timestamp : 
                       new Date(record.timestamp);
      
      historyHtml += `
        <div class="history-item" style="
          display: flex;
          align-items: center;
          padding: 12px;
          margin: 8px 0;
          background: var(--surface-color);
          border-radius: 6px;
          border-left: 4px solid ${actionColor};
        ">
          <div class="history-icon" style="
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: ${actionColor};
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
          ">
            <i class="fas ${actionIcon}" style="color: white; font-size: 12px;"></i>
          </div>
          
          <div class="history-content" style="flex: 1;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="font-size: 14px; font-weight: 500; color: var(--text-primary);">
                  ${record.model_name} - ${actionText}
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                  GPU: [${record.gpu_devices.join(', ')}] | ${record.reason}
                </div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 11px; color: var(--text-secondary);">
                  ${timestamp.toLocaleTimeString()}
                </div>
                <span class="status-badge ${record.result === 'success' ? 'success' : 'error'}" style="
                  padding: 2px 6px;
                  border-radius: 6px;
                  font-size: 10px;
                  font-weight: 500;
                  color: white;
                  background: ${record.result === 'success' ? 'var(--success-color)' : 'var(--error-color)'};
                  margin-top: 4px;
                ">${record.result === 'success' ? '成功' : '失败'}</span>
              </div>
            </div>
          </div>
        </div>
      `;
    });
    
    historyDiv.innerHTML = historyHtml;
    console.log('调度历史加载成功');
  } catch (error) {
    console.error('加载调度历史失败:', error);
    historyDiv.innerHTML = `
      <div style="color: var(--error-color); text-align: center; padding: 20px;">
        <i class="fas fa-exclamation-triangle"></i>
        <p>加载调度历史失败</p>
        <p style="font-size: 12px;">${error.message}</p>
      </div>
    `;
  }
}

// 加载调度策略
async function loadSchedulePolicy() {
  const policyDiv = document.getElementById('schedule-policy');
  if (!policyDiv) return;
  
  try {
    policyDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> 正在加载调度策略...</p>';
    
    // 模拟调度策略配置（实际应该从API获取）
    const mockPolicy = {
      scheduling_algorithm: 'priority_based',
      preemption_enabled: true,
      auto_recovery_enabled: true,
      resource_threshold: 0.8,
      priority_levels: 10,
      max_queue_size: 50,
      scheduling_interval: 30,
      health_check_interval: 60
    };
    
    policyDiv.innerHTML = `
      <div class="policy-grid" style="
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 16px;
      ">
        <div class="policy-section">
          <h5 style="margin: 0 0 12px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
            <i class="fas fa-cogs" style="margin-right: 6px; color: var(--primary-color);"></i>
            基本策略
          </h5>
          <div class="policy-item">
            <span class="policy-label">调度算法:</span>
            <span class="policy-value">基于优先级</span>
          </div>
          <div class="policy-item">
            <span class="policy-label">抢占机制:</span>
            <span class="policy-value">
              <span class="status-badge success" style="
                padding: 2px 6px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 500;
                color: white;
                background: var(--success-color);
              ">已启用</span>
            </span>
          </div>
          <div class="policy-item">
            <span class="policy-label">自动恢复:</span>
            <span class="policy-value">
              <span class="status-badge success" style="
                padding: 2px 6px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 500;
                color: white;
                background: var(--success-color);
              ">已启用</span>
            </span>
          </div>
        </div>
        
        <div class="policy-section">
          <h5 style="margin: 0 0 12px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
            <i class="fas fa-sliders-h" style="margin-right: 6px; color: var(--warning-color);"></i>
            资源配置
          </h5>
          <div class="policy-item">
            <span class="policy-label">资源阈值:</span>
            <span class="policy-value">${(mockPolicy.resource_threshold * 100).toFixed(0)}%</span>
          </div>
          <div class="policy-item">
            <span class="policy-label">优先级级别:</span>
            <span class="policy-value">${mockPolicy.priority_levels}</span>
          </div>
          <div class="policy-item">
            <span class="policy-label">最大队列长度:</span>
            <span class="policy-value">${mockPolicy.max_queue_size}</span>
          </div>
        </div>
        
        <div class="policy-section">
          <h5 style="margin: 0 0 12px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
            <i class="fas fa-clock" style="margin-right: 6px; color: var(--info-color);"></i>
            时间配置
          </h5>
          <div class="policy-item">
            <span class="policy-label">调度间隔:</span>
            <span class="policy-value">${mockPolicy.scheduling_interval}秒</span>
          </div>
          <div class="policy-item">
            <span class="policy-label">健康检查间隔:</span>
            <span class="policy-value">${mockPolicy.health_check_interval}秒</span>
          </div>
        </div>
      </div>
      
      <style>
        .policy-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          font-size: 13px;
        }
        .policy-label {
          color: var(--text-secondary);
          font-weight: 500;
        }
        .policy-value {
          color: var(--text-primary);
          font-weight: 500;
        }
        .policy-section {
          background: var(--background-color);
          padding: 16px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }
      </style>
    `;
    
    console.log('调度策略加载成功');
  } catch (error) {
    console.error('加载调度策略失败:', error);
    policyDiv.innerHTML = `
      <div style="color: var(--error-color); text-align: center; padding: 20px;">
        <i class="fas fa-exclamation-triangle"></i>
        <p>加载调度策略失败</p>
        <p style="font-size: 12px;">${error.message}</p>
      </div>
    `;
  }
}

// 刷新调度状态
async function refreshSchedulerStatus() {
  Utils.showNotification('正在刷新调度状态...', 'info');
  await loadSchedulerData();
  Utils.showNotification('调度状态已刷新', 'success');
}

// 显示手动调度对话框
function showScheduleModelDialog() {
  // 创建模态对话框
  const dialog = document.createElement('div');
  dialog.className = 'modal-overlay';
  dialog.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
  `;
  
  dialog.innerHTML = `
    <div class="modal-content" style="
      background: var(--surface-color);
      border-radius: 8px;
      padding: 24px;
      max-width: 500px;
      width: 90%;
      max-height: 80vh;
      overflow-y: auto;
    ">
      <div class="modal-header" style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-color);
      ">
        <h3 style="margin: 0; color: var(--text-primary);">
          <i class="fas fa-plus" style="color: var(--primary-color); margin-right: 8px;"></i>
          手动调度模型
        </h3>
        <button onclick="closeScheduleDialog()" style="
          background: none;
          border: none;
          font-size: 20px;
          color: var(--text-secondary);
          cursor: pointer;
          padding: 4px;
        ">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">
            选择模型
          </label>
          <select id="schedule-model-select" style="
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--background-color);
            color: var(--text-primary);
          ">
            <option value="">正在加载模型列表...</option>
          </select>
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">
            优先级 (1-10)
          </label>
          <input type="number" id="schedule-priority" min="1" max="10" value="5" style="
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--background-color);
            color: var(--text-primary);
          ">
        </div>
        
        <div class="form-group" style="margin-bottom: 20px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">
            调度选项
          </label>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <label style="display: flex; align-items: center; font-size: 14px; color: var(--text-secondary);">
              <input type="checkbox" id="force-schedule" style="margin-right: 8px;">
              强制调度（忽略资源限制）
            </label>
            <label style="display: flex; align-items: center; font-size: 14px; color: var(--text-secondary);">
              <input type="checkbox" id="preempt-lower" checked style="margin-right: 8px;">
              允许抢占低优先级模型
            </label>
          </div>
        </div>
      </div>
      
      <div class="modal-footer" style="
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        padding-top: 16px;
        border-top: 1px solid var(--border-color);
      ">
        <button onclick="closeScheduleDialog()" class="btn btn-secondary">
          取消
        </button>
        <button onclick="executeManualSchedule()" class="btn btn-primary">
          <i class="fas fa-play"></i>
          开始调度
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(dialog);
  
  // 加载可调度的模型列表
  loadSchedulableModels();
  
  // 点击背景关闭对话框
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) {
      closeScheduleDialog();
    }
  });
}

// 加载可调度的模型列表
async function loadSchedulableModels() {
  const select = document.getElementById('schedule-model-select');
  if (!select) return;
  
  try {
    const models = await Utils.apiRequest('/api/models/');
    
    if (models && models.length > 0) {
      // 过滤出非运行状态的模型
      const schedulableModels = models.filter(m => m.status !== 'running');
      
      select.innerHTML = '<option value="">请选择模型</option>';
      
      schedulableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name} (${model.framework}) - 优先级: ${model.priority || 'N/A'}`;
        select.appendChild(option);
      });
      
      if (schedulableModels.length === 0) {
        select.innerHTML = '<option value="">暂无可调度的模型</option>';
      }
    } else {
      select.innerHTML = '<option value="">暂无模型配置</option>';
    }
  } catch (error) {
    console.error('加载可调度模型失败:', error);
    select.innerHTML = '<option value="">加载失败</option>';
  }
}

// 执行手动调度
async function executeManualSchedule() {
  const modelId = document.getElementById('schedule-model-select')?.value;
  const priority = document.getElementById('schedule-priority')?.value;
  const forceSchedule = document.getElementById('force-schedule')?.checked;
  const preemptLower = document.getElementById('preempt-lower')?.checked;
  
  if (!modelId) {
    Utils.showNotification('请选择要调度的模型', 'warning');
    return;
  }
  
  try {
    Utils.showNotification('正在执行手动调度...', 'info');
    
    // 这里应该调用实际的调度API
    // const result = await Utils.apiRequest(`/api/scheduler/schedule`, {
    //   method: 'POST',
    //   body: JSON.stringify({
    //     model_id: modelId,
    //     priority: parseInt(priority),
    //     force: forceSchedule,
    //     allow_preemption: preemptLower
    //   })
    // });
    
    // 模拟调度结果
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    closeScheduleDialog();
    Utils.showNotification('模型调度请求已提交', 'success');
    
    // 刷新调度数据
    setTimeout(() => {
      loadSchedulerData();
    }, 1000);
    
  } catch (error) {
    console.error('手动调度失败:', error);
    Utils.showNotification(`调度失败: ${error.message}`, 'error');
  }
}

// 关闭调度对话框
function closeScheduleDialog() {
  const dialog = document.querySelector('.modal-overlay');
  if (dialog) {
    dialog.remove();
  }
}

// 显示调度策略编辑对话框
function showSchedulePolicyDialog() {
  Utils.showNotification('调度策略编辑功能正在开发中...', 'info');
}

// 导出调度历史
function exportScheduleHistory() {
  Utils.showNotification('调度历史导出功能正在开发中...', 'info');
}

// 提升模型优先级
async function prioritizeModel(modelId) {
  try {
    Utils.showNotification('正在提升模型优先级...', 'info');
    
    // 这里应该调用实际的API
    // await Utils.apiRequest(`/api/models/${modelId}/prioritize`, { method: 'POST' });
    
    // 模拟操作
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    Utils.showNotification('模型优先级已提升', 'success');
    loadScheduleQueue(); // 刷新队列
  } catch (error) {
    console.error('提升优先级失败:', error);
    Utils.showNotification(`操作失败: ${error.message}`, 'error');
  }
}

// 取消模型调度
async function cancelModelSchedule(modelId) {
  if (!confirm('确定要取消这个模型的调度吗？')) {
    return;
  }
  
  try {
    Utils.showNotification('正在取消模型调度...', 'info');
    
    // 这里应该调用实际的API
    // await Utils.apiRequest(`/api/models/${modelId}/cancel`, { method: 'POST' });
    
    // 模拟操作
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    Utils.showNotification('模型调度已取消', 'success');
    loadScheduleQueue(); // 刷新队列
  } catch (error) {
    console.error('取消调度失败:', error);
    Utils.showNotification(`操作失败: ${error.message}`, 'error');
  }
}