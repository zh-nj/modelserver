<template>
  <f7-popup :opened="opened" @popup:closed="$emit('close')">
    <f7-page>
      <f7-navbar :title="model?.name || '模型详情'">
        <f7-nav-left>
          <f7-link @click="$emit('close')">关闭</f7-link>
        </f7-nav-left>
        <f7-nav-right>
          <f7-link @click="$emit('edit', model)">编辑</f7-link>
        </f7-nav-right>
      </f7-navbar>
      
      <f7-page-content v-if="model">
        <!-- 状态概览 -->
        <f7-block-title>状态概览</f7-block-title>
        <f7-card>
          <f7-card-content>
            <div class="status-overview">
              <div class="status-item">
                <div class="status-label">当前状态</div>
                <StatusBadge :status="model.status" />
              </div>
              <div class="status-item">
                <div class="status-label">运行时间</div>
                <div class="status-value">{{ getUptime() }}</div>
              </div>
              <div class="status-item">
                <div class="status-label">最后检查</div>
                <div class="status-value">
                  {{ model.last_health_check ? formatDate(model.last_health_check) : '未检查' }}
                </div>
              </div>
            </div>
          </f7-card-content>
        </f7-card>
        
        <!-- 基本信息 -->
        <f7-block-title>基本信息</f7-block-title>
        <f7-list>
          <f7-list-item title="模型ID" :after="model.id" />
          <f7-list-item title="模型名称" :after="model.name" />
          <f7-list-item title="推理框架">
            <f7-badge slot="after" :color="getFrameworkColor(model.framework)">
              {{ getFrameworkName(model.framework) }}
            </f7-badge>
          </f7-list-item>
          <f7-list-item title="优先级" :after="`${model.priority}/10`" />
          <f7-list-item title="GPU设备" :after="model.gpu_devices.join(', ')" />
          <f7-list-item title="创建时间" :after="formatDate(model.created_at)" />
          <f7-list-item title="更新时间" :after="formatDate(model.updated_at)" />
        </f7-list>
        
        <!-- 资源使用情况 -->
        <f7-block-title>资源使用情况</f7-block-title>
        <f7-card v-if="resourceUsage">
          <f7-card-content>
            <div class="resource-usage">
              <div class="resource-item">
                <div class="resource-label">GPU内存使用</div>
                <div class="resource-bar">
                  <f7-progressbar
                    :progress="resourceUsage.gpu_memory_usage / resourceUsage.gpu_memory_total * 100"
                    color="blue"
                  />
                  <div class="resource-text">
                    {{ Math.round(resourceUsage.gpu_memory_usage / 1024) }}GB / 
                    {{ Math.round(resourceUsage.gpu_memory_total / 1024) }}GB
                  </div>
                </div>
              </div>
              <div class="resource-item">
                <div class="resource-label">GPU利用率</div>
                <div class="resource-bar">
                  <f7-progressbar
                    :progress="resourceUsage.gpu_utilization"
                    color="green"
                  />
                  <div class="resource-text">{{ resourceUsage.gpu_utilization }}%</div>
                </div>
              </div>
              <div class="resource-item">
                <div class="resource-label">温度</div>
                <div class="resource-value">{{ resourceUsage.temperature }}°C</div>
              </div>
            </div>
          </f7-card-content>
        </f7-card>
        <f7-block v-else>
          <p>暂无资源使用数据</p>
        </f7-block>
        
        <!-- 性能指标 -->
        <f7-block-title>性能指标</f7-block-title>
        <f7-card v-if="metrics">
          <f7-card-content>
            <div class="metrics-grid">
              <div class="metric-item">
                <div class="metric-label">请求总数</div>
                <div class="metric-value">{{ metrics.total_requests }}</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">成功率</div>
                <div class="metric-value">{{ metrics.success_rate }}%</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">平均响应时间</div>
                <div class="metric-value">{{ metrics.avg_response_time }}ms</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">吞吐量</div>
                <div class="metric-value">{{ metrics.throughput }} req/s</div>
              </div>
            </div>
          </f7-card-content>
        </f7-card>
        <f7-block v-else>
          <p>暂无性能指标数据</p>
        </f7-block>
        
        <!-- 配置信息 -->
        <f7-block-title>配置信息</f7-block-title>
        <f7-accordion-item>
          <f7-accordion-toggle>
            <f7-list-item title="框架参数" />
          </f7-accordion-toggle>
          <f7-accordion-content>
            <f7-list>
              <f7-list-item
                v-for="(value, key) in model.parameters"
                :key="key"
                :title="key"
                :after="String(value)"
              />
            </f7-list>
          </f7-accordion-content>
        </f7-accordion-item>
        
        <f7-accordion-item>
          <f7-accordion-toggle>
            <f7-list-item title="资源需求" />
          </f7-accordion-toggle>
          <f7-accordion-content>
            <f7-list>
              <f7-list-item
                title="GPU内存需求"
                :after="`${model.resource_requirements.gpu_memory}MB`"
              />
              <f7-list-item
                title="GPU数量"
                :after="String(model.resource_requirements.gpu_count)"
              />
            </f7-list>
          </f7-accordion-content>
        </f7-accordion-item>
        
        <f7-accordion-item>
          <f7-accordion-toggle>
            <f7-list-item title="健康检查配置" />
          </f7-accordion-toggle>
          <f7-accordion-content>
            <f7-list>
              <f7-list-item
                title="启用状态"
                :after="model.health_check.enabled ? '开启' : '关闭'"
              />
              <f7-list-item
                title="检查间隔"
                :after="`${model.health_check.interval}秒`"
              />
              <f7-list-item
                title="超时时间"
                :after="`${model.health_check.timeout}秒`"
              />
              <f7-list-item
                title="重试次数"
                :after="String(model.health_check.retries)"
              />
            </f7-list>
          </f7-accordion-content>
        </f7-accordion-item>
        
        <!-- 错误信息 -->
        <template v-if="model.error_message">
          <f7-block-title>错误信息</f7-block-title>
          <f7-card>
            <f7-card-content>
              <div class="error-message">
                {{ model.error_message }}
              </div>
            </f7-card-content>
          </f7-card>
        </template>
        
        <!-- 操作按钮 -->
        <f7-block>
          <div class="action-buttons">
            <f7-button
              large
              :color="model.status === 'running' ? 'red' : 'green'"
              :disabled="isTransitioning"
              @click="$emit('toggle', model)"
            >
              {{ getActionText() }}
            </f7-button>
            <f7-button large color="blue" @click="$emit('restart', model)">
              重启
            </f7-button>
            <f7-button large color="orange" @click="$emit('logs', model)">
              查看日志
            </f7-button>
          </div>
        </f7-block>
      </f7-page-content>
    </f7-page>
  </f7-popup>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import type { ModelInfo } from '@/types'
