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
import { apiClient } from '@/services/api'

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
    // 映射到后端字段
    const payload = {
      max_models: settings.value.maxConcurrentModels,
      monitoring_interval: settings.value.gpuCheckInterval,
      health_check_interval: settings.value.modelHealthCheckInterval,
      log_level: settings.value.logLevel
    }
    await apiClient.put('/api/v1/system/config', payload)

    f7.toast.create({
      text: '设置保存成功，部分更改需重启服务生效',
      closeTimeout: 2000
    }).open()
  } catch (error: any) {
    f7.toast.create({
      text: `设置保存失败: ${error.message || '未知错误'}`,
      closeTimeout: 2500
    }).open()
  }
}

// 备份配置
const backupConfig = async () => {
  try {
    const res = await apiClient.post('/api/v1/system/backup')
    const backupPath = (res.data as any)?.backup_path || (res.data as any)?.data?.backup_path
    f7.toast.create({
      text: `配置备份成功${backupPath ? '：' + backupPath : ''}`,
      closeTimeout: 2000
    }).open()
  } catch (error: any) {
    f7.toast.create({
      text: `配置备份失败: ${error.message || '未知错误'}`,
      closeTimeout: 2500
    }).open()
  }
}

// 恢复配置（默认恢复最新备份）
const restoreConfig = async () => {
  f7.dialog.confirm(
    '确定要恢复最近的配置备份吗？这将覆盖当前设置。',
    '确认恢复',
    async () => {
      try {
        // 拉取备份列表，选择最新一个
        const listRes = await apiClient.get('/api/v1/system/backups')
        const backups = (listRes.data as any)?.backups || (listRes.data as any)?.data?.backups || []
        if (!backups.length) {
          f7.toast.create({ text: '未找到备份文件', closeTimeout: 2000 }).open()
          return
        }
        const latest = backups[0]
        const backupPath = latest.path || latest.file_path

        await apiClient.post('/api/v1/system/restore', { backup_path: backupPath })
        f7.toast.create({ text: '配置恢复成功，可能需要重启服务', closeTimeout: 2200 }).open()
        await loadSettings()
      } catch (error: any) {
        f7.toast.create({
          text: `配置恢复失败: ${error.message || '未知错误'}`,
          closeTimeout: 2500
        }).open()
      }
    }
  )
}

// 加载设置
const loadSettings = async () => {
  try {
    const res = await apiClient.get('/api/v1/system/config')
    const data = (res.data as any)
    const app = data?.application || data?.data?.application

    if (app) {
      settings.value.maxConcurrentModels = app.max_models ?? settings.value.maxConcurrentModels
      settings.value.gpuCheckInterval = app.monitoring_interval ?? settings.value.gpuCheckInterval
      settings.value.modelHealthCheckInterval = app.health_check_interval ?? settings.value.modelHealthCheckInterval
      settings.value.logLevel = app.log_level ?? settings.value.logLevel
    }
  } catch (error) {
    // 轻提示，不中断页面
    console.warn('加载系统配置失败:', error)
  }
}

onMounted(() => {
  loadSettings()
})
</script>