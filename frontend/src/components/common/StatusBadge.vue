<template>
  <f7-badge :color="badgeColor" class="status-badge">
    <f7-icon
      v-if="showIcon"
      :ios="iconIos"
      :md="iconMd"
      size="12"
      class="status-icon"
    />
    {{ displayText }}
  </f7-badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STATUS_COLORS, MODEL_STATUS } from '@/constants'

interface Props {
  status: string
  showIcon?: boolean
  customText?: string
}

const props = withDefaults(defineProps<Props>(), {
  showIcon: true,
  customText: ''
})

// 状态颜色
const badgeColor = computed(() => {
  return STATUS_COLORS[props.status as keyof typeof STATUS_COLORS] || 'gray'
})

// 显示文本
const displayText = computed(() => {
  if (props.customText) return props.customText
  
  const statusTexts: Record<string, string> = {
    [MODEL_STATUS.RUNNING]: '运行中',
    [MODEL_STATUS.STOPPED]: '已停止',
    [MODEL_STATUS.ERROR]: '错误',
    [MODEL_STATUS.STARTING]: '启动中',
    [MODEL_STATUS.STOPPING]: '停止中',
    [MODEL_STATUS.PREEMPTED]: '被抢占'
  }
  
  return statusTexts[props.status] || props.status
})

// 图标
const iconIos = computed(() => {
  const icons: Record<string, string> = {
    [MODEL_STATUS.RUNNING]: 'f7:play_circle_fill',
    [MODEL_STATUS.STOPPED]: 'f7:stop_circle',
    [MODEL_STATUS.ERROR]: 'f7:exclamationmark_triangle_fill',
    [MODEL_STATUS.STARTING]: 'f7:arrow_clockwise',
    [MODEL_STATUS.STOPPING]: 'f7:stop_circle',
    [MODEL_STATUS.PREEMPTED]: 'f7:pause_circle'
  }
  return icons[props.status] || 'f7:circle'
})

const iconMd = computed(() => {
  const icons: Record<string, string> = {
    [MODEL_STATUS.RUNNING]: 'material:play_circle_filled',
    [MODEL_STATUS.STOPPED]: 'material:stop_circle',
    [MODEL_STATUS.ERROR]: 'material:error',
    [MODEL_STATUS.STARTING]: 'material:refresh',
    [MODEL_STATUS.STOPPING]: 'material:stop_circle',
    [MODEL_STATUS.PREEMPTED]: 'material:pause_circle'
  }
  return icons[props.status] || 'material:circle'
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
}

.status-icon {
  margin-right: 2px;
}
</style>