<template>
  <f7-card class="model-card">
    <f7-card-header>
      <div class="model-header">
        <div class="model-title">
          <h3>{{ model.name }}</h3>
          <StatusBadge :status="model.status" />
        </div>
        <div class="model-actions">
          <f7-button
            small
            :color="model.status === 'running' ? 'red' : 'green'"
            :disabled="isTransitioning"
            @click="toggleModel"
          >
            {{ getActionText() }}
          </f7-button>
          <f7-button small color="blue" @click="$emit('edit', model)">
            编辑
          </f7-button>
          <f7-button small color="red" @click="$emit('delete', model)">
            删除
          </f7-button>
        </div>
      </div>
    </f7-card-header>
    
    <f7-card-content>
      <div class="model-info">
        <div class="info-row">
          <span class="label">框架:</span>
          <f7-badge :color="getFrameworkColor(model.framework)">
            {{ getFrameworkName(model.framework) }}
          </f7-badge>
        </div>
        <div class="info-row">
          <span class="label">优先级:</span>
          <span class="value">{{ model.priority }}/10</span>
        </div>
        <div class="info-row">
          <span class="label">GPU设备:</span>
          <span class="value">{{ model.gpu_devices.join(', ') }}</span>
        </div>
        <div class="info-row">
          <span class="label">创建时间:</span>
          <span class="value">{{ formatDate(model.created_at) }}</span>
        </div>
        <div v-if="model.last_health_check" class="info-row">
          <span class="label">最后检查:</span>
          <span class="value">{{ formatDate(model.last_health_check) }}</span>
        </div>
        <div v-if="model.error_message" class="info-row error">
          <span class="label">错误信息:</span>
          <span class="value">{{ model.error_message }}</span>
        </div>
      </div>
    </f7-card-content>
    
    <f7-card-footer>
      <f7-link @click="$emit('detail', model)">查看详情</f7-link>
      <f7-link @click="$emit('logs', model)">查看日志</f7-link>
      <f7-link v-if="model.status === 'running'" @click="$emit('metrics', model)">
        性能指标
      </f7-link>
    </f7-card-footer>
  </f7-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ModelInfo } from '@/types'
import { ModelStatus, FrameworkType } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

interface Props {
  model: ModelInfo
}

interface Emits {
  (e: 'toggle', model: ModelInfo): void
  (e: 'edit', model: ModelInfo): void
  (e: 'delete', model: ModelInfo): void
  (e: 'detail', model: ModelInfo): void
  (e: 'logs', model: ModelInfo): void
  (e: 'metrics', model: ModelInfo): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 是否处于状态转换中
const isTransitioning = computed(() => {
  return props.model.status === ModelStatus.STARTING || 
         props.model.status === ModelStatus.STOPPING
})

// 获取操作按钮文本
const getActionText = () => {
  switch (props.model.status) {
    case ModelStatus.RUNNING:
      return '停止'
    case ModelStatus.STARTING:
      return '启动中...'
    case ModelStatus.STOPPING:
      return '停止中...'
    case ModelStatus.ERROR:
      return '重启'
    default:
      return '启动'
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

// 切换模型状态
const toggleModel = () => {
  emit('toggle', props.model)
}
</script>

<style scoped>
.model-card {
  margin-bottom: 16px;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.model-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-row.error {
  color: var(--f7-color-red);
}

.label {
  font-weight: 500;
  color: var(--f7-text-color);
}

.value {
  color: var(--f7-text-color-secondary);
}

@media (max-width: 768px) {
  .model-header {
    flex-direction: column;
    gap: 12px;
  }
  
  .model-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>