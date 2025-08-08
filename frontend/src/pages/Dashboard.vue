<template>
  <f7-page name="dashboard">
    <f7-navbar title="系统概览" back-link="返回">
      <f7-nav-right>
        <RealTimeStatus class="navbar-realtime-status" />
        <f7-link 
          icon-ios="f7:arrow_clockwise" 
          icon-md="material:refresh" 
          @click="refreshData"
          :class="{ 'animate-spin': loading }"
        />
        <f7-link icon-ios="f7:gear_alt" icon-md="material:settings" href="/settings/" />
      </f7-nav-right>
    </f7-navbar>
    
    <f7-page-content>
      <!-- 系统状态概览 -->
      <f7-block-title>系统状态</f7-block-title>
      <f7-block>
        <f7-row>
          <f7-col width="50" tablet-width="25">
            <f7-card class="status-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:cube_box" md="material:view_module" class="metric-icon" />
                  <div class="metric-value">{{ systemOverview.running_models }}/{{ systemOverview.total_models }}</div>
                  <div class="metric-label">运行模型</div>
                  <div class="metric-trend" :class="getModelTrendClass()">
                    <f7-icon :ios="getModelTrendIcon()" size="12" />
                  </div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="status-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:tv" md="material:memory" class="metric-icon" />
                  <div class="metric-value">{{ systemOverview.available_gpus }}/{{ systemOverview.total_gpus }}</div>
                  <div class="metric-label">可用GPU</div>
                  <div class="metric-trend" :class="getGpuTrendClass()">
                    <f7-icon :ios="getGpuTrendIcon()" size="12" />
                  </div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="status-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:memories" md="material:memory" class="metric-icon" />
                  <div class="metric-value">{{ formatMemorySize(systemOverview.used_memory) }}</div>
                  <div class="metric-label">已用内存</div>
                  <div class="metric-progress">
                    <f7-progressbar 
                      :progress="memoryUsageRatio" 
                      :color="getMemoryUsageColor()"
                    />
                  </div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
          <f7-col width="50" tablet-width="25">
            <f7-card class="status-card">
              <f7-card-content>
                <div class="metric-card">
                  <f7-icon ios="f7:clock" md="material:schedule" class="metric-icon" />
                  <div class="metric-value">{{ formatUptime(systemOverview.uptime) }}</div>
                  <div class="metric-label">运行时间</div>
                  <div class="metric-status healthy">
                    <f7-icon ios="f7:checkmark_circle_fill" size="12" />
                  </div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
        </f7-row>
      </f7-block>

      <!-- 系统资源概览图表 -->
      <f7-block-title>资源使用概览</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="chart-container">
            <canvas ref="resourceOverviewChart" width="400" height="200"></canvas>
          </div>
        </f7-card-content>
      </f7-card>

      <!-- GPU状态快览 -->
      <f7-block-title>GPU状态快览</f7-block-title>
      <f7-block>
        <f7-row>
          <f7-col 
            v-for="gpu in gpuList" 
            :key="gpu.device_id"
            width="50" 
            tablet-width="25"
          >
            <f7-card class="gpu-card" :class="getGpuCardClass(gpu)">
              <f7-card-content>
                <div class="gpu-info">
                  <div class="gpu-header">
                    <span class="gpu-name">GPU {{ gpu.device_id }}</span>
                    <span class="gpu-status" :class="getGpuStatusClass(gpu)">
                      {{ getGpuStatusText(gpu) }}
                    </span>
                  </div>
                  <div class="gpu-metrics">
                    <div class="gpu-metric">
                      <span class="metric-label">利用率</span>
                      <span class="metric-value">{{ gpu.utilization }}%</span>
                    </div>
                    <div class="gpu-metric">
                      <span class="metric-label">温度</span>
                      <span class="metric-value">{{ gpu.temperature }}°C</span>
                    </div>
                    <div class="gpu-metric">
                      <span class="metric-label">内存</span>
                      <span class="metric-value">{{ Math.round((gpu.memory_used / gpu.memory_total) * 100) }}%</span>
                    </div>
                  </div>
                  <div class="gpu-progress">
                    <f7-progressbar 
                      :progress="gpu.utilization / 100" 
                      :color="getGpuUtilizationColor(gpu.utilization)"
                    />
                  </div>
                </div>
              </f7-card-content>
            </f7-card>
          </f7-col>
        </f7-row>
      </f7-block>

      <!-- 模型状态概览 -->
      <f7-block-title>模型状态概览</f7-block-title>
      <f7-card>
        <f7-card-content>
          <div class="chart-container">
            <canvas ref="modelStatusChart" width="400" height="200"></canvas>
          </div>
        </f7-card-content>
      </f7-card>

      <!-- 快速操作 -->
      <f7-block-title>快速操作</f7-block-title>
      <f7-list>
        <f7-list-item
          link="/models/"
          title="模型管理"
          after="管理AI模型"
          chevron-right
        >
          <f7-icon slot="media" ios="f7:cube_box" md="material:view_module" />
        </f7-list-item>
        <f7-list-item
          link="/monitoring/"
          title="系统监控"
          after="查看详细监控"
          chevron-right
        >
          <f7-icon slot="media" ios="f7:chart_bar" md="material:monitoring" />
        </f7-list-item>
        <f7-list-item
          @click="showSystemInfo"
          title="系统信息"
          after="查看详细信息"
          chevron-right
        >
          <f7-icon slot="media" ios="f7:info_circle" md="material:info" />
        </f7-list-item>
      </f7-list>

      <!-- 系统告警 -->
      <f7-block-title v-if="alerts.length > 0">系统告警</f7-block-title>
      <f7-list v-if="alerts.length > 0">
        <f7-list-item
          v-for="alert in alerts.slice(0, 3)"
          :key="alert.id"
          :title="alert.title"
          :subtitle="alert.message"
          :after="formatTime(alert.timestamp)"
          :class="`alert-${alert.level}`"
          @click="showAlertDetail(alert)"
        >
          <f7-icon 
            slot="media" 
            :ios="getAlertIcon(alert.level)" 
            :color="getAlertColor(alert.level)"
          />
        </f7-list-item>
        <f7-list-item
          v-if="alerts.length > 3"
          link="/monitoring/"
          title="查看更多告警"
          :after="`+${alerts.length - 3}条`"
          chevron-right
        >
          <f7-icon slot="media" ios="f7:ellipsis_circle" md="material:more_horiz" />
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
import { useModelsStore } from '@/stores/models'
import { Chart, registerables } from 'chart.js'
import type { GPUInfo } from '@/types'
import { f7 } from 'framework7-vue'
import RealTimeStatus from '@/components/common/RealTimeStatus.vue'

