<template>
  <div class="realtime-status" :class="statusClass">
    <div class="status-indicator">
      <div class="status-dot" :class="dotClass"></div>
      <span class="status-text">{{ statusText }}</span>
    </div>
    <div v-if="showDetails" class="status-details">
      <div class="detail-item">
        <span class="detail-label">连接状态:</span>
        <span class="detail-value">{{ connectionStatusText }}</span>
      </div>
      <div class="detail-item" v-if="clientId">
        <span class="detail-label">客户端ID:</span>
        <span class="detail-value">{{ clientId }}</span>
      </div>
      <div class="detail-item" v-if="lastUpdate">
        <span class="detail-label">最后更新:</span>
        <span class="detail-value">{{ formatTime(lastUpdate) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getWebSocketClient, ConnectionStatus, type WebSocketClient } from '@/services/websocket'

// Props
interface Props {
  showDetails?: boolean
  autoConnect?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: false,
  autoConnect: true
})

// 响应式数据
const connectionStatus = ref<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
const clientId = ref<string | null>(null)
const lastUpdate = ref<Date | null>(null)

// WebSocket客户端
let wsClient: WebSocketClient | null = null

// 计算属性
const statusClass = computed(() => {
  switch (connectionStatus.value) {
    case ConnectionStatus.CONNECTED:
      return 'status-connected'
    case ConnectionStatus.CONNECTING:
    case ConnectionStatus.RECONNECTING:
      return 'status-connecting'
    case ConnectionStatus.ERROR:
      return 'status-error'
    default:
      return 'status-disconnected'
  }
})

const dotClass = computed(() => {
  switch (connectionStatus.value) {
    case ConnectionStatus.CONNECTED:
      return 'dot-connected'
    case ConnectionStatus.CONNECTING:
    case ConnectionStatus.RECONNECTING:
      return 'dot-connecting'
    case ConnectionStatus.ERROR:
      return 'dot-error'
    default:
      return 'dot-disconnected'
  }
})

const statusText = computed(() => {
  switch (connectionStatus.value) {
    case ConnectionStatus.CONNECTED:
      return '实时连接'
    case ConnectionStatus.CONNECTING:
      return '连接中...'
    case ConnectionStatus.RECONNECTING:
      return '重连中...'
    case ConnectionStatus.ERROR:
      return '连接错误'
    default:
      return '未连接'
  }
})

const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case ConnectionStatus.CONNECTED:
      return '已连接'
    case ConnectionStatus.CONNECTING:
      return '连接中'
    case ConnectionStatus.RECONNECTING:
      return '重新连接中'
    case ConnectionStatus.ERROR:
      return '连接失败'
    default:
      return '未连接'
  }
})

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

// 初始化WebSocket连接状态监听
const initWebSocketStatus = () => {
  wsClient = getWebSocketClient()
  
  // 获取当前状态
  connectionStatus.value = wsClient.getStatus()
  clientId.value = wsClient.getClientId()
  
  // 监听状态变化
  wsClient.onStatusChange((status) => {
    connectionStatus.value = status
    clientId.value = wsClient!.getClientId()
    lastUpdate.value = new Date()
  })
  
  // 监听数据更新
  wsClient.on('gpuMetricsUpdate', () => {
    lastUpdate.value = new Date()
  })
  
  wsClient.on('modelStatusUpdate', () => {
    lastUpdate.value = new Date()
  })
  
  wsClient.on('systemOverviewUpdate', () => {
    lastUpdate.value = new Date()
  })
  
  // 自动连接
  if (props.autoConnect && connectionStatus.value === ConnectionStatus.DISCONNECTED) {
    wsClient.connect().catch(error => {
      console.error('WebSocket自动连接失败:', error)
    })
  }
}

onMounted(() => {
  initWebSocketStatus()
})

onUnmounted(() => {
  if (wsClient) {
    wsClient.off('gpuMetricsUpdate')
    wsClient.off('modelStatusUpdate')
    wsClient.off('systemOverviewUpdate')
  }
})
</script>

<style scoped>
.realtime-status {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background-color: var(--f7-card-bg-color);
  border: 1px solid rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.dot-connected {
  background-color: #4cd964;
  box-shadow: 0 0 8px rgba(76, 217, 100, 0.5);
}

.dot-connecting {
  background-color: #ff9500;
  animation: pulse 1.5s ease-in-out infinite;
}

.dot-error {
  background-color: #ff3b30;
  animation: blink 1s ease-in-out infinite;
}

.dot-disconnected {
  background-color: #8e8e93;
}

.status-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--f7-text-color);
  white-space: nowrap;
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 4px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  min-width: 200px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 11px;
  color: var(--f7-text-color);
  opacity: 0.7;
}

.detail-value {
  font-size: 11px;
  font-weight: 500;
  color: var(--f7-text-color);
}

/* 状态样式 */
.status-connected {
  border-color: rgba(76, 217, 100, 0.3);
  background-color: rgba(76, 217, 100, 0.05);
}

.status-connecting {
  border-color: rgba(255, 149, 0, 0.3);
  background-color: rgba(255, 149, 0, 0.05);
}

.status-error {
  border-color: rgba(255, 59, 48, 0.3);
  background-color: rgba(255, 59, 48, 0.05);
}

.status-disconnected {
  border-color: rgba(142, 142, 147, 0.3);
  background-color: rgba(142, 142, 147, 0.05);
}

/* 动画效果 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* 深色模式适配 */
.theme-dark .realtime-status {
  background-color: var(--f7-card-bg-color);
  border-color: rgba(255, 255, 255, 0.1);
}

.theme-dark .status-details {
  border-top-color: rgba(255, 255, 255, 0.1);
}

.theme-dark .status-connected {
  border-color: rgba(76, 217, 100, 0.4);
  background-color: rgba(76, 217, 100, 0.1);
}

.theme-dark .status-connecting {
  border-color: rgba(255, 149, 0, 0.4);
  background-color: rgba(255, 149, 0, 0.1);
}

.theme-dark .status-error {
  border-color: rgba(255, 59, 48, 0.4);
  background-color: rgba(255, 59, 48, 0.1);
}

.theme-dark .status-disconnected {
  border-color: rgba(142, 142, 147, 0.4);
  background-color: rgba(142, 142, 147, 0.1);
}

/* 响应式设计 */
@media (max-width: 767px) {
  .realtime-status {
    padding: 6px 10px;
  }
  
  .status-text {
    font-size: 11px;
  }
  
  .detail-label,
  .detail-value {
    font-size: 10px;
  }
  
  .status-details {
    min-width: 150px;
  }
}

/* 紧凑模式 */
.realtime-status.compact {
  padding: 4px 8px;
  flex-direction: row;
  align-items: center;
}

.realtime-status.compact .status-details {
  display: none;
}

.realtime-status.compact .status-text {
  font-size: 11px;
}

.realtime-status.compact .status-dot {
  width: 6px;
  height: 6px;
}
</style>