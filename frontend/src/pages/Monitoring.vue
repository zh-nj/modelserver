<template>
  <f7-page name="monitoring">
    <f7-navbar title="系统监控" back-link="返回">
      <f7-nav-right>
        <RealTimeStatus class="navbar-realtime-status" />
        <f7-link 
          icon-ios="f7:arrow_clockwise" 
          icon-md="material:refresh" 
          @click="refreshData"
          :class="{ 'animate-spin': loading }"
        />
      </f7-nav-right>
    </f7-navbar>
    
    <f7-page-content>
      <!-- 系统概览卡片 -->
      <f7-block-title>系统概览</f7-block-title>
      <f7-block>
        <f7-row>
          <f7-col width="50" tablet-width="25">
            <f7-card class="overview-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:cube_box" md="material:view_module" class="metric-icon" />
                  <div class="metric-value">{{ systemOverview.running_models }}/{{ systemOverview.total_models }}</div>
                  <div class="metric-label">运行模型</div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="overview-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:tv" md="material:memory" class="metric-icon" />
                  <div class="metric-value">{{ systemOverview.available_gpus }}/{{ systemOverview.total_gpus }}</div>
                  <div class="metric-label">可用GPU</div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="overview-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:speedometer" md="material:speed" class="metric-icon" />
                  <div class="metric-value">{{ averageGpuUtilization }}%</div>
                  <div class="metric-label">平均利用率</div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="overview-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:thermometer" md="material:thermostat" class="metric-icon" />
                  <div class="metric-value">{{ averageGpuTemperature }}°C</div>
                  <div class="metric-label">平均温度</div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
        </f7-row>
      </f7-block>

      <!-- GPU资源使用图表 -->
      <f7-block-title>GPU资源使用</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="chart-container">
            <canvas ref="gpuUtilizationChart" width="400" height="200"></canvas>
          </div>
        </f7-card-content>
      </f7-card>

      <!-- GPU内存使用图表 -->
      <f7-block-title>GPU内存使用</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="chart-container">
            <canvas ref="gpuMemoryChart" width="400" height="200"></canvas>
          </div>
        </f7-card-content>
      </f7-card>

      <!-- GPU详细状态列表 -->
      <f7-block-title>GPU详细状态</f7-block-title>
      <f7-list>
        <f7-list-item
          v-for="gpu in gpuList"
          :key="gpu.device_id"
          :title="`GPU ${gpu.device_id}: ${gpu.name}`"
          :after="`${gpu.utilization}%`"
          :class="getGpuStatusClass(gpu)"
        >
          <f7-icon 
            slot="media" 
            ios="f7:tv" 
            md="material:memory" 
            :color="getGpuStatusColor(gpu.utilization, gpu.temperature)"
          />
          <div slot="subtitle">
            内存: {{ formatMemorySize(gpu.memory_used) }} / {{ formatMemorySize(gpu.memory_total) }}
            ({{ Math.round((gpu.memory_used / gpu.memory_total) * 100) }}%)
          </div>
          <div slot="text">
            温度: {{ gpu.temperature }}°C | 功耗: {{ gpu.power_usage }}W
          </div>
          <div slot="after-start" class="gpu-progress-container">
            <f7-progressbar
              :progress="gpu.utilization / 100"
              :color="getGpuStatusColor(gpu.utilization, gpu.temperature)"
            />
            <div class="memory-bar">
              <div 
                class="memory-used" 
                :style="{ width: `${(gpu.memory_used / gpu.memory_total) * 100}%` }"
                :class="getMemoryBarClass(gpu.memory_used / gpu.memory_total)"
              ></div>
            </div>
          </div>
        </f7-list-item>
      </f7-list>

      <!-- 模型性能监控 -->
      <f7-block-title>模型性能监控</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="chart-container">
            <canvas ref="modelPerformanceChart" width="400" height="200"></canvas>
          </div>
        </f7-card-content>
      </f7-card>

      <!-- 系统信息 -->
      <f7-block-title>系统信息</f7-block-title>
      <f7-list>
        <f7-list-item 
          title="系统运行时间" 
          :after="formatUptime(systemOverview.uptime)" 
        >
          <f7-icon slot="media" ios="f7:clock" md="material:schedule" />
        </f7-list-item>
        <f7-list-item 
          title="总GPU内存" 
          :after="formatMemorySize(totalGpuMemory)" 
        >
          <f7-icon slot="media" ios="f7:memories" md="material:memory" />
        </f7-list-item>
        <f7-list-item 
          title="已用GPU内存" 
          :after="formatMemorySize(usedGpuMemory)" 
        >
          <f7-icon slot="media" ios="f7:chart_pie" md="material:pie_chart" />
        </f7-list-item>
        <f7-list-item 
          title="可用GPU内存" 
          :after="formatMemorySize(totalGpuMemory - usedGpuMemory)" 
        >
          <f7-icon slot="media" ios="f7:square_stack_3d_down_right" md="material:storage" />
        </f7-list-item>
      </f7-list>

      <!-- 告警信息 -->
      <f7-block-title v-if="alerts.length > 0">系统告警</f7-block-title>
      <f7-list v-if="alerts.length > 0">
        <f7-list-item
          v-for="alert in alerts"
          :key="alert.id"
          :title="alert.title"
          :subtitle="alert.message"
          :after="formatTime(alert.timestamp)"
          :class="`alert-${alert.level}`"
        >
          <f7-icon 
            slot="media" 
            :ios="getAlertIcon(alert.level)" 
            :md="getAlertIcon(alert.level)"
            :color="getAlertColor(alert.level)"
          />
        </f7-list-item>
      </f7-list>

      <!-- 最后更新时间 -->
      <f7-block v-if="lastUpdate" class="text-align-center">
        <small class="text-color-gray">
          最后更新: {{ formatTime(lastUpdate) }}
        </small>
      </f7-block>
    </f7-page-content>
  </f7-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useMonitoringStore } from '@/stores/monitoring'
