/**
 * 慧儿模型园 - 模型表单管理
 */

function showAddModelForm() {
  // 创建模型添加表单弹窗
  const formModal = document.createElement('div');
  formModal.id = 'add-model-modal';
  formModal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease-out;
  `;

  formModal.innerHTML = `
    <div class="modal-content" style="
      background: var(--surface-color);
      border-radius: var(--border-radius);
      padding: 24px;
      max-width: 500px;
      width: 90%;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: var(--shadow-heavy);
    ">
      <div class="modal-header" style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 16px;
      ">
        <h2 style="margin: 0; color: var(--text-primary);">添加新模型</h2>
        <button onclick="closeAddModelForm()" style="
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: var(--text-secondary);
          width: 32px;
        ">&times;</button>
      </div>
      
      <form id="add-model-form">
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">模型名称 *</label>
          <input type="text" id="model-name" required style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="输入模型名称">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">模型路径 *</label>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="model-path" required style="
              flex: 1;
              padding: 12px;
              border: 1px solid var(--border-color);
              border-radius: var(--border-radius);
              font-size: 14px;
              background: var(--surface-color);
              color: var(--text-primary);
            " placeholder="输入模型文件路径">
            <button type="button" onclick="selectModelFile()" style="
              padding: 12px 16px;
              border: 1px solid var(--border-color);
              border-radius: var(--border-radius);
              background: var(--surface-color);
              color: var(--text-primary);
              cursor: pointer;
              white-space: nowrap;
              transition: var(--transition);
            " onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='var(--surface-color)'">
              <i class="fas fa-folder-open"></i> 浏览
            </button>
            <button type="button" onclick="showPathSuggestions()" style="
              padding: 12px 16px;
              border: 1px solid var(--border-color);
              border-radius: var(--border-radius);
              background: var(--surface-color);
              color: var(--text-primary);
              cursor: pointer;
              white-space: nowrap;
              transition: var(--transition);
            " onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='var(--surface-color)'">
              <i class="fas fa-folder-open"></i> 路径
            </button>
          </div>
          <input type="file" id="model-file-input" style="display: none;" accept=".gguf,.bin,.safetensors,.pt,.pth,.onnx,.tflite">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">推理框架</label>
          <select id="model-framework" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          ">
            <option value="llama_cpp">llama.cpp</option>
            <option value="vllm">vLLM</option>
            <option value="docker">Docker</option>
          </select>
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">优先级</label>
          <input type="number" id="model-priority" min="1" max="10" value="5" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="1-10，数字越大优先级越高">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">GPU内存需求 (MB)</label>
          <input type="number" id="model-gpu-memory" min="0" value="4096" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="所需GPU内存大小">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">附加参数</label>
          <textarea id="model-additional-params" rows="3" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
            resize: vertical;
          " placeholder="例如: --ctx-size 4096 --n-gpu-layers 32"></textarea>
        </div>
        
        <div class="modal-actions" style="
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 20px;
          padding-top: 16px;
          border-top: 1px solid var(--border-color);
        ">
          <button type="button" onclick="closeAddModelForm()" class="btn btn-secondary">取消</button>
          <button type="submit" class="btn btn-primary">创建模型</button>
        </div>
      </form>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(formModal);

  // 绑定表单提交事件
  const form = document.getElementById('add-model-form');
  form.addEventListener('submit', handleAddModelSubmit);

  // 点击背景关闭弹窗
  formModal.addEventListener('click', (e) => {
    if (e.target === formModal) {
      closeAddModelForm();
    }
  });
}

