/**
 * 监控API服务
 */
import { ApiService } from './api'
import type { GPUInfo, SystemOverview } from '@/types'

export class MonitoringApiService {
  // 获取GPU信息
  static async getGpuInfo() {
    return ApiService.get<GPUInfo[]>('/api/system/gpu-info')
  }

  // 获取系统概览
  static async getSystemOverview() {
    return ApiService.get<SystemOverview>('/api/system/overview')
  }

  // 获取系统指标
  static async getSystemMetrics(timeRange: string = '1h') {
    return ApiService.get(`/api/system/metrics?range=${timeRange}`)
  }

  // 获取GPU历史指标
  static async getGpuMetrics(deviceId: number, timeRange: string = '1h') {
    return ApiService.get(`/api/system/gpu/${deviceId}/metrics?range=${timeRange}`)
  }

  // 获取系统健康状态
  static async getSystemHealth() {
    return ApiService.get('/api/system/health')
  }

  // 获取系统日志
  static async getSystemLogs(level: string = 'INFO', lines: number = 100) {
    return ApiService.get(`/api/system/logs?level=${level}&lines=${lines}`)
  }

  // 获取告警列表
  static async getAlerts(status: string = 'active') {
    return ApiService.get(`/api/system/alerts?status=${status}`)
  }

  // 确认告警
  static async acknowledgeAlert(alertId: string) {
    return ApiService.post(`/api/system/alerts/${alertId}/acknowledge`)
  }

  // 获取性能统计
  static async getPerformanceStats(timeRange: string = '24h') {
    return ApiService.get(`/api/system/performance?range=${timeRange}`)
  }

  // 获取资源使用趋势
  static async getResourceTrends(timeRange: string = '7d') {
    return ApiService.get(`/api/system/trends?range=${timeRange}`)
  }
}