/**
 * 慧儿模型园 - 服务器端文件浏览器
 */

let currentServerPath = '/';
let selectedFilePath = '';

function selectModelFile() {
  // 创建服务器端文件浏览器弹窗
  createServerFileBrowser();
}

function createServerFileBrowser() {
  // 创建文件浏览器弹窗
  const browserModal = document.createElement('div');
  browserModal.id = 'file-browser-modal';
  browserModal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2001;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease-out;
  `;

  browserModal.innerHTML = `
    <div class="modal-content" style="
      background: var(--surface-color);
      border-radius: var(--border-radius);
      padding: 24px;
      max-width: 800px;
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
        <h2 style="margin: 0; color: var(--text-primary);">选择模型文件</h2>
        <button onclick="closeFileBrowser()" style="
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          color: var(--text-secondary);
          width: 32px;
        ">&times;</button>
      </div>
      
      <div class="file-browser-content">
        <div class="browser-toolbar" style="
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          align-items: center;
        ">
          <button onclick="loadAllowedRoots()" class="btn btn-secondary" style="font-size: 14px; padding: 8px 12px;">
            <i class="fas fa-home"></i> 根目录
          </button>
          <button onclick="goToParentDirectory()" class="btn btn-secondary" id="parent-btn" style="font-size: 14px; padding: 8px 12px;" disabled>
            <i class="fas fa-arrow-up"></i> 上级
          </button>
        </div>
        
        <div class="current-path" style="
          margin-bottom: 16px;
          padding: 12px;
          background: var(--background-color);
          border-radius: var(--border-radius);
          font-family: monospace;
          font-size: 14px;
          color: var(--text-primary);
          word-break: break-all;
        ">
          当前路径: <span id="current-path">/</span>
        </div>
        
        <div class="file-list" id="file-list" style="
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius);
          max-height: 400px;
          overflow-y: auto;
        ">
          <div class="loading-placeholder" style="
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 40px;
            color: var(--text-secondary);
          ">
            <i class="fas fa-spinner fa-spin"></i>
            <span>正在加载文件列表...</span>
          </div>
        </div>
        
        <div class="selected-file" style="
          margin-top: 16px;
          padding: 12px;
          background: var(--background-color);
          border-radius: var(--border-radius);
          display: none;
        ">
          <strong>已选择:</strong> <span id="selected-file-path"></span>
        </div>
        
        <div class="modal-actions" style="
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          margin-top: 20px;
          padding-top: 16px;
          border-top: 1px solid var(--border-color);
        ">
          <button onclick="closeFileBrowser()" class="btn btn-secondary">取消</button>
          <button onclick="confirmFileSelection()" class="btn btn-primary" id="confirm-btn" disabled>确认选择</button>
        </div>
      </div>
    </div>
  `;

  // 添加到页面
  document.body.appendChild(browserModal);

  // 加载允许的根目录
  loadAllowedRoots();

  // 点击背景关闭弹窗
  browserModal.addEventListener('click', (e) => {
    if (e.target === browserModal) {
      closeFileBrowser();
    }
  });
}

async function loadAllowedRoots() {
  const fileList = document.getElementById('file-list');
  const currentPathSpan = document.getElementById('current-path');
  const parentBtn = document.getElementById('parent-btn');
  
  try {
    // 显示加载状态
    fileList.innerHTML = `
      <div class="loading-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--text-secondary);
      ">
        <i class="fas fa-spinner fa-spin"></i>
        <span>正在加载根目录...</span>
      </div>
    `;

    // 调用后端API获取允许的根目录
    const response = await Utils.apiRequest('/api/files/roots');
    
    currentServerPath = '/';
    currentPathSpan.textContent = '根目录选择';
    parentBtn.disabled = true;
    
    // 渲染根目录列表
    renderRootsList(response.roots);
    
  } catch (error) {
    console.error('加载根目录失败:', error);
    fileList.innerHTML = `
      <div class="error-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--error-color);
      ">
        <i class="fas fa-exclamation-triangle"></i>
        <span>加载根目录失败: ${error.message}</span>
      </div>
    `;
  }
}

function renderRootsList(roots) {
  const fileList = document.getElementById('file-list');
  let html = '';

  if (roots && roots.length > 0) {
    roots.forEach(root => {
      const accessible = root.accessible ? '' : ' (无权限)';
      const style = root.accessible ? '' : 'opacity: 0.5; cursor: not-allowed;';
      
      html += `
        <div class="file-item directory-item" ${root.accessible ? `onclick="loadServerDirectory('${root.path}')"` : ''} style="
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          ${root.accessible ? 'cursor: pointer;' : 'cursor: not-allowed;'}
          border-bottom: 1px solid var(--border-color);
          transition: var(--transition);
          ${style}
        " ${root.accessible ? `onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='transparent'"` : ''}>
          <i class="fas fa-folder" style="color: var(--warning-color); width: 20px;"></i>
          <div>
            <div style="color: var(--text-primary); font-weight: 500;">${root.name}${accessible}</div>
            <div style="color: var(--text-secondary); font-size: 12px; font-family: monospace;">${root.path}</div>
          </div>
        </div>
      `;
    });
  } else {
    html = `
      <div class="empty-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--text-secondary);
      ">
        <i class="fas fa-folder-open"></i>
        <span>没有可用的模型目录</span>
      </div>
    `;
  }

  fileList.innerHTML = html;
}

