/**
 * 常量定义
 */

// API端点
export const API_ENDPOINTS = {
  MODELS: '/api/models',
  SYSTEM: '/api/system',
  MONITORING: '/api/monitoring',
  WEBSOCKET: '/ws'
} as const

// 模型状态
export const MODEL_STATUS = {
  STOPPED: 'stopped',
  STARTING: 'starting',
  RUNNING: 'running',
  ERROR: 'error',
  STOPPING: 'stopping',
  PREEMPTED: 'preempted'
} as const

// 框架类型
export const FRAMEWORK_TYPES = {
  LLAMA_CPP: 'llama_cpp',
  VLLM: 'vllm',
  DOCKER: 'docker'
} as const

// 框架显示名称
export const FRAMEWORK_NAMES = {
  [FRAMEWORK_TYPES.LLAMA_CPP]: 'llama.cpp',
  [FRAMEWORK_TYPES.VLLM]: 'vLLM',
  [FRAMEWORK_TYPES.DOCKER]: 'Docker'
} as const

// 日志级别
export const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'] as const

// 状态颜色映射
export const STATUS_COLORS = {
  [MODEL_STATUS.RUNNING]: 'green',
  [MODEL_STATUS.STOPPED]: 'gray',
  [MODEL_STATUS.ERROR]: 'red',
  [MODEL_STATUS.STARTING]: 'orange',
  [MODEL_STATUS.STOPPING]: 'orange',
  [MODEL_STATUS.PREEMPTED]: 'yellow'
} as const

// GPU阈值
export const GPU_THRESHOLDS = {
  UTILIZATION: {
    LOW: 30,
    HIGH: 80
  },
  TEMPERATURE: {
    LOW: 60,
    HIGH: 80
  },
  MEMORY: {
    LOW: 50,
    HIGH: 90
  }
} as const

// 刷新间隔（毫秒）
export const REFRESH_INTERVALS = {
  FAST: 1000,      // 1秒
  NORMAL: 5000,    // 5秒
  SLOW: 30000,     // 30秒
  VERY_SLOW: 60000 // 1分钟
} as const

// 图表配置
export const CHART_CONFIG = {
  COLORS: {
    PRIMARY: '#007aff',
    SUCCESS: '#34c759',
    WARNING: '#ff9500',
    DANGER: '#ff3b30',
    INFO: '#5ac8fa',
    SECONDARY: '#8e8e93'
  },
  GRID: {
    COLOR: '#f2f2f7',
    BORDER_COLOR: '#c7c7cc'
  }
} as const

// 分页配置
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100]
} as const

// 文件上传配置
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
  ALLOWED_TYPES: ['.json', '.yaml', '.yml', '.conf'],
  CHUNK_SIZE: 1024 * 1024 // 1MB
} as const

// WebSocket消息类型
export const WS_MESSAGE_TYPES = {
  MODEL_STATUS_UPDATE: 'model_status_update',
  GPU_METRICS_UPDATE: 'gpu_metrics_update',
  SYSTEM_ALERT: 'system_alert',
  RESOURCE_SCHEDULE: 'resource_schedule',
  HEARTBEAT: 'heartbeat'
} as const

// 本地存储键名
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_PREFERENCES: 'user_preferences',
  THEME: 'theme',
  LANGUAGE: 'language'
} as const

// 默认配置
export const DEFAULT_CONFIG = {
  MODEL: {
    PRIORITY: 5,
    HEALTH_CHECK_INTERVAL: 30,
    RETRY_MAX_ATTEMPTS: 3,
    RETRY_INTERVAL: 5
  },
  SYSTEM: {
    MAX_CONCURRENT_MODELS: 10,
    GPU_CHECK_INTERVAL: 5,
    LOG_LEVEL: 'INFO'
  }
} as const

// 验证规则
export const VALIDATION_RULES = {
  MODEL_NAME: {
    MIN_LENGTH: 1,
    MAX_LENGTH: 100,
    PATTERN: /^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$/
  },
  PRIORITY: {
    MIN: 1,
    MAX: 10
  },
  PORT: {
    MIN: 1024,
    MAX: 65535
  }
} as const

// 错误消息
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  UNAUTHORIZED: '认证失败，请重新登录',
  FORBIDDEN: '权限不足，无法访问该资源',
  NOT_FOUND: '请求的资源不存在',
  SERVER_ERROR: '服务器内部错误',
  VALIDATION_ERROR: '输入数据验证失败',
  TIMEOUT_ERROR: '请求超时，请稍后重试'
} as const

// 成功消息
export const SUCCESS_MESSAGES = {
  MODEL_CREATED: '模型创建成功',
  MODEL_UPDATED: '模型更新成功',
  MODEL_DELETED: '模型删除成功',
  MODEL_STARTED: '模型启动成功',
  MODEL_STOPPED: '模型停止成功',
  SETTINGS_SAVED: '设置保存成功',
  CONFIG_BACKED_UP: '配置备份成功',
  CONFIG_RESTORED: '配置恢复成功'
} as const