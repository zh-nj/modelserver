<template>
  <f7-page name="models">
    <f7-navbar title="模型管理" back-link="返回">
      <f7-nav-right>
        <f7-link @click="showModelForm = true">
          <f7-icon ios="f7:plus" md="material:add" />
          添加
        </f7-link>
      </f7-nav-right>
    </f7-navbar>
    
    <f7-page-content>
      <!-- 统计概览 -->
      <f7-block-title>概览</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ modelsStore.totalModels }}</div>
              <div class="stat-label">总模型数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ modelsStore.runningModels.length }}</div>
              <div class="stat-label">运行中</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stoppedModels.length }}</div>
              <div class="stat-label">已停止</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ errorModels.length }}</div>
              <div class="stat-label">错误</div>
            </div>
          </div>
        </f7-card-content>
      </f7-card>
      
      <!-- 筛选和搜索 -->
      <f7-block-title>筛选</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="filter-controls">
            <f7-segmented>
              <f7-button
                :active="statusFilter === 'all'"
                @click="statusFilter = 'all'"
              >
                全部
              </f7-button>
              <f7-button
                :active="statusFilter === 'running'"
                @click="statusFilter = 'running'"
              >
                运行中
              </f7-button>
              <f7-button
                :active="statusFilter === 'stopped'"
                @click="statusFilter = 'stopped'"
              >
                已停止
              </f7-button>
              <f7-button
                :active="statusFilter === 'error'"
                @click="statusFilter = 'error'"
              >
                错误
              </f7-button>
            </f7-segmented>
            
            <f7-searchbar
              v-model:value="searchQuery"
              placeholder="搜索模型名称..."
              disable-button-text="取消"
              clear-button
            />
          </div>
        </f7-card-content>
      </f7-card>
      
      <!-- 模型列表 -->
      <f7-block-title>模型列表</f7-block-title>
      
      <!-- 加载状态 -->
      <f7-block v-if="modelsStore.loading">
        <div class="loading-container">
          <f7-preloader />
          <p>加载模型列表...</p>
        </div>
      </f7-block>
      
      <!-- 错误状态 -->
      <ErrorMessage
        v-else-if="modelsStore.error"
        :message="modelsStore.error"
        @retry="loadModels"
      />
      
      <!-- 模型卡片列表 -->
      <div v-else-if="filteredModels.length > 0" class="models-container">
        <ModelCard
          v-for="model in filteredModels"
          :key="model.id"
          :model="model"
          @toggle="handleToggleModel"
          @edit="handleEditModel"
          @delete="handleDeleteModel"
          @detail="handleShowDetail"
          @logs="handleShowLogs"
          @metrics="handleShowMetrics"
        />
      </div>
      
      <!-- 空状态 -->
      <f7-block v-else>
        <div class="empty-state">
          <f7-icon ios="f7:cube" md="material:memory" size="64" color="gray" />
          <h3>{{ searchQuery ? '未找到匹配的模型' : '暂无模型配置' }}</h3>
          <p>{{ searchQuery ? '请尝试其他搜索条件' : '点击右上角添加按钮创建第一个模型' }}</p>
          <f7-button v-if="!searchQuery" large @click="showModelForm = true">
            添加模型
          </f7-button>
        </div>
      </f7-block>
    </f7-page-content>
    
    <!-- 模型表单弹窗 -->
    <ModelForm
      :opened="showModelForm"
      :model="editingModel"
      @close="handleCloseForm"
      @submit="handleSubmitForm"
    />
    
    <!-- 模型详情弹窗 -->
    <ModelDetail
      :opened="showModelDetail"
      :model="selectedModel"
      @close="showModelDetail = false"
      @edit="handleEditModel"
      @toggle="handleToggleModel"
      @restart="handleRestartModel"
      @logs="handleShowLogs"
    />
    
    <!-- 日志查看弹窗 -->
    <f7-popup :opened="showLogs" @popup:closed="showLogs = false">
      <f7-page>
        <f7-navbar :title="`${selectedModel?.name} - 日志`">
          <f7-nav-left>
            <f7-link @click="showLogs = false">关闭</f7-link>
          </f7-nav-left>
          <f7-nav-right>
            <f7-link @click="refreshLogs">刷新</f7-link>
          </f7-nav-right>
        </f7-navbar>
        <f7-page-content>
          <f7-block v-if="logs">
            <pre class="logs-content">{{ logs }}</pre>
          </f7-block>
          <f7-block v-else>
            <div class="loading-container">
              <f7-preloader />
              <p>加载日志...</p>
            </div>
          </f7-block>
        </f7-page-content>
      </f7-page>
    </f7-popup>
  </f7-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { f7 } from 'framework7-vue'