async function handleAddModelSubmit(e) {
  e.preventDefault();

  // 生成唯一的模型ID
  const modelId = 'model_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

  // 获取表单数据
  const modelName = document.getElementById('model-name').value.trim();
  const modelPath = document.getElementById('model-path').value.trim();
  const framework = document.getElementById('model-framework').value;
  const priority = parseInt(document.getElementById('model-priority').value) || 5;
  const additionalParams = document.getElementById('model-additional-params')?.value?.trim() || null;
  const gpuMemory = parseInt(document.getElementById('model-gpu-memory')?.value) || 4096;

  const formData = {
    id: modelId,
    name: modelName,
    model_path: modelPath,
    framework: framework,
    priority: priority,
    gpu_devices: [0], // 默认使用第一个GPU
    additional_parameters: additionalParams,
    parameters: {
      port: framework === 'vllm' ? 8000 : 8080,
      host: '0.0.0.0'
    },
    resource_requirements: {
      gpu_memory: gpuMemory,
      gpu_devices: [0]
    },
    health_check: {
      enabled: true,
      interval: 30,
      timeout: 10,
      max_failures: 3
    },
    retry_policy: {
      enabled: true,
      max_attempts: 3,
      initial_delay: 60,
      max_delay: 300,
      backoff_factor: 2.0
    }
  };

  // 验证表单
  if (!modelName) {
    Utils.showNotification('请输入模型名称', 'error');
    return;
  }

  if (!modelPath) {
    Utils.showNotification('请输入模型路径', 'error');
    return;
  }

  // 验证优先级范围
  if (priority < 1 || priority > 10) {
    Utils.showNotification('优先级必须在1-10之间', 'error');
    return;
  }

  // 验证GPU内存
  if (gpuMemory < 0) {
    Utils.showNotification('GPU内存需求不能为负数', 'error');
    return;
  }

  // 获取提交按钮
  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerHTML;

  try {
    // 显示加载状态
    submitBtn.innerHTML = '<span class="loading-spinner"></span> 创建中...';
    submitBtn.disabled = true;

    // 发送创建请求
    console.log('发送模型创建请求:', formData);
    const response = await Utils.apiRequest('/api/models/', {
      method: 'POST',
      body: JSON.stringify(formData)
    });

    console.log('模型创建响应:', response);
    Utils.showNotification(`模型 "${formData.name}" 创建成功`, 'success');
    closeAddModelForm();

    // 刷新模型列表
    setTimeout(() => {
      if (typeof loadModelList === 'function') {
        loadModelList();
      }
    }, 1000);

  } catch (error) {
    console.error('创建模型详细错误:', error);
    Utils.showNotification(`创建模型失败: ${error.message}`, 'error');
  } finally {
    // 恢复按钮状态
    submitBtn.innerHTML = originalText;
    submitBtn.disabled = false;
  }
}

function closeAddModelForm() {
  const modal = document.getElementById('add-model-modal');
  if (modal) {
    modal.remove();
  }
}