import { ModelStatus, FrameworkType } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { ModelsApiService } from '@/services/models'

interface Props {
  opened: boolean
  model?: ModelInfo
}

interface Emits {
  (e: 'close'): void
  (e: 'edit', model: ModelInfo): void
  (e: 'toggle', model: ModelInfo): void
  (e: 'restart', model: ModelInfo): void
  (e: 'logs', model: ModelInfo): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 资源使用情况
const resourceUsage = ref<any>(null)

// 性能指标
const metrics = ref<any>(null)

// 定时器
let metricsTimer: NodeJS.Timeout | null = null

// 是否处于状态转换中
const isTransitioning = computed(() => {
  return props.model?.status === ModelStatus.STARTING || 
         props.model?.status === ModelStatus.STOPPING
})

// 获取操作按钮文本
const getActionText = () => {
  if (!props.model) return ''
  
  switch (props.model.status) {
    case ModelStatus.RUNNING:
      return '停止模型'
    case ModelStatus.STARTING:
      return '启动中...'
    case ModelStatus.STOPPING:
      return '停止中...'
    case ModelStatus.ERROR:
      return '重新启动'
    default:
      return '启动模型'
  }
}

// 获取框架颜色
const getFrameworkColor = (framework: FrameworkType) => {
  switch (framework) {
    case FrameworkType.LLAMA_CPP:
      return 'blue'
    case FrameworkType.VLLM:
      return 'green'
    case FrameworkType.DOCKER:
      return 'orange'
    default:
      return 'gray'
  }
}

// 获取框架名称
const getFrameworkName = (framework: FrameworkType) => {
  switch (framework) {
    case FrameworkType.LLAMA_CPP:
      return 'llama.cpp'
    case FrameworkType.VLLM:
      return 'vLLM'
    case FrameworkType.DOCKER:
      return 'Docker'
    default:
      return framework
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// 获取运行时间
const getUptime = () => {
  if (!props.model || props.model.status !== ModelStatus.RUNNING) {
    return '未运行'
  }
  
  const startTime = new Date(props.model.updated_at).getTime()
  const now = Date.now()
  const uptime = Math.floor((now - startTime) / 1000)
  
  const hours = Math.floor(uptime / 3600)
  const minutes = Math.floor((uptime % 3600) / 60)
  const seconds = uptime % 60
  
  return `${hours}小时${minutes}分${seconds}秒`
}

// 加载性能指标
const loadMetrics = async () => {
  if (!props.model) return
  
  try {
    const response = await ModelsApiService.getModelMetrics(props.model.id)
    metrics.value = response.data
    
    // 模拟资源使用数据（实际应该从API获取）
    resourceUsage.value = {
      gpu_memory_usage: 6144,
      gpu_memory_total: 8192,
      gpu_utilization: 85,
      temperature: 72
    }
  } catch (error) {
    console.error('加载性能指标失败:', error)
  }
}

// 监听模型变化
watch(() => props.model, (newModel) => {
  if (newModel && props.opened) {
    loadMetrics()
  }
})

// 监听弹窗打开状态
watch(() => props.opened, (opened) => {
  if (opened && props.model) {
    loadMetrics()
    // 每30秒刷新一次指标
    metricsTimer = setInterval(loadMetrics, 30000)
  } else {
    if (metricsTimer) {
      clearInterval(metricsTimer)
      metricsTimer = null
    }
  }
})

onUnmounted(() => {
  if (metricsTimer) {
    clearInterval(metricsTimer)
  }
})
</script>

<style scoped>
.status-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
}

.status-item {
  text-align: center;
}

.status-label {
  font-size: 12px;
  color: var(--f7-text-color-secondary);
  margin-bottom: 8px;
}

.status-value {
  font-weight: 500;
  color: var(--f7-text-color);
}

.resource-usage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.resource-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--f7-text-color);
}

.resource-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.resource-text {
  font-size: 12px;
  color: var(--f7-text-color-secondary);
  text-align: right;
}

.resource-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--f7-text-color);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-item {
  text-align: center;
  padding: 12px;
  background: var(--f7-card-bg-color);
  border-radius: 8px;
}

.metric-label {
  font-size: 12px;
  color: var(--f7-text-color-secondary);
  margin-bottom: 4px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--f7-text-color);
}

.error-message {
  color: var(--f7-color-red);
  font-family: monospace;
  font-size: 14px;
  line-height: 1.4;
  white-space: pre-wrap;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .action-buttons {
    flex-direction: row;
  }
  
  .metrics-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>