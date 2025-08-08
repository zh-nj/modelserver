<template>
  <f7-page name="settings">
    <f7-navbar title="系统设置" back-link="返回" />
    
    <f7-page-content>
      <f7-block-title>系统配置</f7-block-title>
      <f7-list>
        <f7-list-input
          v-model:value="settings.maxConcurrentModels"
          label="最大并发模型数"
          type="number"
          min="1"
          max="20"
        />
        <f7-list-input
          v-model:value="settings.gpuCheckInterval"
          label="GPU检查间隔(秒)"
          type="number"
          min="1"
          max="60"
        />
        <f7-list-input
          v-model:value="settings.modelHealthCheckInterval"
          label="模型健康检查间隔(秒)"
          type="number"
          min="10"
          max="300"
        />
      </f7-list>
      
      <f7-block-title>日志配置</f7-block-title>
      <f7-list>
        <f7-list-item title="日志级别">
          <f7-segmented slot="after">
            <f7-button
              v-for="level in logLevels"
              :key="level"
              :active="settings.logLevel === level"
              @click="settings.logLevel = level"
            >
              {{ level }}
            </f7-button>
          </f7-segmented>
        </f7-list-item>
      </f7-list>
      
      <f7-block-title>操作</f7-block-title>
      <f7-list>
        <f7-list-item
          link="#"
          title="保存配置"
          @click="saveSettings"
        >
          <f7-icon slot="media" ios="f7:checkmark" md="material:save" />
        </f7-list-item>
        <f7-list-item
          link="#"
          title="备份配置"
          @click="backupConfig"
        >
          <f7-icon slot="media" ios="f7:archivebox" md="material:backup" />
        </f7-list-item>
        <f7-list-item
          link="#"
          title="恢复配置"
          @click="restoreConfig"
        >
          <f7-icon slot="media" ios="f7:arrow_clockwise" md="material:restore" />
        </f7-list-item>
      </f7-list>
    </f7-page-content>
  </f7-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { f7 } from 'framework7-vue'

// 设置数据
const settings = ref({
  maxConcurrentModels: 10,
  gpuCheckInterval: 5,
  modelHealthCheckInterval: 30,
  logLevel: 'INFO'
})

// 日志级别选项
const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

// 保存设置
const saveSettings = async () => {
  try {
    // TODO: 调用API保存设置
    console.log('保存设置:', settings.value)
    f7.toast.create({
      text: '设置保存成功',
      closeTimeout: 2000
    }).open()
  } catch (error) {
    f7.toast.create({
      text: '设置保存失败',
      closeTimeout: 2000
    }).open()
  }
}

// 备份配置
const backupConfig = async () => {
  try {
    // TODO: 调用API备份配置
    f7.toast.create({
      text: '配置备份成功',
      closeTimeout: 2000
    }).open()
  } catch (error) {
    f7.toast.create({
      text: '配置备份失败',
      closeTimeout: 2000
    }).open()
  }
}

// 恢复配置
const restoreConfig = async () => {
  f7.dialog.confirm(
    '确定要恢复配置吗？这将覆盖当前设置。',
    '确认恢复',
    async () => {
      try {
        // TODO: 调用API恢复配置
        f7.toast.create({
          text: '配置恢复成功',
          closeTimeout: 2000
        }).open()
      } catch (error) {
        f7.toast.create({
          text: '配置恢复失败',
          closeTimeout: 2000
        }).open()
      }
    }
  )
}

// 加载设置
const loadSettings = async () => {
  // TODO: 从API加载设置
  console.log('加载设置')
}

onMounted(() => {
  loadSettings()
})
</script>