function showEditModelForm(config) {
  // 创建模型编辑表单弹窗
  const formModal = document.createElement('div');
  formModal.id = 'edit-model-modal';
  formModal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease-out;
  `;

  formModal.innerHTML = `
    <div class="modal-content" style="
      background: var(--surface-color);
      border-radius: var(--border-radius);
      padding: 24px;
      max-width: 500px;
      width: 90%;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: var(--shadow-heavy);
    ">
      <div class="modal-header" style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 16px;
      ">
        <h2 style="margin: 0; color: var(--text-primary);">编辑模型</h2>
        <button onclick="closeEditModelForm()" style="
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: var(--text-secondary);
          width: 32px;
        ">&times;</button>
      </div>
      
      <form id="edit-model-form">
        <input type="hidden" id="edit-model-id" value="${config.id}">
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">模型名称 *</label>
          <input type="text" id="edit-model-name" required value="${config.name}" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="输入模型名称">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">模型路径 *</label>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="edit-model-path" required value="${config.model_path}" style="
              flex: 1;
              padding: 12px;
              border: 1px solid var(--border-color);
              border-radius: var(--border-radius);
              font-size: 14px;
              background: var(--surface-color);
              color: var(--text-primary);
            " placeholder="输入模型文件路径">
            <button type="button" onclick="selectEditModelFile()" style="
              padding: 12px 16px;
              border: 1px solid var(--border-color);
              border-radius: var(--border-radius);
              background: var(--surface-color);
              color: var(--text-primary);
              cursor: pointer;
              white-space: nowrap;
              transition: var(--transition);
            " onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='var(--surface-color)'">
              <i class="fas fa-folder-open"></i> 浏览
            </button>
          </div>
          <input type="file" id="edit-model-file-input" style="display: none;" accept=".gguf,.bin,.safetensors,.pt,.pth,.onnx,.tflite">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">推理框架</label>
          <select id="edit-model-framework" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          ">
            <option value="llama_cpp" ${config.framework === 'llama_cpp' ? 'selected' : ''}>llama.cpp</option>
            <option value="vllm" ${config.framework === 'vllm' ? 'selected' : ''}>vLLM</option>
            <option value="docker" ${config.framework === 'docker' ? 'selected' : ''}>Docker</option>
          </select>
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">优先级</label>
          <input type="number" id="edit-model-priority" min="1" max="10" value="${config.priority}" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="1-10，数字越大优先级越高">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">GPU内存需求 (MB)</label>
          <input type="number" id="edit-model-gpu-memory" min="0" value="${config.resource_requirements?.gpu_memory || 4096}" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
          " placeholder="所需GPU内存大小">
        </div>
        
        <div class="form-group" style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">附加参数</label>
          <textarea id="edit-model-additional-params" rows="3" style="
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 14px;
            background: var(--surface-color);
            color: var(--text-primary);
            resize: vertical;
          " placeholder="例如: --ctx-size 4096 --n-gpu-layers 32"></textarea>
        </div>
        
        <div class="modal-actions" style="
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 20px;
          padding-top: 16px;
          border-top: 1px solid var(--border-color);
        ">
          <button type="button" onclick="closeEditModelForm()" class="btn btn-secondary">取消</button>
          <button type="submit" class="btn btn-primary">保存更改</button>
        </div>
      </form>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(formModal);

  // 设置附加参数字段的值（避免HTML转义问题）
  const additionalParamsTextarea = document.getElementById('edit-model-additional-params');
  if (additionalParamsTextarea && config.additional_parameters) {
    additionalParamsTextarea.value = config.additional_parameters;
  }

  // 绑定表单提交事件
  const form = document.getElementById('edit-model-form');
  form.addEventListener('submit', handleEditModelSubmit);

  // 点击背景关闭弹窗
  formModal.addEventListener('click', (e) => {
    if (e.target === formModal) {
      closeEditModelForm();
    }
  });
}

async function handleEditModelSubmit(e) {
  e.preventDefault();

  // 获取表单数据
  const modelId = document.getElementById('edit-model-id').value;
  const modelName = document.getElementById('edit-model-name').value.trim();
  const modelPath = document.getElementById('edit-model-path').value.trim();
  const framework = document.getElementById('edit-model-framework').value;
  const priority = parseInt(document.getElementById('edit-model-priority').value) || 5;
  const additionalParams = document.getElementById('edit-model-additional-params')?.value?.trim() || null;
  const gpuMemory = parseInt(document.getElementById('edit-model-gpu-memory')?.value) || 4096;

  const formData = {
    id: modelId,
    name: modelName,
    model_path: modelPath,
    framework: framework,
    priority: priority,
    gpu_devices: [0], // 默认使用第一个GPU
    additional_parameters: additionalParams,
    parameters: {
      port: framework === 'vllm' ? 8000 : 8080,
      host: '0.0.0.0'
    },
    resource_requirements: {
      gpu_memory: gpuMemory,
      gpu_devices: [0]
    },
    health_check: {
      enabled: true,
      interval: 30,
      timeout: 10,
      max_failures: 3
    },
    retry_policy: {
      enabled: true,
      max_attempts: 3,
      initial_delay: 60,
      max_delay: 300,
      backoff_factor: 2.0
    }
  };

  // 验证表单
  if (!modelName) {
    Utils.showNotification('请输入模型名称', 'error');
    return;
  }

  if (!modelPath) {
    Utils.showNotification('请输入模型路径', 'error');
    return;
  }

  // 验证优先级范围
  if (priority < 1 || priority > 10) {
    Utils.showNotification('优先级必须在1-10之间', 'error');
    return;
  }

  // 验证GPU内存
  if (gpuMemory < 0) {
    Utils.showNotification('GPU内存需求不能为负数', 'error');
    return;
  }

  // 获取提交按钮
  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerHTML;

  try {
    // 显示加载状态
    submitBtn.innerHTML = '<span class="loading-spinner"></span> 保存中...';
    submitBtn.disabled = true;

    // 发送更新请求
    console.log('发送模型更新请求:', formData);
    const response = await Utils.apiRequest(`/api/models/${modelId}`, {
      method: 'PUT',
      body: JSON.stringify(formData)
    });

    console.log('模型更新响应:', response);
    Utils.showNotification(`模型 "${formData.name}" 更新成功`, 'success');
    closeEditModelForm();

    // 刷新模型列表
    setTimeout(() => {
      if (typeof loadModelList === 'function') {
        loadModelList();
      }
    }, 1000);

  } catch (error) {
    console.error('更新模型详细错误:', error);
    Utils.showNotification(`更新模型失败: ${error.message}`, 'error');
  } finally {
    // 恢复按钮状态
    submitBtn.innerHTML = originalText;
    submitBtn.disabled = false;
  }
}