// 注册Chart.js组件
Chart.register(...registerables)

// 使用数据存储
const monitoringStore = useMonitoringStore()
const modelsStore = useModelsStore()

// 响应式数据
const loading = ref(false)
const alerts = ref([
  {
    id: '1',
    title: 'GPU温度告警',
    message: 'GPU 0温度达到82°C，请检查散热系统',
    level: 'warning',
    timestamp: new Date()
  },
  {
    id: '2',
    title: '内存使用率高',
    message: 'GPU内存使用率超过90%，建议释放部分资源',
    level: 'warning',
    timestamp: new Date(Date.now() - 300000)
  }
])

// 图表引用
const resourceOverviewChart = ref<HTMLCanvasElement>()
const modelStatusChart = ref<HTMLCanvasElement>()

// 图表实例
let resourceChartInstance: Chart | null = null
let modelChartInstance: Chart | null = null

// 定时器
let refreshTimer: number | null = null

// 计算属性
const systemOverview = computed(() => monitoringStore.systemOverview)
const gpuList = computed(() => monitoringStore.gpuList)
const lastUpdate = computed(() => monitoringStore.lastUpdate)

const memoryUsageRatio = computed(() => {
  if (systemOverview.value.total_memory === 0) return 0
  return systemOverview.value.used_memory / systemOverview.value.total_memory
})

// 格式化方法
const formatUptime = (seconds: number) => monitoringStore.formatUptime(seconds)
const formatMemorySize = (sizeInMB: number) => monitoringStore.formatMemorySize(sizeInMB)

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

// 状态判断方法
const getModelTrendClass = () => {
  const ratio = systemOverview.value.running_models / systemOverview.value.total_models
  if (ratio > 0.8) return 'trend-up'
  if (ratio < 0.5) return 'trend-down'
  return 'trend-stable'
}

const getModelTrendIcon = () => {
  const ratio = systemOverview.value.running_models / systemOverview.value.total_models
  if (ratio > 0.8) return 'f7:arrow_up_circle_fill'
  if (ratio < 0.5) return 'f7:arrow_down_circle_fill'
  return 'f7:minus_circle_fill'
}

