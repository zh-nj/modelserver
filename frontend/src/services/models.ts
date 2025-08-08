/**
 * 模型管理API服务
 */
import { ApiService } from './api'
import type { ModelConfig, ModelInfo } from '@/types'

export class ModelsApiService {
  // 获取模型列表
  static async getModels() {
    return ApiService.get<ModelInfo[]>('/api/models')
  }

  // 获取单个模型信息
  static async getModel(id: string) {
    return ApiService.get<ModelInfo>(`/api/models/${id}`)
  }

  // 创建模型
  static async createModel(config: ModelConfig) {
    return ApiService.post<ModelInfo>('/api/models', config)
  }

  // 更新模型配置
  static async updateModel(id: string, config: Partial<ModelConfig>) {
    return ApiService.put<ModelInfo>(`/api/models/${id}`, config)
  }

  // 删除模型
  static async deleteModel(id: string) {
    return ApiService.delete(`/api/models/${id}`)
  }

  // 启动模型
  static async startModel(id: string) {
    return ApiService.post(`/api/models/${id}/start`)
  }

  // 停止模型
  static async stopModel(id: string) {
    return ApiService.post(`/api/models/${id}/stop`)
  }

  // 重启模型
  static async restartModel(id: string) {
    return ApiService.post(`/api/models/${id}/restart`)
  }

  // 获取模型状态
  static async getModelStatus(id: string) {
    return ApiService.get(`/api/models/${id}/status`)
  }

  // 获取模型日志
  static async getModelLogs(id: string, lines: number = 100) {
    return ApiService.get(`/api/models/${id}/logs?lines=${lines}`)
  }

  // 获取模型性能指标
  static async getModelMetrics(id: string, timeRange: string = '1h') {
    return ApiService.get(`/api/models/${id}/metrics?range=${timeRange}`)
  }

  // 验证模型配置
  static async validateModelConfig(config: ModelConfig) {
    return ApiService.post('/api/models/validate', config)
  }

  // 获取支持的框架列表
  static async getSupportedFrameworks() {
    return ApiService.get('/api/models/frameworks')
  }

  // 获取模型模板
  static async getModelTemplates() {
    return ApiService.get('/api/models/templates')
  }
}