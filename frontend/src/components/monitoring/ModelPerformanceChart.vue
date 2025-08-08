<template>
  <div class="model-performance-chart">
    <div class="chart-header">
      <h3 class="chart-title">模型性能监控</h3>
      <div class="chart-controls">
        <div class="realtime-toggle">
          <f7-toggle 
            :checked="isRealTimeEnabled"
            @toggle:change="toggleRealTimeUpdates"
          />
          <span class="toggle-label">实时更新</span>
        </div>
        <f7-segmented>
          <f7-button 
            v-for="range in timeRanges"
            :key="range.value"
            :active="selectedTimeRange === range.value"
            @click="changeTimeRange(range.value)"
          >
            {{ range.label }}
          </f7-button>
        </f7-segmented>
      </div>
    </div>
    
    <div class="chart-container">
      <canvas ref="chartCanvas" width="400" height="300"></canvas>
    </div>
    
    <div class="performance-metrics">
      <div class="metric-grid">
        <div class="metric-item">
          <div class="metric-value">{{ totalRequests }}</div>
          <div class="metric-label">总请求数</div>
        </div>
        <div class="metric-item">
          <div class="metric-value">{{ averageLatency }}ms</div>
          <div class="metric-label">平均延迟</div>
        </div>
        <div class="metric-item">
          <div class="metric-value">{{ requestsPerSecond }}</div>
          <div class="metric-label">请求/秒</div>
        </div>
        <div class="metric-item">
          <div class="metric-value">{{ errorRate }}%</div>
          <div class="metric-label">错误率</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import { getWebSocketClient, SubscriptionType, type WebSocketClient } from '@/services/websocket'

// 注册Chart.js组件
Chart.register(...registerables)

// Props
interface Props {
  modelId?: string
  autoRefresh?: boolean
  refreshInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoRefresh: true,
  refreshInterval: 5000
})

// 响应式数据
const chartCanvas = ref<HTMLCanvasElement>()
const selectedTimeRange = ref('1h')
const totalRequests = ref(1250)
const averageLatency = ref(245)
const requestsPerSecond = ref(12.5)
const errorRate = ref(0.8)
const isRealTimeEnabled = ref(false)

// 图表实例
let chartInstance: Chart | null = null

// 定时器和WebSocket客户端
let refreshTimer: number | null = null
let wsClient: WebSocketClient | null = null

// 实时数据缓存
const realtimeDataBuffer: Array<{
  timestamp: Date
  latency: number
  throughput: number
  requests: number
  errors: number
}> = []

// 时间范围选项
const timeRanges = [
  { label: '1小时', value: '1h' },
  { label: '6小时', value: '6h' },
  { label: '24小时', value: '24h' },
  { label: '7天', value: '7d' }
]

// 模拟性能数据
const generatePerformanceData = (timeRange: string) => {
  const now = new Date()
  const dataPoints = timeRange === '1h' ? 60 : timeRange === '6h' ? 72 : timeRange === '24h' ? 96 : 168
  const interval = timeRange === '1h' ? 60000 : timeRange === '6h' ? 300000 : timeRange === '24h' ? 900000 : 3600000
  
  const labels = []
  const latencyData = []
  const throughputData = []
  
  for (let i = dataPoints; i >= 0; i--) {
    const time = new Date(now.getTime() - i * interval)
    labels.push(time.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    }))
    
    // 模拟延迟数据 (200-400ms)
    latencyData.push(200 + Math.random() * 200 + Math.sin(i * 0.1) * 50)
    
    // 模拟吞吐量数据 (5-20 requests/sec)
    throughputData.push(5 + Math.random() * 15 + Math.cos(i * 0.15) * 5)
  }
  
  return { labels, latencyData, throughputData }
}

