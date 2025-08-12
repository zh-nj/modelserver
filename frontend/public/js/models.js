/**
 * 慧儿模型园 - 模型管理
 */

function openModelManagement() {
  // 创建一个简单的模型管理页面
  createSimpleModelManagementPage();
}

function createSimpleModelManagementPage() {
  // 更新导航栏显示模型管理标题和返回按钮
  updateNavbarForPage('模型管理');

  // 隐藏主页内容
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    mainContent.style.display = 'none';
  }

  // 创建模型管理页面
  const modelPage = document.createElement('div');
  modelPage.id = 'model-management-page';
  modelPage.style.cssText = `
    position: fixed;
    top: 64px;
    left: 0;
    width: 100%;
    height: calc(100% - 64px);
    background: var(--background-color);
    z-index: 1000;
    overflow-y: auto;
  `;

  modelPage.innerHTML = `
    <div class="container" style="padding-top: 24px;">
      <div class="cards-grid fade-in">
        <div class="card">
          <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div class="card-title">
              <div class="card-icon success">
                <i class="fas fa-list"></i>
              </div>
              <span>模型列表</span>
            </div>
            <div class="card-actions" style="display: flex; gap: 8px;">
              <button class="btn btn-primary" onclick="showAddModelForm()" style="font-size: 14px;">
                <i class="fas fa-plus"></i>
                添加模型
              </button>
              <button class="btn btn-secondary" onclick="loadModelList()" style="font-size: 14px;">
                <i class="fas fa-sync-alt"></i>
                刷新列表
              </button>
            </div>
          </div>
          <div class="card-content">
            <div id="model-list">
              <p>正在加载模型列表...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(modelPage);

  // 加载模型列表
  loadModelList();

  Utils.showNotification('模型管理页面已加载', 'success');
}

async function loadModelList() {
  const modelListDiv = document.getElementById('model-list');
  if (!modelListDiv) return;

  try {
    modelListDiv.innerHTML = '<p>正在加载模型列表...</p>';
    
    const models = await Utils.apiRequest('/api/models/');
    
    if (models && models.length > 0) {
      let html = '<div class="model-list">';
      models.forEach(model => {
        const statusClass = model.status === 'running' ? 'success' : 
                           model.status === 'stopped' ? 'secondary' : 'error';
        
        html += `
          <div class="model-item" id="model-item-${model.id}" style="
            display: flex;
            flex-direction: column;
            padding: 16px;
            margin: 8px 0;
            background: var(--surface-color);
            border-radius: var(--border-radius);
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.3s ease;
          " onclick="toggleModelDetails('${model.id}')">
            <!-- 简要信息区域 -->
            <div class="model-summary" style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              width: 100%;
            ">
              <div class="model-info">
                <h4 style="margin: 0 0 4px 0; color: var(--text-primary);">
                  <i class="fas fa-chevron-right model-expand-icon" id="expand-icon-${model.id}" style="
                    margin-right: 8px;
                    font-size: 12px;
                    transition: transform 0.3s ease;
                    color: var(--text-secondary);
                  "></i>
                  ${model.name}
                </h4>
                <div style="font-size: 14px; color: var(--text-secondary);">
                  框架: ${model.framework} | 优先级: ${model.priority || 'N/A'}
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                  路径: ${model.model_path}
                </div>
              </div>
              <div class="model-actions" style="display: flex; gap: 8px; align-items: center;">
                <span class="status-badge ${statusClass}" style="
                  padding: 4px 8px;
                  border-radius: 12px;
                  font-size: 12px;
                  font-weight: 500;
                  color: white;
                  background: var(--${statusClass === 'success' ? 'secondary' : statusClass === 'secondary' ? 'text-secondary' : 'error'}-color);
                ">${model.status || '未知'}</span>
                <button class="btn btn-secondary" onclick="event.stopPropagation(); editModel('${model.id}')" style="padding: 6px 12px; font-size: 12px;">
                  <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-secondary" onclick="event.stopPropagation(); deleteModel('${model.id}')" style="padding: 6px 12px; font-size: 12px;">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            
            <!-- 详细信息区域（默认隐藏） -->
            <div class="model-details" id="model-details-${model.id}" style="
              display: none;
              margin-top: 16px;
              padding-top: 16px;
              border-top: 1px solid var(--border-color);
              animation: slideDown 0.3s ease;
            ">
              <div class="details-loading" id="details-loading-${model.id}">
                <p style="color: var(--text-secondary); margin: 0;">
                  <i class="fas fa-spinner fa-spin"></i> 正在加载详细信息...
                </p>
              </div>
              <div class="details-content" id="details-content-${model.id}" style="display: none;">
                <!-- 详细信息将通过JavaScript动态加载 -->
              </div>
            </div>
          </div>
        `;
      });
      html += '</div>';
      modelListDiv.innerHTML = html;
    } else {
      modelListDiv.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">暂无模型配置</p>';
    }
    
  } catch (error) {
    console.error('加载模型列表失败:', error);
    modelListDiv.innerHTML = `<p style="color: var(--error-color);">加载模型列表失败: ${error.message}</p>`;
  }
}

async function editModel(modelId) {
  try {
    // 获取模型配置
    const config = await Utils.apiRequest(`/api/models/${modelId}/config`);
    if (!config) {
      Utils.showNotification('获取模型配置失败', 'error');
      return;
    }
    
    // 显示编辑表单
    showEditModelForm(config);
  } catch (error) {
    console.error('获取模型配置失败:', error);
    Utils.showNotification(`获取模型配置失败: ${error.message}`, 'error');
  }
}

async function deleteModel(modelId) {
  if (!confirm('确定要删除这个模型吗？此操作不可撤销。')) {
    return;
  }
  
  try {
    const response = await Utils.apiRequest(`/api/models/${modelId}`, {
      method: 'DELETE'
    });
    
    if (response && response.success) {
      Utils.showNotification('模型删除成功', 'success');
      // 刷新模型列表
      setTimeout(() => {
        loadModelList();
      }, 1000);
    } else {
      Utils.showNotification('模型删除失败', 'error');
    }
  } catch (error) {
    console.error('删除模型失败:', error);
    Utils.showNotification(`删除模型失败: ${error.message}`, 'error');
  }
}

// 切换模型详情显示/隐藏
async function toggleModelDetails(modelId) {
  const detailsDiv = document.getElementById(`model-details-${modelId}`);
  const expandIcon = document.getElementById(`expand-icon-${modelId}`);
  const loadingDiv = document.getElementById(`details-loading-${modelId}`);
  const contentDiv = document.getElementById(`details-content-${modelId}`);
  
  if (!detailsDiv || !expandIcon) return;
  
  // 如果详情区域当前是隐藏的，则展开并加载详情
  if (detailsDiv.style.display === 'none') {
    // 展开详情区域
    detailsDiv.style.display = 'block';
    expandIcon.style.transform = 'rotate(90deg)';
    
    // 显示加载状态
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (contentDiv) contentDiv.style.display = 'none';
    
    try {
      // 获取详细配置信息
      const config = await Utils.apiRequest(`/api/models/${modelId}/config`);
      
      if (config && contentDiv) {
        // 构建详细信息HTML
        const detailsHTML = `
          <div class="model-details-grid" style="
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 8px;
          ">
            <!-- 基本信息 -->
            <div class="detail-section">
              <h5 style="margin: 0 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
                <i class="fas fa-info-circle" style="margin-right: 6px; color: var(--primary-color);"></i>
                基本信息
              </h5>
              <div class="detail-item">
                <span class="detail-label">模型ID:</span>
                <span class="detail-value">${config.id}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">创建时间:</span>
                <span class="detail-value">${config.created_at ? new Date(config.created_at).toLocaleString() : '未知'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">更新时间:</span>
                <span class="detail-value">${config.updated_at ? new Date(config.updated_at).toLocaleString() : '未知'}</span>
              </div>
            </div>
            
            <!-- 资源配置 -->
            <div class="detail-section">
              <h5 style="margin: 0 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
                <i class="fas fa-microchip" style="margin-right: 6px; color: var(--success-color);"></i>
                资源配置
              </h5>
              <div class="detail-item">
                <span class="detail-label">GPU设备:</span>
                <span class="detail-value">[${config.gpu_devices ? config.gpu_devices.join(', ') : '未指定'}]</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">GPU内存:</span>
                <span class="detail-value">${config.resource_requirements?.gpu_memory || 'N/A'} MB</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">CPU核心:</span>
                <span class="detail-value">${config.resource_requirements?.cpu_cores || '未指定'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">系统内存:</span>
                <span class="detail-value">${config.resource_requirements?.system_memory || '未指定'} MB</span>
              </div>
            </div>
            
            <!-- 服务配置 -->
            <div class="detail-section">
              <h5 style="margin: 0 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
                <i class="fas fa-cogs" style="margin-right: 6px; color: var(--warning-color);"></i>
                服务配置
              </h5>
              <div class="detail-item">
                <span class="detail-label">主机地址:</span>
                <span class="detail-value">${config.parameters?.host || 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">端口:</span>
                <span class="detail-value">${config.parameters?.port || 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">附加参数:</span>
                <span class="detail-value" style="word-break: break-all;">${config.additional_parameters || '无'}</span>
              </div>
            </div>
            
            <!-- 健康检查 -->
            <div class="detail-section">
              <h5 style="margin: 0 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
                <i class="fas fa-heartbeat" style="margin-right: 6px; color: var(--error-color);"></i>
                健康检查
              </h5>
              <div class="detail-item">
                <span class="detail-label">启用状态:</span>
                <span class="detail-value">
                  <span class="status-badge ${config.health_check?.enabled ? 'success' : 'secondary'}" style="
                    padding: 2px 6px;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 500;
                    color: white;
                    background: ${config.health_check?.enabled ? 'var(--success-color)' : 'var(--text-secondary)'};
                  ">${config.health_check?.enabled ? '已启用' : '已禁用'}</span>
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">检查间隔:</span>
                <span class="detail-value">${config.health_check?.interval || 'N/A'} 秒</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">超时时间:</span>
                <span class="detail-value">${config.health_check?.timeout || 'N/A'} 秒</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">最大失败次数:</span>
                <span class="detail-value">${config.health_check?.max_failures || 'N/A'}</span>
              </div>
            </div>
            
            <!-- 重试策略 -->
            <div class="detail-section">
              <h5 style="margin: 0 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600;">
                <i class="fas fa-redo" style="margin-right: 6px; color: var(--info-color);"></i>
                重试策略
              </h5>
              <div class="detail-item">
                <span class="detail-label">启用状态:</span>
                <span class="detail-value">
                  <span class="status-badge ${config.retry_policy?.enabled ? 'success' : 'secondary'}" style="
                    padding: 2px 6px;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 500;
                    color: white;
                    background: ${config.retry_policy?.enabled ? 'var(--success-color)' : 'var(--text-secondary)'};
                  ">${config.retry_policy?.enabled ? '已启用' : '已禁用'}</span>
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">最大尝试次数:</span>
                <span class="detail-value">${config.retry_policy?.max_attempts || 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">初始延迟:</span>
                <span class="detail-value">${config.retry_policy?.initial_delay || 'N/A'} 秒</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">最大延迟:</span>
                <span class="detail-value">${config.retry_policy?.max_delay || 'N/A'} 秒</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">退避因子:</span>
                <span class="detail-value">${config.retry_policy?.backoff_factor || 'N/A'}</span>
              </div>
            </div>
          </div>
          
          <style>
            .detail-item {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              margin-bottom: 6px;
              font-size: 13px;
            }
            .detail-label {
              color: var(--text-secondary);
              font-weight: 500;
              min-width: 80px;
              margin-right: 12px;
            }
            .detail-value {
              color: var(--text-primary);
              text-align: right;
              flex: 1;
              word-wrap: break-word;
            }
            .detail-section {
              background: var(--background-color, #f8f9fa);
              padding: 12px;
              border-radius: 6px;
              border: 1px solid var(--border-color, #e9ecef);
              flex: 1 1 300px;
              min-width: 280px;
            }
          </style>
        `;
        
        contentDiv.innerHTML = detailsHTML;
        
        // 隐藏加载状态，显示内容
        if (loadingDiv) loadingDiv.style.display = 'none';
        contentDiv.style.display = 'block';
      }
    } catch (error) {
      console.error('加载模型详情失败:', error);
      if (contentDiv) {
        contentDiv.innerHTML = `
          <p style="color: var(--error-color); margin: 0;">
            <i class="fas fa-exclamation-triangle"></i> 
            加载详细信息失败: ${error.message}
          </p>
        `;
        if (loadingDiv) loadingDiv.style.display = 'none';
        contentDiv.style.display = 'block';
      }
    }
  } else {
    // 收起详情区域
    detailsDiv.style.display = 'none';
    expandIcon.style.transform = 'rotate(0deg)';
  }
}

function listModels() {
  openModelManagement();
}