import { Chart, registerables } from 'chart.js'
import type { GPUInfo } from '@/types'
import RealTimeStatus from '@/components/common/RealTimeStatus.vue'

// 注册Chart.js组件
Chart.register(...registerables)

// 使用监控数据存储
const monitoringStore = useMonitoringStore()

// 响应式数据
const loading = ref(false)
const alerts = ref([
  {
    id: '1',
    title: 'GPU温度过高',
    message: 'GPU 0温度达到85°C，建议检查散热',
    level: 'warning',
    timestamp: new Date()
  }
])

// 图表引用
const gpuUtilizationChart = ref<HTMLCanvasElement>()
const gpuMemoryChart = ref<HTMLCanvasElement>()
const modelPerformanceChart = ref<HTMLCanvasElement>()

// 图表实例
let utilizationChartInstance: Chart | null = null
let memoryChartInstance: Chart | null = null
let performanceChartInstance: Chart | null = null

// 历史数据存储
const utilizationHistory = ref<number[][]>([])
const memoryHistory = ref<number[][]>([])
const timeLabels = ref<string[]>([])

// 定时器
let refreshTimer: number | null = null

// 计算属性
const gpuList = computed(() => monitoringStore.gpuList)
const systemOverview = computed(() => monitoringStore.systemOverview)
const lastUpdate = computed(() => monitoringStore.lastUpdate)
const totalGpuMemory = computed(() => monitoringStore.totalGpuMemory)
const usedGpuMemory = computed(() => monitoringStore.usedGpuMemory)
const averageGpuUtilization = computed(() => monitoringStore.averageGpuUtilization)
const averageGpuTemperature = computed(() => monitoringStore.averageGpuTemperature)

// 格式化方法
const formatUptime = (seconds: number) => monitoringStore.formatUptime(seconds)
const formatMemorySize = (sizeInMB: number) => monitoringStore.formatMemorySize(sizeInMB)
const getGpuStatusColor = (utilization: number, temperature: number) => 
  monitoringStore.getGpuStatusColor(utilization, temperature)

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

// 获取GPU状态样式类
const getGpuStatusClass = (gpu: GPUInfo) => {
  const color = getGpuStatusColor(gpu.utilization, gpu.temperature)
  return `gpu-status-${color}`
}

// 获取内存条样式类
const getMemoryBarClass = (ratio: number) => {
  if (ratio > 0.9) return 'memory-critical'
  if (ratio > 0.7) return 'memory-warning'
  return 'memory-normal'
}

// 获取告警图标
const getAlertIcon = (level: string) => {
  switch (level) {
    case 'error': return 'f7:exclamationmark_triangle_fill'
    case 'warning': return 'f7:exclamationmark_triangle'
    case 'info': return 'f7:info_circle'
    default: return 'f7:info_circle'
  }
}

// 获取告警颜色
const getAlertColor = (level: string) => {
  switch (level) {
    case 'error': return 'red'
    case 'warning': return 'orange'
    case 'info': return 'blue'
    default: return 'gray'
  }
}