// 初始化图表
const initChart = () => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const { labels, latencyData, throughputData } = generatePerformanceData(selectedTimeRange.value)

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '延迟 (ms)',
          data: latencyData,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          yAxisID: 'y',
          tension: 0.4,
          fill: false
        },
        {
          label: '吞吐量 (req/s)',
          data: throughputData,
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          yAxisID: 'y1',
          tension: 0.4,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: '时间'
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: '延迟 (ms)'
          },
          grid: {
            drawOnChartArea: false,
          },
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: {
            display: true,
            text: '吞吐量 (req/s)'
          },
          grid: {
            drawOnChartArea: false,
          },
        },
      },
      plugins: {
        title: {
          display: true,
          text: '模型性能趋势'
        },
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.dataset.label || ''
              const value = context.parsed.y.toFixed(2)
              const unit = label.includes('延迟') ? 'ms' : 'req/s'
              return `${label}: ${value}${unit}`
            }
          }
        }
      }
    }
  })
}

// 更新图表数据
const updateChart = () => {
  if (!chartInstance) return

  const { labels, latencyData, throughputData } = generatePerformanceData(selectedTimeRange.value)
  
  chartInstance.data.labels = labels
  chartInstance.data.datasets[0].data = latencyData
  chartInstance.data.datasets[1].data = throughputData
  chartInstance.update('none')
  
  // 更新性能指标
  totalRequests.value = Math.floor(1000 + Math.random() * 500)
  averageLatency.value = Math.floor(latencyData.reduce((a, b) => a + b, 0) / latencyData.length)
  requestsPerSecond.value = parseFloat((throughputData.reduce((a, b) => a + b, 0) / throughputData.length).toFixed(1))
  errorRate.value = parseFloat((Math.random() * 2).toFixed(1))
}

// 切换时间范围
const changeTimeRange = (range: string) => {
  selectedTimeRange.value = range
  updateChart()
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

    // 订阅GPU指标更新（用于性能监控）
    wsClient.subscribe(SubscriptionType.GPU_METRICS)

    // 监听GPU指标更新，用于计算性能数据
    wsClient.on('gpuMetricsUpdate', (data: any) => {
      handleRealTimePerformanceUpdate(data)
    })

    // 监听系统告警
    wsClient.on('systemAlert', (data: any) => {
      console.warn('性能监控收到系统告警:', data)
    })

    isRealTimeEnabled.value = true
    console.log('性能图表实时更新已启用')

    // 停止定时刷新，改用实时数据
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }

    // 启动实时数据更新
    startRealTimeDataGeneration()

  } catch (err: any) {
    console.error('启用实时更新失败:', err)
  }
}

const disableRealTimeUpdates = () => {
  if (!isRealTimeEnabled.value || !wsClient) return

  // 取消订阅
  wsClient.unsubscribe(SubscriptionType.GPU_METRICS)
  
  // 移除事件监听器
  wsClient.off('gpuMetricsUpdate')
  wsClient.off('systemAlert')

  isRealTimeEnabled.value = false
  console.log('性能图表实时更新已禁用')

  // 恢复定时刷新
  if (props.autoRefresh && !refreshTimer) {
    refreshTimer = setInterval(updateChart, props.refreshInterval)
  }
}

// 处理实时性能数据更新
const handleRealTimePerformanceUpdate = (gpuData: any) => {
  const now = new Date()
  
  // 基于GPU数据计算性能指标
  const avgUtilization = Array.isArray(gpuData) ? 
    gpuData.reduce((sum: number, gpu: any) => sum + gpu.utilization, 0) / gpuData.length : 0
  
  // 模拟基于GPU利用率的性能数据
  const latency = 150 + (avgUtilization / 100) * 200 + Math.random() * 50
  const throughput = Math.max(1, 20 - (avgUtilization / 100) * 10 + Math.random() * 5)
  const requests = Math.floor(throughput * 60) // 每分钟请求数
  const errors = Math.random() * 3 // 0-3%错误率

  // 添加到实时数据缓存
  realtimeDataBuffer.push({
    timestamp: now,
    latency,
    throughput,
    requests,
    errors
  })

  // 保持缓存大小限制
  const maxBufferSize = selectedTimeRange.value === '1h' ? 60 : 
                       selectedTimeRange.value === '6h' ? 72 : 
                       selectedTimeRange.value === '24h' ? 96 : 168
  
  if (realtimeDataBuffer.length > maxBufferSize) {
    realtimeDataBuffer.shift()
  }

  // 更新图表
  updateChartWithRealTimeData()
}

