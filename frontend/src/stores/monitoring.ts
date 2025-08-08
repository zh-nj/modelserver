/**
 * 监控数据状态存储
 */
import { defineStore } from 'pinia'
import { ref, computed, onUnmounted } from 'vue'
import type { GPUInfo, SystemOverview } from '@/types'
import { apiClient } from '@/services/api'
import { getWebSocketClient, SubscriptionType, type WebSocketClient } from '@/services/websocket'

export const useMonitoringStore = defineStore('monitoring', () => {
  // 状态
  const gpuList = ref<GPUInfo[]>([])
  const systemOverview = ref<SystemOverview>({
    total_models: 0,
    running_models: 0,
    total_gpus: 0,
    available_gpus: 0,
    total_memory: 0,
    used_memory: 0,
    free_memory: 0,
    uptime: 0
  })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref<Date | null>(null)
  const isRealTimeEnabled = ref(false)
  
  // WebSocket客户端
  let wsClient: WebSocketClient | null = null

  // 计算属性
  const totalGpuMemory = computed(() => 
    gpuList.value.reduce((total, gpu) => total + gpu.memory_total, 0)
  )

  const usedGpuMemory = computed(() => 
    gpuList.value.reduce((total, gpu) => total + gpu.memory_used, 0)
  )

  const averageGpuUtilization = computed(() => {
    if (gpuList.value.length === 0) return 0
    const total = gpuList.value.reduce((sum, gpu) => sum + gpu.utilization, 0)
    return Math.round(total / gpuList.value.length)
  })

  const averageGpuTemperature = computed(() => {
    if (gpuList.value.length === 0) return 0
    const total = gpuList.value.reduce((sum, gpu) => sum + gpu.temperature, 0)
    return Math.round(total / gpuList.value.length)
  })

  const highUtilizationGpus = computed(() => 
    gpuList.value.filter(gpu => gpu.utilization > 80)
  )

  const overheatedGpus = computed(() => 
    gpuList.value.filter(gpu => gpu.temperature > 80)
  )

  // 操作方法
  const fetchGpuInfo = async () => {
    loading.value = true
    error.value = null
    try {
      // TODO: 替换为实际API调用
      // const response = await apiClient.get('/api/system/gpu-info')
      // gpuList.value = response.data.data || []
      
      // 模拟数据用于开发测试
      gpuList.value = [
        {
          device_id: 0,
          name: 'NVIDIA RTX 4090',
          memory_total: 24576,
          memory_used: 18432,
          memory_free: 6144,
          utilization: 75 + Math.random() * 20,
          temperature: 68 + Math.random() * 15,
          power_usage: 320 + Math.random() * 50
        },
        {
          device_id: 1,
          name: 'NVIDIA RTX 4090',
          memory_total: 24576,
          memory_used: 12288,
          memory_free: 12288,
          utilization: 45 + Math.random() * 30,
          temperature: 62 + Math.random() * 18,
          power_usage: 280 + Math.random() * 60
        },
        {
          device_id: 2,
          name: 'NVIDIA RTX 3090',
          memory_total: 24576,
          memory_used: 20480,
          memory_free: 4096,
          utilization: 85 + Math.random() * 10,
          temperature: 72 + Math.random() * 12,
          power_usage: 350 + Math.random() * 40
        },
        {
          device_id: 3,
          name: 'NVIDIA RTX 3090',
          memory_total: 24576,
          memory_used: 8192,
          memory_free: 16384,
          utilization: 35 + Math.random() * 25,
          temperature: 58 + Math.random() * 20,
          power_usage: 250 + Math.random() * 70
        }
      ]
      
      lastUpdate.value = new Date()
    } catch (err: any) {
      error.value = err.message || '获取GPU信息失败'
      console.error('获取GPU信息失败:', err)
    } finally {
      loading.value = false
    }
  }

  const fetchSystemOverview = async () => {
    loading.value = true
    error.value = null
    try {
      // TODO: 替换为实际API调用
      // const response = await apiClient.get('/api/system/overview')
      // systemOverview.value = response.data.data || systemOverview.value
      
      // 模拟数据用于开发测试
      const totalMemory = gpuList.value.reduce((total, gpu) => total + gpu.memory_total, 0)
      const usedMemory = gpuList.value.reduce((total, gpu) => total + gpu.memory_used, 0)
      
      systemOverview.value = {
        total_models: 8,
        running_models: 5,
        total_gpus: gpuList.value.length,
        available_gpus: gpuList.value.filter(gpu => gpu.utilization < 80).length,
        total_memory: totalMemory,
        used_memory: usedMemory,
        free_memory: totalMemory - usedMemory,
        uptime: 86400 + Math.floor(Math.random() * 172800) // 1-3天的随机运行时间
      }
      
      lastUpdate.value = new Date()
    } catch (err: any) {
      error.value = err.message || '获取系统概览失败'
      console.error('获取系统概览失败:', err)
    } finally {
      loading.value = false
    }
  }

  const fetchAllMonitoringData = async () => {
    await Promise.all([
      fetchGpuInfo(),
      fetchSystemOverview()
    ])
  }

  const updateGpuInfo = (newGpuList: GPUInfo[]) => {
    gpuList.value = newGpuList
    lastUpdate.value = new Date()
  }

  const updateSystemOverview = (newOverview: SystemOverview) => {
    systemOverview.value = newOverview
    lastUpdate.value = new Date()
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

      // 订阅GPU指标更新
      wsClient.subscribe(SubscriptionType.GPU_METRICS)

      // 监听GPU指标更新
      wsClient.on('gpuMetricsUpdate', (data: GPUInfo[]) => {
        updateGpuInfo(data)
        console.log('实时GPU指标更新:', data)
      })

      // 监听系统概览更新
      wsClient.on('systemOverviewUpdate', (data: SystemOverview) => {
        updateSystemOverview(data)
        console.log('实时系统概览更新:', data)
      })

      // 监听系统告警
      wsClient.on('systemAlert', (data: any) => {
        console.warn('系统告警:', data)
        // 可以在这里触发通知或更新UI状态
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
      console.log('实时监控已启用')

    } catch (err: any) {
      error.value = err.message || '启用实时更新失败'
      console.error('启用实时更新失败:', err)
    }
  }

  const disableRealTimeUpdates = () => {
    if (!isRealTimeEnabled.value || !wsClient) return

    // 取消订阅
    wsClient.unsubscribe(SubscriptionType.GPU_METRICS)
    
    // 移除事件监听器
    wsClient.off('gpuMetricsUpdate')
    wsClient.off('systemOverviewUpdate')
    wsClient.off('systemAlert')

    isRealTimeEnabled.value = false
    console.log('实时监控已禁用')
  }

  // 模拟实时数据更新（用于开发测试）
  const simulateRealTimeUpdates = () => {
    if (!isRealTimeEnabled.value) return

    // 模拟GPU指标变化
    const updatedGpuList = gpuList.value.map(gpu => ({
      ...gpu,
      utilization: Math.max(0, Math.min(100, gpu.utilization + (Math.random() - 0.5) * 10)),
      temperature: Math.max(30, Math.min(90, gpu.temperature + (Math.random() - 0.5) * 5)),
      memory_used: Math.max(0, Math.min(gpu.memory_total, gpu.memory_used + (Math.random() - 0.5) * 2048)),
      power_usage: Math.max(100, Math.min(400, gpu.power_usage + (Math.random() - 0.5) * 20))
    }))

    // 更新内存空闲量
    updatedGpuList.forEach(gpu => {
      gpu.memory_free = gpu.memory_total - gpu.memory_used
    })

    updateGpuInfo(updatedGpuList)

    // 更新系统概览
    const totalMemory = updatedGpuList.reduce((total, gpu) => total + gpu.memory_total, 0)
    const usedMemory = updatedGpuList.reduce((total, gpu) => total + gpu.memory_used, 0)
    
    updateSystemOverview({
      ...systemOverview.value,
      available_gpus: updatedGpuList.filter(gpu => gpu.utilization < 80).length,
      total_memory: totalMemory,
      used_memory: usedMemory,
      free_memory: totalMemory - usedMemory,
      uptime: systemOverview.value.uptime + 5 // 增加5秒运行时间
    })
  }

  // 启动模拟数据更新定时器（仅用于开发测试）
  let simulationTimer: number | null = null
  
  const startSimulation = () => {
    if (simulationTimer) return
    
    simulationTimer = setInterval(() => {
      if (isRealTimeEnabled.value) {
        simulateRealTimeUpdates()
      }
    }, 3000) as unknown as number // 每3秒更新一次
  }

  const stopSimulation = () => {
    if (simulationTimer) {
      clearInterval(simulationTimer)
      simulationTimer = null
    }
  }

  // 格式化运行时间
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) {
      return `${days}天${hours}小时${minutes}分钟`
    } else if (hours > 0) {
      return `${hours}小时${minutes}分钟`
    } else {
      return `${minutes}分钟`
    }
  }

  // 格式化内存大小
  const formatMemorySize = (sizeInMB: number) => {
    if (sizeInMB >= 1024) {
      return `${(sizeInMB / 1024).toFixed(1)}GB`
    }
    return `${sizeInMB}MB`
  }

  // 获取GPU状态颜色
  const getGpuStatusColor = (utilization: number, temperature: number) => {
    if (temperature > 80 || utilization > 90) return 'red'
    if (temperature > 70 || utilization > 70) return 'orange'
    return 'green'
  }

  return {
    // 状态
    gpuList,
    systemOverview,
    loading,
    error,
    lastUpdate,
    isRealTimeEnabled,
    
    // 计算属性
    totalGpuMemory,
    usedGpuMemory,
    averageGpuUtilization,
    averageGpuTemperature,
    highUtilizationGpus,
    overheatedGpus,
    
    // 方法
    fetchGpuInfo,
    fetchSystemOverview,
    fetchAllMonitoringData,
    updateGpuInfo,
    updateSystemOverview,
    clearError,
    formatUptime,
    formatMemorySize,
    getGpuStatusColor,
    
    // WebSocket实时更新方法
    enableRealTimeUpdates,
    disableRealTimeUpdates,
    startSimulation,
    stopSimulation
  }
})