const getGpuTrendClass = () => {
  const ratio = systemOverview.value.available_gpus / systemOverview.value.total_gpus
  if (ratio > 0.5) return 'trend-up'
  if (ratio < 0.3) return 'trend-down'
  return 'trend-stable'
}

const getGpuTrendIcon = () => {
  const ratio = systemOverview.value.available_gpus / systemOverview.value.total_gpus
  if (ratio > 0.5) return 'f7:arrow_up_circle_fill'
  if (ratio < 0.3) return 'f7:arrow_down_circle_fill'
  return 'f7:minus_circle_fill'
}

const getMemoryUsageColor = () => {
  if (memoryUsageRatio.value > 0.9) return 'red'
  if (memoryUsageRatio.value > 0.7) return 'orange'
  return 'green'
}

const getGpuCardClass = (gpu: GPUInfo) => {
  if (gpu.temperature > 80 || gpu.utilization > 90) return 'gpu-card-critical'
  if (gpu.temperature > 70 || gpu.utilization > 70) return 'gpu-card-warning'
  return 'gpu-card-normal'
}

const getGpuStatusClass = (gpu: GPUInfo) => {
  if (gpu.temperature > 80 || gpu.utilization > 90) return 'status-critical'
  if (gpu.temperature > 70 || gpu.utilization > 70) return 'status-warning'
  return 'status-normal'
}

const getGpuStatusText = (gpu: GPUInfo) => {
  if (gpu.temperature > 80 || gpu.utilization > 90) return '异常'
  if (gpu.temperature > 70 || gpu.utilization > 70) return '警告'
  return '正常'
}

const getGpuUtilizationColor = (utilization: number) => {
  if (utilization > 90) return 'red'
  if (utilization > 70) return 'orange'
  return 'green'
}

// 告警相关方法
const getAlertIcon = (level: string) => {
  switch (level) {
    case 'error': return 'f7:exclamationmark_triangle_fill'
    case 'warning': return 'f7:exclamationmark_triangle'
    case 'info': return 'f7:info_circle'
    default: return 'f7:info_circle'
  }
}

const getAlertColor = (level: string) => {
  switch (level) {
    case 'error': return 'red'
    case 'warning': return 'orange'
    case 'info': return 'blue'
    default: return 'gray'
  }
}

// 初始化资源概览图表
const initResourceOverviewChart = () => {
  if (!resourceOverviewChart.value) return

  const ctx = resourceOverviewChart.value.getContext('2d')
  if (!ctx) return

  resourceChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['已用内存', '可用内存'],
      datasets: [{
        data: [
          systemOverview.value.used_memory,
          systemOverview.value.total_memory - systemOverview.value.used_memory
        ],
        backgroundColor: [
          'rgba(255, 99, 132, 0.8)',
          'rgba(75, 192, 192, 0.8)'
        ],
        borderColor: [
          'rgba(255, 99, 132, 1)',
          'rgba(75, 192, 192, 1)'
        ],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'GPU内存使用分布'
        },
        legend: {
          position: 'bottom'
        }
      }
    }
  })
}

// 初始化模型状态图表
const initModelStatusChart = () => {
  if (!modelStatusChart.value) return

  const ctx = modelStatusChart.value.getContext('2d')
  if (!ctx) return

  // 模拟模型状态数据
  const modelStatusData = {
    running: systemOverview.value.running_models,
    stopped: systemOverview.value.total_models - systemOverview.value.running_models,
    error: 0
  }

  modelChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['运行中', '已停止', '错误'],
      datasets: [{
        label: '模型数量',
        data: [modelStatusData.running, modelStatusData.stopped, modelStatusData.error],
        backgroundColor: [
          'rgba(75, 192, 192, 0.8)',
          'rgba(201, 203, 207, 0.8)',
          'rgba(255, 99, 132, 0.8)'
        ],
        borderColor: [
          'rgba(75, 192, 192, 1)',
          'rgba(201, 203, 207, 1)',
          'rgba(255, 99, 132, 1)'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: '模型状态分布'
        },
        legend: {
          display: false
        }
      }
    }
  })
}