// 使用实时数据更新图表
const updateChartWithRealTimeData = () => {
  if (!chartInstance || realtimeDataBuffer.length === 0) return

  const labels = realtimeDataBuffer.map(item => 
    item.timestamp.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  )
  
  const latencyData = realtimeDataBuffer.map(item => item.latency)
  const throughputData = realtimeDataBuffer.map(item => item.throughput)

  chartInstance.data.labels = labels
  chartInstance.data.datasets[0].data = latencyData
  chartInstance.data.datasets[1].data = throughputData
  chartInstance.update('none')

  // 更新性能指标
  const latestData = realtimeDataBuffer[realtimeDataBuffer.length - 1]
  const recentData = realtimeDataBuffer.slice(-10) // 最近10个数据点

  totalRequests.value = recentData.reduce((sum, item) => sum + item.requests, 0)
  averageLatency.value = Math.floor(recentData.reduce((sum, item) => sum + item.latency, 0) / recentData.length)
  requestsPerSecond.value = parseFloat((recentData.reduce((sum, item) => sum + item.throughput, 0) / recentData.length).toFixed(1))
  errorRate.value = parseFloat((recentData.reduce((sum, item) => sum + item.errors, 0) / recentData.length).toFixed(1))
}

// 启动实时数据生成（用于演示）
const startRealTimeDataGeneration = () => {
  if (refreshTimer) return

  refreshTimer = setInterval(() => {
    if (isRealTimeEnabled.value) {
      // 模拟实时性能数据
      const mockGpuData = [
        { utilization: 60 + Math.random() * 30 },
        { utilization: 45 + Math.random() * 40 }
      ]
      handleRealTimePerformanceUpdate(mockGpuData)
    }
  }, 3000) as unknown as number // 每3秒更新一次
}

// 切换实时更新
const toggleRealTimeUpdates = (enabled: boolean) => {
  if (enabled) {
    enableRealTimeUpdates()
  } else {
    disableRealTimeUpdates()
  }
}

// 监听时间范围变化
watch(selectedTimeRange, () => {
  if (isRealTimeEnabled.value) {
    // 清空缓存，重新开始收集数据
    realtimeDataBuffer.length = 0
  } else {
    updateChart()
  }
})

onMounted(async () => {
  await nextTick()
  initChart()
  
  if (props.autoRefresh) {
    refreshTimer = setInterval(updateChart, props.refreshInterval)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>

<style scoped>
.model-performance-chart {
  background: var(--f7-card-bg-color);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--f7-text-color);
  margin: 0;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.realtime-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-label {
  font-size: 14px;
  color: var(--f7-text-color);
  white-space: nowrap;
}

.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
  margin-bottom: 16px;
}

.chart-container canvas {
  max-width: 100%;
  height: auto;
}

.performance-metrics {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding-top: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
}

.metric-item {
  text-align: center;
  padding: 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--f7-theme-color);
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--f7-text-color);
  opacity: 0.7;
}

/* 响应式设计 */
@media (max-width: 767px) {
  .chart-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .chart-title {
    text-align: center;
  }
  
  .chart-container {
    height: 250px;
  }
  
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .metric-item {
    padding: 8px;
  }
  
  .metric-value {
    font-size: 16px;
  }
}

/* 深色模式适配 */
.theme-dark .model-performance-chart {
  background-color: var(--f7-card-bg-color);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
}

.theme-dark .performance-metrics {
  border-top-color: rgba(255, 255, 255, 0.1);
}

.theme-dark .metric-item {
  background: rgba(255, 255, 255, 0.05);
}
</style>