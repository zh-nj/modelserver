/**
 * 系统配置状态存储
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SystemSettings, GPUInfo, SystemOverview } from '@/types'
import { apiClient } from '@/services/api'

export const useSystemStore = defineStore('system', () => {
  // 状态
  const settings = ref<SystemSettings>({
    max_concurrent_models: 10,
    gpu_check_interval: 5,
    model_health_check_interval: 30,
    log_level: 'INFO',
    auto_restart_failed_models: true,
    resource_allocation_strategy: 'priority'
  })
  const gpuInfo = ref<GPUInfo[]>([])
  const systemOverview = ref<SystemOverview | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 操作方法
  const fetchSettings = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/api/system/settings')
      settings.value = { ...settings.value, ...response.data.data }
    } catch (err: any) {
      error.value = err.message || '获取系统设置失败'
      console.error('获取系统设置失败:', err)
    } finally {
      loading.value = false
    }
  }

  const updateSettings = async (newSettings: Partial<SystemSettings>) => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.put('/api/system/settings', newSettings)
      settings.value = { ...settings.value, ...response.data.data }
    } catch (err: any) {
      error.value = err.message || '更新系统设置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const backupConfig = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.post('/api/system/backup')
      return response.data.data
    } catch (err: any) {
      error.value = err.message || '备份配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const restoreConfig = async (backupFile?: File) => {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      if (backupFile) {
        formData.append('backup_file', backupFile)
      }
      const response = await apiClient.post('/api/system/restore', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      // 重新获取设置
      await fetchSettings()
      return response.data.data
    } catch (err: any) {
      error.value = err.message || '恢复配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchGPUInfo = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await apiClient.get('/api/system/gpu')
      gpuInfo.value = response.data.data || []
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
      const response = await apiClient.get('/api/system/overview')
      systemOverview.value = response.data.data
    } catch (err: any) {
      error.value = err.message || '获取系统概览失败'
      console.error('获取系统概览失败:', err)
    } finally {
      loading.value = false
    }
  }

  const clearError = () => {
    error.value = null
  }

  // 验证设置
  const validateSettings = (settingsToValidate: Partial<SystemSettings>) => {
    const errors: string[] = []

    if (settingsToValidate.max_concurrent_models !== undefined) {
      if (settingsToValidate.max_concurrent_models < 1 || settingsToValidate.max_concurrent_models > 50) {
        errors.push('最大并发模型数必须在1-50之间')
      }
    }

    if (settingsToValidate.gpu_check_interval !== undefined) {
      if (settingsToValidate.gpu_check_interval < 1 || settingsToValidate.gpu_check_interval > 300) {
        errors.push('GPU检查间隔必须在1-300秒之间')
      }
    }

    if (settingsToValidate.model_health_check_interval !== undefined) {
      if (settingsToValidate.model_health_check_interval < 10 || settingsToValidate.model_health_check_interval > 3600) {
        errors.push('模型健康检查间隔必须在10-3600秒之间')
      }
    }

    if (settingsToValidate.log_level !== undefined) {
      const validLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
      if (!validLevels.includes(settingsToValidate.log_level)) {
        errors.push('日志级别必须是DEBUG、INFO、WARNING或ERROR之一')
      }
    }

    return errors
  }

  return {
    // 状态
    settings,
    gpuInfo,
    systemOverview,
    loading,
    error,
    
    // 方法
    fetchSettings,
    updateSettings,
    fetchGPUInfo,
    fetchSystemOverview,
    backupConfig,
    restoreConfig,
    clearError,
    validateSettings
  }
})