function closeEditModelForm() {
  const modal = document.getElementById('edit-model-modal');
  if (modal) {
    modal.remove();
  }
}

function selectEditModelFile() {
  const fileInput = document.getElementById('edit-model-file-input');
  fileInput.click();
  
  fileInput.onchange = function(e) {
    const file = e.target.files[0];
    if (file) {
      const pathInput = document.getElementById('edit-model-path');
      pathInput.value = file.name; // 这里可以根据需要设置完整路径
    }
  };
}

function selectModelFile() {
  const fileInput = document.getElementById('model-file-input');
  fileInput.click();
  
  fileInput.onchange = function(e) {
    const file = e.target.files[0];
    if (file) {
      const pathInput = document.getElementById('model-path');
      pathInput.value = file.name; // 这里可以根据需要设置完整路径
    }
  };
}

function showPathSuggestions() {
  // 显示常用路径建议
  const pathInput = document.getElementById('model-path');
  const suggestions = [
    '/models/',
    '/data/models/',
    '/home/models/',
    '/opt/models/',
    './models/',
    '../models/'
  ];
  
  // 创建建议列表
  const suggestionList = document.createElement('div');
  suggestionList.style.cssText = `
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-medium);
    z-index: 1000;
    max-height: 200px;
    overflow-y: auto;
  `;
  
  suggestions.forEach(path => {
    const item = document.createElement('div');
    item.style.cssText = `
      padding: 8px 12px;
      cursor: pointer;
      border-bottom: 1px solid var(--border-color);
      transition: var(--transition);
    `;
    item.textContent = path;
    
    item.addEventListener('mouseenter', () => {
      item.style.background = 'var(--background-color)';
    });
    
    item.addEventListener('mouseleave', () => {
      item.style.background = 'transparent';
    });
    
    item.addEventListener('click', () => {
      pathInput.value = path;
      suggestionList.remove();
    });
    
    suggestionList.appendChild(item);
  });
  
  // 移除已存在的建议列表
  const existingSuggestions = document.querySelector('.path-suggestions');
  if (existingSuggestions) {
    existingSuggestions.remove();
  }
  
  // 添加建议列表
  suggestionList.className = 'path-suggestions';
  const pathContainer = pathInput.parentElement;
  pathContainer.style.position = 'relative';
  pathContainer.appendChild(suggestionList);
  
  // 点击其他地方关闭建议列表
  setTimeout(() => {
    document.addEventListener('click', function closeSuggestions(e) {
      if (!pathContainer.contains(e.target)) {
        suggestionList.remove();
        document.removeEventListener('click', closeSuggestions);
      }
    });
  }, 100);
}