// 更新图表数据
const updateCharts = () => {
  if (resourceChartInstance) {
    resourceChartInstance.data.datasets[0].data = [
      systemOverview.value.used_memory,
      systemOverview.value.total_memory - systemOverview.value.used_memory
    ]
    resourceChartInstance.update('none')
  }

  if (modelChartInstance) {
    const modelStatusData = {
      running: systemOverview.value.running_models,
      stopped: systemOverview.value.total_models - systemOverview.value.running_models,
      error: 0
    }
    modelChartInstance.data.datasets[0].data = [
      modelStatusData.running, 
      modelStatusData.stopped, 
      modelStatusData.error
    ]
    modelChartInstance.update('none')
  }
}

// 刷新数据
const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      monitoringStore.fetchAllMonitoringData(),
      modelsStore.fetchModels()
    ])
    updateCharts()
  } catch (error) {
    console.error('刷新数据失败:', error)
    f7.toast.create({
      text: '刷新数据失败，请稍后重试',
      closeTimeout: 3000
    }).open()
  } finally {
    loading.value = false
  }
}

// 显示系统信息
const showSystemInfo = () => {
  f7.dialog.create({
    title: '系统信息',
    content: `
      <div class="system-info-dialog">
        <div class="info-item">
          <span class="info-label">系统运行时间:</span>
          <span class="info-value">${formatUptime(systemOverview.value.uptime)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">总GPU数量:</span>
          <span class="info-value">${systemOverview.value.total_gpus}</span>
        </div>
        <div class="info-item">
          <span class="info-label">可用GPU:</span>
          <span class="info-value">${systemOverview.value.available_gpus}</span>
        </div>
        <div class="info-item">
          <span class="info-label">总内存:</span>
          <span class="info-value">${formatMemorySize(systemOverview.value.total_memory)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">已用内存:</span>
          <span class="info-value">${formatMemorySize(systemOverview.value.used_memory)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">可用内存:</span>
          <span class="info-value">${formatMemorySize(systemOverview.value.free_memory)}</span>
        </div>
      </div>
    `,
    buttons: [{
      text: '确定',
      bold: true
    }]
  }).open()
}

// 显示告警详情
const showAlertDetail = (alert: any) => {
  f7.dialog.create({
    title: alert.title,
    content: `
      <div class="alert-detail-dialog">
        <div class="alert-message">${alert.message}</div>
        <div class="alert-time">时间: ${formatTime(alert.timestamp)}</div>
        <div class="alert-level">级别: ${alert.level === 'warning' ? '警告' : alert.level === 'error' ? '错误' : '信息'}</div>
      </div>
    `,
    buttons: [
      {
        text: '忽略',
        color: 'gray'
      },
      {
        text: '查看详情',
        bold: true,
        onClick: () => {
          f7.views.main.router.navigate('/monitoring/')
        }
      }
    ]
  }).open()
}

// 初始化图表
const initCharts = async () => {
  await nextTick()
  initResourceOverviewChart()
  initModelStatusChart()
}

onMounted(async () => {
  // 初始加载数据
  await refreshData()
  
  // 初始化图表
  await initCharts()
  
  // 启用实时更新
  try {
    await monitoringStore.enableRealTimeUpdates()
    await modelsStore.enableRealTimeUpdates()
    
    // 启动模拟数据（用于开发测试）
    monitoringStore.startSimulation()
    modelsStore.startModelSimulation()
    
    console.log('Dashboard实时更新已启用')
  } catch (error) {
    console.error('启用实时更新失败，使用定时刷新:', error)
    // 如果WebSocket连接失败，回退到定时刷新
    refreshTimer = setInterval(refreshData, 10000) // 10秒刷新一次
  }
  
  // 监听数据变化并更新图表
  monitoringStore.$subscribe(() => {
    updateCharts()
  })
})

onUnmounted(() => {
  // 清理定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  
  // 禁用实时更新
  monitoringStore.disableRealTimeUpdates()
  modelsStore.disableRealTimeUpdates()
  monitoringStore.stopSimulation()
  modelsStore.stopModelSimulation()
  
  // 销毁图表实例
  if (resourceChartInstance) {
    resourceChartInstance.destroy()
  }
  if (modelChartInstance) {
    modelChartInstance.destroy()
  }
})
</script>