async function loadServerDirectory(path) {
  const fileList = document.getElementById('file-list');
  const currentPathSpan = document.getElementById('current-path');
  const parentBtn = document.getElementById('parent-btn');
  
  try {
    // 显示加载状态
    fileList.innerHTML = `
      <div class="loading-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--text-secondary);
      ">
        <i class="fas fa-spinner fa-spin"></i>
        <span>正在加载文件列表...</span>
      </div>
    `;

    // 调用后端API获取目录内容
    const response = await Utils.apiRequest(`/api/files/browse?path=${encodeURIComponent(path)}`);
    
    currentServerPath = response.path;
    currentPathSpan.textContent = response.path;
    parentBtn.disabled = !response.parent;
    
    // 渲染文件列表
    renderFileList(response.files, response.directories, response.parent);
    
  } catch (error) {
    console.error('加载目录失败:', error);
    fileList.innerHTML = `
      <div class="error-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--error-color);
      ">
        <i class="fas fa-exclamation-triangle"></i>
        <div>
          <div>加载目录失败</div>
          <div style="font-size: 12px; margin-top: 4px;">${error.message}</div>
        </div>
      </div>
    `;
  }
}

function renderFileList(files, directories, parentPath) {
  const fileList = document.getElementById('file-list');
  let html = '';

  // 添加目录
  if (directories && directories.length > 0) {
    directories.forEach(dir => {
      const accessible = dir.accessible ? '' : ' (无权限)';
      const style = dir.accessible ? '' : 'opacity: 0.5; cursor: not-allowed;';
      
      html += `
        <div class="file-item directory-item" ${dir.accessible ? `onclick="loadServerDirectory('${dir.path}')"` : ''} style="
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          ${dir.accessible ? 'cursor: pointer;' : 'cursor: not-allowed;'}
          border-bottom: 1px solid var(--border-color);
          transition: var(--transition);
          ${style}
        " ${dir.accessible ? `onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='transparent'"` : ''}>
          <i class="fas fa-folder" style="color: var(--warning-color); width: 20px;"></i>
          <span style="color: var(--text-primary);">${dir.name}${accessible}</span>
        </div>
      `;
    });
  }

  // 添加文件（只显示模型文件）
  if (files && files.length > 0) {
    const modelFiles = files.filter(file => file.is_model);
    
    modelFiles.forEach(file => {
      const fileSize = formatFileSize(file.size);
      const modifiedDate = new Date(file.modified * 1000).toLocaleString('zh-CN');
      
      html += `
        <div class="file-item model-file" onclick="selectServerFile('${file.path}')" style="
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          cursor: pointer;
          border-bottom: 1px solid var(--border-color);
          transition: var(--transition);
        " onmouseover="this.style.background='var(--background-color)'" onmouseout="this.style.background='transparent'">
          <i class="fas fa-file" style="color: var(--secondary-color); width: 20px;"></i>
          <div style="flex: 1;">
            <div style="color: var(--text-primary); font-weight: 500;">${file.name}</div>
            <div style="color: var(--text-secondary); font-size: 12px;">
              ${fileSize} • ${modifiedDate}
            </div>
          </div>
        </div>
      `;
    });
  }

  if (html === '') {
    html = `
      <div class="empty-placeholder" style="
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 40px;
        color: var(--text-secondary);
      ">
        <i class="fas fa-folder-open"></i>
        <span>此目录下没有模型文件</span>
      </div>
    `;
  }

  fileList.innerHTML = html;
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function goToParentDirectory() {
  const parentBtn = document.getElementById('parent-btn');
  if (!parentBtn.disabled && currentServerPath !== '/') {
    const parentPath = currentServerPath.split('/').slice(0, -1).join('/') || '/';
    loadServerDirectory(parentPath);
  }
}

function selectServerFile(filePath) {
  selectedFilePath = filePath;
  
  // 更新选中文件显示
  const selectedFileDiv = document.querySelector('.selected-file');
  const selectedFilePathSpan = document.getElementById('selected-file-path');
  const confirmBtn = document.getElementById('confirm-btn');
  
  selectedFileDiv.style.display = 'block';
  selectedFilePathSpan.textContent = filePath;
  confirmBtn.disabled = false;
  
  // 高亮选中的文件
  document.querySelectorAll('.model-file').forEach(item => {
    item.style.background = 'transparent';
    item.style.color = '';
  });
  
  const clickedItem = event.target.closest('.file-item');
  if (clickedItem) {
    clickedItem.style.background = 'var(--primary-color)';
    clickedItem.style.color = 'white';
  }
}

function confirmFileSelection() {
  if (selectedFilePath) {
    const pathInput = document.getElementById('model-path');
    pathInput.value = selectedFilePath;
    
    Utils.showNotification(`已选择文件: ${selectedFilePath}`, 'success');
    closeFileBrowser();
  }
}

function closeFileBrowser() {
  const modal = document.getElementById('file-browser-modal');
  if (modal) {
    modal.remove();
  }
  selectedFilePath = '';
  currentServerPath = '/';
}

// 路径建议功能
function showPathSuggestions() {
  const pathInput = document.getElementById('model-path');
  if (!pathInput) return;
  
  const suggestions = [
    '/models/',
    '/data/models/',
    '/home/models/',
    '/opt/models/',
    './models/',
    '../models/',
    '/usr/local/models/',
    '/var/lib/models/'
  ];
  
  // 创建路径建议下拉菜单
  const suggestionDiv = document.createElement('div');
  suggestionDiv.id = 'path-suggestions';
  suggestionDiv.style.cssText = `
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-top: none;
    border-radius: 0 0 var(--border-radius) var(--border-radius);
    box-shadow: var(--shadow-medium);
    z-index: 1000;
    max-height: 200px;
    overflow-y: auto;
  `;
  
  // 添加标题
  const title = document.createElement('div');
  title.style.cssText = `
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--background-color);
    border-bottom: 1px solid var(--border-color);
  `;
  title.textContent = '常用模型路径';
  suggestionDiv.appendChild(title);
  
  suggestions.forEach(path => {
    const item = document.createElement('div');
    item.style.cssText = `
      padding: 12px 16px;
      cursor: pointer;
      border-bottom: 1px solid var(--border-color);
      transition: var(--transition);
      display: flex;
      align-items: center;
      gap: 8px;
    `;
    item.innerHTML = `<i class="fas fa-folder" style="color: var(--warning-color);"></i>${path}`;
    item.onclick = () => {
      pathInput.value = path;
      suggestionDiv.remove();
      pathInput.focus();
      Utils.showNotification(`已选择路径: ${path}`, 'success');
    };
    item.onmouseover = () => item.style.background = 'var(--background-color)';
    item.onmouseout = () => item.style.background = 'transparent';
    suggestionDiv.appendChild(item);
  });
  
  // 移除已存在的建议
  const existing = document.getElementById('path-suggestions');
  if (existing) existing.remove();
  
  // 添加到路径输入框的父容器
  const pathContainer = pathInput.parentElement;
  pathContainer.style.position = 'relative';
  pathContainer.appendChild(suggestionDiv);
  
  // 点击其他地方关闭建议
  setTimeout(() => {
    document.addEventListener('click', function closeSuggestions(e) {
      if (!pathContainer.contains(e.target)) {
        suggestionDiv.remove();
        document.removeEventListener('click', closeSuggestions);
      }
    });
  }, 100);
}