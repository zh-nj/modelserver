/**
 * TypeScript类型定义
 */

// 模型配置类型
export interface ModelConfig {
  id: string
  name: string
  framework: FrameworkType
  model_path: string
  priority: number
  gpu_devices: number[]
  additional_parameters?: string  // 新增：附加参数
  parameters: Record<string, any>
  resource_requirements: ResourceRequirement
  health_check: HealthCheckConfig
  retry_policy: RetryPolicy
}

// 框架类型
export enum FrameworkType {
  LLAMA_CPP = 'llama_cpp',
  VLLM = 'vllm',
  DOCKER = 'docker'
}

// 模型状态
export enum ModelStatus {
  STOPPED = 'stopped',
  STARTING = 'starting',
  RUNNING = 'running',
  ERROR = 'error',
  STOPPING = 'stopping',
  PREEMPTED = 'preempted'
}

// GPU信息
export interface GPUInfo {
  device_id: number
  name: string
  memory_total: number
  memory_used: number
  memory_free: number
  utilization: number
  temperature: number
  power_usage: number
}

// 资源需求
export interface ResourceRequirement {
  gpu_memory: number
  gpu_count: number
  cpu_cores?: number
  system_memory?: number
}

// 健康检查配置
export interface HealthCheckConfig {
  enabled: boolean
  interval: number
  timeout: number
  retries: number
  endpoint?: string
}

// 重试策略
export interface RetryPolicy {
  max_retries: number
  retry_interval: number
  backoff_factor: number
}

// 模型信息
export interface ModelInfo {
  id: string
  name: string
  framework: FrameworkType
  status: ModelStatus
  priority: number
  gpu_devices: number[]
  created_at: string
  updated_at: string
  last_health_check?: string
  error_message?: string
}

// 系统概览
export interface SystemOverview {
  total_models: number
  running_models: number
  total_gpus: number
  available_gpus: number
  total_memory: number
  used_memory: number
  free_memory: number
  uptime: number
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
}

// 告警规则
export interface AlertRule {
  id: string
  name: string
  condition: string
  threshold: number
  enabled: boolean
  notification_channels: string[]
}

// 系统设置
export interface SystemSettings {
  max_concurrent_models: number
  gpu_check_interval: number
  model_health_check_interval: number
  log_level: string
  auto_restart_failed_models: boolean
  resource_allocation_strategy: string
}