<style scoped>
/* 状态卡片样式 */
.status-card {
  margin-bottom: 8px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.metric-card {
  text-align: center;
  padding: 16px 8px;
  position: relative;
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

.metric-trend {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.trend-up {
  background-color: rgba(76, 217, 100, 0.2);
  color: #4cd964;
}

.trend-down {
  background-color: rgba(255, 59, 48, 0.2);
  color: #ff3b30;
}

.trend-stable {
  background-color: rgba(255, 149, 0, 0.2);
  color: #ff9500;
}

.metric-progress {
  margin-top: 8px;
}

.metric-status {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-status.healthy {
  color: #4cd964;
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

/* GPU卡片样式 */
.gpu-card {
  margin-bottom: 8px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.gpu-card-normal {
  border-left: 4px solid #4cd964;
  box-shadow: 0 2px 8px rgba(76, 217, 100, 0.1);
}

.gpu-card-warning {
  border-left: 4px solid #ff9500;
  box-shadow: 0 2px 8px rgba(255, 149, 0, 0.1);
}

.gpu-card-critical {
  border-left: 4px solid #ff3b30;
  box-shadow: 0 2px 8px rgba(255, 59, 48, 0.1);
}

.gpu-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.gpu-info {
  padding: 12px;
}

.gpu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.gpu-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--f7-text-color);
}

.gpu-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.status-normal {
  background-color: rgba(76, 217, 100, 0.2);
  color: #4cd964;
}

.status-warning {
  background-color: rgba(255, 149, 0, 0.2);
  color: #ff9500;
}

.status-critical {
  background-color: rgba(255, 59, 48, 0.2);
  color: #ff3b30;
}

.gpu-metrics {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.gpu-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.gpu-metric .metric-label {
  font-size: 10px;
  color: var(--f7-text-color);
  opacity: 0.6;
  margin-bottom: 2px;
}

.gpu-metric .metric-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--f7-text-color);
}

.gpu-progress {
  margin-top: 8px;
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

/* 对话框样式 */
.system-info-dialog .info-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.system-info-dialog .info-item:last-child {
  border-bottom: none;
}

.system-info-dialog .info-label {
  font-weight: 500;
  color: var(--f7-text-color);
}

.system-info-dialog .info-value {
  font-weight: 600;
  color: var(--f7-theme-color);
}

.alert-detail-dialog {
  text-align: left;
}

.alert-detail-dialog .alert-message {
  margin-bottom: 12px;
  font-size: 16px;
  line-height: 1.4;
}

.alert-detail-dialog .alert-time,
.alert-detail-dialog .alert-level {
  font-size: 14px;
  color: var(--f7-text-color);
  opacity: 0.7;
  margin-bottom: 8px;
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
  
  .gpu-info {
    padding: 8px;
  }
  
  .gpu-metrics {
    flex-direction: column;
    gap: 4px;
  }
  
  .gpu-metric {
    flex-direction: row;
    justify-content: space-between;
  }
}

@media (min-width: 768px) {
  .status-card {
    margin-bottom: 12px;
  }
  
  .metric-card {
    padding: 20px 12px;
  }
  
  .chart-container {
    height: 300px;
    padding: 15px;
  }
  
  .gpu-info {
    padding: 16px;
  }
}

/* 桌面端优化 */
@media (min-width: 1024px) {
  .chart-container {
    height: 350px;
    padding: 20px;
  }
  
  .gpu-card {
    margin-bottom: 12px;
  }
  
  .metric-card {
    padding: 24px 16px;
  }
  
  .metric-value {
    font-size: 24px;
  }
  
  .metric-icon {
    font-size: 28px;
  }
}

/* 深色模式适配 */
.theme-dark .status-card,
.theme-dark .gpu-card {
  background-color: var(--f7-card-bg-color);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
}

.theme-dark .gpu-card-normal {
  box-shadow: 0 2px 8px rgba(76, 217, 100, 0.2);
}

.theme-dark .gpu-card-warning {
  box-shadow: 0 2px 8px rgba(255, 149, 0, 0.2);
}

.theme-dark .gpu-card-critical {
  box-shadow: 0 2px 8px rgba(255, 59, 48, 0.2);
}

.theme-dark .chart-container {
  background-color: var(--f7-card-bg-color);
  border-radius: 8px;
}

.theme-dark .system-info-dialog .info-item {
  border-bottom-color: rgba(255, 255, 255, 0.1);
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

/* 空状态样式 */
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

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 卡片悬停效果 */
.status-card:active,
.gpu-card:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

/* 进度条自定义样式 */
.f7-progressbar {
  border-radius: 4px;
  overflow: hidden;
}

.f7-progressbar-fill {
  transition: width 0.3s ease;
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