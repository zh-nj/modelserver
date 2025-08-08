<template>
  <f7-block v-if="error" class="error-message">
    <f7-card>
      <f7-card-content>
        <div class="error-content">
          <f7-icon ios="f7:exclamationmark_triangle" md="material:error" color="red" size="24" />
          <div class="error-text">
            <div class="error-title">{{ title || '错误' }}</div>
            <div class="error-description">{{ error }}</div>
          </div>
          <f7-button
            v-if="showRetry"
            small
            color="red"
            @click="$emit('retry')"
          >
            重试
          </f7-button>
        </div>
      </f7-card-content>
    </f7-card>
  </f7-block>
</template>

<script setup lang="ts">
interface Props {
  error: string | null
  title?: string
  showRetry?: boolean
}

defineProps<Props>()

defineEmits<{
  retry: []
}>()
</script>

<style scoped>
.error-message {
  margin: 10px 0;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.error-text {
  flex: 1;
}

.error-title {
  font-weight: 600;
  color: var(--f7-text-color);
  margin-bottom: 4px;
}

.error-description {
  font-size: 14px;
  color: var(--f7-text-color);
  opacity: 0.8;
  line-height: 1.4;
}
</style>