import type { ModelInfo, ModelConfig } from '@/types'
import { ModelStatus } from '@/types'
import { useModelsStore } from '@/stores/models'
import { ModelsApiService } from '@/services/models'
import ModelCard from '@/components/models/ModelCard.vue'
import ModelForm from '@/components/models/ModelForm.vue'
import ModelDetail from '@/components/models/ModelDetail.vue'
import ErrorMessage from '@/components/common/ErrorMessage.vue'

// 使用模型存储
const modelsStore = useModelsStore()

// 界面状态
const showModelForm = ref(false)
const showModelDetail = ref(false)
const showLogs = ref(false)
const statusFilter = ref<'all' | 'running' | 'stopped' | 'error'>('all')
const searchQuery = ref('')

// 当前操作的模型
const selectedModel = ref<ModelInfo | null>(null)
const editingModel = ref<ModelInfo | null>(null)
const logs = ref<string>('')

// WebSocket连接
let wsConnection: WebSocket | null = null

// 计算属性
const stoppedModels = computed(() => 
  modelsStore.models.filter(model => model.status === ModelStatus.STOPPED)
)

const errorModels = computed(() => 
  modelsStore.models.filter(model => model.status === ModelStatus.ERROR)
)

const filteredModels = computed(() => {
  let filtered = modelsStore.models

  // 状态筛选
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter(model => {
      switch (statusFilter.value) {
        case 'running':
          return model.status === ModelStatus.RUNNING
        case 'stopped':
          return model.status === ModelStatus.STOPPED
        case 'error':
          return model.status === ModelStatus.ERROR
        default:
          return true
      }
    })
  }

  // 搜索筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(model =>
      model.name.toLowerCase().includes(query) ||
      model.id.toLowerCase().includes(query)
    )
  }

  return filtered
})

// 加载模型列表
const loadModels = async () => {
  try {
    await modelsStore.fetchModels()
  } catch (error) {
    console.error('加载模型列表失败:', error)
    f7.toast.create({
      text: '加载模型列表失败',
      closeTimeout: 3000
    }).open()
  }
}

// 处理模型状态切换
const handleToggleModel = async (model: ModelInfo) => {
  try {
    if (model.status === ModelStatus.RUNNING) {
      await modelsStore.stopModel(model.id)
      f7.toast.create({
        text: `正在停止模型 ${model.name}`,
        closeTimeout: 2000
      }).open()
    } else {
      await modelsStore.startModel(model.id)
      f7.toast.create({
        text: `正在启动模型 ${model.name}`,
        closeTimeout: 2000
      }).open()
    }
  } catch (error: any) {
    f7.dialog.alert(error.message || '操作失败', '错误')
  }
}

// 处理模型重启
const handleRestartModel = async (model: ModelInfo) => {
  try {
    await modelsStore.restartModel(model.id)
    f7.toast.create({
      text: `正在重启模型 ${model.name}`,
      closeTimeout: 2000
    }).open()
  } catch (error: any) {
    f7.dialog.alert(error.message || '重启失败', '错误')
  }
}

// 处理编辑模型
const handleEditModel = (model: ModelInfo) => {
  editingModel.value = model
  showModelForm.value = true
  showModelDetail.value = false
}

// 处理删除模型
const handleDeleteModel = (model: ModelInfo) => {
  f7.dialog.confirm(
    `确定要删除模型 "${model.name}" 吗？此操作不可撤销。`,
    '确认删除',
    async () => {
      try {
        await modelsStore.deleteModel(model.id)
        f7.toast.create({
          text: `模型 ${model.name} 已删除`,
          closeTimeout: 2000
        }).open()
      } catch (error: any) {
        f7.dialog.alert(error.message || '删除失败', '错误')
      }
    }
  )
}

// 处理显示详情
const handleShowDetail = (model: ModelInfo) => {
  selectedModel.value = model
  showModelDetail.value = true
}

// 处理显示日志
const handleShowLogs = async (model: ModelInfo) => {
  selectedModel.value = model
  showLogs.value = true
  await loadLogs(model.id)
}

