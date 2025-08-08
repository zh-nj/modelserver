/**
 * 模型管理状态存储
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ModelInfo, ModelConfig, ModelStatus } from '@/types'
import { apiClient } from '@/services/api'
import { getWebSocketClient, SubscriptionType, type WebSocketClient } from '@/services/websocket'

export const useModelsStore = defineStore('models', () => {
  // 状态
  const models = ref<ModelInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isRealTimeEnabled = ref(false)
  
  // WebSocket客户端
  let wsClient: WebSocketClient | null = null

  // 计算属性
  const runningModels = computed(() => 
    models.value.filter(model => model.status === ModelStatus.RUNNING)
  )

  const totalModels = computed(() => models.value.length)

  const modelsByFramework = computed(() => {
    const grouped: Record<string, ModelInfo[]> = {}
    models.value.forEach(model => {
      if (!grouped[model.framework]) {
        grouped[model.framework] = []
      }
      grouped[model.framework].push(model)
    })
    return grouped
  })

  // 操作方法
  const fetchModels = async () => {
    loading.value = true
    error.value = null
    try {
      // TODO: 替换为实际API调用
      // const response = await apiClient.get('/api/models')
      // models.value = response.data.data || []
      
      // 模拟数据用于开发测试
      models.value = [
        {
          id: 'model-1',
          name: 'Llama2-7B-Chat',
          framework: 'llama_cpp' as any,
          status: ModelStatus.RUNNING,
          priority: 8,
          gpu_devices: [0],
          created_at: '2024-01-15T10:30:00Z',
          updated_at: '2024-01-15T14:20:00Z',
          last_health_check: new Date().toISOString()
        },
        {
          id: 'model-2',
          name: 'CodeLlama-13B',
          framework: 'vllm' as any,
          status: ModelStatus.RUNNING,
          priority: 7,
          gpu_devices: [1, 2],
          created_at: '2024-01-15T11:00:00Z',
          updated_at: '2024-01-15T13:45:00Z',
          last_health_check: new Date().toISOString()
        },
        {
          id: 'model-3',
          name: 'Mistral-7B-Instruct',
          framework: 'llama_cpp' as any,
          status: ModelStatus.STOPPED,
          priority: 6,
          gpu_devices: [3],
          created_at: '2024-01-15T09:15:00Z',
          updated_at: '2024-01-15T12:30:00Z',
          last_health_check: new Date().toISOString()
        },
        {
          id: 'model-4',
          name: 'ChatGLM3-6B',
          framework: 'docker' as any,
          status: ModelStatus.ERROR,
          priority: 5,
          gpu_devices: [0],
          created_at: '2024-01-15T08:45:00Z',
          updated_at: '2024-01-15T15:10:00Z',
          last_health_check: new Date().toISOString(),
          error_message: 'GPU内存不足'
        },
        {
          id: 'model-5',
          name: 'Qwen-14B-Chat',
          framework: 'vllm' as any,
          status: ModelStatus.STARTING,
          priority: 9,
          gpu_devices: [2, 3],
          created_at: '2024-01-15T12:20:00Z',
          updated_at: '2024-01-15T15:30:00Z',
          last_health_check: new Date().toISOString()
        }
      ]
      
    } catch (err: any) {
      error.value = err.message || '获取模型列表失败'
      console.error('获取模型列表失败:', err)
    } finally {
      loading.value = false
    }
  }

  const createModel = async (config: ModelConfig) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post('/api/models', config)
      const newModel = response.data.data
      models.value.push(newModel)
      return newModel
    } catch (err: any) {
      error.value = err.message || '创建模型失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateModel = async (id: string, config: Partial<ModelConfig>) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put(`/api/models/${id}`, config)
      const updatedModel = response.data.data
      const index = models.value.findIndex(model => model.id === id)
      if (index !== -1) {
        models.value[index] = updatedModel
      }
      return updatedModel
    } catch (err: any) {
      error.value = err.message || '更新模型失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteModel = async (id: string) => {
    loading.value = true
    error.value = null
    try {
      await apiClient.delete(`/api/models/${id}`)
      models.value = models.value.filter(model => model.id !== id)
    } catch (err: any) {
      error.value = err.message || '删除模型失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const startModel = async (id: string) => {
    try {
      await apiClient.post(`/api/models/${id}/start`)
      const model = models.value.find(m => m.id === id)
      if (model) {
        model.status = ModelStatus.STARTING
      }
    } catch (err: any) {
      error.value = err.message || '启动模型失败'
      throw err
    }
  }

  const stopModel = async (id: string) => {
    try {
      await apiClient.post(`/api/models/${id}/stop`)
      const model = models.value.find(m => m.id === id)
      if (model) {
        model.status = ModelStatus.STOPPING
      }
    } catch (err: any) {
      error.value = err.message || '停止模型失败'
      throw err
    }
  }

  const restartModel = async (id: string) => {
    try {
      await apiClient.post(`/api/models/${id}/restart`)
      const model = models.value.find(m => m.id === id)
      if (model) {
        model.status = ModelStatus.STARTING
      }
    } catch (err: any) {
      error.value = err.message || '重启模型失败'
      throw err
    }
  }

  const updateModelStatus = (id: string, status: ModelStatus, errorMessage?: string) => {
    const model = models.value.find(m => m.id === id)
    if (model) {
      model.status = status
      if (errorMessage) {
        model.error_message = errorMessage
      }
      model.last_health_check = new Date().toISOString()
    }
  }

  const clearError = () => {
    error.value = null
  }

  // WebSocket实时更新功能
  const enableRealTimeUpdates = async () => {
    if (isRealTimeEnabled.value) return

    try {
      wsClient = getWebSocketClient()
      
      // 连接WebSocket
      if (wsClient.getStatus() === 'disconnected') {
        await wsClient.connect()
      }

      // 订阅模型状态更新
      wsClient.subscribe(SubscriptionType.MODEL_UPDATES)
      wsClient.subscribe(SubscriptionType.CONFIG_CHANGES)

      // 监听模型状态更新
      wsClient.on('modelStatusUpdate', (data: { model_id: string, status: ModelStatus, error_message?: string }) => {
        updateModelStatus(data.model_id, data.status, data.error_message)
        console.log('实时模型状态更新:', data)
      })

      // 监听配置变更
      wsClient.on('configChange', (data: any) => {
        console.log('模型配置变更:', data)
        // 重新获取模型列表以确保数据同步
        fetchModels()
      })

      // 监听连接状态变化
      wsClient.onStatusChange((status) => {
        console.log('WebSocket连接状态变化:', status)
        if (status === 'connected') {
          error.value = null
        } else if (status === 'error') {
          error.value = 'WebSocket连接失败'
        }
      })

      isRealTimeEnabled.value = true
      console.log('模型实时更新已启用')

    } catch (err: any) {
      error.value = err.message || '启用实时更新失败'
      console.error('启用实时更新失败:', err)
    }
  }

  const disableRealTimeUpdates = () => {
    if (!isRealTimeEnabled.value || !wsClient) return

    // 取消订阅
    wsClient.unsubscribe(SubscriptionType.MODEL_UPDATES)
    wsClient.unsubscribe(SubscriptionType.CONFIG_CHANGES)
    
    // 移除事件监听器
    wsClient.off('modelStatusUpdate')
    wsClient.off('configChange')

    isRealTimeEnabled.value = false
    console.log('模型实时更新已禁用')
  }

  // 模拟模型状态变化（用于开发测试）
  const simulateModelStatusChanges = () => {
    if (!isRealTimeEnabled.value || models.value.length === 0) return

    // 随机选择一个模型进行状态变化
    const randomModel = models.value[Math.floor(Math.random() * models.value.length)]
    const currentStatus = randomModel.status
    
    // 定义状态转换规则
    const statusTransitions: Record<ModelStatus, ModelStatus[]> = {
      [ModelStatus.STOPPED]: [ModelStatus.STARTING],
      [ModelStatus.STARTING]: [ModelStatus.RUNNING, ModelStatus.ERROR],
      [ModelStatus.RUNNING]: [ModelStatus.STOPPING, ModelStatus.ERROR],
      [ModelStatus.STOPPING]: [ModelStatus.STOPPED],
      [ModelStatus.ERROR]: [ModelStatus.STARTING, ModelStatus.STOPPED],
      [ModelStatus.PREEMPTED]: [ModelStatus.STARTING, ModelStatus.STOPPED]
    }

    const possibleTransitions = statusTransitions[currentStatus] || []
    if (possibleTransitions.length > 0) {
      const newStatus = possibleTransitions[Math.floor(Math.random() * possibleTransitions.length)]
      const errorMessage = newStatus === ModelStatus.ERROR ? '模拟错误：资源不足' : undefined
      
      updateModelStatus(randomModel.id, newStatus, errorMessage)
      console.log(`模拟状态变化: ${randomModel.name} ${currentStatus} -> ${newStatus}`)
    }
  }

  // 启动模拟状态变化定时器（仅用于开发测试）
  let modelSimulationTimer: number | null = null
  
  const startModelSimulation = () => {
    if (modelSimulationTimer) return
    
    modelSimulationTimer = setInterval(() => {
      if (isRealTimeEnabled.value) {
        simulateModelStatusChanges()
      }
    }, 8000) as unknown as number // 每8秒随机变化一个模型状态
  }

  const stopModelSimulation = () => {
    if (modelSimulationTimer) {
      clearInterval(modelSimulationTimer)
      modelSimulationTimer = null
    }
  }

  return {
    // 状态
    models,
    loading,
    error,
    isRealTimeEnabled,
    
    // 计算属性
    runningModels,
    totalModels,
    modelsByFramework,
    
    // 方法
    fetchModels,
    createModel,
    updateModel,
    deleteModel,
    startModel,
    stopModel,
    restartModel,
    updateModelStatus,
    clearError,
    
    // WebSocket实时更新方法
    enableRealTimeUpdates,
    disableRealTimeUpdates,
    startModelSimulation,
    stopModelSimulation
  }
})