// 初始化GPU利用率图表
const initUtilizationChart = () => {
  if (!gpuUtilizationChart.value) return

  const ctx = gpuUtilizationChart.value.getContext('2d')
  if (!ctx) return

  utilizationChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeLabels.value,
      datasets: gpuList.value.map((gpu, index) => ({
        label: `GPU ${gpu.device_id}`,
        data: utilizationHistory.value[index] || [],
        borderColor: `hsl(${index * 60}, 70%, 50%)`,
        backgroundColor: `hsla(${index * 60}, 70%, 50%, 0.1)`,
        tension: 0.4,
        fill: false
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          title: {
            display: true,
            text: '利用率 (%)'
          }
        },
        x: {
          title: {
            display: true,
            text: '时间'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'GPU利用率趋势'
        },
        legend: {
          display: true,
          position: 'top'
        }
      }
    }
  })
}

// 初始化GPU内存图表
const initMemoryChart = () => {
  if (!gpuMemoryChart.value) return

  const ctx = gpuMemoryChart.value.getContext('2d')
  if (!ctx) return

  memoryChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: gpuList.value.map(gpu => `GPU ${gpu.device_id}`),
      datasets: [
        {
          label: '已用内存',
          data: gpuList.value.map(gpu => gpu.memory_used),
          backgroundColor: 'rgba(54, 162, 235, 0.8)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        },
        {
          label: '可用内存',
          data: gpuList.value.map(gpu => gpu.memory_free),
          backgroundColor: 'rgba(75, 192, 192, 0.8)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          stacked: true,
          title: {
            display: true,
            text: '内存 (MB)'
          }
        },
        x: {
          stacked: true
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'GPU内存使用情况'
        },
        legend: {
          display: true,
          position: 'top'
        }
      }
    }
  })
}

// 初始化模型性能图表
const initPerformanceChart = () => {
  if (!modelPerformanceChart.value) return

  const ctx = modelPerformanceChart.value.getContext('2d')
  if (!ctx) return

  // 模拟模型性能数据
  const modelData = [
    { name: 'llama-7b', requests: 120, avgLatency: 250 },
    { name: 'llama-13b', requests: 80, avgLatency: 450 },
    { name: 'codellama', requests: 60, avgLatency: 300 }
  ]

  performanceChartInstance = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: '模型性能',
        data: modelData.map(model => ({
          x: model.requests,
          y: model.avgLatency,
          label: model.name
        })),
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
        borderColor: 'rgba(255, 99, 132, 1)',
        pointRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: {
            display: true,
            text: '请求数/分钟'
          }
        },
        y: {
          title: {
            display: true,
            text: '平均延迟 (ms)'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: '模型性能分布'
        },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const point = context.raw
              return `${point.label}: ${point.x}请求/分钟, ${point.y}ms延迟`
            }
          }
        }
      }
    }
  })
}

// 更新图表数据
const updateCharts = () => {
  // 更新时间标签
  const now = new Date()
  const timeLabel = formatTime(now)
  timeLabels.value.push(timeLabel)
  
  // 保持最近20个数据点
  if (timeLabels.value.length > 20) {
    timeLabels.value.shift()
  }

  // 更新利用率历史数据
  gpuList.value.forEach((gpu, index) => {
    if (!utilizationHistory.value[index]) {
      utilizationHistory.value[index] = []
    }
    utilizationHistory.value[index].push(gpu.utilization)
    
    // 保持最近20个数据点
    if (utilizationHistory.value[index].length > 20) {
      utilizationHistory.value[index].shift()
    }
  })

  // 更新图表
  if (utilizationChartInstance) {
    utilizationChartInstance.data.labels = timeLabels.value
    utilizationChartInstance.data.datasets.forEach((dataset, index) => {
      dataset.data = utilizationHistory.value[index] || []
    })
    utilizationChartInstance.update('none')
  }

  if (memoryChartInstance) {
    memoryChartInstance.data.datasets[0].data = gpuList.value.map(gpu => gpu.memory_used)
    memoryChartInstance.data.datasets[1].data = gpuList.value.map(gpu => gpu.memory_free)
    memoryChartInstance.update('none')
  }
}