// 处理显示指标
const handleShowMetrics = (model: ModelInfo) => {
  // 跳转到监控页面，显示特定模型的指标
  f7.views.main.router.navigate('/monitoring', {
    props: { modelId: model.id }
  })
}

// 处理表单关闭
const handleCloseForm = () => {
  showModelForm.value = false
  editingModel.value = null
}

// 处理表单提交
const handleSubmitForm = async (config: ModelConfig) => {
  try {
    if (editingModel.value) {
      // 更新模型
      await modelsStore.updateModel(editingModel.value.id, config)
      f7.toast.create({
        text: `模型 ${config.name} 已更新`,
        closeTimeout: 2000
      }).open()
    } else {
      // 创建模型
      await modelsStore.createModel(config)
      f7.toast.create({
        text: `模型 ${config.name} 已创建`,
        closeTimeout: 2000
      }).open()
    }
    handleCloseForm()
  } catch (error: any) {
    f7.dialog.alert(error.message || '操作失败', '错误')
  }
}

// 加载日志
const loadLogs = async (modelId: string) => {
  try {
    logs.value = ''
    const response = await ModelsApiService.getModelLogs(modelId, 500)
    logs.value = response.data || '暂无日志'
  } catch (error) {
    logs.value = '加载日志失败'
    console.error('加载日志失败:', error)
  }
}

// 刷新日志
const refreshLogs = async () => {
  if (selectedModel.value) {
    await loadLogs(selectedModel.value.id)
  }
}

// 建立WebSocket连接以接收实时更新
const connectWebSocket = () => {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/models`
    
    wsConnection = new WebSocket(wsUrl)
    
    wsConnection.onopen = () => {
      console.log('模型WebSocket连接已建立')
    }
    
    wsConnection.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleWebSocketMessage(message)
      } catch (error) {
        console.error('解析WebSocket消息失败:', error)
      }
    }
    
    wsConnection.onclose = () => {
      console.log('模型WebSocket连接已关闭')
      // 5秒后尝试重连
      setTimeout(connectWebSocket, 5000)
    }
    
    wsConnection.onerror = (error) => {
      console.error('模型WebSocket连接错误:', error)
    }
  } catch (error) {
    console.error('建立WebSocket连接失败:', error)
  }
}

// 处理WebSocket消息
const handleWebSocketMessage = (message: any) => {
  switch (message.type) {
    case 'model_status_update':
      modelsStore.updateModelStatus(
        message.data.model_id,
        message.data.status,
        message.data.error_message
      )
      break
    case 'model_created':
      modelsStore.fetchModels() // 重新加载列表
      break
    case 'model_deleted':
      modelsStore.fetchModels() // 重新加载列表
      break
    default:
      console.log('未知的WebSocket消息类型:', message.type)
  }
}

// 组件挂载时的操作
onMounted(async () => {
  await loadModels()
  connectWebSocket()
})

// 组件卸载时的清理
onUnmounted(() => {
  if (wsConnection) {
    wsConnection.close()
    wsConnection = null
  }
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  text-align: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--f7-color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--f7-text-color-secondary);
}

.filter-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.models-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px;
  text-align: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 24px;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--f7-text-color);
}

.empty-state p {
  margin: 0;
  color: var(--f7-text-color-secondary);
  line-height: 1.4;
}

.logs-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  background: var(--f7-card-bg-color);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .stat-value {
    font-size: 20px;
  }
  
  .filter-controls {
    gap: 12px;
  }
  
  .models-container {
    gap: 12px;
  }
  
  .empty-state {
    padding: 32px 16px;
  }
  
  .logs-content {
    font-size: 11px;
    padding: 12px;
  }
}

/* 平板端适配 */
@media (min-width: 769px) and (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  
  .filter-controls {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  
  .filter-controls .searchbar {
    flex: 1;
    max-width: 300px;
  }
}

/* 桌面端适配 */
@media (min-width: 1025px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
  }
  
  .stat-value {
    font-size: 28px;
  }
  
  .filter-controls {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  
  .filter-controls .searchbar {
    flex: 1;
    max-width: 400px;
  }
  
  .models-container {
    gap: 20px;
  }
  
  .empty-state {
    padding: 64px 32px;
  }
  
  .logs-content {
    font-size: 13px;
    padding: 20px;
  }
}
</style>