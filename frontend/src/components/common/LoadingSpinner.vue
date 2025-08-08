<template>
  <div class="loading-spinner" :class="{ 'loading-overlay': overlay }">
    <f7-preloader :size="size" :color="color" />
    <div v-if="text" class="loading-text">{{ text }}</div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  size?: number
  color?: string
  text?: string
  overlay?: boolean
}

withDefaults(defineProps<Props>(), {
  size: 42,
  color: 'blue',
  text: '',
  overlay: false
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 10000;
}

.loading-text {
  margin-top: 10px;
  font-size: 14px;
  color: var(--f7-text-color);
  text-align: center;
}
</style>