// 刷新数据
const refreshData = async () => {
  loading.value = true
  try {
    await monitoringStore.fetchAllMonitoringData()
    updateCharts()
  } catch (error) {
    console.error('刷新监控数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 初始化图表
const initCharts = async () => {
  await nextTick()
  initUtilizationChart()
  initMemoryChart()
  initPerformanceChart()
}

onMounted(async () => {
  // 初始加载数据
  await refreshData()
  
  // 初始化图表
  await initCharts()
  
  // 启用实时更新
  try {
    await monitoringStore.enableRealTimeUpdates()
    
    // 启动模拟数据（用于开发测试）
    monitoringStore.startSimulation()
    
    console.log('监控页面实时更新已启用')
    
    // 监听数据变化并更新图表
    monitoringStore.$subscribe(() => {
      updateCharts()
    })
  } catch (error) {
    console.error('启用实时更新失败，使用定时刷新:', error)
    // 如果WebSocket连接失败，回退到定时刷新
    refreshTimer = setInterval(refreshData, 5000)
  }
})

onUnmounted(() => {
  // 清理定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 禁用实时更新
  monitoringStore.disableRealTimeUpdates()
  monitoringStore.stopSimulation()
  
  // 销毁图表实例
  if (utilizationChartInstance) {
    utilizationChartInstance.destroy()
  }
  if (memoryChartInstance) {
    memoryChartInstance.destroy()
  }
  if (performanceChartInstance) {
    performanceChartInstance.destroy()
  }
})
</script>

<style scoped>
/* 概览卡片样式 */
.overview-card {
  margin-bottom: 8px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.metric-card {
  text-align: center;
  padding: 16px 8px;
}

.metric-icon {
  font-size: 24px;
  margin-bottom: 8px;
  color: var(--f7-theme-color);
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--f7-text-color);
  margin-bottom: 4px;
  line-height: 1.2;
}

.metric-label {
  font-size: 12px;
  color: var(--f7-text-color);
  opacity: 0.7;
  font-weight: 500;
}

/* 图表容器样式 */
.chart-container {
  position: relative;
  height: 250px;
  width: 100%;
  padding: 10px;
}

.chart-container canvas {
  max-width: 100%;
  height: auto;
}

/* GPU状态样式 */
.gpu-status-green {
  border-left: 4px solid #4cd964;
}

.gpu-status-orange {
  border-left: 4px solid #ff9500;
}

.gpu-status-red {
  border-left: 4px solid #ff3b30;
}

.gpu-progress-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 100px;
}

/* 内存条样式 */
.memory-bar {
  height: 4px;
  background-color: #e5e5e5;
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}

.memory-used {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.memory-normal {
  background-color: #4cd964;
}

.memory-warning {
  background-color: #ff9500;
}

.memory-critical {
  background-color: #ff3b30;
}

/* 告警样式 */
.alert-error {
  background-color: rgba(255, 59, 48, 0.1);
  border-left: 4px solid #ff3b30;
}

.alert-warning {
  background-color: rgba(255, 149, 0, 0.1);
  border-left: 4px solid #ff9500;
}

.alert-info {
  background-color: rgba(0, 122, 255, 0.1);
  border-left: 4px solid #007aff;
}

/* 动画效果 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 767px) {
  .metric-card {
    padding: 12px 6px;
  }
  
  .metric-value {
    font-size: 18px;
  }
  
  .metric-icon {
    font-size: 20px;
  }
  
  .chart-container {
    height: 200px;
    padding: 5px;
  }
}

@media (min-width: 768px) {
  .overview-card {
    margin-bottom: 12px;
  }
  
  .metric-card {
    padding: 20px 12px;
  }
  
  .chart-container {
    height: 300px;
    padding: 15px;
  }
}

/* 桌面端优化 */
@media (min-width: 1024px) {
  .chart-container {
    height: 350px;
    padding: 20px;
  }
  
  .gpu-progress-container {
    min-width: 120px;
  }
}

/* 深色模式适配 */
.theme-dark .overview-card {
  background-color: var(--f7-card-bg-color);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
}

.theme-dark .memory-bar {
  background-color: #333;
}

.theme-dark .chart-container {
  background-color: var(--f7-card-bg-color);
  border-radius: 8px;
}

/* 加载状态 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.theme-dark .loading-overlay {
  background-color: rgba(0, 0, 0, 0.8);
}

/* 数据为空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--f7-text-color);
  opacity: 0.6;
}

.empty-state-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state-text {
  font-size: 16px;
  margin-bottom: 8px;
}

.empty-state-subtext {
  font-size: 14px;
  opacity: 0.7;
}

/* 导航栏实时状态样式 */
.navbar-realtime-status {
  margin-right: 8px;
}

.navbar-realtime-status .realtime-status {
  padding: 4px 8px;
  font-size: 11px;
  border-radius: 6px;
}

.navbar-realtime-status .status-dot {
  width: 6px;
  height: 6px;
}

.navbar-realtime-status .status-text {
  font-size: 11px;
}

/* 响应式导航栏状态 */
@media (max-width: 767px) {
  .navbar-realtime-status .status-text {
    display: none;
  }
  
  .navbar-realtime-status .realtime-status {
    padding: 4px;
  }
}
</style>